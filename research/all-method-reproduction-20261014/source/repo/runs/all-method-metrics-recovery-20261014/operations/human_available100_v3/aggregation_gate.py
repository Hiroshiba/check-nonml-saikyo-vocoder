"""集約直前に事前固定source/全800終端recordを照合し、事後条件変更を拒否する。"""
from types import SimpleNamespace

from settings import OUT
from all_metrics_common import METHODS, now, read
from release_proof import verify_release
from supervisor import inspect_records, require_inputs
from vocoderbench.quality_core import sha256, write_json


def verify_aggregation():
    preflight = OUT / 'preflight-freeze-v3.json'
    release = read(OUT / 'execution-release-v3.json')
    if set(release.get('released_batches', [])) != set(range(10)):
        raise ValueError('全10batchの親資源releaseが未完です')
    args = SimpleNamespace(preflight_sha256=release['preflight_sha256'], batch=0,
        inputs_sha256=sha256(OUT / 'inputs.json'),
        input_contract_sha256=sha256(OUT / 'input-contract.json'))
    receipt = require_inputs(args)
    specs = read(OUT / 'inputs.json')
    states = {}
    for method in METHODS:
        rows = inspect_records(method, specs, verify=True)
        if len(rows) != 100 or any(row['status'] not in ('measured', 'failed') for row in rows):
            raise ValueError('全8方式×100録音が未終端。評定一致をまだ計算しません')
        states[method] = rows
    write_json(OUT / 'rankings/aggregation-start-gate.json', {'verified_at_utc': now(),
        'preflight_sha256': sha256(preflight), 'fixed_input_receipt': receipt,
        'release_proof': verify_release(preflight, 0), 'terminal_feature_records': states,
        'scope': 'metadata/identity/hash gate only; no agreement metric yet'})
