"""LLSM2 Layer 0の公開C構造を欠落なく数値化・復元する。Layer 1 coder不使用。"""
from __future__ import annotations

import ctypes as ct

import numpy as np


F = ct.c_float
FP = ct.POINTER(F)
P = ct.c_void_p


class Container(ct.Structure):
    _fields_ = [('members', ct.POINTER(P)), ('destructors', ct.POINTER(P)),
                ('copyctors', ct.POINTER(P)), ('nmember', ct.c_int)]


CP = ct.POINTER(Container)


class Harmonic(ct.Structure):
    _fields_ = [('ampl', FP), ('phse', FP), ('nhar', ct.c_int)]


HP = ct.POINTER(Harmonic)


class Noise(ct.Structure):
    _fields_ = [('eenv', ct.POINTER(HP)), ('edc', FP), ('psd', FP),
                ('npsd', ct.c_int), ('nchannel', ct.c_int)]


NP = ct.POINTER(Noise)


class Chunk(ct.Structure):
    _fields_ = [('conf', CP), ('frames', ct.POINTER(CP))]


CHP = ct.POINTER(Chunk)
CONF_TYPES = {0: 'int', 1: 'fp', 2: 'int', 3: 'int', 4: 'int',
              6: 'fp', 7: 'int', 8: 'fparray', 10: 'int', 11: 'fp'}
FRAME_TYPES = {0: 'fp', 1: 'hmframe', 2: 'nmframe', 3: 'fparray'}


def array(pointer, size):
    if size < 0 or size > 10000000 or (size and not pointer):
        raise ValueError('LLSM配列の長さまたはpointerが無効です')
    return np.ctypeslib.as_array(pointer, shape=(size,)).copy() if size else np.zeros(0, np.float32)


def put(pointer, values):
    values = np.asarray(values, dtype=np.float32)
    if values.size:
        np.ctypeslib.as_array(pointer, shape=(values.size,))[:] = values.reshape(-1)


class Layer0Storage:
    def __init__(self, path):
        self.lib = ct.CDLL(str(path))
        signatures = {
            'llsm_create_container': ([ct.c_int], CP),
            'llsm_container_get': ([CP, ct.c_int], P),
            'llsm_container_attach_': ([CP, ct.c_int, P, P, P], None),
            'llsm_fparray_length': ([FP], ct.c_int),
            'llsm_create_fp': ([F], FP), 'llsm_create_int': ([ct.c_int], ct.POINTER(ct.c_int)),
            'llsm_create_fparray': ([ct.c_int], FP),
            'llsm_create_hmframe': ([ct.c_int], HP),
            'llsm_create_nmframe': ([ct.c_int, ct.c_int, ct.c_int], NP),
            'llsm_create_chunk': ([CP, ct.c_int], CHP),
            'llsm_copy_chunk': ([CHP], CHP),
            'llsm_chunk_phasepropagate': ([CHP, ct.c_int], None),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.lib, name)
            function.argtypes, function.restype = args, result
        for kind in ['container', 'fp', 'int', 'fparray', 'hmframe', 'nmframe', 'chunk']:
            getattr(self.lib, 'llsm_delete_' + kind).argtypes = [P]

    def _harmonic(self, pointer):
        harmonic = ct.cast(pointer, HP).contents
        return {'ampl': array(harmonic.ampl, harmonic.nhar),
                'phse': array(harmonic.phse, harmonic.nhar)}

    def _noise(self, pointer):
        noise = ct.cast(pointer, NP).contents
        return {'edc': array(noise.edc, noise.nchannel), 'psd': array(noise.psd, noise.npsd),
                'eenv': [self._harmonic(noise.eenv[k]) for k in range(noise.nchannel)]}

    def _container(self, pointer, kinds):
        result = {}
        for index in range(pointer.contents.nmember):
            value = self.lib.llsm_container_get(pointer, index)
            if not value:
                continue
            if index not in kinds:
                raise ValueError(f'未対応のLLSM field {index}を黙って落とせません')
            kind = kinds[index]
            if kind in ('fp', 'int'):
                dtype = F if kind == 'fp' else ct.c_int
                value = np.array([ct.cast(value, ct.POINTER(dtype))[0]],
                                 dtype=np.float32 if kind == 'fp' else np.int32)
            elif kind == 'fparray':
                value = ct.cast(value, FP)
                value = array(value, self.lib.llsm_fparray_length(value))
            elif kind == 'hmframe':
                value = self._harmonic(value)
            else:
                value = self._noise(value)
            result[str(index)] = value
        return result

    def export(self, pointer):
        chunk = ct.cast(pointer, CHP).contents
        config = self._container(chunk.conf, CONF_TYPES)
        return {'config': config, 'frames': [self._container(chunk.frames[k], FRAME_TYPES)
                                             for k in range(int(config['0'][0]))]}

    def _new_harmonic(self, values):
        if len(values['ampl']) != len(values['phse']):
            raise ValueError('LLSM harmonic amplitude/phase長が違います')
        pointer = self.lib.llsm_create_hmframe(len(values['ampl']))
        put(pointer.contents.ampl, values['ampl'])
        put(pointer.contents.phse, values['phse'])
        return pointer

    def _new_noise(self, values):
        if len(values['edc']) != len(values['eenv']):
            raise ValueError('LLSM noise channel数が違います')
        pointer = self.lib.llsm_create_nmframe(len(values['edc']), 0, len(values['psd']))
        noise = pointer.contents
        put(noise.edc, values['edc'])
        put(noise.psd, values['psd'])
        for k, harmonic in enumerate(values['eenv']):
            self.lib.llsm_delete_hmframe(noise.eenv[k])
            noise.eenv[k] = self._new_harmonic(harmonic)
        return pointer

    def _new_container(self, values, kinds):
        pointer = self.lib.llsm_create_container(max(kinds) + 1)
        try:
            for index, value in values.items():
                index = int(index)
                kind = kinds[index]
                if kind in ('fp', 'int'):
                    value = getattr(self.lib, 'llsm_create_' + kind)(np.asarray(value).item())
                elif kind == 'fparray':
                    new = self.lib.llsm_create_fparray(len(value))
                    put(new, value)
                    value = new
                elif kind == 'hmframe':
                    value = self._new_harmonic(value)
                else:
                    value = self._new_noise(value)
                self.lib.llsm_container_attach_(
                    pointer, index, ct.cast(value, P),
                    ct.cast(getattr(self.lib, 'llsm_delete_' + kind), P),
                    ct.cast(getattr(self.lib, 'llsm_copy_' + kind), P))
            return pointer
        except Exception:
            self.lib.llsm_delete_container(pointer)
            raise

    def restore(self, values):
        if len(values['frames']) != int(values['config']['0'][0]):
            raise ValueError('LLSM frame数とconfigが違います')
        config = self._new_container(values['config'], CONF_TYPES)
        try:
            chunk = self.lib.llsm_create_chunk(config, 0)
        finally:
            self.lib.llsm_delete_container(config)
        if not chunk:
            raise ValueError('LLSM chunkの構築に失敗しました')
        try:
            for k, frame in enumerate(values['frames']):
                chunk.contents.frames[k] = self._new_container(frame, FRAME_TYPES)
            return ct.cast(chunk, P).value
        except Exception:
            self.lib.llsm_delete_chunk(chunk)
            raise
