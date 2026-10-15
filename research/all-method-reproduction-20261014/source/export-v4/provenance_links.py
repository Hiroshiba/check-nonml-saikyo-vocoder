"""既知来歴間のhash/ID結合だけを検査する。科学量を再計算しない。"""
from export_types import METHODS, fail


def equal(left, right, where):
    if left != right:
        fail(where, '保存hash/ID/条件の結合が不一致')


def input_links(docs, entries, report):
    missing = []
    counts = {'main120': 120, 'readout_train120': 120, 'asv_available100': 100, 'vctk_available16': 16}
    for study, expected in counts.items():
        key = 'inputs:' + study
        rows = docs.get(key)
        if rows is None:
            continue
        equal(len(rows), expected, key)
        equal(len({r['id'] for r in rows}), expected, key + ' unique IDs')
    main = docs.get('inputs:main120')
    if main is not None:
        equal(entries['inputs:main120']['sha256'], report['input_manifest_sha256'], 'main manifest')
        cases = {r['id']: r for r in main}
        for case, item in cases.items():
            key = 'main_input_processing:' + case
            if key not in docs:
                missing.append(key + ': 使用したexcerpt PCM hashの保存record未指定')
                continue
            record = docs[key]
            equal((record['case'], record['method'], record['condition']), (case, 'hnm', 'unedited'), key)
            raw = record['input']
            equal((raw['source_sha256'], raw['source_samples'], raw['source_sample_rate']),
                  (item['sha256'], item['samples'], item['sample_rate']), key)
            equal((raw['native_samples'], raw['native_sample_rate']), (item['samples'], item['sample_rate']), key)
            equal((raw['resampling']['up'], raw['resampling']['down'], raw['input_quantization']), (1, 1, 'none'), key)
            if 'synthesis:hnm' in entries:
                equal(record['contract_sha256'], entries['synthesis:hnm']['sha256'], key)
        for key in docs:
            if key.startswith('main_input_processing:') and key.split(':', 1)[1] not in cases:
                fail(key, '固定120にない入力PCM record')
    available = docs.get('inputs:asv_available100')
    if available is not None:
        cases = {r['metadata']['source_utterance_id']: r for r in available}
        equal(len(cases), 100, 'ASV input IDs')
        for case, item in cases.items():
            key = 'asv_input_pcm:' + case
            if key not in docs:
                missing.append(key + ': 全長PCM hashの保存record未指定')
                continue
            record = docs[key]
            equal(record['input'], item, key + ' private original input')
            equal((record['sample'], record['speaker'], record['samples'], record['sample_rate'], record['excerpt']),
                  (item['metadata']['official_rating_sample_id'], item['speaker'], item['samples'], item['sample_rate'], False), key)
        for key in docs:
            if key.startswith('asv_input_pcm:') and key.split(':', 1)[1] not in cases:
                fail(key, '補助100にない入力PCM record')
    for key, rows in [('inputs:readout_train120', docs.get('inputs:readout_train120')),
                      ('inputs:vctk_available16', docs.get('inputs:vctk_available16'))]:
        if rows is None:
            continue
        for item in rows:
            meta = item['metadata']
            equal((meta['excerpt_samples'], meta['sample_rate']), (item['samples'], item['sample_rate']), key)
            field = 'excerpt_pcm_sha256' if key.endswith('readout_train120') else 'excerpt_float64_sha256'
            if not meta.get(field):
                missing.append(key + ':' + item['id'] + ': 保存excerpt PCM hashなし')
    return missing


