"""費用範囲の別注記と、承認済み固定短音声だけを照合する。"""

import base64
import io
import wave
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urlsplit

from common import METHODS, code, count, digest, require, scalar, sha

COST_STATUS = "partial_derived_preparation_not_final"
COST_CONDITIONS = ("native", "pitch_minus3", "pitch_plus3")
COST_METHODS = ("candidate", "pml", "world_harvest")
AUDIO_CASES = ("librispeech_1089-134686-0008", "librispeech_1188-133604-0003")


def cost_projection(sources):
    data = sources.data("cost_report", "cost_report")
    require(data["schema_version"] == 1 and data["report_status"] == COST_STATUS, "費用原状態は部分報告のまま保持")
    require(data["planned_cases"] == 120 and data["planned_conditions_per_method"] == {
        "candidate": 360, "pml": 360, "world_harvest": 120}, "費用予定分母不一致")
    require(data["duration_basis"] == "full original encoded excerpt; not common quality window",
            "RTF分母は原入力全抜粋秒")
    require(all(data[key] is None for key in ("speed_ranking", "codec_total_seconds", "shared_model_assets_bytes")),
            "速度順位/codec総時間/共有資産量は未確定のまま")
    audit = sources.data("cost_coverage_audit", "cost_coverage_audit")
    require(audit["schema_version"] == 1 and audit["validation_state"] == "validated_end"
            and audit["scope"] == "terminal-source-coverage-audit", "終端出典の別監査が必要")
    require(audit["cost_sha256"] == sources.entries["cost_report"]["sha256"]
            and audit["run_plan_sha256"] == sources.entries["plan"]["sha256"], "費用と同一計画のbinding不一致")
    require(audit["coverage"] == data["coverage"], "別注記と保存費用範囲が不一致")
    identities = set()
    proof = []
    for row in audit["terminal_receipts"]:
        require(set(row) == {"method", "chunk_id", "sha256", "run_plan_sha256", "validation_state"},
                "費用監査の終端列不正")
        identity = (row["method"], row["chunk_id"])
        require(identity not in identities and row["validation_state"] == "validated_end"
                and row["run_plan_sha256"] == audit["run_plan_sha256"], "費用出典終端/計画不一致")
        require(sha(row["sha256"]) in data["scientific_digests"], "費用出典SHAが原費用JSONにありません")
        identities.add(identity)
        proof.append(dict(row))
    expected = {(m, f"chunk-{i:02d}") for m in COST_METHODS for i in range(1, 11)}
    require(identities == expected, "費用は候補/PML/WORLD各10終端receipt監査が必要")
    cover_seen = set()
    coverage = []
    for row in data["coverage"]:
        identity = (row["method"], row["condition"])
        require(identity not in cover_seen and row["planned_denominator"] == 120, "費用範囲分母/重複不正")
        keys = ("successful_support", "failed_or_other_terminal_support", "unobserved_support")
        require(sum(count(row[k], 120) for k in keys) == 120, "費用範囲分母が合いません")
        coverage.append({key: row[key] for key in ("method", "condition", "planned_denominator", *keys)})
        cover_seen.add(identity)
    require(cover_seen == {(m, c) for m in COST_METHODS for c in (
        ("native",) if m == "world_harvest" else COST_CONDITIONS)}, "費用条件が不足")
    rows, seen = [], set()
    for row in data["partial_summaries"]:
        identity = tuple(row[key] for key in ("method", "condition", "category", "metric", "unit"))
        require(identity not in seen and row["method"] in COST_METHODS
                and row["condition"] in (*COST_CONDITIONS, "case"), "費用観測の重複/条件不正")
        code(row["category"])
        code(row["metric"])
        require(row["unit"] in ("seconds", "bytes") and row["planned_denominator"] == 120,
                "費用単位/分母不正")
        count(row["measured_support"], 120)
        require(row["measured_support"] + count(row["missing_or_failed"], 120) == 120, "費用欠測分母不一致")
        if row["successful_condition_support"] is not None:
            count(row["successful_condition_support"], row["measured_support"])
        copied = {key: row[key] for key in ("method", "condition", "category", "metric", "unit",
                  "planned_denominator", "measured_support", "missing_or_failed", "successful_condition_support")}
        for name in ("values", "rtf", "bytes_per_second", "bits_per_second"):
            if name not in row:
                continue
            value = row[name]
            require(value["support"] == row["measured_support"], "費用平均/中央値の支持不一致")
            for key in ("mean", "median"):
                require(scalar(value[key]) is None or value[key] >= 0, "負の費用観測")
            copied[name] = {key: value[key] for key in ("support", "mean", "median")}
        rows.append(copied)
        seen.add(identity)
    threads = data["thread_counts"]
    require(set(threads) == set(COST_METHODS) and threads["candidate"] is None
            and threads["pml"] == threads["world_harvest"] == 2
            and data["candidate_thread_count_reported_by_operator"] == 1, "費用thread来歴が変化しています")
    return {"schema_version": 1, "source_status_unchanged": COST_STATUS,
            "cost_sha256": sources.entries["cost_report"]["sha256"],
            "run_plan_sha256": audit["run_plan_sha256"],
            "audit_source": sources.identity("cost_coverage_audit"),
            "terminal_receipts": proof, "coverage": coverage, "observations": rows,
            "thread_counts": dict(threads), "candidate_operator_reported_threads": 1,
            "scope": "coverage_annotation_only_not_finality_or_speed_ranking"}


class AudioHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []
        self.strong_text = None
        self.last_strong = ""

    def handle_starttag(self, tag, attrs):
        require(tag not in {"script", "iframe", "object", "embed", "video"}, "凍結HTMLに動的/外部埋込があります")
        values = dict(attrs)
        require(not any(key.lower().startswith("on") for key in values), "HTMLイベント属性は禁止")
        if tag == "strong":
            self.strong_text = []
        if tag == "audio":
            require("src" in values, "音声srcが必要")
            self.sources.append((self.last_strong, values["src"]))
        require(tag != "source", "このprototypeはaudio srcのdata URIのみ対応")

    def handle_data(self, data):
        if self.strong_text is not None:
            self.strong_text.append(data)

    def handle_endtag(self, tag):
        if tag == "strong" and self.strong_text is not None:
            self.last_strong = " ".join("".join(self.strong_text).split())
            self.strong_text = None


def audio_blob(src):
    require(isinstance(src, str) and src.startswith("data:audio/wav;base64,"), "承認音声はWAV data URIのみ")
    return base64.b64decode(src.split(",", 1)[1], validate=True)


def validate_audio(sources):
    manifest = sources.data("audio_manifest", "audio_manifest")
    require(manifest["schema_version"] == 1 and manifest["scope"] == "approved-fixed-native-clips",
            "承認済み固定短音声manifestが必要")
    expected = {(case, method, "native") for case in AUDIO_CASES for method in (*METHODS, "original")}
    seen, identities, rows = set(), [], []
    names = {"pml": "現ベース PML", "world_harvest": "WORLD Harvest", "original": "原音",
             "ahm_cartesian_node_editor_v1": "候補 aHM＋Cartesian編集"}
    for clip in manifest["clips"]:
        identity = tuple(clip[key] for key in ("case", "method", "condition"))
        require(identity in expected and identity not in seen, "音声許可範囲/重複不正")
        require(clip["status"] in ("available", "upstream_failed"), "音声は保存済み終端のみ")
        if clip["status"] == "available":
            require(set(clip) == {"case", "method", "condition", "status", "src", "sha256",
                    "source_output_sha256", "samples", "start_sample", "end_sample", "sample_rate",
                    "license", "source_url", "changes"}, "公開音声の列不正")
            require(clip["license"] == "CC-BY-4.0" and clip["start_sample"] == 0
                    and clip["sample_rate"] == 16000 and 0 < count(clip["samples"], 32000)
                    and clip["end_sample"] == clip["samples"], "短音声の許可範囲外")
            url = urlsplit(clip["source_url"])
            require(url.scheme == "https" and url.netloc == "www.openslr.org", "OpenSLR公式出典が必要")
            sha(clip["source_output_sha256"])
            blob = audio_blob(clip["src"])
            require(digest(blob) == sha(clip["sha256"]), "音声SHA不一致")
            with wave.open(io.BytesIO(blob)) as wav:
                require(wav.getnchannels() == 1 and wav.getframerate() == 16000
                        and wav.getnframes() == clip["samples"], "短音声ヘッダ不一致")
            caption = f'{clip["case"]} / {names[clip["method"]]}'
            identities.append((caption, clip["sha256"]))
        else:
            require(set(clip) == {"case", "method", "condition", "status", "reason_code"}
                    and clip["reason_code"] == "generation_failed", "欠測音声は上流失敗の明記が必要")
        displayed = {key: clip[key] for key in ("case", "method", "condition", "status")}
        if clip["status"] == "available":
            displayed["src"] = clip["src"]
        rows.append(displayed)
        seen.add(identity)
    require(seen == expected, "固定2録音×原音/PML/WORLD/候補の音声状態が必要")
    parser = AudioHTML()
    parser.feed(sources.blobs["ordinary_html"].decode("utf-8"))
    require(Counter((caption, digest(audio_blob(src))) for caption, src in parser.sources) == Counter(identities),
            "凍結HTMLの録音/方式表示・音声bytesと承認manifest不一致")
    attribution = sources.blobs["audio_attribution"].decode("utf-8")
    require("https://creativecommons.org/licenses/by/4.0/" in attribution
            and "LibriVox" in attribution and "openslr.org" in attribution, "承認帰属HTMLの必須出典が不足")
    attribution_parser = AudioHTML()
    attribution_parser.feed(attribution)
    require(not attribution_parser.sources, "帰属HTMLへ追加音声を含められません")
    return rows
