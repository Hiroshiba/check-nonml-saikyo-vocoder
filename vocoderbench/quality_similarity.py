"""既存の人間話者類似度評定と、提供された特徴量の近さを照合する。"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from .quality_core import measure_repeated, read_json, sha256, write_json


def compare_ratings(feature_document, ratings):
    """特徴抽出や距離学習はしない。人間評定の方向と条件は明示入力する。"""
    vectors = feature_document['vectors']
    direction = feature_document['rating_direction']
    if direction not in ('higher_is_more_similar', 'lower_is_more_similar'):
        raise ValueError('rating_directionを明示してください')
    if feature_document.get('rating_kind') != 'human':
        raise ValueError('人間の既存評定だけが対象です。人工順位を人間評定と扱いません')
    for key in ('method', 'feature_description', 'pooling', 'rating_experiment'):
        if not isinstance(feature_document.get(key), str) or not feature_document[key].strip():
            raise ValueError(f'特徴・評定の来歴が必要です: {key}')
    normalized = {}
    dimension = None
    for speaker, value in vectors.items():
        vector = np.asarray(value, dtype=np.float64)
        if vector.ndim != 1 or not vector.size or not np.isfinite(vector).all() or np.linalg.norm(vector) == 0:
            raise ValueError(f'特徴量は有限値の非ゼロ1次元ベクトルにしてください: {speaker}')
        if dimension is not None and len(vector) != dimension:
            raise ValueError('話者特徴量の次元が不一致です')
        dimension = len(vector)
        normalized[speaker] = vector / np.linalg.norm(vector)
    records, seen = [], set()
    for rating in ratings:
        a, b, group = rating['speaker_a'], rating['speaker_b'], rating['group']
        if not a or not b or a == b or not group:
            raise ValueError('異なる2話者と空でない比較groupが必要です')
        key = (group, *sorted((a, b)))
        if key in seen:
            raise ValueError('同じ話者対の重複があります。個人評定は同一条件内で事前集約してください')
        seen.add(key)
        score = float(rating['rating'])
        if not np.isfinite(score):
            raise ValueError('人間評定は有限値にしてください')
        row = {'speaker_a': a, 'speaker_b': b, 'group': group, 'human_rating': score,
               'status': 'missing_features', 'feature_similarity': None}
        if a in normalized and b in normalized:
            row.update(status='measured', feature_similarity=float(normalized[a] @ normalized[b]))
        else:
            logging.warning('評定対の話者特徴が不足: %s / %s', a, b)
        records.append(row)
    if not records:
        raise ValueError('評定CSVにデータがありません')
    groups = {}
    for group in sorted({r['group'] for r in records}):
        planned = [r for r in records if r['group'] == group]
        valid = [r for r in planned if r['status'] == 'measured']
        human = np.asarray([r['human_rating'] for r in valid])
        if direction == 'lower_is_more_similar':
            human = -human
        feature = np.asarray([r['feature_similarity'] for r in valid])
        computable = len(valid) >= 3 and np.unique(human).size > 1 and np.unique(feature).size > 1
        rho = float(spearmanr(human, feature).statistic) if computable else None
        neighbors = []
        for anchor in sorted({r[k] for r in valid for k in ('speaker_a', 'speaker_b')}):
            indices = [i for i, r in enumerate(valid) if anchor in (r['speaker_a'], r['speaker_b'])]
            if len(indices) < 2:
                continue
            h, f = human[indices], feature[indices]
            predicted = f == f.max()
            neighbors.append(float(np.mean(h[predicted] == h.max())))
        groups[group] = {'status': 'measured' if computable else 'not_applicable',
                         'spearman_rho': rho, 'rated_neighbor_top1_agreement': float(np.mean(neighbors)) if neighbors else None,
                         'neighbor_anchor_count': len(neighbors), 'valid_pairs': len(valid), 'planned_pairs': len(planned),
                         'speakers_with_valid_pairs': len({r[k] for r in valid for k in ('speaker_a', 'speaker_b')}),
                         'reason': None if computable else '3対未満または評定・特徴類似度が定数です'}
    return {'groups': groups, 'pairs': records, 'feature_dimension': dimension,
            'interpretation': '評定groupごとの順位対応。話者対は独立標本ではないためp値・単純な信頼区間を出さない。',
            'distance': 'untrained cosine similarity',
            'scope': '特徴距離の評価。再合成音へ元の人間評定を転用していない。'}


def run_comparison(features_path, ratings_path, output, repetitions=5):
    if Path(output).exists() or Path(output).with_suffix('.html').exists():
        raise FileExistsError('結果は上書きしません')
    if not 1 <= repetitions <= 100:
        raise ValueError('反復回数は1〜100回にしてください')
    features = read_json(features_path)
    with Path(ratings_path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'speaker_a', 'speaker_b', 'group', 'rating'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('評定CSVにはspeaker_a,speaker_b,group,ratingが必要です')
        ratings = list(reader)
    # 集約して一つの品質値にはしない。タイマーの値は処理済み対数だけとする。
    details = {}
    def measure():
        nonlocal details
        details = compare_ratings(features, ratings)
        return len(details['pairs']), details
    timing = measure_repeated(measure, repetitions)
    result = {'schema_version': 1, 'features_sha256': sha256(features_path),
              'ratings_sha256': sha256(ratings_path),
              'feature_metadata': {k: v for k, v in features.items() if k != 'vectors'},
              'timing': timing, 'comparison': details,
              'timing_scope': 'ファイル読込・エンコーダー特徴抽出を除く。正規化、距離、順位相関を含む。'}
    write_json(output, result)
    from .quality_report import render_similarity
    render_similarity(result, Path(output).with_suffix('.html'))
    incomplete = timing['status'] != 'measured' or any(r['status'] != 'measured' for r in details.get('pairs', []))
    incomplete = incomplete or any(g['status'] != 'measured' for g in details.get('groups', {}).values())
    return result, 1 if incomplete else 0


def main():
    from .logging_utils import LoggedArgumentParser
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path, required=True)
    parser.add_argument('--ratings', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=5)
    args = parser.parse_args()
    if args.repetitions < 1 or args.repetitions > 100:
        raise ValueError('反復回数は1〜100回にしてください')
    if args.output.exists():
        raise FileExistsError('結果は上書きしません')
    _, code = run_comparison(args.features, args.ratings, args.output, args.repetitions)
    return code


if __name__ == '__main__':
    from .logging_utils import run_cli
    raise SystemExit(run_cli(main, 'human-similarity'))
