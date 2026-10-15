"""全8 primaryを保持する別の事後・成功方式条件付き解析root。"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
RUN = ROOT / 'runs/all-method-metrics-recovery-20261014'
PRIMARY_PACKAGE = RUN / 'operations/human_available100_v3'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(PRIMARY_PACKAGE))
OUT = RUN / 'human-availability100'
PUBLIC = OUT / 'conditional-private-evidence'
PLAN = PACKAGE / 'protocol.md'
ANALYSIS = OUT / 'conditional-rankings'
