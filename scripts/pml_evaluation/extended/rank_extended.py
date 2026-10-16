"""Common-support append of PML to published edit/precision recording-level evidence."""

from portable_context import HISTORICAL, REPO
from functools import lru_cache
from collections import defaultdict, Counter
import numpy as np
from run_edits import ROOT, read, write, sha

OLD = HISTORICAL / "edited-comparison"
PML = "pml_fwcep60_lowband_package_v1"
raw = read(OLD / "raw-records.json")["records"]
meta = read(OLD / "group-contracts-and-aggregates.json")
spec = read(ROOT / "input-contract.json")
cases = spec["cases"]
evidence = {}


@lru_cache(maxsize=None)
def get(path):
    if not path.exists():
        return None
    evidence[str(path.relative_to(ROOT))] = sha(path)
    return read(path)


def checked(path, case, **expected):
    row = get(path)
    if row is None:
        return None
    assert row["case"] == case and row["speaker"] == case_speakers[case], str(path)
    for k, v in expected.items():
        assert row[k] == v, (path, k)
    if "contract_sha256" in row:
        contract = path.parent.parent / "contract.json"
        if contract.exists():
            assert row["contract_sha256"] == sha(contract), str(path)
    return row


case_speakers = {c["id"]: c["speaker"] for c in cases}
compat = read(OLD / "compatibility-check.json")
assert compat["input_id_sets_match"] and {r["case"] for r in compat["inputs"]} == set(
    case_speakers
)
assert all(
    all(
        r[k]
        for k in ("same_npy_sha256", "same_speaker", "same_samples", "same_sample_rate")
    )
    for r in compat["inputs"]
)
assert all(
    r["match"] and sha(REPO / r["path"].split("/source/", 1)[-1]) == r["expected"]
    for r in compat["source_checks"]
)
assert all(
    compat[k]
    for k in (
        "ecapa_model_matches",
        "mos_model_matches",
        "mos_config_matches",
        "mos_preprocessor_matches",
        "ecapa_environment_matches",
    )
)


def quality(case, metric, condition, precision=None):
    if precision:
        return checked(
            ROOT
            / "extended/quantization-quality"
            / metric
            / "measurements"
            / f"{case}__{precision}.json",
            case,
            condition=precision,
        )
    if condition == "unedited" and metric == "utmosv2":
        return checked(ROOT / "results/utmosv2/measurements" / f"{case}.json", case)
    return checked(
        ROOT
        / "extended/quality"
        / metric
        / "measurements"
        / f"{case}__{condition}.json",
        case,
        condition=condition,
    )


def scalar(row):
    if row is None:
        return None, "pending"
    value = row.get("value")
    status = row["status"]
    return (
        value
        if status in ("measured", "ok", "analytic_identity")
        and value is not None
        and np.isfinite(value)
        else None
    ), status


def point(g, case):
    bits = g.split(".")
    family = bits[0]
    if family in ("7", "8"):
        r = checked(
            ROOT / "extended/measurements" / f"{case}__{bits[1]}.json",
            case,
            condition=bits[1],
        )
        if r is None:
            return None, "pending"
        m = r.get("measurement", {})
        if bits[2] == "missing_voiced_fraction":
            n = m.get("expected_voiced_frames", 0)
            return (
                (m["missing_voiced_frames"] / n, "measured")
                if n
                else (None, "not_applicable")
            )
        return m.get("value"), r["status"]
    if family == "11":
        r = checked(
            ROOT / "extended/measurements" / f"{case}__gain_interference.json",
            case,
            condition="gain_interference",
        )
        if r is None:
            return None, "pending"
        cell = next(
            (
                x
                for x in r.get("measurement", {}).get("matrix", [])
                if x["attribute"] == bits[2]
            ),
            None,
        )
        return (
            (abs(cell["normalized_error"]), "measured")
            if cell and cell["normalized_error"] is not None
            else (None, "not_applicable")
        )
    if family == "12":
        metric = "utmosv2" if bits[3] == "predicted_mos" else "speaker_ecapa"
        value, status = scalar(quality(case, metric, bits[2]))
        if len(bits) > 4:
            base, bs = scalar(quality(case, metric, "unedited"))
            return (
                (value - base, "measured")
                if value is not None and base is not None
                else (
                    None,
                    "pending" if "pending" in (status, bs) else "upstream_failed",
                )
            )
        return value, status
    if family == "17":
        precision = bits[1]
        r = checked(
            ROOT
            / "extended/quantization-measurements/measurements"
            / f"{case}__{precision}.json",
            case,
            precision=precision,
        )
        if r is None:
            return None, "pending"
        if bits[2] == "erb":
            return r.get("auditory", {}).get("value"), r.get("auditory", {}).get(
                "status", r["status"]
            )
        if bits[2] == "control":
            x = next(x for x in r["controls"] if x["condition"] == bits[3])
            return x.get("measurement", {}).get("value"), x["status"]
        if bits[2] == "delta":
            metric = "utmosv2" if bits[3] == "predicted_mos" else "speaker_ecapa"
            value, status = scalar(quality(case, metric, "unedited", precision))
            base, bs = scalar(quality(case, metric, "unedited"))
            return (
                (value - base, "measured")
                if value is not None and base is not None
                else (
                    None,
                    "pending" if "pending" in (status, bs) else "upstream_failed",
                )
            )
        d = r.get("attribute_deltas", {}).get(bits[2], {})
        v = d.get("signed_delta")
        return abs(v) if v is not None else None, d.get("status", "not_applicable")
    if family == "18":
        precision = None if bits[1] == "native" else bits[1].replace("quantized_", "")
        if bits[2] == "payload_bitrate":
            if precision:
                r = get(
                    ROOT
                    / "extended/quantization/native"
                    / case
                    / precision
                    / "payload.json"
                )
                if r:
                    assert r["contract_sha256"] == sha(
                        ROOT / "extended/quantization/contract.json"
                    )
                    assert r["native_record_sha256"] == sha(
                        ROOT / "native" / case / "record.json"
                    )
                return (
                    (r["bits_per_source_second"], "measured")
                    if r
                    else (None, "pending")
                )
            r = checked(ROOT / "native" / case / "record.json", case)
            return (
                (r["payload"]["bytes_per_second"] * 8, "measured")
                if r and r["status"] == "measured"
                else (None, "upstream_failed")
            )
        return scalar(
            quality(
                case,
                "utmosv2" if bits[2] == "predicted_mos" else "speaker_ecapa",
                "unedited",
                precision,
            )
        )
    raise ValueError("Unknown group " + g)


