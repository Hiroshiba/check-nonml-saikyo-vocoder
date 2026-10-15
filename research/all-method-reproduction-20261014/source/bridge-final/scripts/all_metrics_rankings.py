"""正式rawから全8方式の軸別順位・全18群状態・日本語HTMLを保存する。再測定しない。"""
from __future__ import annotations

import argparse
from pathlib import Path

from all_metrics_common import METHODS, ROOT, RUN, now, read
from all_metrics_final_gate import inventory
from all_metrics_rankings_acoustic import groups as acoustic_groups
from all_metrics_rankings_core import aggregate
from all_metrics_rankings_availability import availability_groups
from all_metrics_rankings_coverage import coverage, retain_group_conditional
from all_metrics_rankings_extra import asr_groups, special_groups, vctk_groups
from all_metrics_rankings_html import render
from all_metrics_rankings_inputs import (Sources, imported_groups, mos_groups, native_groups, public_audio,
                                        quality_groups, runtime_supplement)
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


def quantization_link(output, sources):
    # 別のレビュー済みpublisherが生成済みの成果だけをリンク。ここでは計算しない。
    folder = output / 'quantization-common-window'
    data = sources.get(folder / 'results.json')
    if data is None:
        return {'status': 'pending', 'note': '量子化共通窓の事後補助は未添付。元の厳格全長比較を維持。'}
    if (data.get('post_hoc') is not True or data.get('replaces_primary') is not False
            or data.get('counts_as_additional_independent_metric') is not False
            or data.get('contract_sha256') != 'dd0a439858c3a6864346712cbd3dbed05a550fd4da8c10f49706f478d948db6f'
            or len(data.get('groups', [])) != 2 or not (folder / 'index.html').is_file()):
        raise ValueError('量子化共通窓のレビュー済み公開向け成果が未完成です')
    manifest = sources.get(folder / 'artifact-manifest.json')
    if (not manifest or manifest.get('renderer_sha256') != 'cc37e923327e1c41faed36ebc365b74b196aa64e0d36a5ed587baf2bbb50a930'
            or manifest.get('scientific_values_recomputed') is not False
            or manifest.get('whole_18_study_completion_claim') is not False
            or {f['name'] for f in manifest['files']} != {'results.json', 'index.html'}):
        raise ValueError('量子化共通窓の独立レビュー済み表示sourceの証跡が不一致')
    for item in manifest['files']:
        path = folder / item['name']
        if sha256(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('量子化共通窓の成果SHA/bytesが不一致')
    if {g['condition'] for g in data['groups']} != {'quantized_float16', 'quantized_float32'}:
        raise ValueError('量子化共通窓の固定2精度が不一致')
    for group in data['groups']:
        if group['primary'].get('terminal') is not True:
            raise ValueError('量子化共通窓の全120終端が未確認です')
        if (group['primary'].get('planned_recordings_per_method') != 120
                or group['primary'].get('comparable_methods') != list(METHODS)):
            raise ValueError('量子化共通窓の全120×8主群が不一致')
        conditional = group['conditional']
        if not conditional.get('same_as_primary') and conditional.get('terminal') is not True:
            raise ValueError('量子化共通窓の固定条件付き群が未終端です')
    return {'status': 'available', 'href': 'quantization-common-window/index.html',
        'results_href': 'quantization-common-window/results.json',
        'results_sha256': sources.evidence[str(folder / 'results.json')],
        'html_sha256': sha256(folder / 'index.html'), 'family_ids': [17, 18],
        'replaces_primary': False, 'counts_as_additional_independent_metric': False}

LIMITATIONS = [
    '主LibriSpeechは凍結120録音40話者。native全長MOS、共通16kHz忠実性、全文正解55録音32話者のASRは別の比較範囲。',
    '通常の録音指標は群ごとに同じ録音→話者内平均→話者等重み。専用評定・ABXは各表の集約定義を使う。主群の共通0は0のまま。全有効値の方式別集計は無順位補助。',
    '全予定終端後の補助比較では、許容状態の有限値が1件以上ある方式を先に全て固定。共通数を増やす方式選別はしない。',
    '通常録音指標は話者復元抽出2000回、seed20261014の記述的95%区間。評定・ABXの専用区間は各表の定義を使う。HNMとの差も同じ録音・同じ話者抽出。多重比較未補正。',
    '同点は未丸め値の絶対1e-12/相対1e-9許容差を同点群先頭と比較する競技順位。区間重なりだけで同点にしない。',
    '符号付きRMS、低エネルギー区間の比率/RMS/peak、補間の線形性、共有資産量は診断値で無順位。',
    '可用性によるASV100・VCTK16の事後別群は元105/126の未完状態を変更しない。18群の独立項目数へ加算しない。',
    'VCTKは126録音7話者の独立48kHz群。原音・共通区間とも8秒以上の別補助層。元の上流失敗を時間不足へ置換しない。',
    '人間評定はASVspoof2019の105録音84対28話者。声の同一人物らしさとの一致であり、復号MOSではない。',
    'ABXは同話者/異話者×層等重み/X話者等重み/入れ子補助の6推定対象。話者グラフ条件付きnode区間。公式全コーパス順位ではない。',
    '読み出しは別40話者120録音で固定尺度とRidgeを学習。3種類の独立推定音響属性に対する話者等重みMAE。',
    '直接実測と、厳密に同一の復号入力・PCMに基づくanalytic_identity値を分けて計数。欠測・失敗・未対応はnull。',
    '表現量は宣言容器の実bytesと固定元入力秒による量。共有モデル等が別途必要。容器量順位と品質付き圧縮効率を混同しない。',
    '速度は全8とも各ライブラリのスレッド設定2・worker1の独立native工程の単回。初回正式入力を除かず、初期化・前処理・保存読込は別。区間は録音構成だけ。',
    '速度の全120録音は保存I/O条件混在の参考値として保持。batch005–011の固定70録音24話者は別の補助比較で、品質の主120録音や比較分母を置換しない。補助分析計画はbatch005開始後の採用であり、指標値・順位による対象選別ではない。',
    '喪失した旧rawや会話の途中集計を復元値へ使わない。原音・生成波形の全長、モデル、元人間評定CSVは公開対象外。許諾済み短例だけを帰属付きで公開する。',
]


def length_evidence(specs, sources):
    rows = []
    for batch in range(12):
        manifest = sources.get(RUN / f'quality-inputs/common-{batch:02d}.json')
        for spec in specs[10 * batch:10 * (batch + 1)]:
            path = RUN / 'derived16' / manifest['snapshot'] / spec['id'] / 'derivation.json' if manifest else None
            raw = sources.get(path) if path else None
            raw = raw or {'status': 'pending_derivation'}
            rows.append({'case': spec['id'], 'speaker': spec['speaker'], 'status': raw['status'],
                'common_seconds': raw.get('common_seconds'), 'coverage': raw.get('coverage'),
                'omitted_tail_samples_16k': raw.get('omitted_tail_samples'),
                'full_length_seconds': {method: cell['derived']['seconds']
                    for method, cell in raw.get('full_length_derivations', {}).items()},
                'source_result': str(path) if path else None})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='上書きしない新しい集約保存先')
    parser.add_argument('--allow-incomplete', action='store_true', help='正式測定の途中rawを未完了と明記して集計')
    parser.add_argument('--audio-manifest', type=Path, help='既存許諾2録音の先頭2秒公開例だけの一覧')
    args = parser.parse_args()
    if any((args.output / filename).exists() for filename in ('results.json', 'index.html', 'artifact-manifest.json')):
        raise FileExistsError('過去集計は上書きしません。新しいoutputを指定してください')
    sources = Sources()
    specs = sources.get(RUN / 'inputs.json')
    if (not isinstance(specs, list) or len(specs) != 120 or len({s['id'] for s in specs}) != 120
            or len({s['speaker'] for s in specs}) != 40):
        raise ValueError('正式固定120録音40話者の完全manifestが必要です')
    speed, lengths = native_groups(specs, sources)
    speed_supplement, timing = runtime_supplement(specs, sources, speed)
    raw_groups = [*mos_groups(specs, sources), *quality_groups(specs, sources), *acoustic_groups(specs, sources),
                  *asr_groups(specs, sources), *vctk_groups(sources), *imported_groups(specs, sources),
                  *speed, *speed_supplement]
    groups = [aggregate(group) for group in raw_groups] + special_groups(sources)
    if len({group['id'] for group in groups}) != len(groups):
        raise ValueError('指標群IDの重複')
    gate = inventory(specs, sources, groups)
    if not gate['terminal'] and not args.allow_incomplete:
        raise ValueError(f'予定recordが未完了: {gate["unresolved_records"]}件。途中報告には--allow-incompleteを明示')
    for group in groups:
        retain_group_conditional(group)
    # 元105/126群とfinal_gateは先に確定し、別群の完了で置換しない。
    groups.extend(availability_groups(sources))
    if len({group['id'] for group in groups}) != len(groups):
        raise ValueError('別群を含む指標群IDの重複')
    samples = public_audio(read(args.audio_manifest), args.output) if args.audio_manifest else []
    if gate['terminal'] and not any(sample.get('publication_status') == 'available' for sample in samples):
        raise ValueError('最終HTMLには許可済み2秒音声例manifestが必要です')
    derived = length_evidence(specs, sources)
    initializations = [{'path': str(path), 'record': sources.get(path)}
                       for path in sorted((RUN / 'synthesis-initializations').glob('*.json'))]
    script_paths = [*sorted((ROOT / 'scripts').glob('all_metrics_rankings*.py')),
                    ROOT / 'scripts/all_metrics_final_gate.py']
    report = {'schema_version': 1, 'generated_at_utc': now(), 'implementation_origin': 'new_recovery_run',
        'formal_base': read(ROOT / 'BASELINE.json'), 'methods': list(METHODS), 'terminal': gate['terminal'],
        'coverage': coverage(groups), 'groups': groups, 'limitations': LIMITATIONS,
        'native_length_and_timing': lengths, 'common16_derivation': derived,
        'timing_interpretation': timing,
        'native_initializations_excluded_from_speed': initializations,
        'source_sha256': {str(path.relative_to(ROOT)): sha256(path) for path in script_paths},
        'raw_source_inventory': sources.evidence, 'final_gate': gate,
        'input_manifest_sha256': sources.evidence[str(RUN / 'inputs.json')],
        'overall_winner': None, 'average_rank': None,
        'publication_state': 'private_draft; numerical Git publication awaits user approval',
        'availability_studies_replace_formal_groups': False,
        'quantization_common_supplement': quantization_link(args.output, sources)}
    html = render(report, samples)
    write_json(args.output / 'results.json', report)
    (args.output / 'index.html').write_text(html, encoding='utf-8')
    write_json(args.output / 'artifact-manifest.json', {'generated_at_utc': now(), 'terminal': report['terminal'],
        'results_sha256': sha256(args.output / 'results.json'), 'html_sha256': sha256(args.output / 'index.html'),
        'audio_manifest_sha256': sha256(args.audio_manifest) if args.audio_manifest else None})
    return 0 if gate['terminal'] else 2


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-rankings'))
