"""全8成功nativeが揃った正式VCTK batchだけを共有排他の品質queueへ渡す。"""
from __future__ import annotations

import argparse
from pathlib import Path
import time

from all_metrics_common import METHODS, ROOT, now, read
from all_metrics_vctk_inputs import VCTK_RUN
from all_metrics_vctk_run import process
from vocoderbench.quality_core import sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=VCTK_RUN / 'quality-assets.json')
    args = parser.parse_args()
    failures = []
    for batch in range(13):
        specs = read(VCTK_RUN / 'input-batches' / f'{batch:02d}.json')
        while True:
            not_ready, terminal = [], []
            for spec in specs:
                for method in METHODS:
                    path = VCTK_RUN / 'native' / method / spec['id'] / 'unedited.json'
                    state = read(path)['status'] if path.exists() else 'pending'
                    if state == 'failed' and method == 'magphase':
                        error = read(path).get('error', '')
                        if 'gen_centr_win' in error and 'could not broadcast input array' in error:
                            terminal.append({'case': spec['id'], 'method': method,
                                             'status': 'terminal_native_failure',
                                             'native_record_path': str(path), 'native_record_sha256': sha256(path),
                                             'reason': '固定MagPhaseの窓生成broadcast ValueError。窓/実装を変更せず終端失敗。',
                                             'excluded_quality_methods': list(METHODS),
                                             'quality_value': None, 'common_samples': None, 'coverages': None,
                                             'coverage_reason': '全8成功出力が揃わず共通区間未定義。成功7方式だけで長さを再決定しない。'})
                            continue
                    if state != 'measured':
                        not_ready.append({'case': spec['id'], 'method': method, 'status': state})
            write_json(VCTK_RUN / 'quality-readiness' / f'{batch:02d}.json',
                       {'checked_at_utc': now(), 'all_eight_successful': not not_ready and not terminal,
                        'all_planned_native_terminal': not not_ready, 'not_ready': not_ready,
                        'terminal_exclusions': terminal, 'planned_recordings': len(specs),
                        'native_complete_recordings': len(specs) - len({r['case'] for r in terminal + not_ready}),
                        'watcher_source_sha256': sha256(Path(__file__))})
            if not not_ready:
                break
            print(f'全8成功native待機 batch={batch:02d} 残り={len(not_ready)} at={now()}', flush=True)
            time.sleep(60)
        for offset, spec in enumerate(specs):
            expected = [VCTK_RUN / 'quality' / spec['id'] / f'{method}.json' for method in METHODS]
            if all(p.exists() and read(p)['status'] in ('measured', 'pcm16_range_exceeded', 'not_applicable',
                                                       'upstream_failed') for p in expected):
                signature = sha256(VCTK_RUN / 'quality-contract.json')
                if any(read(p)['contract_sha256'] != signature for p in expected):
                    raise ValueError('品質成功行の契約hash不一致')
                print(f'品質保存済み case={spec["id"]}', flush=True)
                continue
            command = [str(ROOT / '.venv/bin/python'), str(ROOT / 'scripts/all_metrics_vctk_quality_resume.py'),
                       '--batch', str(batch), '--case-start', str(offset), '--assets', str(args.assets.resolve())]
            code = process(f'quality-case{offset:02d}', 'all8', batch, command)
            if code:
                failures.append({'batch': batch, 'case': spec['id'], 'returncode': code})
    write_json(VCTK_RUN / 'quality-watch-completion.json',
               {'finished_at_utc': now(), 'failures': failures})
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
