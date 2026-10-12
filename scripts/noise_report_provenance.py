"""レポート用のMOS引用監査と実行記録。測定値・測定コードは変更しない。"""
from collections import Counter
import hashlib
import shutil

import numpy as np

from vocoderbench.benchmark_io import ROOT, read, sha, write


def inspect_mos_origin(directory, data):
    records = [(p['case']['id'], r) for p in data['parts'] for r in [p['original'], *p['rows']]]
    valid = [(c, r) for c, r in records if r.get('mos', {}).get('status') == 'measured']
    reused = [(c, r) for c, r in valid if r['mos'].get('reused_from')]
    audit_path = directory / 'mos_reuse_audit.json'
    audit = read(audit_path) if audit_path.exists() else None
    if reused and audit is None:
        raise ValueError('引用MOSには監査JSONが必要です')
    histories = {}
    provenance = read(directory / 'mos_provenance.json')
    audited = {(r['case'], r['method']): r for r in audit['application']['records']
               if r['status'] == 'reused'} if audit else {}
    if len(audited) != (audit['application']['reuse_count'] if audit else 0):
        raise ValueError('MOS監査の件数または重複が不正です')
    for case, row in reused:
        method, mos = row['method'], row['mos']
        source = mos['reused_from']
        if method not in ('identity', 'hnm'):
            raise ValueError('A〜E候補のMOSを過去値として再利用できません')
        if (case, method) not in audited or audited[case, method]['source'] != source:
            raise ValueError('MOS引用と監査台帳が一致しません')
        path = (ROOT / source['path']).resolve()
        if path not in histories:
            old = read(path)
            histories[path] = (sha(path), old, {(r['case'], r['method']): r
                                              for r in old['resynthesis'] + old['calibration']})
        source_sha, old, old_rows = histories[path]
        if source_sha != source['results_sha256']:
            raise ValueError('引用元結果のSHAが変わりました')
        if old['mos_provenance'] != provenance:
            raise ValueError('引用元と現在のMOS評価器由来が一致しません')
        if old['contract']['source_sha256']['mos.py'] != data['contract']['sources']['mos.py']:
            raise ValueError('引用元と現在のMOS実装SHAが一致しません')
        previous = old_rows[case, source['row_method']]['mos']
        wave = directory / 'waveforms' / case / (method + '.npy')
        if sha(wave) != row.get('waveform_sha256'):
            raise ValueError('引用MOSの保存波形SHAが一致しません')
        float32_sha = hashlib.sha256(np.asarray(np.load(wave, allow_pickle=False), dtype=np.float32).tobytes()).hexdigest()
        if not (float32_sha == source['input_float32_sha256'] == mos['input_float32_sha256'] == previous['input_float32_sha256']):
            raise ValueError('引用MOSの入力float32 SHAが一致しません')
        if previous['status'] != 'measured' or previous['value'] != mos['value']:
            raise ValueError('引用MOSの値または状態が一致しません')
    if set(audited) != {(c, r['method']) for c, r in reused}:
        raise ValueError('MOS引用の有効行と監査台帳に過不足があります')
    execution = []
    for path in sorted(directory.glob('parallel_mos_execution*.json')):
        item = read(path)
        execution.append({'file': path.name, 'sha256': sha(path),
                          **{k: item.get(k) for k in ('started_at', 'finished_at', 'status', 'workers', 'threads_per_worker')}})
    methods = {}
    for method in ('identity', 'hnm', 'A', 'B', 'C', 'D', 'E'):
        values = [r['mos'] for _, r in records if r['method'] == method]
        methods[method] = {'new': sum(v.get('status') == 'measured' and not v.get('reused_from') for v in values),
                           'reused': sum(v.get('status') == 'measured' and bool(v.get('reused_from')) for v in values),
                           'pending': sum(v.get('status') == 'pending' for v in values),
                           'failed_or_unavailable': sum(v.get('status') not in ('measured', 'pending') for v in values)}
    return {'planned_values': len(records), 'available_values': len(valid),
            'new_values': len(valid) - len(reused), 'reused_historical_values': len(reused),
            'new_by_method': dict(Counter(r['method'] for _, r in valid if not r['mos'].get('reused_from'))),
            'reused_by_method': dict(Counter(r['method'] for _, r in reused)),
            'cache_policy': 'float32入力・評価器全由来・mos.py SHA・元値を再照合。旧Linux引用は新Windows測定と数えない。',
            'audit_sha256': sha(audit_path) if audit else None,
            'source_results_sha256': {str(p.relative_to(ROOT)): item[0] for p, item in histories.items()},
            'execution_history': execution, 'by_method': methods}


def copy_execution_records(directory, output):
    names = {'mos_reuse_audit.json', 'mos_thread_observation.json', 'effective_mos_contract.json',
             'acoustic_contract.json', 'mos_execution.json'}
    paths = {p for p in directory.glob('parallel_mos_execution*.json')}
    paths.update(directory.glob('failed_checkpoint_*.json'))
    paths.update(directory / n for n in names if (directory / n).exists())
    copied = {}
    for path in sorted(paths):
        shutil.copyfile(path, output / path.name)
        copied[path.name] = sha(path)
    return copied


def copy_world_records(world_data, failed_directory, output):
    contract = world_data['contract']
    result = {'build_metadata': None, 'initial_failed_execution': None}
    build_path = ROOT / 'build/world-windows/build.json'
    if 'build_sha256' in contract:
        if not build_path.exists() or sha(build_path) != contract['build_sha256']:
            raise ValueError('WORLD build.jsonのSHAが測定契約と一致しません')
        if read(build_path) != contract['build']:
            raise ValueError('WORLD build.jsonの内容が契約と一致しません')
        shutil.copyfile(build_path, output / 'world_build.json')
        result['build_metadata'] = {'file': 'world_build.json', 'sha256': sha(build_path),
                                    'dll_sha256': contract['dll_sha256'],
                                    'exports_definition_sha256': contract['build']['exports_definition_sha256']}
    if failed_directory and (failed_directory / 'results.json').exists():
        failed = read(failed_directory / 'results.json')
        rows = [r for p in failed['parts'] for r in p['rows'] if r['status'] != 'measured']
        errors = Counter(r.get('error', 'unknown') for r in rows)
        copied = {}
        for name in ('results.json', 'contract.json', 'execution.json'):
            path = failed_directory / name
            if path.exists():
                target = 'world_initial_failed_' + name
                shutil.copyfile(path, output / target)
                copied[target] = sha(path)
        result['initial_failed_execution'] = {
            'failed_rows': len(rows), 'errors': dict(errors), 'copied_sha256': copied,
            'interpretation': 'DLL公開関数不足という共通原因1件が120録音へ波及。120独立不具合ではない。'
            if set(errors) == {"function 'InitializeHarvestOption' not found"} else '失敗理由はerrorsを参照'}
    write(output / 'world_execution_provenance.json', result)
    return result
