"""公開来歴に固定された品質モデルを取得する。音声は外部へ送信しない。"""

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--mos-cache", type=Path)
    args = parser.parse_args()
    data = json.loads(args.provenance.read_text())
    assets = next(
        r["data"]["assets"]
        for r in data["records"]
        if r["kind"] == "acquisition_assets"
    )
    for asset in assets:
        identifier = asset["id"]
        if identifier not in ("ecapa", "scoreq") and not identifier.startswith("asr_"):
            continue
        name = asset["url"].rsplit("/", 1)[1]
        target = (
            args.run_root
            / "assets"
            / ("asr" if identifier.startswith("asr_") else identifier)
            / name
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            partial = target.with_suffix(target.suffix + ".part")
            with (
                urllib.request.urlopen(asset["url"], timeout=120) as source,
                partial.open("wb") as destination,
            ):
                total = 0
                while chunk := source.read(4 * 1024 * 1024):
                    total += len(chunk)
                    if total > asset["bytes"]:
                        raise ValueError("Asset exceeds declared size")
                    destination.write(chunk)
            with partial.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if total != asset["bytes"] or digest != asset["sha256"]:
                raise ValueError("Downloaded asset does not match fixed provenance")
            partial.replace(target)
        with target.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if target.stat().st_size != asset["bytes"] or digest != asset["sha256"]:
            raise ValueError("Existing asset does not match fixed provenance")
        print(identifier, digest)
    if args.mos_cache:
        from vocoderbench.mos import MosEvaluator

        evaluator = MosEvaluator(
            cache_root=args.mos_cache, repetitions=1, seed=20261012, threads=2
        )
        if not evaluator.prepare():
            raise RuntimeError("UTMOS preparation failed; inspect logged exception")


if __name__ == "__main__":
    main()
