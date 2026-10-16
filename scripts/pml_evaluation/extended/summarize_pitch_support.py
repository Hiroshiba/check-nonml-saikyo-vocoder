"""Descriptive accounting of saved YIN support; no new detector or thresholds."""

from run_edits import ROOT, read, write, sha
import numpy as np

spec = read(ROOT / "input-contract.json")
rows = []
groups = {}
for condition in ("pitch_minus3", "pitch_plus3"):
    totals = {
        k: 0
        for k in [
            "total_frames",
            "expected_voiced_frames",
            "expected_unvoiced_frames",
            "missing_voiced_frames",
            "false_voiced_frames",
            "out_of_range_frames",
            "unmapped_frames",
            "below65_frames",
            "above700_frames",
        ]
    }
    for c in spec["cases"]:
        p = ROOT / "extended/measurements" / f"{c['id']}__{condition}.json"
        r = read(p)
        m = r["measurement"]
        expected = np.asarray(m["expected_relative_f0_hz"])
        counts = {
            k: m[k] for k in totals if k not in ("below65_frames", "above700_frames")
        }
        counts.update(
            below65_frames=int(((expected > 0) & (expected < 65)).sum()),
            above700_frames=int((expected > 700).sum()),
        )
        assert counts["unmapped_frames"] == 0
        assert (
            counts["below65_frames"] + counts["above700_frames"]
            == counts["out_of_range_frames"]
        )
        rows.append(
            dict(case=c["id"], condition=condition, source_sha256=sha(p), **counts)
        )
        for k in totals:
            totals[k] += counts[k]
    groups[condition] = dict(
        **totals,
        pooled_missing_among_in_range_expected_voiced=totals["missing_voiced_frames"]
        / totals["expected_voiced_frames"],
    )
write(
    ROOT / "extended/pitch-support-explanation.json",
    dict(
        driver_sha256=sha(__file__),
        groups=groups,
        rows=rows,
        explanation_ja=[
            "基準F0は原音ではなく同じ手法の無編集再合成にYINを適用した推定値。そこへ±300 centを加えて期待F0を作る。",
            "範囲外65 Hz未満・700 Hz超は別集計し、expected_voicedとmissingの分母から既に除外している。",
            "missingは範囲内で基準側有声、編集側YIN無声となった窓。音声が消失した割合ではない。波形の周期性・調波構造と推定器特性が関与し得るが、ここから原因割合は分離できない。",
            "全方式共通なのは録音集合であり、方式ごとの無編集推定F0が異なるためフレーム支持は共通ではない。",
            "この集計は保存値の説明であり、主指標・65–700 Hzの範囲・判定器を変更しない。",
        ],
    ),
)
print(groups)
