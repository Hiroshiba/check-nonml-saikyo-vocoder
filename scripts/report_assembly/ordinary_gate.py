"""保存済み通常評価の終端・支持・順位を照合する。統計は算出しない。"""

import gzip
import io
from collections import Counter

from common import (
    BASE_VERSION,
    LIMIT,
    METHODS,
    count,
    decode,
    digest,
    interval,
    require,
    scalar,
    sha,
)

STATUSES = {"measured", "failed", "unsupported", "not_applicable", "upstream_failed",
            "reference_cer_gate_exceeded", "insufficient_support"}
REASONS = {"none", "generation_failed", "metric_failed", "model_initialization_failed",
           "unsupported_operation", "outside_scope", "full_transcript_unavailable",
           "reference_cer_gate_exceeded", "insufficient_voiced_support", "no_low_energy_segment",
           "length_mismatch", "output_shorter_than_fixed_window", "invalid_f0",
           "diagnostic_failed", "other_classified_failure"}


def check_estimate(row, rank_allowed):
    scalar(row["value"])
    interval(row["ci95"])
    count(row["valid_recordings"], 120)
    count(row["valid_speakers"], 40)
    rank = row["rank"]
    require(rank is None or rank_allowed and type(rank) is int and 1 <= rank <= 3,
            "保存順位が比較範囲外")
    require(row["value"] is not None or rank is None, "欠測へ順位が付与されています")
    if row.get("pml_difference") is not None:
        scalar(row["pml_difference"]["value"])
        interval(row["pml_difference"]["ci95"])


def checkpoints(sources, plan):
    bindings = sources.manifest["checkpoint_bindings"]
    require(len(bindings) == 10, "全10区間の入力が必要")
    require({r["checkpoint_id"] for r in bindings} == set(sources.by_role("checkpoint"))
            and {r["storage_id"] for r in bindings} == set(sources.by_role("checkpoint_storage")),
            "区間入力allowlistに過不足")
    planned = {row["id"]: row for row in plan["chunks"]}
    seen, audit = set(), []
    for binding in bindings:
        require(set(binding) == {"checkpoint_id", "storage_id"}, "保存対応の列不正")
        identifier = binding["checkpoint_id"]
        require(sources.entries[identifier]["role"] == "checkpoint", "区間入力の役割不正")
        storage = sources.data(binding["storage_id"], "checkpoint_storage")
        stored = sources.blobs[identifier]
        require(storage["format"] == "gzip" and storage["lossless"] is True, "無損失gzipが必要")
        require(storage["stored_sha256"] == digest(stored) and storage["stored_bytes"] == len(stored),
                "gzipの保存SHA/byte数不一致")
        with gzip.GzipFile(fileobj=io.BytesIO(stored)) as stream:
            logical = stream.read(LIMIT)
        require(len(logical) < LIMIT, "復元JSONが10MiB以上")
        require(storage["logical_checkpoint_sha256"] == digest(logical)
                and storage["logical_bytes"] == len(logical), "復元JSONのSHA/byte数不一致")
        data = decode(logical)
        chunk = data["chunk_id"]
        require(chunk in planned and chunk not in seen, "未知/重複の区間")
        require(data["schema_version"] == 2 and data["validation_state"] == "chunk_validated_end",
                "区間が未終端")
        require(data["run_plan_sha256"] == sources.entries["plan"]["sha256"]
                and data["frozen_digests"] == plan["frozen_digests"], "区間の凍結条件不一致")
        require(data["case_ids"] == planned[chunk]["case_ids"], "区間の固定録音順不一致")
        expected = {(case, axis["id"], axis["condition"], method)
                    for case in data["case_ids"] for axis in plan["axes"] for method in axis["methods"]}
        keys = set()
        for row in data["rows"]:
            key = tuple(row[k] for k in ("case", "axis", "condition", "method"))
            require(key in expected and key not in keys, "区間の予定行欠落/重複")
            require(row["status"] in STATUSES and row["reason_code"] in REASONS, "区間行が未終端")
            require((row["status"] == "measured" and scalar(row["value"]) is not None
                     and row["reason_code"] == "none") or
                    (row["status"] != "measured" and row["value"] is None
                     and row["reason_code"] != "none"), "欠測値/理由が不整合")
            if "support_numerator" in row or "support_denominator" in row:
                count(row["support_numerator"], count(row["support_denominator"]))
            keys.add(key)
        require(keys == expected, "全予定評価行が必要")
        seen.add(chunk)
        audit.append({"chunk_id": chunk, "logical_sha256": digest(logical),
                      "logical_bytes": len(logical), "stored_sha256": digest(stored),
                      "stored_bytes": len(stored)})
    require(seen == set(planned), "全10区間が必要")
    return audit


