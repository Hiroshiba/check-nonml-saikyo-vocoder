"""Planned native edit and representation coverage; no missing-as-success."""

from run_edits import ROOT, read, write, sha

spec = read(ROOT / "input-contract.json")
rows = []
unsupported = {
    "time_scale1p25": "time scaling not implemented in frozen PML parameters",
    "slope_minus3": "spectral tilt control not implemented",
    "slope_plus3": "spectral tilt control not implemented",
    "interpolation": "binary NM interpolation is undefined in frozen representation; no new blend invented",
}
for c in spec["cases"]:
    for condition, reason in unsupported.items():
        rows.append(
            dict(
                case=c["id"],
                speaker=c["speaker"],
                condition=condition,
                status="unsupported",
                reason=reason,
            )
        )
write(
    ROOT / "extended/unsupported-coverage.json",
    dict(
        driver_sha256=sha(__file__),
        native_contract_sha256=sha(ROOT / "native-contract.json"),
        planned_cases=120,
        rows=rows,
        scope="unsupported controls/representation operations, separate from unedited preservation measurements",
    ),
)
