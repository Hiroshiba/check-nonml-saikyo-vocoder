"""公開DSP実装のビルドとMagPhaseのPython 3互換変換。"""
import ast
import difflib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from ..logging_utils import run_process
from .common import write


def build_llsm(cache):
    src, native = cache / 'src', cache / 'native'
    native.mkdir(exist_ok=True)
    run_process(['make', 'CONFIG=Release', '-j2'], cwd=src / 'ciglet')
    run_process(['make', 'install', f'PREFIX={native}'], cwd=src / 'ciglet')
    run_process(['make', 'CONFIG=Release', f'CIGLET_PREFIX={native}', '-j2'], cwd=src / 'llsm')
    wrapper = native / 'wrapper.c'
    wrapper.write_text('''#include "llsm.h"
llsm_chunk* speed_encode(float* x, int nx, float fs, float* f0, int nfrm, int l1) {
    llsm_aoptions* a = llsm_create_aoptions();
    a->thop = .005; a->maxnhar = 400; a->maxnhar_e = 5; a->npsd = 128;
    a->hm_method = LLSM_AOPTION_HMPP;
    llsm_chunk* c = llsm_analyze(a, x, nx, fs, f0, nfrm, 0);
    llsm_delete_aoptions(a);
    if (l1 && c) llsm_chunk_tolayer1(c, 2048);
    return c;
}
llsm_output* speed_decode(llsm_chunk* c, float fs, int l1) {
    llsm_soptions* s = llsm_create_soptions(fs);
    s->use_l1 = l1;
    llsm_output* o = llsm_synthesize(s, c);
    llsm_delete_soptions(s);
    return o;
}
''')
    command = ['gcc', '-shared', '-fPIC', '-fopenmp', '-Ofast', '-DFP_TYPE=float',
               '-I' + str(src / 'llsm'), str(wrapper), '-Wl,--whole-archive',
               str(src / 'llsm/build/libllsm2.a'), str(src / 'ciglet/libciglet.a'),
               '-Wl,--no-whole-archive', '-lm', '-o', str(native / 'libllsm_speed.so')]
    run_process(command)
    write(native / 'build.json', {'command': command, 'compiler': run_process(['gcc', '--version']).stdout})


class LegacyDivision(ast.NodeTransformer):
    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Div):
            return ast.copy_location(ast.Call(func=ast.Name(id='old_div', ctx=ast.Load()),
                                             args=[node.left, node.right], keywords=[]), node)
        return node


def build_magphase(cache):
    src, port = cache / 'src', cache / 'magphase-port'
    run_process(['cmake', '-S', str(src / 'reaper'), '-B', str(src / 'reaper/build'),
                 '-DCMAKE_BUILD_TYPE=Release'])
    run_process(['cmake', '--build', str(src / 'reaper/build'), '-j2'])
    # Re-copy the pinned original before conversion; never apply the port twice.
    if port.exists():
        shutil.rmtree(port)
    shutil.copytree(src / 'magphase', port, ignore=shutil.ignore_patterns('.git'))
    bins = port / 'tools/bin'
    bins.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / 'reaper/build/reaper', bins / 'reaper')
    files = subprocess.check_output(['dpkg', '-L', 'sptk'], text=True).splitlines()
    for name in files:
        path = Path(name)
        if path.is_file() and os.access(path, os.X_OK) and not (bins / path.name).exists():
            (bins / path.name).symlink_to(path)
    if not (bins / 'mcep').exists():
        raise FileNotFoundError('SPTK 3.9が必要です。Ubuntu: sudo apt-get install sptk')
    sources = sorted((port / 'src').glob('*.py'))
    original = {p.name: p.read_text() for p in sources}
    run_process([sys.executable, '-m', 'lib2to3', '-w', '-n', *map(str, sources)])
    patches = []
    for path in sources:
        text = re.sub(r'np\.(int|float|complex|bool)\b', lambda m: m[1], path.read_text())
        for window in ('hanning', 'hamming', 'blackman'):
            text = text.replace('signal.' + window, 'signal.windows.' + ('hann' if window == 'hanning' else window))
        tree = ast.fix_missing_locations(LegacyDivision().visit(ast.parse(text)))
        text = 'from past.utils import old_div\n' + ast.unparse(tree) + '\n'
        path.write_text(text)
        patches.extend(difflib.unified_diff(original[path.name].splitlines(True), text.splitlines(True),
                                           fromfile='original/' + path.name, tofile='ported/' + path.name))
    (cache / 'magphase-compat.patch').write_text(''.join(patches))
