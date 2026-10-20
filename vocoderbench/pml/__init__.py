"""RAW_FULL（16 kHz研究用）。pmlは互換package名であり独立した旧方式ではない。"""

from .codec import decode, encode
from .parameters import RAWFullParameters, edit_parameters
from .payload import load_parameters, save_parameters

VERSION = "raw-full-fwcep60-v1"
load = load_parameters
save = save_parameters

__all__ = [
    "RAWFullParameters", "VERSION", "encode", "decode", "edit_parameters",
    "save_parameters", "load_parameters", "save", "load",
]
