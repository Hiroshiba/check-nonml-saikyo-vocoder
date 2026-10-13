"""保存した正式ASR・既存assessment結果を話者別に集計する。再推論しない。"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vocoderbench.logging_utils import run_cli  # noqa: E402

OUTPUT = ROOT / "runs/added-metrics-20261014/asr"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def describe(values):
    return {"count": len(values), "mean": statistics.mean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "min": min(values) if values else None, "max": max(values) if values else None}


def scores(rows):
    result = {"case_count": len(rows), "speaker_count": len({r["spec"]["speaker"] for r in rows})}
    for metric in ("cer", "wer"):
        items = [r["result"]["scores"][metric] for r in rows]
        denominator = sum(x["truth_tokens"] for x in items)
        result[metric] = {"truth_tokens": denominator, "micro": {}, "utterance_macro": {}}
        for field in ("reference_rate", "output_rate", "delta"):
            numerator = sum(x["reference_errors"] if field == "reference_rate" else x["output_errors"]
                            if field == "output_rate" else x["output_errors"] - x["reference_errors"] for x in items)
            result[metric]["micro"][field] = numerator / denominator if denominator else None
            result[metric]["utterance_macro"][field] = describe([x[field] for x in items])
    return result


def grouped(rows):
    by_speaker = defaultdict(list)
    for row in rows:
        by_speaker[row["spec"]["speaker"]].append(row)
    speakers = {speaker: scores(group) for speaker, group in sorted(by_speaker.items())}
    overall = scores(rows)
    for metric in ("cer", "wer"):
        overall[metric]["speaker_macro"] = {
            field: describe([x[metric]["utterance_macro"][field]["mean"] for x in speakers.values()])
            for field in ("reference_rate", "output_rate", "delta")}
    return {"overall": overall, "by_speaker": speakers}


def summarize():
    result_path = OUTPUT / "assessment/results.json"
    report = read(result_path)
    rows = report["rows"]
    if len(rows) != 110:
        raise ValueError("予定110jobが完了するまで最終集計しません")
    recordings = [read(path) for path in sorted((OUTPUT / "recognitions").glob("*.json"))]
    summary = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "scope": report["scope"],
               "result_source_sha256": digest(result_path), "configuration_sha256": digest(OUTPUT / "configuration.json"),
               "aggregation_source_sha256": digest(Path(__file__)), "planned_recordings": 55,
               "planned_speakers": 32, "planned_waveforms": 165, "planned_assessment_jobs": 110,
               "unmeasured_clipped_recordings": 65, "recognition_counts": dict(Counter(x["status"] for x in recordings)),
               "assessment_counts": report["counts"], "methods": {}, "paired_world_minus_hnm": {},
               "aggregation_definition": "発話macroは発話等重み、話者macroは話者内発話macroを話者等重み、microは正解文字/語数重み。差は誤り率差。",
               "quality_gate": {"maximum_reference_cer": .20, "excluded_cases": []},
               "timing": {}, "limitations": ["55録音の補助集合を固定120録音全体のASR結果としない。",
                   "切出しなしの6秒以下の発話集合であり、短い発話への選択がある。",
                   "英語LibriSpeech朗読、単一認識器。ASR誤りの増分を自然さや知覚品質全体と同一視しない。",
                   "単一CPU環境で他の実計算と併走。反復推論や速度安定性の比較ではない。",
                   "原音CER上限超過はprimary null/partial。全件の生誤り率を診断用として残す。",
                   "同一録音の原音・方式出力・集計反復を独立サンプルとして水増ししない。"]}
    excluded = {}
    for row in rows:
        if row["status"] == "partial" and not row["result"].get("reference_usable", True):
            excluded[row["spec"]["case"]] = {"case": row["spec"]["case"], "speaker": row["spec"]["speaker"],
                                            "reference_cer": row["result"]["scores"]["cer"]["reference_rate"]}
    summary["quality_gate"]["excluded_cases"] = list(excluded.values())
    for method in ("hnm", "world_harvest"):
        method_rows = [r for r in rows if r["spec"]["method"] == method]
        raw = [r for r in method_rows if "scores" in r["result"]]
        usable = [r for r in raw if r["status"] == "ok"]
        summary["methods"][method] = {"counts": dict(Counter(r["status"] for r in method_rows)),
                                        "all_raw_diagnostic": grouped(raw), "reference_usable": grouped(usable)}
    for scope in ("all_raw_diagnostic", "reference_usable"):
        eligible = [r for r in rows if "scores" in r["result"] and
                    (scope == "all_raw_diagnostic" or r["status"] == "ok")]
        by_method = {m: {r["spec"]["case"]: r for r in eligible if r["spec"]["method"] == m}
                     for m in ("hnm", "world_harvest")}
        common_cases = sorted(by_method["hnm"].keys() & by_method["world_harvest"].keys())
        hnm = grouped([by_method["hnm"][c] for c in common_cases])["by_speaker"]
        world = grouped([by_method["world_harvest"][c] for c in common_cases])["by_speaker"]
        common = sorted(hnm.keys() & world.keys())
        pairs = {s: {m: world[s][m]["utterance_macro"]["delta"]["mean"] -
                    hnm[s][m]["utterance_macro"]["delta"]["mean"] for m in ("cer", "wer")} for s in common}
        summary["paired_world_minus_hnm"][scope] = {"speaker_count": len(common), "case_count": len(common_cases),
            "common_case_ids": common_cases, "by_speaker": pairs,
            "cer_delta": describe([x["cer"] for x in pairs.values()]),
            "wer_delta": describe([x["wer"] for x in pairs.values()])}
    for method in ("original", "hnm", "world_harvest"):
        recs = [x for x in recordings if x["method"] == method and x["status"] == "measured"]
        seconds = sum(x["inference_wall_seconds"] for x in recs)
        duration = sum(x["duration_seconds"] for x in recs)
        summary["timing"][method] = {"count": len(recs), "audio_seconds": duration,
            "inference_wall_seconds": seconds, "inference_process_cpu_seconds": sum(x["inference_process_cpu_seconds"] for x in recs),
            "inference_real_time_factor": seconds / duration if duration else None,
            "per_waveform_wall_seconds": describe([x["inference_wall_seconds"] for x in recs])}
    summary["timing"]["assessment_first_wall_seconds"] = sum(r["timing"]["first_wall_seconds"] or 0 for r in rows)
    summary["timing"]["assessment_repeat_wall_seconds"] = sum(r["timing"]["warm_median_seconds"] or 0 for r in rows)
    source = ROOT / ".venv/lib/python3.12/site-packages/transformers/models/wav2vec2/modeling_wav2vec2.py"
    summary["initialization_warning"] = {"key": "wav2vec2.masked_spec_embed", "status": "unused_in_this_inference",
        "reason": "公式checkpointにSpecAugment用埋込みがないため初期化警告。Transformers4.51.3の_mask_hidden_statesは、mask_time_indices指定またはtraining=True時だけこの値を使用する。今回model.eval()かつmask_time_indices未指定。警告を消すための再学習や重み差替えはしない。",
        "source_url": "https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/wav2vec2/modeling_wav2vec2.py#L1738-L1782",
        "installed_source_sha256": digest(source)}
    console = OUTPUT / "console.log"
    (OUTPUT / "console-log.json").write_text(json.dumps({"source_name": "console.log",
        "source_sha256": digest(console), "text": console.read_text()}, ensure_ascii=False, indent=2) + "\n")
    (OUTPUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    text = ["# 英語全文55録音のASR内容保持\n", "## 現ベースとWORLDの比較\n"]
    for method, label in (("hnm", "HNM v3"), ("world_harvest", "WORLD Harvest")):
        stats = summary["methods"][method]["reference_usable"]["overall"]
        text.append(f"- {label}: 原音CER上限を満たす{stats['case_count']}/55録音・{stats['speaker_count']}話者。"
                    f"発話平均の増分CER {100*stats['cer']['utterance_macro']['delta']['mean']:.3f}ポイント、"
                    f"増分WER {100*stats['wer']['utterance_macro']['delta']['mean']:.3f}ポイント。")
    reference = summary["methods"]["hnm"]["all_raw_diagnostic"]["overall"]
    text += [f"\n原音全55録音の発話平均CERは{100*reference['cer']['utterance_macro']['reference_rate']['mean']:.3f}%、"
             f"WERは{100*reference['wer']['utterance_macro']['reference_rate']['mean']:.3f}%。"
             f"原音CERが事前上限20%を超える録音は{len(excluded)}件。"
             "上限を超えた録音がある場合、その録音の両方式をpartialとする。",
             "\n詳細値、話者等重み、micro、対応のある話者差はsummary.jsonに保存。"
             "母数・重みの違う値を同じ平均として混ぜない。",
             "発話等重みと話者等重み・文字数重みではCERの方式順位が変わる。"
             "全語数重みのWERは両方式で同じ値だった。小さい差を方式の総合的優越としない。",
             "\n## 条件と根拠\n", report["scope"],
             "\n公式facebook/wav2vec2-base-960hのcommit 22aad52d435eb6dbaf354bdad9b0da84ce7d6156を使用。"
             "safetensors SHA256は8aa76ab2243c81747a1f832954586bc566090c83a0ac167df6f31f0fa917d74aで公式HTTPヘッダーと一致。"
             "認識器標準の発話単位平均・分散正規化を原音と方式出力へ同じように適用。"
             "音声データ自体の音量合わせ、無音除去、再標本化、切り詰めは行っていない。",
             "\n正解は固定コーパス内の公式全文転記。原音ASRを正解として使わない。"
             "既存assessmentの増分CER/WERを初回＋1反復で計算し、ASRは各165波形1回。",
             "\n## 未完了範囲\n", *[f"- {x}" for x in summary["limitations"]],
             "\n## 保存物\n", "- recognitions/: 全165波形の転記、生入力hash、前処理hash、推論時間",
             "- sidecars/: 55録音×2方式の公式正解・原音転記・方式転記",
             "- configuration.json / asset-acquisition.json: 固定条件・モデル資産・取得根拠",
             "- execution.json / progress.json / console-log.json: 実行履歴・全分母・警告を含むログ",
             "- assessment/: PR30式による110jobの生値・初回と1反復・HTML",
             "- summary.json: 発話・話者・全トークン別の記述的集計",
             "\n## 初期化警告\n", summary["initialization_warning"]["reason"]]
    (OUTPUT / "README.md").write_text("\n".join(text) + "\n")
    print(json.dumps({"counts": summary["assessment_counts"], "excluded": list(excluded.values()),
                      "methods": {m: x["reference_usable"]["overall"] for m, x in summary["methods"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(run_cli(summarize, "added-metrics-asr-summary"))
