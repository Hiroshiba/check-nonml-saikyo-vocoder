"""Fetch pinned upstreams outside Git and build an offline LLSM comparator.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations
from .logging_utils import LoggedArgumentParser, configure_logging, run_cli, run_process

if __name__ == '__main__':
    configure_logging('build_llsm')

import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(argv: list[str], **kwargs):
    return run_process(argv, **kwargs)


def build(cache: Path, output: Path, cc: str = "cc") -> Path:
    cache = cache.resolve()
    output = output.resolve()
    lock = json.loads((HERE / "dependencies.lock.json").read_text())
    cache.mkdir(parents=True, exist_ok=True)
    for dep in lock["dependencies"]:
        dest = cache / dep["name"]
        if not dest.exists():
            run(["git", "clone", "--quiet", dep["url"], str(dest)])
        if not (dest / ".git").exists():
            raise RuntimeError(f"Refusing non-Git dependency directory: {dest}")
        dirty = run(["git", "-C", str(dest), "status", "--porcelain", "--untracked-files=no"], capture_output=True).stdout
        if dirty.strip():
            raise RuntimeError(f"Dependency has local changes: {dest}")
        run(["git", "-C", str(dest), "checkout", "--quiet", "--detach", dep["commit"]])
        revision = run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True).stdout.strip()
        if revision != dep["commit"]:
            raise RuntimeError(f"Dependency revision mismatch: {dep['name']}")
    names = ["container.c", "frame.c", "dsputils.c", "llsmutils.c", "layer0.c", "layer1.c", "coder.c"]
    sources = [cache / "libllsm2" / n for n in names]
    sources += [cache / "ciglet" / n for n in ("ciglet.c", "external/fftsg_h.c", "external/fast_median.c", "external/wavfile.c")]
    output.parent.mkdir(parents=True, exist_ok=True)
    argv = [cc, "-shared", "-fPIC", "-O2", "-std=c99", "-D_DEFAULT_SOURCE", "-DFP_TYPE=double",
            "-I" + str(cache), "-I" + str(cache / "libllsm2"),
            str(HERE / "llsm_shim.c"), *map(str, sources), "-lm", "-o", str(output)]
    run(argv)
    metadata = {"dependencies": lock["dependencies"], "command": argv,
                "compiler": run([cc, "--version"], capture_output=True).stdout.splitlines()[0],
                "library_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "shim_sha256": hashlib.sha256((HERE / "llsm_shim.c").read_bytes()).hexdigest()}
    output.with_suffix(".build.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return output


def main():
    p = LoggedArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, default=HERE / ".cache/llsm/source")
    p.add_argument("--output", type=Path, default=HERE / "build/libllsm_adapter.so")
    p.add_argument("--cc", default=os.environ.get("CC", "cc"))
    a = p.parse_args()
    print(build(a.cache, a.output, a.cc))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'build_llsm'))
