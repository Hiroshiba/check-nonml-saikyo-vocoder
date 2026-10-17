"""終端summaryから保存scalarだけを抜く。raw再集計、fit、順位付与はしない。"""

from common import (
    CONDITIONS,
    ESTIMANDS,
    FEATURE_AXES,
    REPRESENTATIONS,
    TARGETS,
    VIEWS,
    count,
    interval,
    require,
    scalar,
    sha,
)


def numeric_row(row):
    require(row["rank"] is None and row["lower_better"] is True, "特徴順位はnullのまま保持")
    return {**{key: scalar(row[key]) for key in ("candidate", "pml", "candidate_minus_pml")},
            "delta_ci95": interval(row["delta_ci95"]), "rank": None, "lower_better": True}


def terminal_sources(sources, freeze):
    collected = {}
    for role in ("readout_summary", "abx_summary"):
        for identifier in sources.by_role(role):
            data = sources.data(identifier)
            contract = data["contract"]
            identity = (role, contract["method"], contract["view"])
            require(identity not in collected, "特徴終端summary重複")
            require(data["validation_state"] == "validated_end"
                    and contract["source_freeze_sha256"] == freeze, "特徴終端/凍結SHA不一致")
            collected[identity] = (identifier, data)
    require(set(collected) == {(role, method, view) for role in ("readout_summary", "abx_summary")
                              for method, view in REPRESENTATIONS}, "特徴の4表現×2終端が必要")
    return collected


def readout_projection(identifier, source, data):
    require(source["planned_cases"] == 120 and source["contract"]["alpha"] == 1,
            "読み出しの固定分母/alpha不一致")
    require(set(source["summaries"]) == set(TARGETS), "読み出しの3targetが必要")
    rows = []
    for target in TARGETS:
        row = source["summaries"][target]
        require(row["status"] in ("measured", "not_applicable"), "読み出し状態が未終端")
        require(row.get("rank") is None, "特徴順位を付与できません")
        if row.get("reason_code") is not None:
            require(row["reason_code"] == "insufficient_train_targets", "未知の読み出し理由")
        diagnostic = row.get("diagnostics")
        if diagnostic is not None:
            require(diagnostic["alpha"] == 1, "診断alpha不一致")
            count(diagnostic["valid_train"], 120)
            dimensions = count(diagnostic["dimensions"])
            count(diagnostic["constant_dimensions"], dimensions)
            count(diagnostic["matrix_rank"], min(dimensions, diagnostic["valid_train"]))
            scalar(diagnostic["constant_prediction"])
            diagnostic = {key: diagnostic[key] for key in (
                "alpha", "valid_train", "dimensions", "constant_dimensions", "matrix_rank",
                "constant_prediction")}
        for key, maximum in (("recordings", 120), ("speakers", 40), ("planned_recordings", 120)):
            if key in row:
                count(row[key], maximum)
        if "planned_recordings" in row:
            require(row["planned_recordings"] == 120, "読み出し予定分母不一致")
        rows.append({"target": target, "status": row["status"], "rank": None,
                     "planned_recordings": 120, "planned_source": "summary.planned_cases",
                     "recordings": row.get("recordings"), "speakers": row.get("speakers"),
                     "speaker_macro_mae": scalar(row.get("speaker_macro_mae")),
                     "ci95": interval(row.get("ci95")),
                     "constant_train_mean_speaker_macro_mae": scalar(
                         row.get("constant_train_mean_speaker_macro_mae")),
                     "diagnostics": diagnostic, "reason_code": row.get("reason_code"),
                     "missing_reason_counts": None,
                     "missing_reason_counts_unavailable": "not_saved_in_terminal_summary",
                     "support_basis": "own_support_not_paired_support"})
    return {"source": data.identity(identifier), "method": source["contract"]["method"],
            "view": source["contract"]["view"], "targets": rows}


def abx_projection(identifier, source, data):
    require(source["planned_triplets"] == 4960, "ABX分母不一致")
    count(source["measured_triplets"], 4960)
    allowed = {f"{c}/{e}" for c in CONDITIONS for e in ESTIMANDS}
    require(set(source["summaries"]) <= allowed, "未知のABX軸")
    values = {}
    for axis, row in source["summaries"].items():
        require(row["rank"] is None, "ABX順位を付与できません")
        values[axis] = {"value": scalar(row["value"]), "ci95": interval(row["ci95"]), "rank": None}
    scale = source["contract"]["scale_info"]
    require(scale["recording_count"] == 120, "ABX尺度調整はtrain120が必要")
    count(scale["constant_dimensions"])
    scalar(scale["minimum_total_variance"])
    return {"source": data.identity(identifier), "method": source["contract"]["method"],
            "view": source["contract"]["view"], "planned_triplets": 4960,
            "measured_triplets": source["measured_triplets"], "values": values,
            "scale": {k: scale[k] for k in ("recording_count", "constant_dimensions", "minimum_total_variance")},
            "planned_by_condition": None, "distance_failure_counts": None,
            "token_support_failure_counts": None,
            "unavailable_reason": "not_saved_in_terminal_summary",
            "support_basis": "own_support_not_paired_support"}


