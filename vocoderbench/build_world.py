"""Build the pinned, unmodified WORLD sources without pip or CMake."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "world.lock.json"


def _run(argv: list[str], cwd: Path | None = None) -> str:
    return subprocess.check_output(argv, cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()


def cache_dir() -> Path:
    return Path(os.environ.get("NONML_WORLD_CACHE", ROOT / ".cache" / "world")).resolve()


def build(*, force: bool = False) -> Path:
    lock = json.loads(LOCK_PATH.read_text())
    revision = lock["revision"]
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("WORLD revision must be a full lowercase commit SHA")
    target = cache_dir() / revision
    source = target / "source"
    target.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        # Clone into a private temporary directory and publish only a complete checkout.
        with tempfile.TemporaryDirectory(prefix="world-source-", dir=target) as tmp:
            checkout = Path(tmp) / "source"
            _run(["git", "clone", "--quiet", "--no-checkout", lock["repository"], str(checkout)])
            _run(["git", "checkout", "--quiet", "--detach", revision], cwd=checkout)
            checkout.rename(source)
    actual_revision = _run(["git", "rev-parse", "HEAD"], cwd=source)
    if actual_revision != revision:
        raise RuntimeError(f"WORLD checkout is {actual_revision}, expected {revision}")
    for rel, expected in lock["sources"].items():
        actual = hashlib.sha256((source / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"WORLD source hash mismatch: {rel}")
    compiler = os.environ.get("CXX", lock["compiler"])
    if not compiler or any(c.isspace() for c in compiler):
        raise ValueError("CXX must name one executable, without flags")
    version = _run([compiler, "--version"]).splitlines()[0]
    src_paths = [source / rel for rel in sorted(lock["sources"]) if rel.endswith(".cpp")]
    library = target / "libworld.so"
    metadata = target / "build.json"
    fingerprint = {
        "revision": revision,
        "lock_sha256": hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest(),
        "compiler": compiler,
        "compiler_version": version,
        "flags": lock["flags"],
    }
    if not force and library.is_file() and metadata.is_file():
        previous = json.loads(metadata.read_text())
        if (all(previous.get(k) == v for k, v in fingerprint.items())
                and previous.get("library_sha256") == hashlib.sha256(library.read_bytes()).hexdigest()):
            return library
    with tempfile.TemporaryDirectory(prefix="world-build-", dir=target) as tmp:
        output = Path(tmp) / "libworld.so"
        command = [compiler, *lock["flags"], "-I", str(source / "src"),
                   *map(str, src_paths), "-o", str(output)]
        _run(command)
        output.replace(library)
    fingerprint["library_sha256"] = hashlib.sha256(library.read_bytes()).hexdigest()
    fingerprint["source_sha256"] = lock["sources"]
    fingerprint["command"] = command
    metadata.write_text(json.dumps(fingerprint, indent=2) + "\n")
    return library


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(build(force=args.force))
