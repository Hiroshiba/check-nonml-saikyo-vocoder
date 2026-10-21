"""固定 LLSM2 Layer1 の候補境界。未計測・未実行。

比較 ID llsm2 の Layer0 アダプターを変更しない。保存状態は元 HM を含まない。
"""

import ctypes as ct
import hashlib
import json
import math
from pathlib import Path
import random

import numpy as np

from .storage_base import CHP, FP, P
from .tree import export_tree, import_tree

from .storage import Layer1Storage


SOURCE_REVISION = 'd18cdf02b31819670e3bc23ead933ad9467da06d'
NATIVE_SHA256 = 'd8da444d9c3298899065de57d5efbea69574d38ec1c4d9f42a50c2cb1a730c2a'
SAMPLE_RATE = 24000


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def seed_zero():
    random.seed(0)
    np.random.seed(0)
    libc = ct.CDLL(None)
    libc.srand.argtypes = [ct.c_uint]
    libc.srand(ct.c_uint(0))


class Output(ct.Structure):
    _fields_ = [('ny', ct.c_int), ('fs', ct.c_float),
                ('y', FP), ('y_sin', FP), ('y_noise', FP)]


class Layer1Engine:
    def __init__(self, library_path):
        if sha256(library_path) != NATIVE_SHA256:
            raise ValueError('固定 LLSM2 native library の SHA が一致しません')
        self.storage = Layer1Storage(library_path)
        lib = self.storage.lib
        contiguous = np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS')
        lib.speed_encode.argtypes = [contiguous, ct.c_int, ct.c_float,
                                     contiguous, ct.c_int, ct.c_int]
        lib.speed_encode.restype = P
        lib.speed_decode.argtypes = [P, ct.c_float, ct.c_int]
        lib.speed_decode.restype = ct.POINTER(Output)
        lib.llsm_delete_output.argtypes = [ct.POINTER(Output)]
        lib.llsm_chunk_phasepropagate.argtypes = [CHP, ct.c_int]

    def analyze_to_saved(self, x, sample_rate, destination):
        """入力24 kHzを一度解析し、Layer1だけの新規保存directoryを作る。"""
        if sample_rate != SAMPLE_RATE:
            raise ValueError('Layer1 native 入力は明示的な24 kHzが必要です')
        x = np.asarray(x, dtype=np.float64)
        if x.ndim != 1 or not len(x) or not np.isfinite(x).all():
            raise ValueError('入力は有限の単一チャンネル音声が必要です')
        import pyworld as pw

        seed_zero()
        f0, times = pw.dio(x, SAMPLE_RATE, f0_floor=60, f0_ceil=1000, frame_period=5)
        f0 = pw.stonemask(x, f0, times, SAMPLE_RATE)
        pcm = np.ascontiguousarray(x, dtype=np.float32)
        f0_native = np.ascontiguousarray(f0, dtype=np.float32)
        chunk = self.storage.lib.speed_encode(pcm, len(pcm), SAMPLE_RATE,
                                               f0_native, len(f0_native), 1)
        if not chunk:
            raise RuntimeError('llsm_analyze / llsm_chunk_tolayer1 に失敗しました')
        try:
            values = self.storage.export(chunk)  # 元 HM は出力に含めない。
            arrays, tree = export_tree(values)
            destination = Path(destination)
            destination.mkdir(parents=True, exist_ok=False)
            with (destination / 'arrays.npz').open('xb') as stream:
                np.savez_compressed(stream, **arrays)
            tree.update(llsm_layer=1, native_float_type='float32',
                        sample_rate=SAMPLE_RATE, source_revision=SOURCE_REVISION,
                        native_sha256=NATIVE_SHA256,
                        native_input_samples=len(pcm),
                        native_input_float32_sha256=hashlib.sha256(pcm.tobytes()).hexdigest(),
                        external_f0='pyworld DIO + StoneMask, 60..1000 Hz, 5 ms',
                        f0_float32_sha256=hashlib.sha256(f0_native.tobytes()).hexdigest(),
                        analysis_seed=0, decoder_seed=0,
                        arrays_sha256=sha256(destination / 'arrays.npz'),
                        original_hm_saved=False, pbp_saved=False)
            with (destination / 'metadata.json').open('x', encoding='utf-8') as stream:
                json.dump(tree, stream, ensure_ascii=False, allow_nan=False, indent=2)
                stream.write('\n')
        finally:
            self.storage.lib.llsm_delete_chunk(chunk)

    def _fresh_chunk(self, source):
        source = Path(source)
        metadata = json.loads((source / 'metadata.json').read_text(encoding='utf-8'))
        if (metadata.get('llsm_layer') != 1 or metadata.get('sample_rate') != SAMPLE_RATE
                or metadata.get('source_revision') != SOURCE_REVISION
                or metadata.get('native_sha256') != NATIVE_SHA256
                or metadata.get('original_hm_saved') is not False
                or metadata.get('pbp_saved') is not False):
            raise ValueError('固定 Layer1 保存版と一致しません')
        if sha256(source / 'arrays.npz') != metadata['arrays_sha256']:
            raise ValueError('保存 Layer1 配列の SHA が一致しません')
        with np.load(source / 'arrays.npz', allow_pickle=False) as bundle:
            arrays = {name: np.array(bundle[name], copy=True) for name in bundle.files}
        return self.storage.restore(import_tree(arrays, metadata))

    def decode_from_saved(self, source, *, pitch_semitones=0):
        """各呼出しで再読込・独立復元する。出力は native 24 kHz 全長。"""
        if pitch_semitones not in (-3, 0, 3):
            raise ValueError('対応する音高操作は -3、0、+3 半音だけです')
        chunk = self._fresh_chunk(source)
        try:
            native = ct.cast(chunk, CHP).contents
            nfrm = int(ct.cast(self.storage.lib.llsm_container_get(native.conf, 0),
                               ct.POINTER(ct.c_int))[0])
            for index in range(nfrm):
                if self.storage.lib.llsm_container_get(native.frames[index], 1):
                    raise ValueError(f'復号前に元 HM が存在します: frame={index}')
            if pitch_semitones:
                ratio = 2.0 ** (pitch_semitones / 12.0)
                self.storage.lib.llsm_chunk_phasepropagate(ct.cast(chunk, CHP), -1)
                for index in range(nfrm):
                    frame = native.frames[index]
                    f0 = ct.cast(self.storage.lib.llsm_container_get(frame, 0), FP)
                    f0[0] *= ratio
                    envelope_ptr = self.storage.lib.llsm_container_get(frame, 11)
                    if envelope_ptr:
                        envelope = ct.cast(envelope_ptr, FP)
                        size = self.storage.lib.llsm_fparray_length(envelope)
                        np.ctypeslib.as_array(envelope, shape=(size,))[:] -= 20 * math.log10(ratio)
                self.storage.lib.llsm_chunk_phasepropagate(ct.cast(chunk, CHP), 1)
            seed_zero()
            output = self.storage.lib.speed_decode(chunk, SAMPLE_RATE, 1)
            if not output:
                raise RuntimeError('Layer1 synthesis returned NULL')
            try:
                if output.contents.fs != SAMPLE_RATE or output.contents.ny <= 0:
                    raise ValueError('Layer1 native 出力の標本化周波数・長さが不正です')
                y = np.ctypeslib.as_array(output.contents.y,
                                          shape=(output.contents.ny,)).copy()
                if not np.isfinite(y).all():
                    raise ValueError('Layer1 native 出力に非有限値があります')
                return y, SAMPLE_RATE
            finally:
                self.storage.lib.llsm_delete_output(output)
        finally:
            self.storage.lib.llsm_delete_chunk(chunk)
