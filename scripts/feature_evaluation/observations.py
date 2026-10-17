"""Read-only observation dispatch; private mapper is separately frozen."""

import importlib.util
import sys
from pathlib import Path
import numpy as np
from contracts import resolve, ContractError

DIMENSIONS = {
    "canonical_complex4099": 4099,
    "amp3075": 3075,
    "rawcomplex4099": 4099,
    "pml2110": 2110,
}


def observe(context, method, view, record, base):
    if record["status"] != "measured":
        raise ValueError("Upstream payload unavailable")
    if method == "candidate":
        mapper = resolve(context.root, context.config["private_native_mapper"])
        spec = importlib.util.spec_from_file_location(
            "private_native_feature_mapper", mapper
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.observe(record, base, context, view)
    if method != "pml" or view != "pml2110":
        raise ValueError("Method/view mismatch")
    sys.path.insert(0, str(Path(context.config["repository"]).resolve()))
    from vocoderbench.pml import load

    params = load(resolve(base, record["payload"]))
    if params.n_samples != record["samples"] or params.sample_rate != 16000:
        raise ContractError("PML payload input size/rate mismatch")
    matrix = np.column_stack((params.f0, params.fwcep, params.noise_mask)).astype(
        np.float64
    )
    times = np.asarray(params.times, dtype=np.float64)
    if (
        matrix.ndim != 2
        or matrix.shape[1] != 2110
        or times.shape != (len(matrix),)
        or np.any(np.diff(times) <= 0)
        or not np.isfinite(matrix).all()
        or not np.isfinite(times).all()
    ):
        raise ValueError("Invalid PML observed features")
    return (
        matrix,
        times,
        {
            "view": view,
            "dimension": 2110,
            "frame_count": len(times),
            "actual_times": True,
            "averaging": "frame equal; not continuous-time average",
            "outside_original_frame_count": int(
                np.sum(times > (record["samples"] - 1) / 16000)
            ),
            "last_frame_minus_last_sample_seconds": float(
                times[-1] - (record["samples"] - 1) / 16000
            ),
            "source": "saved positive synthesis-clock F0, FWCEP60, original noise mask2049; no PDD",
        },
    )


def targets(context, path, spec):
    sys.path.insert(0, str(Path(context.config["repository"]).resolve()))
    from vocoderbench.metrics import estimate_f0_yin
    from vocoderbench.assessment.acoustics import spectral_slope
    from vocoderbench.assessment.common import NotApplicable

    x = np.load(path, allow_pickle=False)
    if (
        x.dtype != np.float64
        or x.shape != (spec["samples"],)
        or spec["sample_rate"] != 16000
        or not len(x)
        or not np.isfinite(x).all()
    ):
        raise ValueError("Invalid target source")
    f = estimate_f0_yin(x, 16000)["f0_hz"]
    valid = f > 0
    power = float(np.mean(x * x))
    try:
        slope = spectral_slope(x, 16000, 300, 5000)
    except NotApplicable:
        slope = None
    return {
        "log_f0": float(np.log(f[valid]).mean()) if valid.any() else None,
        "rms_dbfs": float(10 * np.log10(power)) if power > 0 else None,
        "spectral_slope": slope,
    }
