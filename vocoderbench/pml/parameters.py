"""PML の保存特徴量。60 係数・2,049 ビンの二値マスク・連続 F0。"""

from dataclasses import dataclass, fields, replace

import numpy as np

FS = 16000
NFFT = 4096
BINS = NFFT // 2 + 1
STEP = 0.005
DEFAULT_SEED = 20261015


@dataclass(frozen=True)
class PMLParameters:
    """16 kHz 研究用表現。F0 は無声区間でも正の合成用クロック。

    配列は保存時の精度に固定する。NM は低域拡張・平滑化の前のマスク。
    pitch_shift_semitones は保存元からの累積編集量を記録する。
    """

    fwcep: np.ndarray
    noise_mask: np.ndarray
    f0: np.ndarray
    n_samples: int
    sample_rate: int = FS
    seed: int = DEFAULT_SEED
    pitch_shift_semitones: float = 0.0

    def __post_init__(self):
        if type(self.sample_rate) is not int or self.sample_rate != FS:
            raise ValueError("PML は現在 16000 Hz のみ対応しています")
        if type(self.n_samples) is not int or self.n_samples < 1:
            raise ValueError("n_samples は正の整数で指定してください")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("seed は 0 以上 2**32 未満の整数で指定してください")
        if (
            np.asarray(self.f0).dtype.kind not in "fiu"
            or np.asarray(self.fwcep).dtype.kind not in "fiu"
        ):
            raise ValueError("F0 と FWCEP は実数配列で指定してください")
        f0 = np.array(self.f0, dtype=np.float64, copy=True)
        coeff = np.array(self.fwcep, dtype=np.float32, copy=True)
        mask = np.asarray(self.noise_mask)
        if f0.ndim != 1 or len(f0) < 2:
            raise ValueError("連続 F0 は 2 フレーム以上必要です")
        if coeff.shape != (len(f0), 60) or mask.shape != (len(f0), BINS):
            raise ValueError("FWCEP または二値マスクの形状が不正です")
        if not np.isfinite(f0).all() or np.any(f0 <= 50) or np.any(f0 >= 700):
            raise ValueError("合成用連続 F0 の対応範囲は 50 Hz 超・700 Hz 未満です")
        if not np.isfinite(coeff).all():
            raise ValueError("FWCEP に非有限値があります")
        if not np.all((mask == 0) | (mask == 1)):
            raise ValueError("noise_mask は 0 または 1 の二値です")
        if not np.isfinite(self.pitch_shift_semitones):
            raise ValueError("音程編集量は有限値が必要です")
        mask = np.array(mask, dtype=np.bool_, copy=True)
        for name, value in [("f0", f0), ("fwcep", coeff), ("noise_mask", mask)]:
            value.setflags(write=False)
            object.__setattr__(self, name, value)

    @property
    def times(self):
        return np.arange(len(self.f0), dtype=np.float64) * np.float64(STEP)

    @property
    def fs(self):
        return self.sample_rate


@dataclass(frozen=True, kw_only=True)
class RAWFullParameters(PMLParameters):
    """RAW_FULL の保存表現。A/L は未編集の原音・F0から得た復号情報。

    既存PML成分への射影と、A/Lを含む全表現の距離は区別する。
    """

    A_raw: np.ndarray
    L_raw: np.ndarray

    def __post_init__(self):
        super().__post_init__()
        if abs(self.pitch_shift_semitones) > 3:
            raise ValueError("実験的な音程編集は元の特徴量から ±3 半音以内です")
        for name, shape in (
            ("A_raw", ((self.n_samples + 7) // 8,)),
            ("L_raw", self.f0.shape),
        ):
            value = np.asarray(getattr(self, name))
            if value.dtype.kind not in "fiu":
                raise ValueError(f"{name} は実数配列で指定してください")
            value = np.array(value, dtype=np.float64, copy=True)
            if value.shape != shape or not np.isfinite(value).all() or np.any(value < 0):
                raise ValueError(f"{name} の形状または値が不正です")
            value.setflags(write=False)
            object.__setattr__(self, name, value)


def _with_raw(params, A_raw, L_raw):
    """内部のPML成分に、必須の保存A/Lを付ける。A/Lの再計算はしない。"""
    return RAWFullParameters(
        **{field.name: getattr(params, field.name) for field in fields(PMLParameters)},
        A_raw=A_raw,
        L_raw=L_raw,
    )


def validate_raw(params):
    """保存・編集・復号境界で旧PML単体や不正なRAWを拒否する。"""
    if not isinstance(params, RAWFullParameters):
        raise ValueError("RAW_FULL の保存A_raw/L_rawが必須です。旧PML単体は復号できません")
    if params.sample_rate != FS or not np.isfinite(params.pitch_shift_semitones):
        raise ValueError("RAW_FULL のメタデータが不正です")
    if abs(params.pitch_shift_semitones) > 3:
        raise ValueError("実験的な音程編集は元の特徴量から ±3 半音以内です")
    for name, shape in (
        ("A_raw", ((params.n_samples + 7) // 8,)),
        ("L_raw", params.f0.shape),
    ):
        value = getattr(params, name)
        if (not isinstance(value, np.ndarray) or value.dtype != np.float64
                or value.shape != shape or not np.isfinite(value).all()
                or np.any(value < 0)):
            raise ValueError(f"保存{name} の形状・精度または値が不正です")


def edit_parameters(params, *, pitch_semitones=0.0, gain_db=0.0, time_scale=1.0):
    """実験的な音程編集。±3 半音内でも有声判定・音質の変化がある。

    A/Lは原音由来の保存値を維持する。RAWのgain追従性能は未測定。
    F0 変更に高域通過・低域マスク境界・雑音の時間支持・エネルギー補正が
    追従する、既測定の native 編集契約。時間伸縮は未対応。
    ゲイン編集も DC floor と float32 丸めにより厳密な波形倍率ではない。
    """
    validate_raw(params)
    if time_scale != 1.0:
        raise NotImplementedError("時間伸縮は未対応です")
    if not np.isfinite(pitch_semitones) or not np.isfinite(gain_db):
        raise ValueError("編集値は有限値で指定してください")
    total = params.pitch_shift_semitones + float(pitch_semitones)
    if abs(total) > 3:
        raise ValueError("実験的な音程編集は元の特徴量から ±3 半音以内です")
    coeff = params.fwcep.copy()
    coeff[:, 0] += float(gain_db) * np.log(10.0) / 20.0
    return replace(
        params,
        fwcep=coeff,
        f0=params.f0 * 2 ** (float(pitch_semitones) / 12.0),
        pitch_shift_semitones=total,
    )
