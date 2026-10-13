"""固定自然音声への追加品質評価。小分けの正式実行とMOS再利用証跡。"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
from vocoderbench.logging_utils import configure_logging, run_cli  # noqa: E402
from vocoderbench.quality_core import environment, sha256, write_json  # noqa: E402
from vocoderbench.quality_evidence import fingerprint  # noqa: E402
from vocoderbench.mos import (MosEvaluator, SOURCE_COMMIT, MODEL_REVISION,  # noqa: E402
    CHECKPOINT_SHA256, CONFIG_HASHES)

RUN = ROOT/'runs/added-metrics-20261014'
PRIOR = ROOT/'experiments/2026-10-13/formal-hnm-v3-references/results/run-001/results.json'
CONDITIONS = ('unedited', 'pitch_minus3', 'pitch_plus3', 'gain_minus6', 'gain_plus6')
METHODS = ('hnm', 'world_harvest')


def now():
    return datetime.now(timezone.utc).isoformat()


def label(method, condition):
    return method if condition == 'unedited' else f'{method}__{condition}'


def prepare():
    entries = json.loads((ROOT/'data/clean_speech_v1.json').read_text())['entries']
    base = json.loads((ROOT/'BASELINE.json').read_text())
    directory = RUN/'quality-inputs'
    directory.mkdir(exist_ok=True)
    asset = {'schema_version': 1, 'metrics': {
        'erb': {}, 'speaker_ecapa': {'embedding_model': str(ROOT/'.cache/ecapa/embedding_model.ckpt'),
            'embedding_model_sha256': '0575cb64845e6b9a10db9bcb74d5ac32b326b8dc90352671d345e2ee3d0126a2'},
        'scoreq': {'model': str(ROOT/'.cache/quality/fixed_nmr_telephone.onnx'), 'domain': 'natural'}}}
    model = ROOT/'.cache/quality/fixed_nmr_telephone.onnx'
    if model.exists():
        asset['metrics']['scoreq']['model_sha256'] = sha256(model)
    write_json(directory/'assets.json', asset)
    for offset in range(0, len(entries), 10):
        batch = offset//10
        selected = entries[offset:offset+10]
        for mode, conditions in [('main', ('unedited',)), ('all', CONDITIONS)]:
            cases = []
            for entry in selected:
                case_id = entry['id']
                path = RUN/'audio'/case_id
                cases.append({'id': case_id, 'kind': 'natural_speech', 'sample_rate': 16000,
                    'speaker': entry['speaker'], 'language': entry['language'], 'style': entry['style'],
                    'reference': str(path/'original.npy'),
                    'outputs': {label(m, c): str(path/m/f'{c}.npy') for m in METHODS for c in conditions}})
            write_json(directory/f'{mode}-{batch:02d}.json', {'schema_version': 1,
                'baseline': 'hnm', 'formal_base': base, 'cases': cases})


def wait_audio(manifest):
    data = json.loads(manifest.read_text())
    files = [p for c in data['cases'] for p in [c['reference'], *c['outputs'].values()]]
    while not all(Path(p).exists() for p in files):
        ended = RUN/'synthesis-execution.json'
        if ended.exists() and json.loads(ended.read_text()).get('finished_at_utc'):
            break
        time.sleep(15)


def mos_configuration():
    return {'evaluator': 'vocoderbench.mos.MosEvaluator', 'source_commit': SOURCE_COMMIT,
        'checkpoint_revision': MODEL_REVISION, 'checkpoint_sha256': CHECKPOINT_SHA256,
        'config_sha256': CONFIG_HASHES, 'source_sha256': sha256(ROOT/'vocoderbench/mos.py'),
        'fold': 0, 'extraction_seed': 20261012, 'extraction_repetitions': 1,
        'device': 'cpu', 'threads': 4, 'predict_dataset': 'bvcc', 'remove_silent_section': False,
        'input': 'native_full_length_float32', 'nnpack_enabled': False}


def mos_batch(batch):
    configure_logging('added-metrics-mos')
    manifest = RUN/f'quality-inputs/all-{batch:02d}.json'
    wait_audio(manifest)
    data = json.loads(manifest.read_text())
    output = RUN/f'mos/batch-{batch:02d}'
    output.mkdir(parents=True, exist_ok=True)
    old = json.loads(PRIOR.read_text())
    previous = {(r['case'], r['method']): r['mos'] for r in old['resynthesis']+old['calibration']}
    config = mos_configuration()
    signature = fingerprint(config)
    contract = {'configuration': config, 'configuration_sha256': signature,
                'source_script_sha256': sha256(Path(__file__)), 'manifest_sha256': sha256(manifest),
                'previous_results_sha256': sha256(PRIOR), 'environment': environment(),
                'previous_mos_provenance': old['mos_provenance']}
    path = output/'contract.json'
    if path.exists() and json.loads(path.read_text()) != contract:
        raise ValueError('MOS再開条件が変わりました')
    write_json(path, contract)
    evaluator = None
    rows, points = [], []
    for case in data['cases']:
        for method, audio in {'identity': case['reference'], **case['outputs']}.items():
            key = fingerprint([case['id'], method])
            saved = output/f'measurement-{key}.json'
            wave_path = Path(audio)
            file_hash = sha256(wave_path)
            if saved.exists():
                record = json.loads(saved.read_text())
                if record['audio_sha256'] != file_hash:
                    raise ValueError('MOS成功済み入力が変わりました')
            else:
                wave = np.load(wave_path, allow_pickle=False)
                old_mos = previous.get((case['id'], method))
                pcm_hash = hashlib.sha256(wave.astype('<f4').tobytes()).hexdigest()
                compatible = old_mos and old_mos['status'] == 'measured' and (
                    old_mos['input_float32_sha256'] == pcm_hash and old_mos['input_sample_rate'] == 16000
                    and old_mos['input_samples'] == len(wave) and old_mos['extraction_seed'] == 20261012
                    and old_mos['repetitions'] == 1 and old['mos_provenance']['checkpoint_sha256'] == CHECKPOINT_SHA256)
                record = {'case': case['id'], 'method': method, 'audio_path': audio,
                    'audio_sha256': file_hash, 'speaker': case['speaker'], 'language': case['language'],
                    'style': case['style'], 'started_at_utc': now(), 'configuration_sha256': signature}
                if compatible:
                    result = old_mos
                    record.update(origin='reused_previous_same_float32_audio',
                                  source_report=str(PRIOR.relative_to(ROOT)))
                else:
                    if evaluator is None:
                        evaluator = MosEvaluator(ROOT/'.cache/mos', repetitions=1, seed=20261012, threads=4)
                        start = time.perf_counter()
                        if not evaluator.prepare():
                            raise RuntimeError('UTMOSモデル初期化失敗')
                        write_json(output/'initialization.json', {'seconds': time.perf_counter()-start,
                            'provenance': evaluator.provenance, 'environment': environment()})
                    result = evaluator.predict(wave, 16000, language=case['language'], style=case['style'])
                    record['origin'] = 'new_inference'
                record.update(measurement=result, finished_at_utc=now())
                write_json(saved, record)
            result = record['measurement']
            side = f'quality-evidence-{key}.json'
            score = {'status': 'ok' if result['status'] == 'measured' else result['status'],
                     'value': result['value'] if result['status'] == 'measured' else None,
                     'evaluator': config['evaluator'], 'configuration_sha256': signature,
                     'configuration': config, 'unit': 'predicted MOS', 'direction': 'higher',
                     'origin': record['origin'], 'source_result': saved.name,
                     'source_result_sha256': sha256(saved), 'measurement': result}
            write_json(output/side, {'schema_version': 1, 'audio_path': audio,
                'audio_sha256': file_hash, 'case': case['id'], 'method': method,
                'scores': {'predicted_mos': score}})
            points.append({'case': case['id'], 'method': method, 'audio_path': audio,
                'audio_sha256': file_hash, 'quality_evidence': side, 'scores': {'predicted_mos': score['status']}})
            rows.append(record)
            write_json(output/'results.json', {'configuration': config, 'rows': rows})
            write_json(output/'quality-evidence-index.json', {'schema_version': 1, 'points': points})
            logging.info('MOS %d/%d %s %s %s', len(rows), len(data['cases'])*11,
                         case['id'], method, record['origin'])
    return int(any(r['measurement']['status'] != 'measured' for r in rows))


def run_stage(stage):
    configure_logging('added-metrics-quality-driver')
    process_file = RUN/f'{stage}-processes.json'
    history = json.loads(process_file.read_text()) if process_file.exists() else []
    for batch in range(12):
        if any(p['batch'] == batch and p.get('returncode') == 0 for p in history):
            continue
        manifest = RUN/f'quality-inputs/{"all" if stage in ("ecapa", "mos") else "main"}-{batch:02d}.json'
        wait_audio(manifest)
        output = RUN/f'quality/{stage}-{batch:02d}'
        if stage == 'mos':
            command = [sys.executable, str(Path(__file__)), 'mos-batch', '--batch', str(batch)]
        else:
            metrics = {'ecapa': ['speaker_ecapa'], 'erb': ['erb'], 'scoreq': ['scoreq']}[stage]
            command = [sys.executable, '-m', 'vocoderbench.quality', '--manifest', str(manifest),
                '--assets', str(RUN/'quality-inputs/assets.json'), '--metrics', *metrics,
                '--repetitions', '1', '--threads', '4', '--output', str(output)]
        logfile = RUN/f'{stage}-batch-{batch:02d}-{len(history):02d}.log'
        started = time.time()
        item = {'stage': stage, 'batch': batch, 'command': command, 'started_at_utc': now(),
                'log': str(logfile.relative_to(RUN))}
        history.append(item)
        write_json(process_file, history)
        with logfile.open('w') as stream:
            code = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                env=dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', MKL_NUM_THREADS='4',
                    HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')).returncode
        item.update(returncode=code, wall_seconds=time.time()-started, finished_at_utc=now())
        write_json(process_file, history)
        logging.info('%s batch %d/12 終了 code=%d', stage, batch+1, code)
        if code:
            return code
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'ecapa', 'erb', 'scoreq', 'mos', 'mos-batch'])
    parser.add_argument('--batch', type=int)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
        return 0
    if args.action == 'mos-batch':
        return mos_batch(args.batch)
    return run_stage(args.action)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'added-metrics-quality-driver'))