def crosslinks(docs, entries):
    missing = []
    contract = entries.get('input_contract', {}).get('sha256')
    for key, record in docs.items():
        if not isinstance(record, dict):
            continue
        if key.startswith('synthesis:') or key in ('mos', 'asr', 'speaker', 'derived16', 'acoustic', 'controls', 'slope', 'edit', 'latent'):
            if 'input_contract_sha256' in record and contract is not None:
                equal(record['input_contract_sha256'], contract, key + ' input contract')
    for key, field, target in [('targets', 'input_contract_sha256', 'train_input_contract'),
                               ('train_input_contract', 'inputs_sha256', 'inputs:readout_train120'),
                               ('train_input_contract', 'evaluation_inputs_sha256', 'inputs:main120'),
                               ('asv_input_contract', 'inputs_sha256', 'inputs:asv_available100'),
                               ('visqol_contract', 'input_contract_sha256', 'vctk_input_contract')]:
        if key in docs and target in entries:
            equal(docs[key][field], entries[target]['sha256'], key + ' cohort-specific contract')
    lock = docs.get('reference_lock')
    for method in METHODS:
        key = 'synthesis:' + method
        if key not in docs:
            continue
        record, prepared = docs[key], docs[key]['prepared']
        equal((record['method'], prepared['method']), (method, method), key)
        if method in ('hnm', 'world_harvest'):
            if 'world_lock' in entries:
                equal(prepared['world_lock_sha256'], entries['world_lock']['sha256'], key)
            continue
        if lock is None:
            continue
        equal(prepared['lock_sha256'], entries['reference_lock']['sha256'], key)
        for name, source in prepared['sources'].items():
            equal(source, lock['sources'][name], key + ' source revision')
        weights = lock['weights'].get(method, [])
        prepared_hashes = set(prepared['files'].values())
        for weight in weights:
            if weight['sha256'] not in prepared_hashes:
                # 配布archiveと使用展開checkpointを同一hashにしない。
                if weight['path'].endswith('.tar.gz'):
                    continue
                fail(key, 'model hashがprepared filesに結合しない')
            if 'revision' not in weight:
                missing.append(method + ':' + weight['path'] + ': model独立revision未保存。code revisionと内容SHAを区別。')
        checkpoint = record['adapter_info'].get('checkpoint_sha256')
        if checkpoint:
            values = checkpoint if isinstance(checkpoint, list) else [checkpoint]
            if not set(values) <= {w['sha256'] for w in weights}:
                fail(key, '使用checkpointが公開source lockに結合しない')
    acquisition = docs.get('acquisition_assets')
    if acquisition is not None:
        assets = {a['id']: a for a in acquisition['assets']}
        equal(len(assets), len(acquisition['assets']), 'asset IDs unique')
        for key, asset_id, field in [('mos', 'utmos_checkpoint', 'checkpoint_sha256'),
                                     ('speaker', 'ecapa', 'embedding_model_sha256')]:
            if key in docs:
                equal(docs[key][field], assets[asset_id]['sha256'], key + ' public asset')
        if 'asr' in docs:
            for name, content_hash in docs['asr']['asset_sha256'].items():
                equal(content_hash, assets['asr_' + name.replace('.', '_')]['sha256'], 'ASR asset ' + name)
        if 'quality_assets' in docs:
            for metric, asset_id, field in [('scoreq', 'scoreq', 'model_sha256'), ('speaker_ecapa', 'ecapa', 'embedding_model_sha256')]:
                equal(docs['quality_assets']['metrics'][metric][field], assets[asset_id]['sha256'], metric)
    for key, data in docs.items():
        if not key.startswith('quality_result:'):
            continue
        if 'quality_assets' in docs:
            equal(data['settings'], docs['quality_assets'], key + ' asset settings')
        for metric, row in data['metrics'].items():
            equal(row['provenance'], row['configuration']['model_provenance'], key + ':' + metric)
    if 'human_contract' in docs and 'inputs:asv_available100' in entries:
        equal(docs['human_contract']['inputs_sha256'], entries['inputs:asv_available100']['sha256'], 'ASV input manifest')
    if 'visqol_contract' in docs:
        record = docs['visqol_contract']
        for field, key in [('inputs_sha256', 'inputs:vctk_available16'), ('assets_sha256', 'visqol_assets')]:
            if key in entries:
                equal(record[field], entries[key]['sha256'], 'ViSQOL ' + key)
        if 'visqol_build' in docs:
            for asset in ('binary', 'model'):
                equal(record['backend_provenance']['assets'][asset]['sha256'], docs['visqol_build'][asset]['sha256'], 'ViSQOL ' + asset)
    if 'visqol_build' in docs and 'visqol_dependencies' in entries:
        equal(docs['visqol_build']['dependency_inventory']['sha256'], entries['visqol_dependencies']['sha256'], 'ViSQOL dependencies')
    missing.extend([
        '公開来歴は保存済みhash/settingsの転記。モデル・全波形・特徴配列・元評定CSVの取得権を付与しない。',
        'ViSQOL依存は保存済み内容manifest SHAとruntime library hash。全dependencyのgit revisionが保存されているとは主張しない。',
        '独自sourceの保存relative名と内容SHAを保持。input-contract.source_commitは入力準備commitであり全改変sourceの共通revisionではない。',
        '原音のdecoded PCM hashは元全長、main_input_processingのnative_input_float64_sha256は使用excerpt。両者を同一視しない。',
    ])
    return missing
