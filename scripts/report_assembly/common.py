"""表示専用の入力境界。科学モジュールは読み込まない。"""

import hashlib
import json
import math
import re
from pathlib import Path

LIMIT = 10 * 1024 * 1024
VIEWS = ("canonical_complex4099", "amp3075", "rawcomplex4099")
REPRESENTATIONS = tuple(("candidate", view) for view in VIEWS) + (("pml", "pml2110"),)
TARGETS = ("log_f0", "rms_dbfs", "spectral_slope")
CONDITIONS = ("within_speaker", "across_speaker")
ESTIMANDS = ("flat_stratum", "x_speaker_macro", "nested_phone_context")
FEATURE_AXES = tuple(f"abx/{c}/{e}" for c in CONDITIONS for e in ESTIMANDS) + tuple(
    f"readout/{target}" for target in TARGETS
)
METHODS = ("ahm_cartesian_node_editor_v1", "pml", "world_harvest")
BASE_VERSION = "pml-lowband-fwcep60-v1"
PUBLIC_NAMES = {
    "plan": "plan.json", "ordinary_summary": "ordinary-summary.json",
    "ordinary_html": "ordinary.html", "axis_metadata": "axis-metadata.json",
    "feature_public": "feature-public.json", "cost_report": "cost.json",
    "audio_manifest": "audio-manifest.json", "audio_attribution": "audio-attribution.html",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "SHA256形式不正")
    return value


def count(value, maximum=None):
    require(type(value) is int and value >= 0, "支持数は非負整数が必要")
    require(maximum is None or value <= maximum, "支持数が予定分母を超過")
    return value


def scalar(value):
    require(value is None or type(value) in (int, float) and math.isfinite(value), "非有限数値")
    return value


def interval(value):
    if value is not None:
        require(isinstance(value, list) and len(value) == 2, "95%区間形式不正")
        require(all(scalar(v) is not None for v in value) and value[0] <= value[1], "95%区間不正")
    return value


def code(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-zA-Z0-9_.+-]{1,100}", value), "識別子不正")
    return value


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "JSONキー重複")
        result[key] = value
    return result


def decode(blob):
    def reject(value):
        raise ValueError("JSON非有限数値: " + value)
    return json.loads(blob, object_pairs_hook=pairs, parse_constant=reject)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def public_text(value):
    """追加の漏出防止。公開承認そのものの代わりにはならない。"""
    if isinstance(value, dict):
        forbidden = {"path", "sourcepath", "traceback", "coefficients", "prediction", "truth"}
        require(not forbidden.intersection(value), "公開JSONに私有列が含まれています")
        for item in value.values():
            public_text(item)
    elif isinstance(value, list):
        for item in value:
            public_text(item)
    elif isinstance(value, str):
        require(not re.search(r"(?:file://|/(?:workspace|home|tmp|Users|private)/|[A-Z]:\\)", value),
                "公開内容にローカルパスが含まれています")


class Sources:
    """私有manifestの明示ファイルだけ読む。pathを成果物へ引き継がない。"""

    def __init__(self, manifest_path, expected_sha):
        self.manifest_path = Path(manifest_path).resolve()
        blob = self.manifest_path.read_bytes()
        require(digest(blob) == sha(expected_sha), "入力manifest SHA不一致")
        self.manifest_sha = expected_sha
        self.manifest = decode(blob)
        require(self.manifest["schema_version"] == 1, "組立てmanifest版不正")
        require(self.manifest["scope"] == "terminal-presentation-only", "表示専用manifestが必要")
        self.entries, self.blobs, self.paths = {}, {}, {}
        allowed_roles = set(PUBLIC_NAMES) | {"checkpoint", "checkpoint_storage", "readout_summary",
                                            "abx_summary", "comparison_summary", "cost_coverage_audit"}
        for entry in self.manifest["sources"]:
            require(set(entry) == {"id", "role", "path", "sha256", "bytes"}, "入力宣言列不正")
            identifier = code(entry["id"])
            require(identifier not in self.entries, "入力ID重複")
            require(entry["role"] in allowed_roles, "入力の役割がallowlist外です")
            path = (self.manifest_path.parent / entry["path"]).resolve()
            require(path.is_file(), "宣言入力がファイルではありません")
            data = path.read_bytes()
            require(len(data) == count(entry["bytes"]) and digest(data) == sha(entry["sha256"]),
                    "宣言入力のbyte数/SHA不一致")
            require(len(data) < LIMIT, "入力は1ファイル10MiB未満")
            self.entries[identifier], self.blobs[identifier], self.paths[identifier] = entry, data, path
        require(len(set(self.paths.values())) == len(self.paths), "同一入力の重複宣言")
        require(len(self.entries) == 40, "公開8＋区間保存20＋特徴11＋費用監査1の入力が必要")

    def data(self, identifier, role=None):
        require(identifier in self.entries, "必要な入力IDがありません")
        require(role is None or self.entries[identifier]["role"] == role, "入力の役割不一致")
        return decode(self.blobs[identifier])

    def identity(self, identifier):
        entry = self.entries[identifier]
        return {key: entry[key] for key in ("id", "role", "sha256", "bytes")}

    def by_role(self, role):
        return [key for key, row in self.entries.items() if row["role"] == role]

    def recheck(self):
        require(digest(self.manifest_path.read_bytes()) == self.manifest_sha, "manifest変更検出")
        for key, path in self.paths.items():
            require(path.read_bytes() == self.blobs[key], "組立て中の入力変更検出")

    def approved_public(self):
        approved = self.manifest["publication_approval"]
        require(set(approved) == set(PUBLIC_NAMES), "公開承認の役割が過不足")
        result = {}
        for role, filename in PUBLIC_NAMES.items():
            entry = self.entries[role]
            require(entry["role"] == role and approved[role] == entry["sha256"], "公開承認SHA不一致")
            blob = self.blobs[role]
            if filename.endswith(".json"):
                public_text(decode(blob))
            else:
                public_text(blob.decode("utf-8"))
            result[filename] = blob
        return result