rows_by = defaultdict(list)
seen = set()
for item in raw:
    if item["kind"] == "metric_recording":
        r = item["row"]
        key = (item["group_id"], r["method"], r["case"])
        assert key not in seen, key
        seen.add(key)
        assert r["speaker"] == case_speakers[r["case"]]
        rows_by[item["group_id"]].append(r)
out = ROOT / "extended/common-comparison"
out.mkdir(parents=True, exist_ok=True)
results = []
allrows = []
for g in meta["groups"]:
    gid = g["id"]
    newrows = []
    for c in cases:
        value, status = point(gid, c["id"])
        newrows.append(
            dict(
                case=c["id"],
                speaker=c["speaker"],
                method=PML,
                value=value,
                status=status,
            )
        )
    rows = rows_by[gid] + newrows
    planned = [*meta["methods"], PML]
    valid = {
        m: {
            r["case"]: r
            for r in rows
            if r["method"] == m
            and r["status"] in g["admissible_status"]
            and r["value"] is not None
            and np.isfinite(r["value"])
        }
        for m in planned
    }
    counts = {
        m: dict(Counter(r["status"] for r in rows if r["method"] == m)) for m in planned
    }
    pending = any(r["status"].startswith("pending") for r in rows)
    selected = [m for m in planned if valid[m]]
    ids = (
        sorted(set.intersection(*[set(valid[m]) for m in selected])) if selected else []
    )
    summary = dict(
        id=gid,
        label=g["label"],
        unit=g["unit"],
        direction=g["direction"],
        status="pending" if pending else "measured" if ids else "no_common_support",
        planned_methods=planned,
        included_methods=selected,
        excluded_methods=[m for m in planned if m not in selected],
        status_counts=counts,
        common_case_ids=ids,
        common_recordings=len(ids),
        conditional=len(selected) != len(planned),
        selection="after terminal states include every method with at least one admissible finite value, then intersect all recording IDs; never select methods to enlarge support",
        methods={},
    )
    if ids and not pending:
        speakers = sorted({valid[selected[0]][i]["speaker"] for i in ids})
        values = np.stack(
            [
                [
                    np.mean(
                        [
                            valid[m][i]["value"]
                            for i in ids
                            if valid[m][i]["speaker"] == s
                        ]
                    )
                    for m in selected
                ]
                for s in speakers
            ]
        )
        means = values.mean(0)
        draws = np.random.default_rng(20261014).integers(
            0, len(speakers), (2000, len(speakers))
        )
        boot = values[draws].mean(1)
        ci = np.quantile(boot, [0.025, 0.975], axis=0)
        bootstrap_path = out / (gid + ".bootstrap.npz")
        np.savez_compressed(
            bootstrap_path,
            draws=draws,
            speaker_values=values,
            bootstrap=boot,
            speakers=np.asarray(speakers),
            methods=np.asarray(selected),
        )
        summary["bootstrap_sha256"] = sha(bootstrap_path)
        ranks = []
        for v in means:
            ranks.append(
                1
                + sum(
                    ((w > v) if g["direction"] == "higher" else (w < v))
                    and not np.isclose(w, v, rtol=1e-9, atol=1e-12)
                    for w in means
                )
            )
        summary.update(
            common_speakers=len(speakers),
            methods={
                m: dict(
                    value=float(means[j]), rank=int(ranks[j]), ci95=ci[:, j].tolist()
                )
                for j, m in enumerate(selected)
            },
        )
    results.append(summary)
    allrows.extend([dict(group_id=gid, **r) for r in rows if r["method"] == PML])
write(
    out / "results.json",
    dict(
        driver_sha256=sha(__file__),
        historical_records_sha256=sha(OLD / "raw-records.json"),
        historical_groups_sha256=sha(OLD / "group-contracts-and-aggregates.json"),
        compatibility_evidence_sha256=sha(OLD / "compatibility-check.json"),
        mos_reuse_provenance_sha256=sha(ROOT / "extended/mos-reuse-provenance.json"),
        source_evidence=evidence,
        groups=results,
        pml_recordings=allrows,
        limits=[
            "historical UTMOS used four CPU threads, new PML uses two; checkpoint/config/preprocessor match",
            "full-length edits separate from common-prefix quality",
            "quantization NPZ is research-only, standard .pml unchanged",
            "within-method precision perturbations differ by representation; not matched-bit-rate codec comparison",
            "historical missing/failed methods retained in status tables; conditional rankings explicitly labelled",
        ],
    ),
)