def paired_projection(source):
    result = {}
    for condition in CONDITIONS:
        bootstrap = source["support"]["abx"].get("bootstrap")
        saved = bootstrap["by_condition"][condition] if bootstrap is not None else None
        if saved is not None:
            require(bootstrap["support_columns"] == ["strata", "triplets", "speakers", "x_speakers"],
                    "ABX支持列が変更されています")
            values = saved["point_support"]
            require(len(values) == 4, "ABX支持列数不一致")
            for value in values:
                count(value)
            count(values[1], 4960)
            count(values[2], 40)
            count(values[3], 40)
            count(saved["drawn_replicates"], 2000)
        result[condition] = {
            "planned_triplets": None,
            "planned_unavailable_reason": "not_saved_in_terminal_summary",
            "point_support": None if saved is None else dict(zip(
                ("strata", "triplets", "speakers", "x_speakers"), saved["point_support"], strict=True)),
            "drawn_replicates": None if saved is None else saved["drawn_replicates"],
            "bootstrap_unavailable_reason": "not_saved_in_terminal_summary" if saved is None else None,
        }
    return result


def project(sources):
    public = sources.data("feature_public", "feature_public")
    require(public["schema_version"] == 1 and public["scope"] == "feature-evaluation-new-run",
            "特徴公開形式不一致")
    require(public["validation_state"] == "validated_end" and public["incomplete_components"] == [],
            "特徴が全終端になるまで統合HTMLを生成しません")
    require(public["common_plan_sha256"] == sources.entries["plan"]["sha256"]
            and public["formal_base"] == "pml" and public["planned_train"] == 120
            and public["planned_test"] == 120 and public["planned_abx"] == 4960
            and public["fixed_alpha"] == 1, "特徴計画/分母/alpha不一致")
    freeze = sha(public["source_freeze_sha256"])
    terminal = terminal_sources(sources, freeze)
    comparisons = {}
    for identifier in sources.by_role("comparison_summary"):
        source = sources.data(identifier)
        view = source["view"]
        require(view in VIEWS and view not in comparisons, "特徴比較view重複/不正")
        require(source["validation_state"] == "validated_end"
                and source["source_freeze_sha256"] == freeze and source["formal_base"] == "pml",
                "特徴比較が未終端/凍結不一致")
        require(sources.entries[identifier]["sha256"] in public["terminal_summary_sha256"],
                "特徴公開JSONと比較終端SHAが不一致")
        expected = {sources.entries[terminal[role, method, representation][0]]["sha256"]
                    for role in ("abx_summary", "readout_summary")
                    for method, representation in (("candidate", view), ("pml", "pml2110"))}
        declared = [row["sha256"] for row in source["source_summaries"]]
        require(len(declared) == 4 and set(declared) == expected, "比較元4終端SHA不一致")
        require(set(source["results"]) <= set(FEATURE_AXES), "未知の特徴比較軸")
        results = {key: numeric_row(row) for key, row in source["results"].items()}
        comparisons[view] = (identifier, source, results)
    require(set(comparisons) == set(VIEWS) and len(public["comparison"]) == 3, "特徴3viewが必要")
    seen, paired = set(), []
    for row in public["comparison"]:
        view = row["view"]
        require(view in comparisons and view not in seen and row["status"] == "validated_end"
                and row["primary"] is (view == VIEWS[0]), "公開view/状態不一致")
        identifier, source, values = comparisons[view]
        require(row["values"] == values, "特徴公開値と比較終端の保存scalar不一致")
        support = row["paired_support"]
        require(set(support) == {"abx", *(f"readout/{t}" for t in TARGETS)}, "特徴支持軸不一致")
        projected_support = {}
        for key, maximum in [("abx", 4960), *((f"readout/{t}", 120) for t in TARGETS)]:
            saved, item = source["support"][key], support[key]
            require(saved["planned"] == item["planned"] == maximum
                    and saved["paired_measured"] == item["paired_measured"], "特徴対応支持不一致")
            count(item["paired_measured"], maximum)
            projected_support[key] = {k: item[k] for k in ("planned", "paired_measured")}
            if key != "abx":
                require(item["speaker_count"] == len(saved["speakers"]), "対応話者支持不一致")
                projected_support[key]["speaker_count"] = count(item["speaker_count"], 40)
        paired.append({"view": view, "source": sources.identity(identifier), "values": values,
                       "support": projected_support, "abx_by_condition": paired_projection(source),
                       "unsaved_axes": [axis for axis in FEATURE_AXES if axis not in values]})
        seen.add(view)
    failures, failure_seen = [], set()
    for row in public["failures"]:
        identity = (row["split"], row["method"], row["view"])
        require(identity not in failure_seen and row["planned"] == 120, "moments分母/重複不正")
        require(set(row["status_counts"]) <= {"measured", "failed", "upstream_failed"}
                and set(row["reason_counts"]) <= {"feature_observation_failed", "payload_not_available"},
                "moments欠測理由不正")
        require(sum(count(v, 120) for v in row["status_counts"].values()) == 120, "moments状態分母不一致")
        for value in row["reason_counts"].values():
            count(value, 120)
        failures.append({k: row[k] for k in ("split", "method", "view", "planned", "status_counts", "reason_counts")})
        failure_seen.add(identity)
    require(failure_seen == {(split, method, view) for split in ("train", "test")
                             for method, view in REPRESENTATIONS}, "moments全8終端の支持が必要")
    return {"schema_version": 1, "scope": "saved-feature-scalars-only", "rank": None,
            "feature_public_sha256": sources.entries["feature_public"]["sha256"],
            "source_freeze_sha256": freeze, "common_plan_sha256": public["common_plan_sha256"],
            "paired": paired, "readout_own_support": [
                readout_projection(identifier, source, sources)
                for (role, _, _), (identifier, source) in terminal.items() if role == "readout_summary"],
            "abx_own_support": [abx_projection(identifier, source, sources)
                                for (role, _, _), (identifier, source) in terminal.items() if role == "abx_summary"],
            "moment_failures": failures,
            "limitation": "保存のない条件別予定数・失敗理由数はnull。raw再集計・新規統計・特徴順位なし。"}
