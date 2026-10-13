"""#14、#15。固定距離での音素ABXと未知話者への単純読み出し。"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.spatial.distance import cdist

from .common import NotApplicable, error_summary, finite, integer, number, ok


def feature_items(job, inputs):
    data = inputs.json(job["dataset"])
    if not data.get("representation") or not data.get("extraction_revision"):
        raise ValueError("特徴表現と抽出器の版を指定してください")
    items = {}
    dimension = None
    for item in data["items"]:
        if item["id"] in items:
            raise ValueError("特徴項目IDが重複しています")
        array = inputs.array(item["features"])
        if array.ndim == 1:
            array = array[None, :]
        if array.ndim != 2:
            raise ValueError("特徴量はフレーム×次元の有限配列が必要です")
        dimension = array.shape[1] if dimension is None else dimension
        if array.shape[1] != dimension:
            raise ValueError("特徴次元が一致しません")
        items[item["id"]] = (item, array)
    if not items:
        raise ValueError("特徴量がありません")
    return data, items


def dtw(a, b, mode, weights, max_cells):
    if a.shape[0]*b.shape[0] > max_cells:
        raise ValueError("DTWの上限を超えました。分割条件を事前に固定してください")
    a, b = a*weights, b*weights
    if mode == "angular":
        na, nb = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
        if np.any(na <= 1e-12) or np.any(nb <= 1e-12):
            raise NotApplicable("角距離にゼロノルムの特徴フレームは使えません")
        costs = np.arccos(np.clip((a @ b.T)/(na[:, None]*nb[None, :]), -1, 1))/np.pi
    elif mode == "euclidean":
        costs = cdist(a, b, metric="euclidean")
    else:
        raise ValueError("距離はangularかeuclideanです")
    # 無制約DTWは特徴ABX専用。編集の時間整列には流用しない。
    previous = np.full(len(b)+1, np.inf)
    previous[0] = 0
    previous_lengths = np.zeros(len(b)+1, dtype=int)
    for row in costs:
        current = np.full(len(b)+1, np.inf)
        lengths = np.zeros(len(b)+1, dtype=int)
        for j, cost in enumerate(row, 1):
            candidates = ((previous[j-1], previous_lengths[j-1]),
                          (previous[j], previous_lengths[j]), (current[j-1], lengths[j-1]))
            value, length = min(candidates)
            current[j], lengths[j] = value+cost, length+1
        previous, previous_lengths = current, lengths
    return float(previous[-1]/previous_lengths[-1])


def abx(job, inputs):
    data, items = feature_items(job, inputs)
    weights = finite(job["feature_weights"])
    dimension = next(iter(items.values()))[1].shape[1]
    if weights.shape != (dimension,) or np.any(weights <= 0) or not job.get("distance_calibration_id"):
        raise ValueError("開発集合で固定した正の次元重みと校正IDが必要です")
    tolerance = number(job.get("tie_atol", 1e-12))
    if tolerance < 0:
        raise ValueError("同点許容差は非負で指定してください")
    limit = integer(job.get("max_dtw_cells", 2_000_000))
    triplets = data["triplets"]
    if not triplets:
        raise ValueError("三つ組がありません")
    cache, groups, rows, seen = {}, defaultdict(list), [], set()
    def distance(a, b):
        key = tuple(sorted((a, b)))
        if key not in cache:
            cache[key] = dtw(items[a][1], items[b][1], job["distance"], weights, limit)
        return cache[key]
    for triplet in triplets:
        ids = tuple(triplet[key] for key in ("a", "b", "x"))
        if len(set(ids)) != 3 or ids in seen:
            raise ValueError("三つ組内の同一項目・重複三つ組は使えません")
        seen.add(ids)
        a, b, x = (items[key][0] for key in ids)
        if a["phone"] == b["phone"] or a["phone"] != x["phone"] or len({p["context"] for p in (a, b, x)}) != 1:
            raise ValueError("ABXの音素・左右文脈ラベルが成立していません")
        if a["speaker"] != b["speaker"]:
            raise ValueError("AとBは同話者である必要があります")
        condition = "within_speaker" if a["speaker"] == x["speaker"] else "across_speaker"
        if triplet["condition"] != condition:
            raise ValueError("指定された話者条件とラベルが不一致です")
        da, db = distance(ids[0], ids[2]), distance(ids[1], ids[2])
        tie = abs(da-db) <= tolerance
        error = .5 if tie else float(da > db)
        # 音素の向き・文脈・話者組を保持し、条件別にまず集約する。
        group = (condition, a["phone"], b["phone"], a["context"], a["speaker"], x["speaker"])
        groups[group].append(error)
        rows.append({**triplet, "distance_ax": da, "distance_bx": db, "error": error, "tie": tie})
    grouped = [{"stratum": list(key), "count": len(values), "error_rate": float(np.mean(values))}
               for key, values in sorted(groups.items())]
    conditions = {}
    for condition in ("within_speaker", "across_speaker"):
        values = [r["error_rate"] for r in grouped if r["stratum"][0] == condition]
        conditions[condition] = {"status": "ok" if values else "not_configured",
                                 "macro_error_rate": float(np.mean(values)) if values else None,
                                 "strata": len(values)}
    return ok(None, "ABX誤り率", conditions=conditions, strata=grouped, triplets=rows,
              micro_error_rate=float(np.mean([r["error"] for r in rows])),
              triplet_count=len(rows), unique_items=len({key for triple in seen for key in triple}),
              unique_distances=len(cache), distance=job["distance"], tie_atol=tolerance,
              definition="同点0.5。各条件・層の値を保持。公式ZeroSpeech集計との同値性は未検証")


def attribute_access(job, inputs):
    data, items = feature_items(job, inputs)
    targets = job["targets"]
    if not targets or len(set(targets)) != len(targets) or set(data["target_units"]) != set(targets):
        raise ValueError("重複しない属性名と対応単位が必要です")
    train, evaluation = [], []
    for item, array in items.values():
        row = (item, array.mean(axis=0), finite([item["targets"][key] for key in targets]))
        if item["split"] == "train":
            train.append(row)
        elif item["split"] == "evaluation":
            evaluation.append(row)
        else:
            raise ValueError("splitはtrainまたはevaluationです")
    if len(train) < 2 or not evaluation:
        raise ValueError("学習2項目以上・評価1項目以上が必要です")
    train_speakers, eval_speakers = ({r[0]["speaker"] for r in rows} for rows in (train, evaluation))
    if train_speakers & eval_speakers:
        raise ValueError("学習と評価で話者が重複しています")
    if {r[0]["utterance_id"] for r in train} & {r[0]["utterance_id"] for r in evaluation}:
        raise ValueError("学習と評価で発話が重複しています")
    alpha = number(job["ridge_alpha"])
    if alpha <= 0:
        raise ValueError("ridge_alphaは事前固定した正の値を指定してください")
    x, y = np.stack([r[1] for r in train]), np.stack([r[2] for r in train])
    z, truth = np.stack([r[1] for r in evaluation]), np.stack([r[2] for r in evaluation])
    center, scale, target_center = x.mean(axis=0), x.std(axis=0), y.mean(axis=0)
    scale = np.where(scale > 1e-12, scale, 1)
    x, z = (x-center)/scale, (z-center)/scale
    u, s, vt = np.linalg.svd(x, full_matrices=False)
    coefficients = (vt.T*(s/(s*s+alpha))) @ (u.T @ (y-target_center))
    predicted = z @ coefficients + target_center
    errors = predicted-truth
    results = {}
    for i, name in enumerate(targets):
        by_speaker = {speaker: error_summary(errors[[r[0]["speaker"] == speaker for r in evaluation], i])
                      for speaker in sorted(eval_speakers)}
        results[name] = {"unit": data["target_units"][name], **error_summary(errors[:, i]),
                         "constant_baseline": error_summary(target_center[i]-truth[:, i]),
                         "speaker_macro_mae": float(np.mean([r["mae"] for r in by_speaker.values()])),
                         "by_speaker": by_speaker}
    return ok(None, "属性別誤差", attributes=results, train_items=len(train), evaluation_items=len(evaluation),
              train_speakers=sorted(train_speakers), evaluation_speakers=sorted(eval_speakers),
              ridge_alpha=alpha, feature_dimensions=x.shape[1], parameters_per_target=x.shape[1]+1,
              predicted=predicted.tolist(), truth=truth.tolist(), evaluation_ids=[r[0]["id"] for r in evaluation],
              definition="発話内フレーム平均＋学習側のみ標準化＋固定Ridge。評価側で調整しない")
