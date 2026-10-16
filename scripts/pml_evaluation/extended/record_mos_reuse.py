"""Record provenance for reuse of completed unedited MOS, avoiding duplicate inference."""

from run_edits import ROOT, read, write, sha
import numpy as np
import hashlib

mainpath = ROOT / "results/utmosv2/contract.json"
main = read(mainpath)
contracts = {}
for stage in ("quality", "quantization-quality"):
    p = ROOT / "extended" / stage / "utmosv2/contract.json"
    c = read(p)
    for key in ("assets", "options", "environment", "threads"):
        assert c[key] == main[key], key
    assert c["seed"].replace(" ", "") == main["seed"].replace(" ", "")
    contracts[stage] = {
        "path": str(p.relative_to(ROOT)),
        "sha256": sha(p),
        "assets_options_environment_threads_seed_match": True,
    }
rows = []
for case in read(ROOT / "input-contract.json")["cases"]:
    cid = case["id"]
    p = ROOT / "results/utmosv2/measurements" / f"{cid}.json"
    r = read(p)
    n = read(ROOT / "native" / cid / "record.json")
    wave = np.load(n["audio"]["path"], allow_pickle=False)
    assert r["contract_sha256"] == sha(mainpath) and r["audio_sha256"] == n["audio"][
        "sha256"
    ] == sha(n["audio"]["path"])
    assert r["evaluated_samples"] == len(wave) == n["audio"]["samples"]
    pcmhash = hashlib.sha256(
        np.ascontiguousarray(wave, dtype="<f8").tobytes()
    ).hexdigest()
    assert pcmhash == r["output_pcm_sha256"]
    rows.append(
        dict(
            case=cid,
            source_result_sha256=sha(p),
            full_audio_sha256=r["audio_sha256"],
            full_pcm_sha256=pcmhash,
            samples=len(wave),
            value=r["value"],
        )
    )
write(
    ROOT / "extended/mos-reuse-provenance.json",
    dict(
        driver_sha256=sha(__file__),
        main_contract_sha256=sha(mainpath),
        contracts=contracts,
        rows=rows,
        scope="120 full-length native UTMOS results reused for edited/precision delta baselines; no duplicate inference",
        historical_comparison="Old models/config/preprocessor and sources match compatibility-check; historical CPU threads4 versus new2 disclosed.",
    ),
)
