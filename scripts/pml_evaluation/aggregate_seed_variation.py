"""Eight-seed stability: recordings/speakers remain the statistical units."""

import sys
import argparse
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from run_quality import REPO, read, write, sha, add_run_arguments, configure

sys.path.insert(0, str(REPO / "scripts"))
from all_metrics_rankings_acoustic import descriptors, extract
from all_metrics_rankings_core import finite


def main():
    global ROOT
    parser = argparse.ArgumentParser()
    add_run_arguments(parser)
    ROOT = configure(parser.parse_args())
    folder = ROOT / "results/seed-variation"
    summary = read(folder / "summary.json")
    contract = read(folder / "contract.json")
    assert summary["contract_sha256"] == sha(folder / "contract.json")
    spec = read(ROOT / "input-contract.json")["cases"]
    seeds = {(r["case"], r["seed"]): r for r in summary["rows"]}
    assert len(seeds) == len(summary["rows"]) == 840
    assert set(seeds) == {(c["id"], s) for c in spec for s in range(1, 8)}
    natives = {r["case"]: r for r in read(ROOT / "native-summary.json")["rows"]}
    inputs = {c["id"]: c for c in spec}
    for r in seeds.values():
        assert r["contract_sha256"] == summary["contract_sha256"]
        assert r["payload_sha256"] == natives[r["case"]]["payload"]["sha256"]
        assert r["reference_sha256"] == inputs[r["case"]]["input"]["sha256"]
    acoustic_path = ROOT / "results/acoustic/summary.json"
    erb_path = ROOT / "results/erb/summary.json"
    assert sha(acoustic_path) == contract["seed0_acoustic_sha256"]
    assert sha(erb_path) == contract["seed0_erb_sha256"]
    acoustic = {r["case"]: r for r in read(acoustic_path)["rows"]}
    erb = {r["case"]: r for r in read(erb_path)["rows"]}
    groups = []
    descriptor_list = [d for d in descriptors() if d["id"] != "existing.estoi"]
    descriptor_list.append(
        dict(id="existing.erb20", label="ERB20", unit="dB", direction="lower")
    )
    for d in descriptor_list:
        rows = []
        for c in spec:
            values, states = [], []
            for s in range(8):
                raw = acoustic[c["id"]] if s == 0 else seeds[(c["id"], s)]
                assert raw["speaker"] == c["speaker"]
                if d["id"] == "existing.erb20":
                    er = erb[c["id"]] if s == 0 else raw
                    value, status = (
                        er.get("value" if s == 0 else "erb20_value"),
                        er["status"],
                    )
                else:
                    value, status, _ = extract(raw, d)
                ok = status in ("measured", "ok") and finite(value)
                values.append(float(value) if ok else None)
                states.append(status if not ok else "measured")
            complete = all(v is not None for v in values)
            rows.append(
                dict(
                    case=c["id"],
                    speaker=c["speaker"],
                    status="measured" if complete else "incomplete_seed_support",
                    seed_values=values,
                    seed_states=states,
                    mean=float(np.mean(values)) if complete else None,
                    standard_deviation=float(np.std(values, ddof=0))
                    if complete
                    else None,
                    minimum=min(values) if complete else None,
                    maximum=max(values) if complete else None,
                    range=max(values) - min(values) if complete else None,
                )
            )
        supported = [r for r in rows if r["status"] == "measured"]
        speakers = defaultdict(list)
        for r in supported:
            speakers[r["speaker"]].append(r)
        aggregate = {}
        for field in ("mean", "standard_deviation", "range"):
            per_speaker = [
                float(np.mean([r[field] for r in group])) for group in speakers.values()
            ]
            aggregate[field] = float(np.mean(per_speaker)) if per_speaker else None
        groups.append(
            dict(
                id=d["id"],
                label=d["label"],
                unit=d["unit"],
                direction=d["direction"],
                complete_recordings=len(supported),
                complete_speakers=len(speakers),
                status_counts=dict(Counter(r["status"] for r in rows)),
                speaker_equal_weight=aggregate,
                rows=rows,
            )
        )
    write(
        folder / "stability-summary.json",
        dict(
            status="complete"
            if all(g["complete_recordings"] == 120 for g in groups)
            else "complete_with_missing_support",
            source_sha256={
                str(p): sha(p)
                for p in [
                    Path(__file__),
                    folder / "summary.json",
                    acoustic_path,
                    erb_path,
                    REPO / "scripts/all_metrics_rankings_acoustic.py",
                    REPO / "scripts/all_metrics_rankings_core.py",
                ]
            },
            scope="Fixed historical common-prefix windows; seeds 0 through 7 from identical encoded payloads.",
            aggregation="Require all eight seeds per recording and axis. Average seed values within each recording, then recordings within speaker, then speakers equally. Population standard deviation describes the eight fixed seeds, not sampling uncertainty. No additional ranking or pseudo-replicated confidence intervals.",
            estoi_and_mos="Seed zero only; excluded from repeated-seed summary.",
            groups=groups,
        ),
    )


if __name__ == "__main__":
    main()
