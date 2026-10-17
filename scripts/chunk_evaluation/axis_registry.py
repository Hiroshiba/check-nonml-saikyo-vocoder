"""既存65音響軸＋6品質軸と、別群の編集品質軸の対応。数式は既存実装へ委譲。"""
import sys
from pathlib import Path

from .chunk_contracts import ContractError


def legacy():
    scripts = str(Path(__file__).resolve().parents[1])
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from all_metrics_rankings_acoustic import descriptors, extract
    from all_metrics_rankings_core import competition_ranks
    return descriptors, extract, competition_ranks


def specs(methods):
    descriptors, _, _ = legacy()
    acoustic = descriptors()
    if len(acoustic) != 65:
        raise ContractError('既存音響registryの65軸が変わりました')
    result = [{**d, 'direction': d['direction'] or 'diagnostic', 'condition': 'native',
               'methods': list(methods), 'stage': 'acoustic', 'metric': 'acoustic'} for d in acoustic]
    for metric, key, label, unit, direction in (
        ('erb', 'existing.erb20', '20ms ERB距離', 'dB', 'lower'),
        ('scoreq', '2.scoreq', 'SCOREQ参照距離', 'score', 'lower'),
        ('utmosv2', '1.native_mos', '予測MOS', 'predicted MOS', 'higher'),
        ('speaker_ecapa', '5.ecapa', 'ECAPA話者類似度', 'cosine', 'higher')):
        conditions = ('native', 'pitch_minus3', 'pitch_plus3') if metric in ('utmosv2', 'speaker_ecapa') else ('native',)
        for condition in conditions:
            result.append({'id': key if condition == 'native' else key+'.'+condition,
                           'label': label, 'unit': unit, 'direction': direction, 'condition': condition,
                           'methods': list(methods)+(['original'] if metric == 'utmosv2' and condition == 'native' else []),
                           'stage': metric+('-edited' if condition != 'native' else ''), 'metric': metric})
    for condition in ('pitch_minus3', 'pitch_plus3'):
        for suffix, label, unit in (('pitch', '音高追従MAE', 'cent'), ('pitch_missing', '有声未検出率', 'fraction')):
            result.append({'id': '7.'+suffix+'.'+condition, 'label': label, 'unit': unit,
                           'direction': 'lower', 'condition': condition, 'methods': list(methods),
                           'stage': 'pitch-edited', 'metric': suffix})
    for kind in ('cer', 'wer'):
        result.append({'id': '4.incremental_'+kind, 'label': '増分'+kind.upper(), 'unit': 'rate',
                       'direction': 'lower', 'condition': 'native', 'methods': list(methods),
                       'stage': 'asr', 'metric': 'asr_'+kind})
    return result


def public_axes(methods):
    return [{key: value[key] for key in ('id', 'condition', 'direction', 'methods')} for value in specs(methods)]


def validate_registry(plan):
    if plan['axes'] != public_axes(plan['methods']):
        raise ContractError('計画軸が既存71軸＋編集群の厳密対応と一致しません')
