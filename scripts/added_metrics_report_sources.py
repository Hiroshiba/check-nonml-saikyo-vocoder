"""生計測証跡を保存し、公開用のパス秘匿と音声抜粋を作る。重み・全長音声は含めない。"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np

from vocoderbench import audio_samples

ROOT = Path(__file__).resolve().parents[1]
REASON = "実行環境の絶対パスをリポジトリ相対のデータ参照へ置換。環境外のprivate path・認証値・署名URLは秘匿。数値は変更しない。"
PRIVATE_PATH = re.compile(r"/(?:workspace|home|root|tmp)/[^\s\"'<>),;]*")
SIGNED_URL = re.compile(r"https?://[^\s\"'<>]+[?&](?:X-Amz-[^\s\"'<>]+|X-Goog-[^\s\"'<>]+|sig=[^\s\"'<>]+)", re.I)
SECRET_VALUE = re.compile(r"(?i)(authorization\s*[:=]\s*(?:bearer\s+)?|(?:access_token|api_key|password|secret|hf_token)\s*[:=]\s*)[^\s,;\"']+")
MAX_PUBLIC_BYTES = 9 * 1024 * 1024
SECRET_KEYS = {"authorization", "access_token", "api_key", "password", "secret", "hf_token", "refresh_token"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest_bytes(content):
    return hashlib.sha256(content).hexdigest()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def encoded(data):
    return (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def save(path, data, *, allow_split=False):
    path = Path(path)
    content = encoded(data)
    if len(content) > 256 * 1024:
        content = (json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    if len(content) <= MAX_PUBLIC_BYTES:
        path.write_bytes(content)
        return []
    if not allow_split:
        raise ValueError(f"公開JSONは9 MiB以下で保存してください: {path.name}")
    # 公開転送上限に対する保存形式の分割。復元式と各部hashを必ず残す。
    parts = []
    text = content.decode("utf-8")
    for start in range(0, len(text), 1_000_000):
        part = path.with_name(path.stem + f"--part-{len(parts) + 1:03d}.json")
        payload = {"format": "utf8_json_fragment", "fragment": text[start:start + 1_000_000]}
        save(part, payload)
        parts.append({"path": part.name, "sha256": digest(part), "bytes": part.stat().st_size})
    save(path, {"format": "utf8_json_text_fragments", "parts": parts,
                "reconstructed_sha256": digest_bytes(content), "reconstructed_bytes": len(content),
                "reconstruction": "partsを記載順に読み、各fragment文字列を連結すると元のJSON全文。数値を含め全内容を保持。"})
    return parts


def sanitize_text(value):
    value = value.replace(str(ROOT) + "/", "").replace(str(ROOT), ".")
    value = PRIVATE_PATH.sub(lambda m: "<private-path>/" + Path(m.group()).name, value)
    value = SIGNED_URL.sub("<signed-url-redacted>", value)
    return SECRET_VALUE.sub(lambda m: m.group(1) + "<redacted>", value)


def sanitize(value):
    if isinstance(value, dict):
        return {sanitize_text(str(key)): "<redacted>" if str(key).lower() in SECRET_KEYS else sanitize(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return sanitize_text(value) if isinstance(value, str) else value


def public_name(relative):
    return "raw--" + "--".join(relative.parts)


def expose(relative):
    """要約・実行条件は直接公開し、重複する巨大な全行値は完全保存ZIPへまとめる。"""
    if relative.suffix != ".json":
        return False
    if len(relative.parts) == 1:
        return True
    if relative.parts[0] == "preparation":
        return True
    if relative.name == "results.json":
        return relative.parts[:2] in (("quality", "ecapa-00"), ("quality", "erb-00"), ("quality", "scoreq-00"))
    if relative.name in ("contract.json", "initialization.json",
                         "configuration.json", "asset-acquisition.json", "execution.json", "progress.json",
                         "serialized-size.json", "aggregation-contract.json", "preparation.json"):
        return True
    return False


def export_sources(run, output, archive_folder, extras):
    """全JSON・ログ・説明文を無欠落でアーカイブ。公開run直下はHTML/JSONのみ。"""
    paths = sorted(p for p in run.rglob("*") if p.is_file() and p.suffix in (".json", ".log", ".txt"))
    if not paths:
        raise ValueError("保存する計測証跡がありません")
    archive_folder.mkdir(parents=True, exist_ok=True)
    ledger, archives, handles, names, logs = [], {}, {}, {}, []
    try:
        for source in paths:
            relative = source.relative_to(run)
            group = relative.parts[0] if len(relative.parts) > 1 else "execution"
            if group not in handles:
                target = archive_folder / f"run-001-{group}.zip"
                if target.exists():
                    raise FileExistsError(f"既存アーカイブは上書きしません: {target}")
                handles[group] = ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=9)
                archives[group] = target
            raw = source.read_bytes()
            data = sanitize(json.loads(raw)) if source.suffix == ".json" else sanitize_text(raw.decode("utf-8"))
            transformed = encoded(data) if source.suffix == ".json" else data.encode("utf-8")
            handles[group].writestr(str(relative), transformed)
            if source.suffix == ".log":
                logs.append({"source": str(source.relative_to(ROOT)), "source_sha256": digest_bytes(raw), "text": data})
            published = public_name(relative) if expose(relative) else None
            public_parts = []
            if published:
                if published in names:
                    raise ValueError("公開名が重複しています")
                public_parts = save(output / published, data, allow_split=True)
                names[published] = str(relative)
            ledger.append({"source": str(source.relative_to(ROOT)), "source_sha256": digest_bytes(raw),
                "source_bytes": len(raw), "sanitized_sha256": digest_bytes(transformed),
                "sanitized_bytes": len(transformed), "transformation": REASON,
                "archive": str(archives[group].relative_to(ROOT)), "archive_member": str(relative),
                "public_json": published, "public_parts": public_parts,
                "public_sha256": digest(output / published) if published else None,
                "public_format": "9 MiBを超えるJSONは空白のみ削減。全値は保持。" if published else None})
    finally:
        for handle in handles.values():
            handle.close()
    for label, source in extras.items():
        raw = source.read_bytes()
        transformed = encoded(sanitize(json.loads(raw)))
        published = label + ".json"
        public_parts = save(output / published, sanitize(json.loads(raw)), allow_split=True)
        ledger.append({"source": str(source.relative_to(ROOT)), "source_sha256": digest_bytes(raw),
                       "source_bytes": len(raw), "sanitized_sha256": digest_bytes(transformed),
                       "sanitized_bytes": len(transformed), "transformation": REASON, "public_json": published, "public_parts": public_parts,
                       "public_sha256": digest(output / published)})
    archive_records = [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest(path),
                        "group": group, "published_on_pages": False} for group, path in archives.items()]
    for record in archive_records:
        if record["bytes"] > MAX_PUBLIC_BYTES:
            path = ROOT / record["path"]
            parts = []
            with path.open("rb") as stream:
                while chunk := stream.read(MAX_PUBLIC_BYTES):
                    part = path.with_name(path.name + f".part-{len(parts) + 1:03d}")
                    part.write_bytes(chunk)
                    parts.append({"path": str(part.relative_to(ROOT)), "bytes": len(chunk), "sha256": digest_bytes(chunk)})
            path.unlink()
            record.update(storage_parts=parts, reconstruction="storage_partsを記載順にバイト連結すると元ZIP。各partと復元ZIPのSHA256を保持。")
    result = {"schema_version": 1, "source_files": len(ledger), "files": ledger, "archives": archive_records,
        "publication_note": "全長音声・モデル重みは非公開。音声パスと表現パスはデータ参照であり、ダウンロードリンクではない。"
                            "圧縮証跡はGit保存のみでPagesへ配置しない。元ファイルは実行保存先に保持し、変換前後のSHA256を記録。",
        "transform_reason": REASON,
        "excluded_generated_documents": "各測定器のHTMLとREADMEは再保存対象外。全計測値・設定は元JSONにあり、今回の完成HTMLを別途保存する。",
        "excluded_binary_formats": ["npy", "npz", "wav", "flac", "ckpt", "onnx", "safetensors"],
        "source_counts_by_suffix": dict(Counter(path.suffix for path in paths))}
    save(output / "execution-logs.json", {"format": "sanitized_execution_logs", "transformation": REASON, "logs": logs}, allow_split=True)
    save(output / "provenance-index.json", result)
    return result


def collect_audio(run, dataset):
    from added_metrics_report_data import CONDITIONS, CONDITION_LABELS, LABELS, METHODS
    entries = {row["id"]: row for row in dataset["entries"]}
    allowed = dataset["public_audio_example_ids"]
    if len(allowed) != 2:
        raise ValueError("公開許可済みの固定2録音以外は載せません")
    samples = []
    for identifier in allowed:
        entry = entries[identifier]
        case = {"id": identifier, "kind": "natural_speech", "sr": entry["sample_rate"]}
        folder = run / "audio" / identifier
        audio_samples.collect(samples, case, "identity", np.load(folder / "original.npy", allow_pickle=False))
        samples[-1].update(condition="unedited", display_label=LABELS["identity"], source=entry["source"])
        for method in METHODS:
            for condition in CONDITIONS:
                wave = np.load(folder / method / f"{condition}.npy", allow_pickle=False)
                key = method if condition == "unedited" else f"{method}__{condition}"
                previous = len(samples)
                audio_samples.collect(samples, case, key, wave)
                if len(samples) != previous + 1:
                    raise ValueError("指定音声例を保存できません")
                samples[-1].update(condition=condition, base_method=method, source=entry["source"],
                    display_label=LABELS[method] + "・" + CONDITION_LABELS[condition])
    return {"schema_version": 1, "public_audio_example_ids": allowed, "samples": samples,
            "selection_note": "固定許可2録音の先頭最大2秒のみ。原音・無編集・±3半音・±6 dB。"
                              "WAV IEEE float32、無正規化・無クリッピング・無再標本化。+6 dBは音量注意。",
            "attribution": "LibriSpeech test-clean (OpenSLR 12), CC BY 4.0。先頭最大2秒への切出しと各方式の合成・操作。",
            "source_url": "https://www.openslr.org/12/", "license_url": "https://creativecommons.org/licenses/by/4.0/"}
