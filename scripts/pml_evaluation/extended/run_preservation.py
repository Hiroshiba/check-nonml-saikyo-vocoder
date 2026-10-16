"""Full-length original event and spectral-slope preservation; no edit algorithm."""

from portable_context import REPO

import traceback
import numpy as np
from run_edits import ROOT, sha, read, write, freeze
from pathlib import Path
from preserved_time_metric import original_events, evaluate_time, EVENT_RULE
from vocoderbench.assessment.acoustics import spectral_slope
from vocoderbench.assessment.common import NotApplicable, ok


def main():
    out = ROOT / "extended/preservation"
    spec = read(ROOT / "input-contract.json")
    native = read(ROOT / "native-contract.json")
    for name, digest in native["source_sha256"].items():
        if sha(REPO / name) != digest:
            raise ValueError("Frozen source changed: " + name)
    contract = dict(
        source_contract_sha256=sha(ROOT / "native-contract.json"),
        input_contract_sha256=sha(ROOT / "input-contract.json"),
        drivers={
            p.name: sha(p)
            for p in [
                Path(__file__),
                Path(__file__).with_name("run_edits.py"),
                Path(__file__).with_name("preserved_time_metric.py"),
            ]
        },
        event_rule=EVENT_RULE,
        slope_band_hz=[300, 5000],
        reference="original full length; no alignment/resampling/cropping",
        scope="preservation not edit tracking",
    )
    freeze(out / "contract.json", contract)
    sig = sha(out / "contract.json")
    rows = []
    for c in spec["cases"]:
        src = ROOT / "native" / c["id"] / "record.json"
        r = read(src)
        inp = Path(c["input"]["path"])
        inp = inp if inp.is_absolute() else ROOT.parent / inp
        if sha(inp) != c["input"]["sha256"]:
            raise ValueError("Original changed")
        if (
            r["status"] == "measured"
            and sha(r["audio"]["path"]) != r["audio"]["sha256"]
        ):
            raise ValueError("Native audio changed")
        for metric in ["time_preservation", "slope_preservation"]:
            dest = out / "measurements" / f"{c['id']}__{metric}.json"
            if dest.exists():
                row = read(dest)
                if row["contract_sha256"] != sig or row["native_record_sha256"] != sha(
                    src
                ):
                    raise ValueError("Preservation resume mismatch")
                rows.append(row)
                continue
            row = dict(
                case=c["id"],
                speaker=c["speaker"],
                metric=metric,
                contract_sha256=sig,
                native_record_sha256=sha(src),
                status="upstream_failed",
            )
            if r["status"] == "measured":
                try:
                    x = np.load(inp, allow_pickle=False)
                    y = np.load(r["audio"]["path"], allow_pickle=False)
                    if metric == "time_preservation":
                        value = evaluate_time(
                            original_events(x, 16000),
                            x,
                            16000,
                            y,
                            16000,
                            y,
                            16000,
                            scale=1.0,
                            preservation=True,
                        )
                    else:
                        a, b = (
                            spectral_slope(x, 16000, 300, 5000),
                            spectral_slope(y, 16000, 300, 5000),
                        )
                        value = ok(
                            abs(b - a),
                            "dB/oct",
                            reference_slope=a,
                            output_slope=b,
                            signed_error=b - a,
                        )
                    row.update(
                        status="measured"
                        if value["status"] == "ok"
                        else value["status"],
                        measurement=value,
                    )
                except NotApplicable as e:
                    row.update(status="not_applicable", reason=str(e))
                except Exception as e:
                    row.update(
                        status="failed", reason=str(e), traceback=traceback.format_exc()
                    )
            else:
                row["reason"] = r.get("reason")
            write(dest, row)
            rows.append(row)
    write(out / "summary.json", dict(contract_sha256=sig, rows=rows))


if __name__ == "__main__":
    main()
