"""Portable entry point for the frozen extended PML evaluation drivers.

All path options precede STAGE. Arguments after STAGE belong to that driver.
This wrapper changes paths only. It has not generated the published results.
"""

import argparse
import runpy
import sys
from pathlib import Path

import portable_context
from run_quality import configure, verify_native

HERE = Path(__file__).resolve().parent
STAGES = {
    str(p.relative_to(HERE).with_suffix("")): p
    for group in ("extended", "abx", "auxiliary")
    for p in (HERE / group).glob("*.py")
    if p.stem
    not in {
        "run_edits",
        "extract_features",
        "run_train_features",
        "abx_inputs",
        "frozen_abx_statistics",
        "human_statistics",
        "preserved_time_metric",
    }
}
# These three modules are both executable stages and shared helpers.
for name in ("run_edits", "extract_features", "run_train_features"):
    STAGES["extended/" + name] = HERE / "extended" / (name + ".py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-root", type=Path, default=Path("runs/pml-package-evaluation-20261016")
    )
    parser.add_argument(
        "--corpora-root", type=Path, default=Path("data/pml-evaluation/corpora")
    )
    parser.add_argument(
        "--historical-root", type=Path, default=Path("data/pml-evaluation/historical")
    )
    parser.add_argument(
        "--asv-input-root",
        type=Path,
        default=Path("data/pml-evaluation/human-similarity"),
    )
    parser.add_argument("--model-cache", type=Path, default=Path("models/utmosv2"))
    parser.add_argument("stage", choices=sorted(STAGES))
    parser.add_argument("driver_arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    configure(args)
    verify_native()
    portable_context.configure(args)
    for group in ("extended", "abx", "auxiliary"):
        sys.path.insert(0, str(HERE / group))
    sys.argv = [str(STAGES[args.stage]), *args.driver_arguments]
    runpy.run_path(str(STAGES[args.stage]), run_name="__main__")


if __name__ == "__main__":
    main()
