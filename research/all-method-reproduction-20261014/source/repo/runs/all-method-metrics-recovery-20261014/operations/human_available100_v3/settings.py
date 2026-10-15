"""可用性で事後選択した100録音群の独立root。元105群は変更しない。"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from all_metrics_common import RUN  # noqa: E402

PACKAGE = Path(__file__).resolve().parent
OUT = RUN / 'human-availability100'
PUBLIC = OUT / 'private-evidence'
PLAN = PACKAGE / 'protocol.md'
ORIGINAL = RUN / 'human-similarity'
