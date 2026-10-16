"""取得済み公式固定コーパスから正式PML評価の入力NPYを保存する。"""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-manifest', type=Path, required=True)
    parser.add_argument('--corpus-manifest', type=Path, default=ROOT / 'data/clean_speech_v1.json')
    parser.add_argument('--corpus-cache', type=Path, default=ROOT / 'data/cache/clean_speech_v1')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import numpy as np
    from vocoderbench.corpus import load_cases

    expected = {c['id']: c for c in json.loads(args.input_manifest.read_text())['cases']}
    found = set()
    args.output.mkdir(parents=True, exist_ok=True)
    for case in load_cases(args.corpus_manifest, args.corpus_cache):
        if case['id'] not in expected:
            continue
        entry = expected[case['id']]
        if case['sr'] != 16000 or len(case['x']) != entry['input']['excerpt_samples']:
            raise ValueError(f'入力形式が固定契約と異なります: {case["id"]}')
        path = args.output / entry['input']['path']
        if not path.exists():
            np.save(path, case['x'], allow_pickle=False)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry['input']['sha256']:
            raise ValueError(f'入力SHAが異なります。既存ファイルは上書きしません: {path}')
        found.add(case['id'])
        logging.info('入力保存: %s', case['id'])
    if found != set(expected):
        raise ValueError(f'固定入力が不足しています: {sorted(set(expected) - found)}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        main()
    except Exception:
        logging.exception('固定入力の準備が中断しました')
        raise