def validate(sources):
    plan = sources.data("plan", "plan")
    require(plan["schema_version"] == 2 and plan["scope"] == "fixed120-chunked-evaluation",
            "固定120計画が必要")
    require(plan["formal_base"] == "pml" and plan["formal_base_version"] == BASE_VERSION
            and plan["candidate"] == METHODS[0] and set(plan["methods"]) == set(METHODS),
            "今回のbase/candidate/比較方式と不一致")
    ids = [row["case"] for row in plan["cases"]]
    speakers = Counter(row["speaker"] for row in plan["cases"])
    require(len(ids) == len(set(ids)) == 120 and len(speakers) == 40
            and set(speakers.values()) == {3}, "固定120録音・40話者が必要")
    require(plan["chunks"] == [{"id": f"chunk-{i + 1:02d}", "case_ids": ids[i * 12:(i + 1) * 12]}
                               for i in range(10)], "固定chunk順不一致")
    axes = [(row["id"], row["condition"]) for row in plan["axes"]]
    require(len(axes) == len(set(axes)) == 79 and sum(c == "native" for _, c in axes) == 71,
            "通常71＋編集8軸が必要")
    for axis in plan["axes"]:
        require(axis["condition"] in ("native", "pitch_minus3", "pitch_plus3")
                and axis["direction"] in ("higher", "lower", "diagnostic"), "軸条件不正")
        require(len(axis["methods"]) == len(set(axis["methods"]))
                and set(axis["methods"]) <= set(METHODS) | {"original"}, "軸方式不正")
    audit = checkpoints(sources, plan)
    summary = sources.data("ordinary_summary", "ordinary_summary")
    require(summary["schema_version"] == 2 and summary["validation_state"] == "validated_end",
            "通常集約が未終端")
    require(summary["planned_recordings"] == 120 and summary["planned_speakers"] == 40
            and summary["run_plan_sha256"] == sources.entries["plan"]["sha256"], "通常集約の計画不一致")
    require(summary["formal_base"] == "pml" and summary["formal_base_version"] == BASE_VERSION
            and summary["candidate"] == METHODS[0] and summary["adoption_decision"] is None,
            "正式base/採否を変更できません")
    require(summary["chunk_sources"] == [{"chunk_id": row["chunk_id"], "sha256": row["logical_sha256"]}
                                         for row in audit], "通常集約の区間SHA/順序不一致")
    require([(row["id"], row["condition"]) for row in summary["axes"]] == axes, "79軸の順序不一致")
    metadata = sources.data("axis_metadata", "axis_metadata")["axes"]
    require(len(metadata) == 79 and {(r["id"], r["condition"]) for r in metadata} == set(axes),
            "表示metadataの79軸不一致")
    labels = {(r["id"], r["condition"]): r for r in metadata}
    for declared, axis in zip(plan["axes"], summary["axes"], strict=True):
        require(all(axis[key] == declared[key] for key in ("methods", "direction")), "軸契約不一致")
        common = axis["common_support"]
        count(common["common_valid_recordings"], 120)
        count(common["common_valid_speakers"], 40)
        for method in axis["methods"]:
            state = axis["method_states"][method]
            require(state["planned_recordings"] == 120, "方式分母不一致")
            count(state["measured_recordings"], 120)
            require(set(state["status_counts"]) <= STATUSES and set(state["reason_counts"]) <= REASONS,
                    "未知の欠測理由")
            for counts in (state["status_counts"], state["reason_counts"]):
                require(sum(count(v, 120) for v in counts.values()) == 120, "状態/理由の分母不一致")
            check_estimate(axis["own_support_unranked"][method], False)
        for row in common["methods"].values():
            check_estimate(row, axis["direction"] != "diagnostic")
            require(row["valid_recordings"] == common["common_valid_recordings"]
                    and row["valid_speakers"] == common["common_valid_speakers"], "共通支持不一致")
        for pair in axis["pairwise_pml"].values():
            count(pair["common_valid_recordings"], 120)
            count(pair["common_valid_speakers"], 40)
            for row in pair["methods"].values():
                check_estimate(row, False)
    binding = sources.manifest["ordinary_html_binding"]
    renderer_audio_sha = sha(binding["renderer_audio_manifest_sha256"])
    require(binding == {"html_sha256": sources.entries["ordinary_html"]["sha256"],
                        "summary_sha256": sources.entries["ordinary_summary"]["sha256"],
                        "plan_sha256": sources.entries["plan"]["sha256"],
                        "metadata_sha256": sources.entries["axis_metadata"]["sha256"],
                        "approved_audio_manifest_sha256": sources.entries["audio_manifest"]["sha256"],
                        "renderer_audio_manifest_sha256": renderer_audio_sha},
            "凍結HTMLと入力の生成時bindingが必要")
    html = sources.blobs["ordinary_html"].decode("utf-8")
    require(binding["summary_sha256"] in html and binding["plan_sha256"] in html,
            "凍結HTMLに集約/計画SHAが見つかりません")
    return plan, summary, labels, audit
