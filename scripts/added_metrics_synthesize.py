"""固定120録音の現HNM/WORLDと既存操作を逐次保存する研究実行。"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vocoderbench import corpus, hnm, methods, world  # noqa: E402
from vocoderbench.logging_utils import configure_logging, run_cli  # noqa: E402
from vocoderbench.quality_core import environment, sha256, write_json  # noqa: E402
import numpy as np  # noqa: E402

RUN = ROOT / 'runs/added-metrics-20261014'
CONDITIONS = {
    'unedited': {}, 'pitch_minus3': {'pitch_semitones': -3},
    'pitch_plus3': {'pitch_semitones': 3}, 'gain_minus6': {'gain_db': -6},
    'gain_plus6': {'gain_db': 6},
}


def now():
    return datetime.now(timezone.utc).isoformat()


def save_audio(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.part')
    with temporary.open('wb') as stream:
        np.save(stream, x, allow_pickle=False)
    temporary.replace(path)
    return {'file_sha256': sha256(path), 'samples': len(x), 'sample_rate': 16000,
            'float64_sha256': hashlib.sha256(x.astype('<f8').tobytes()).hexdigest(),
            'float32_sha256': hashlib.sha256(x.astype('<f4').tobytes()).hexdigest(),
            'peak': float(abs(x).max()), 'over_one_fraction': float(np.mean(abs(x) > 1))}


def main():
    configure_logging('added-metrics-synthesis')
    sources = [*sorted((ROOT / 'vocoderbench').glob('*.py')), Path(__file__)]
    contract = {'schema_version': 1, 'source_commit': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in sources},
        'manifest_sha256': sha256(corpus.MANIFEST), 'conditions': CONDITIONS,
        'methods': list(methods.METHODS), 'seed': 0, 'threads': 4,
        'sample_rate': 16000, 'planned_cases': 120, 'planned_outputs': 1200,
        'environment': environment(), 'formal_base': json.loads((ROOT/'BASELINE.json').read_text()),
        'goal': '現ベースとWORLDの再合成品質と既存pitch/gain操作の追従を固定自然音声で測る。新候補や動作テストではない。'}
    path = RUN/'synthesis-contract.json'
    if path.exists() and json.loads(path.read_text()) != contract:
        raise ValueError('再開条件が保存済み契約と異なります')
    if not path.exists():
        write_json(path, contract)
        write_json(RUN/'synthesis-execution.json', {'started_at_utc': now()})
    previous = json.loads((ROOT/'experiments/2026-10-13/formal-hnm-v3-references/results/run-001/results.json').read_text())
    old = {(r['case'], r['method']): r for r in previous['resynthesis']}
    old.update({(r['case'], 'identity'): r for r in previous['calibration']})
    count = 0
    for case in corpus.load_cases():
        case_dir = RUN/'audio'/case['id']
        original = case_dir/'original.npy'
        if not original.exists():
            save_audio(original, case['x'])
        write_json(case_dir/'metadata.json', {k: v for k, v in case.items() if k not in ('x', 'f0_truth')})
        for method in methods.METHODS:
            target = case_dir/method
            target.mkdir(exist_ok=True)
            record_path = target/'synthesis.json'
            record = json.loads(record_path.read_text()) if record_path.exists() else {
                'case': case['id'], 'method': method, 'started_at_utc': now(), 'outputs': {}}
            module = hnm if method == 'hnm' else world
            try:
                representation = target/'representation.npz'
                if representation.exists():
                    params = module.load(representation)
                else:
                    started = time.perf_counter()
                    params = methods.encode(method, case['x'], case['sr'])
                    record['analysis_seconds'] = time.perf_counter()-started
                    module.save(params, representation)
                    record['representation'] = {'bytes': representation.stat().st_size,
                        'sha256': sha256(representation), 'encoding': 'native np.savez_compressed with metadata',
                        'bit_per_second': representation.stat().st_size*8/(len(case['x'])/case['sr'])}
                    write_json(record_path, record)
                for condition, controls in CONDITIONS.items():
                    wave_path = target/f'{condition}.npy'
                    saved = record['outputs'].get(condition)
                    if saved and saved.get('status') == 'measured' and wave_path.exists():
                        if sha256(wave_path) != saved['audio']['file_sha256']:
                            raise ValueError('保存済み成功音声のhashが変わりました')
                        count += 1
                        continue
                    started, cpu = time.perf_counter(), time.process_time()
                    edited = methods.edit(method, params, **controls) if controls else params
                    wave = methods.decode(method, edited)
                    data = {'status': 'measured', 'controls': controls,
                            'wall_seconds': time.perf_counter()-started,
                            'process_cpu_seconds': time.process_time()-cpu,
                            'audio': save_audio(wave_path, wave), 'finished_at_utc': now()}
                    if condition == 'unedited':
                        before = old[(case['id'], method)]
                        data['previous_output_file_matches'] = data['audio']['file_sha256'] == before['output_sha256']
                        data['previous_mos_input_float32_matches'] = data['audio']['float32_sha256'] == before['mos']['input_float32_sha256']
                        data['previous_mos'] = before['mos'] if data['previous_mos_input_float32_matches'] else None
                    record['outputs'][condition] = data
                    write_json(record_path, record)
                    count += 1
                    logging.info('正式合成 %d/1200: %s %s %s', count, case['id'], method, condition)
                record.update(status='measured', finished_at_utc=now())
            except Exception as error:
                logging.exception('正式合成失敗: %s %s', case['id'], method)
                record.update(status='failed', reason=f'{type(error).__name__}: {error}')
            write_json(record_path, record)
            write_json(RUN/'synthesis-progress.json', {'saved_outputs': count, 'planned_outputs': 1200,
                       'last_case': case['id'], 'last_method': method, 'updated_at_utc': now()})
    execution = json.loads((RUN/'synthesis-execution.json').read_text())
    execution.update(finished_at_utc=now(), saved_outputs=count, planned_outputs=1200)
    write_json(RUN/'synthesis-execution.json', execution)
    return int(count != 1200)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'added-metrics-synthesis'))
