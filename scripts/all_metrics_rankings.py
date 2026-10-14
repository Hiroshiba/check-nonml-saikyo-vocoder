"""正式rawから全8方式の軸別順位・全18群状態・日本語HTMLを保存する。再測定しない。"""
from __future__ import annotations

import argparse
from pathlib import Path

from all_metrics_common import METHODS, ROOT, RUN, now, read
from all_metrics_final_gate import inventory
from all_metrics_rankings_acoustic import groups as acoustic_groups
from all_metrics_rankings_core import aggregate
from all_metrics_rankings_coverage import coverage
from all_metrics_rankings_extra import asr_groups, special_groups, vctk_groups
from all_metrics_rankings_html import render
from all_metrics_rankings_inputs import Sources, imported_groups, mos_groups, native_groups, public_audio, quality_groups
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json

LIMITATIONS = [
    '主LibriSpeechは凍結120録音40話者。native全長MOS、共通16kHz忠実性、全文正解55録音32話者のASRは別の比較範囲。',
    '群ごとに同じ録音→話者内平均→話者等重み。主群の共通0は0のまま。全有効値の方式別集計は無順位補助。',
    '全予定終端後の補助比較では、許容状態の有限値が1件以上ある方式を先に全て固定。共通数を増やす方式選別はしない。',
    '話者復元抽出2000回、seed20261014の記述的95%区間。HNMとの差も同じ録音・同じ話者抽出。多重比較未補正。',
    '同点は未丸め値の絶対1e-12/相対1e-9許容差を同点群先頭と比較する競技順位。区間重なりだけで同点にしない。',
    '符号付きRMS、低エネルギー区間の比率/RMS/peak、補間の線形性、共有資産量は診断値で無順位。',
    'VCTKは126録音7話者の独立48kHz群。原音・共通区間とも8秒以上の別補助層。元の上流失敗を時間不足へ置換しない。',
    '人間評定はASVspoof2019の105録音84対28話者。声の同一人物らしさとの一致であり、復号MOSではない。',
    'ABXは同話者/異話者×層等重み/X話者等重み/入れ子補助の6推定対象。話者グラフ条件付きnode区間。公式全コーパス順位ではない。',
    '読み出しは別40話者120録音で固定尺度とRidgeを学習。3種類の独立推定音響属性に対する話者等重みMAE。',
    '直接実測と、厳密に同一の復号入力・PCMに基づくanalytic_identity値を分けて計数。欠測・失敗・未対応はnull。',
    '表現量は宣言容器の実bytesと固定元入力秒による量。共有モデル等が別途必要。容器量順位と品質付き圧縮効率を混同しない。',
    '速度は全8ともworker1・CPU上限2の独立native工程の単回。初回正式入力を除かず、初期化・前処理・保存読込は別。区間は録音構成だけ。',
    '喪失した旧rawや会話の途中集計を復元値へ使わない。原音、全長生成波形、モデル、元人間評定CSVは公開対象外。',
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
    raw_groups = [*mos_groups(specs, sources), *quality_groups(specs, sources), *acoustic_groups(specs, sources),
                  *asr_groups(specs, sources), *vctk_groups(sources), *imported_groups(specs, sources), *speed]
    groups = [aggregate(group) for group in raw_groups] + special_groups(sources)
    if len({group['id'] for group in groups}) != len(groups):
        raise ValueError('指標群IDの重複')
    gate = inventory(specs, sources, groups)
    if not gate['terminal'] and not args.allow_incomplete:
        raise ValueError(f'予定recordが未完了: {gate["unresolved_records"]}件。途中報告には--allow-incompleteを明示')
    if not gate['terminal']:
        for group in groups:
            group['conditional'] = None
    samples = public_audio(read(args.audio_manifest), args.output) if args.audio_manifest else []
    if gate['terminal'] and not samples:
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
        'native_initializations_excluded_from_speed': initializations,
        'source_sha256': {str(path.relative_to(ROOT)): sha256(path) for path in script_paths},
        'raw_source_inventory': sources.evidence, 'final_gate': gate,
        'input_manifest_sha256': sources.evidence[str(RUN / 'inputs.json')],
        'overall_winner': None, 'average_rank': None}
    html = render(report, samples)
    write_json(args.output / 'results.json', report)
    (args.output / 'index.html').write_text(html, encoding='utf-8')
    write_json(args.output / 'artifact-manifest.json', {'generated_at_utc': now(), 'terminal': report['terminal'],
        'results_sha256': sha256(args.output / 'results.json'), 'html_sha256': sha256(args.output / 'index.html'),
        'audio_manifest_sha256': sha256(args.audio_manifest) if args.audio_manifest else None})
    return 0 if gate['terminal'] else 2


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-rankings'))
