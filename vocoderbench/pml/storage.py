"""内部PML成分serializerと履歴読取り。RAW復号には別途保存A/Lが必須。"""

import hashlib
import json
import struct
from pathlib import Path

import numpy as np

from .parameters import BINS, FS, NFFT, PMLParameters

_MAGIC = b"PMLFWC01"
_SCHEMA = "pml-fwcep60-lowband-v1"


def save_parameters(params, path):
    """F0 float64 / FWCEP float32 / bit-packed NM を保存する。既存を上書きしない。"""
    packed = np.packbits(params.noise_mask, axis=1, bitorder="little")
    body = (
        np.asarray(params.f0, dtype="<f8").tobytes()
        + np.asarray(params.fwcep, dtype="<f4").tobytes()
        + packed.tobytes()
    )
    header = dict(
        schema=_SCHEMA,
        sample_rate=FS,
        nfft=NFFT,
        step=0.005,
        frames=len(params.f0),
        n_samples=params.n_samples,
        seed=params.seed,
        pitch_shift_semitones=params.pitch_shift_semitones,
        body_sha256=hashlib.sha256(body).hexdigest(),
    )
    encoded = json.dumps(
        header, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf8")
    with Path(path).open("xb") as handle:
        handle.write(_MAGIC + struct.pack("<I", len(encoded)) + encoded + body)


def load_parameters(path):
    """固定 5 ms グリッド、2,049 ビン、60 係数の保存表現を読み込む。"""
    data = Path(path).read_bytes()
    if len(data) < 12 or data[:8] != _MAGIC:
        raise ValueError("PML 特徴量ファイルではないか、ファイルが切れています")
    length = struct.unpack("<I", data[8:12])[0]
    if not 0 < length <= 65536 or len(data) < 12 + length:
        raise ValueError("PML ヘッダー長が不正です")
    header = json.loads(data[12 : 12 + length].decode("utf8"))
    fields = {
        "schema",
        "sample_rate",
        "nfft",
        "step",
        "frames",
        "n_samples",
        "seed",
        "pitch_shift_semitones",
        "body_sha256",
    }
    if not isinstance(header, dict) or set(header) != fields:
        raise ValueError("PML ヘッダーの項目が不正です")
    if (
        header["schema"] != _SCHEMA
        or header["sample_rate"] != FS
        or header["nfft"] != NFFT
        or header["step"] != 0.005
    ):
        raise ValueError("未対応の PML 特徴量形式です")
    frames = header["frames"]
    if type(frames) is not int or frames < 2:
        raise ValueError("PML フレーム数が不正です")
    body = data[12 + length :]
    row_bytes = (BINS + 7) // 8
    if len(body) != frames * (8 + 60 * 4 + row_bytes):
        raise ValueError("PML データ長が不正です")
    if hashlib.sha256(body).hexdigest() != header["body_sha256"]:
        raise ValueError("PML データのチェックサムが一致しません")
    a, b = frames * 8, frames * (8 + 60 * 4)
    f0 = np.frombuffer(body[:a], dtype="<f8").copy()
    coeff = np.frombuffer(body[a:b], dtype="<f4").reshape(frames, 60).copy()
    packed = np.frombuffer(body[b:], dtype=np.uint8).reshape(frames, row_bytes)
    if np.any(packed[:, -1] & 254):
        raise ValueError("PML 二値マスクのパディングが不正です")
    mask = np.unpackbits(packed, axis=1, bitorder="little")[:, :BINS]
    return PMLParameters(
        fwcep=coeff,
        noise_mask=mask,
        f0=f0,
        n_samples=header["n_samples"],
        sample_rate=header["sample_rate"],
        seed=header["seed"],
        pitch_shift_semitones=header["pitch_shift_semitones"],
    )
