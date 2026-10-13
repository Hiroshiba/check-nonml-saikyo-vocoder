"""PR #24で実測した構成の解析・合成アダプター。操作・学習のAPIではない。"""
from __future__ import annotations
import ctypes as ct
import sys
import time
from types import SimpleNamespace
import numpy as np

def total_params(*models):
    return sum((p.numel() for model in models for p in model.parameters()))

def build_llsm(src, models, out):
    import pyworld as pw

    class Output(ct.Structure):
        _fields_ = [('ny', ct.c_int), ('fs', ct.c_float), ('y', ct.POINTER(ct.c_float)), ('y_sin', ct.POINTER(ct.c_float)), ('y_noise', ct.POINTER(ct.c_float))]
    lib = ct.CDLL(str(src.parent / 'native/libllsm_speed.so'))
    arr = np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS')
    lib.speed_encode.argtypes = [arr, ct.c_int, ct.c_float, arr, ct.c_int, ct.c_int]
    lib.speed_encode.restype = ct.c_void_p
    lib.speed_decode.argtypes = [ct.c_void_p, ct.c_float, ct.c_int]
    lib.speed_decode.restype = ct.POINTER(Output)
    lib.llsm_delete_chunk.argtypes = [ct.c_void_p]
    lib.llsm_delete_output.argtypes = [ct.POINTER(Output)]
    a = SimpleNamespace(sr=24000, info=dict(variant='LLSM2 Layer0 peak-picking; maxnhar400 npsd128 hop5ms; DIO+StoneMask', parameter_count=0, compile='Release -Ofast float32'), stage_times={})

    def encode(x, p):
        t = time.perf_counter()
        f0, ts = pw.dio(x, a.sr, f0_floor=60, f0_ceil=1000, frame_period=5)
        f0 = pw.stonemask(x, f0, ts, a.sr)
        a.stage_times['external_f0_s'] = time.perf_counter() - t
        z = lib.speed_encode(x.astype(np.float32), len(x), a.sr, f0.astype(np.float32), len(f0), 0)
        if not z:
            raise RuntimeError('llsm_analyze returned NULL')
        return z

    def decode(z):
        p = lib.speed_decode(z, a.sr, 0)
        if not p:
            raise RuntimeError('llsm_synthesize returned NULL')
        y = np.ctypeslib.as_array(p.contents.y, shape=(p.contents.ny,)).copy()
        lib.llsm_delete_output(p)
        return y
    a.encode = encode
    a.decode = decode
    a.release = lib.llsm_delete_chunk
    return a

def build_magphase(src, models, out):
    sys.path.insert(0, str(src.parent / 'magphase-port'))
    sys.path.insert(0, str(src.parent / 'magphase-port/src'))
    from src import magphase as mp

    def encode(x, p):
        return mp.analysis_compressed(str(p), mag_dim=100, phase_dim=45, b_const_rate=False)

    def decode(z):
        return mp.synthesis_from_compressed(*z[:4], z[5], b_const_rate=False, b_out_hpf=False)
    return SimpleNamespace(sr=48000, encode=encode, decode=decode, info=dict(variant='MagPhase2 compressed100/45/45 pitch-synchronous; SPTK3.9+REAPER; Python3 compatibility patch', parameter_count=0, analysis_file_io_included=True))

def build_world_harvest(src, models, out):
    from .. import world
    return SimpleNamespace(sr=16000, encode=lambda x, path: world.encode(x, 16000), decode=world.decode, info={'variant': '固定版WORLD・Harvest/CheapTrick/D4C', 'source_revision': world.REVISION})
