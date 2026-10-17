"""全終端の保存値を日本語HTMLへ接続する。新規科学計算・Pages生成はしない。"""

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

from common import Sources, digest, encode, public_text, require
from cost_audio_gate import cost_projection, validate_audio
from feature_appendix import project
from ordinary_gate import validate
from presentation import costs, detail_page, features, render

LOGGER = logging.getLogger("terminal-presentation-assembly")


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "記録日時はUTC offset必須")
    require(parsed <= datetime.now(UTC), "未来の記録日時は不可")
    return value


def assemble(args):
    sources = Sources(args.manifest, args.manifest_sha256)
    plan, summary, labels, storage = validate(sources)
    appendix = project(sources)
    cost = cost_projection(sources)
    audio = validate_audio(sources)
    outputs = sources.approved_public()
    now = datetime.now(UTC).isoformat()
    dates = sources.manifest["recorded_at"]
    require(set(dates) == {"ordinary_summary", "ordinary_html", "cost_coverage_audit"}, "実記録日時が必要")
    dates = {key: timestamp(value) for key, value in dates.items()}
    inputs = [sources.identity(key) for key in sorted(sources.entries)]
    code_root = Path(__file__).resolve().parent
    code_bytes = {name: (code_root / name).read_bytes() for name in (
        "assemble.py", "common.py", "ordinary_gate.py", "feature_appendix.py",
        "cost_audio_gate.py", "presentation.py")}
    provenance = {
        "schema_version": 1, "scope": "presentation-only-assembly",
        "assembled_at": now, "source_recorded_at": dates,
        "private_input_manifest_sha256": sources.manifest_sha,
        "run_plan_sha256": sources.entries["plan"]["sha256"],
        "formal_base": plan["formal_base"], "formal_base_version": plan["formal_base_version"],
        "adoption_decision": None, "input_identities": inputs,
        "generator_sources": [{"name": name, "sha256": digest(blob), "bytes": len(blob)}
                              for name, blob in code_bytes.items()],
        "ordinary_html_binding": sources.manifest["ordinary_html_binding"],
        "checkpoint_storage": storage,
        "feature_rank": None, "cost_source_report_status": cost["source_status_unchanged"],
        "scientific_computation_performed": False,
        "limitations": [
            "凍結HTML・公開JSONは承認済みbytesをそのまま複製。私有summaryはscalar列のみ投影。",
            "この組立ては元評価の科学的正しさや実行認可を再証明しない。終端SHAの結合を照合する。",
            "入力manifestと公開承認欄は事前に独立レビューする。manifest自体のpathは公開しない。",
            "ABX条件別予定数・距離失敗理由数・token支持欠落数はsummaryに保存なし。全体予定4960は保持。",
            "読み出し欠測理由の件数はsummaryに保存なし。全体予定120録音・40話者は保持。",
            "定数train平均基準は単独支持。対応支持上の基準差や順位を算出していない。",
            "費用監査は別の承認済み保存監査の引用。ここで原receiptやpayloadを再展開しない。",
            "費用の原partial状態を保持。全終端入力と速度比較可能性は別。unknownをゼロにしない。",
            "短音声は承認済み固定2録音の無編集data URIだけ。全長音声やpayloadを公開しない。",
            "Pages一覧adapter・公開・実URL検査はこのprototypeの対象外。",
        ],
    }
    for filename, data in (("feature-appendix.json", appendix), ("cost-coverage.json", cost),
                           ("provenance.json", provenance)):
        public_text(data)
        outputs[filename] = encode(data)
    outputs["index.html"] = render(summary, labels, appendix, cost, audio, now).encode()
    outputs["features.html"] = detail_page("aHM特徴表現と現PML：ABX・読み出し", features(appendix)).encode()
    outputs["costs.html"] = detail_page("aHM・現PML・WORLD：保存済み費用の観測", costs(cost)).encode()
    for data in outputs.values():
        require(len(data) < 10 * 1024 * 1024, "公開成果物は各10MiB未満")
    directory = args.output_dir.resolve()
    require(not directory.exists(), "既存出力へ上書きできません。新しいディレクトリを指定してください")
    require(all(not path.is_relative_to(directory) for path in sources.paths.values()), "入力内へ出力できません")
    require(not args.log_file.resolve().is_relative_to(directory), "ログは公開ディレクトリ外へ保存")
    artifact_manifest = {
        "schema_version": 1, "scope": "terminal-presentation-artifacts",
        "assembled_at": now, "input_manifest_sha256": sources.manifest_sha,
        "count": len(outputs), "artifacts": [{"path": name, "sha256": digest(data), "bytes": len(data)}
                                             for name, data in sorted(outputs.items())],
        "manifest_self_hash": "artifact-manifest.sha256を参照。自己参照hashは作らない。",
    }
    sources.recheck()
    directory.mkdir(parents=False, exist_ok=False)
    for name, data in outputs.items():
        with (directory / name).open("xb") as stream:
            stream.write(data)
    sources.recheck()
    require(all((code_root / name).read_bytes() == blob for name, blob in code_bytes.items()),
            "組立てソースの実行中変更を検出")
    manifest_bytes = encode(artifact_manifest)
    with (directory / "artifact-manifest.json").open("xb") as stream:
        stream.write(manifest_bytes)
    with (directory / "artifact-manifest.sha256").open("x", encoding="ascii") as stream:
        stream.write(digest(manifest_bytes) + "  artifact-manifest.json\n")
    LOGGER.info("表示専用組立て完了: %s; 原HTML・原JSONのbytes変更なし", directory)


def main():
    logging.basicConfig(level=logging.INFO)
    logging.captureWarnings(True)
    try:
        parser = Parser(description=__doc__)
        parser.add_argument("--manifest", type=Path, required=True)
        parser.add_argument("--manifest-sha256", required=True)
        parser.add_argument("--output-dir", type=Path, required=True)
        parser.add_argument("--log-file", type=Path, required=True)
        args = parser.parse_args()
        handler = logging.FileHandler(args.log_file, mode="x", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logging.getLogger().addHandler(handler)
        assemble(args)
    except BaseException:
        LOGGER.exception("表示用組立てを中断しました。既存入力は変更していません")
        raise


if __name__ == "__main__":
    main()
