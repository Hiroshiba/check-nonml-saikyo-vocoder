"""RAW保存境界。directory内のparameters.pmlと非圧縮raw.npzを一体として扱う。"""

from pathlib import Path

import numpy as np

from .parameters import _with_raw, validate_raw
from .storage import load_parameters as _load_components
from .storage import save_parameters as _save_components


def save_parameters(params, path):
    """新規directoryへ保存する。部分失敗は完了ではなく、別の保存先が必要。"""
    validate_raw(params)
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=False)
    _save_components(params, directory / "parameters.pml")
    with (directory / "raw.npz").open("xb") as handle:
        np.savez(handle, A_raw=params.A_raw, L_raw=params.L_raw)


def load_parameters(path):
    """原音・外部特徴を参照せず、保存された必須A/LとPML成分を読む。"""
    directory = Path(path)
    if not directory.is_dir():
        raise ValueError("RAW_FULLの保存directoryが必要です。旧PML単体は未対応です")
    components = _load_components(directory / "parameters.pml")
    with np.load(directory / "raw.npz", allow_pickle=False) as saved:
        if set(saved.files) != {"A_raw", "L_raw"}:
            raise ValueError("RAW保存項目はA_rawとL_rawのみです")
        A, L = saved["A_raw"].copy(), saved["L_raw"].copy()
    if A.dtype != np.float64 or L.dtype != np.float64:
        raise ValueError("保存A_raw/L_rawはfloat64が必要です")
    params = _with_raw(components, A, L)
    validate_raw(params)
    return params
