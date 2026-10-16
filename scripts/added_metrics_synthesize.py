"""過去HNM固定研究の再実行場所を案内する。保存済み集計は別スクリプトで扱う。"""
from vocoderbench.logging_utils import run_cli


def main():
    raise ValueError('旧HNM固定研究の再計算はbbab81fをcheckoutしてください。PMLはvocoderbench.reference --include-current-baseで評価します')


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'historical-added-metrics'))
