"""固定 libllsm2 の Layer1 chunk を HM 抜きで保存・復元する候補。

上流 d18cdf02 の llsm.h / layer1.c / frame.c と、既存 Layer0Storage の
ctypes 所有権処理を静的に参照した。科学実行・動作確認は未実施。
"""

import ctypes as ct

import numpy as np

from .storage_base import (
    CHP, CONF_TYPES, FP, NP, P, Layer0Storage, array,
)


FRAME_TYPES = {0: 'fp', 2: 'nmframe', 3: 'fparray',
               10: 'fp', 11: 'fparray', 12: 'fparray'}
NFFT = 2048
NSPEC = NFFT // 2 + 1


class Layer1Storage(Layer0Storage):
    """1/HM と 8/9/PbP を保存形式から排除する。"""

    def _frame(self, pointer):
        result = {}
        for index in range(pointer.contents.nmember):
            value = self.lib.llsm_container_get(pointer, index)
            if not value or index in (1, 8, 9):  # 元 HM と PbP は保存しない。
                continue
            if index not in FRAME_TYPES:
                raise ValueError(f'Layer1 に未対応の frame field {index}')
            kind = FRAME_TYPES[index]
            if kind == 'fp':
                data = np.array([ct.cast(value, FP)[0]], dtype=np.float32)
            elif kind == 'fparray':
                ptr = ct.cast(value, FP)
                data = array(ptr, self.lib.llsm_fparray_length(ptr))
            else:
                data = self._noise(ct.cast(value, NP))
            result[str(index)] = data
        return result

    @staticmethod
    def _validate(config, frames):
        required_config = {'0', '1', '2', '3', '4', '6', '7', '8', '10', '11'}
        if not required_config.issubset(config) or any(int(k) not in CONF_TYPES for k in config):
            raise ValueError('Layer1 config に必要 field がありません')
        nfrm = int(np.asarray(config['0']).item())
        npsd = int(np.asarray(config['4']).item())
        nspec = int(np.asarray(config['10']).item())
        nchannel = int(np.asarray(config['7']).item())
        if (nfrm <= 0 or nfrm != len(frames) or npsd <= 0 or nspec != NSPEC
                or nchannel <= 0 or len(config['8']) != nchannel - 1):
            raise ValueError('Layer1 config の frame/PSD/NSPEC が不正です')
        for number, frame in enumerate(frames):
            indices = {int(key) for key in frame}
            if not indices.issubset(FRAME_TYPES) or not {0, 2, 3, 10}.issubset(indices):
                raise ValueError(f'Layer1 frame field が不正です: {number}')
            f0 = float(np.asarray(frame['0']).item())
            if not np.isfinite(f0) or f0 < 0:
                raise ValueError(f'Layer1 F0 が不正です: {number}')
            if f0 > 0 and not {11, 12}.issubset(indices):
                raise ValueError(f'有声 frame の VTMAGN/VSPHSE がありません: {number}')
            if f0 == 0 and ({11, 12} & indices):
                raise ValueError(f'無声 frame に余分な Layer1 スペクトルがあります: {number}')
            if len(frame['3']) != npsd:
                raise ValueError(f'PSDRES の長さが不正です: {number}')
            if 11 in indices and len(frame['11']) != nspec:
                raise ValueError(f'VTMAGN の長さが不正です: {number}')
            if 12 in indices and not len(frame['12']):
                raise ValueError(f'VSPHSE が空です: {number}')
            for key, value in frame.items():
                if key == '2':
                    noise = value
                    if (len(noise['edc']) != nchannel or len(noise['eenv']) != nchannel
                            or len(noise['psd']) != npsd
                            or any(len(harmonic['ampl']) != len(harmonic['phse'])
                                   for harmonic in noise['eenv'])):
                        raise ValueError(f'Layer1 NM の長さが不正です: {number}')
                    vectors = [noise['edc'], noise['psd'],
                               *(v for harmonic in noise['eenv']
                                 for v in (harmonic['ampl'], harmonic['phse']))]
                    if any(not np.isfinite(vector).all() for vector in vectors):
                        raise ValueError(f'非有限な Layer1 NM: {number}')
                elif not np.isfinite(value).all():
                    raise ValueError(f'非有限な Layer1 field {key}: {number}')

    def export(self, pointer):
        chunk = ct.cast(pointer, CHP).contents
        config = self._container(chunk.conf, CONF_TYPES)
        nfrm = int(config['0'][0])
        frames = [self._frame(chunk.frames[i]) for i in range(nfrm)]
        self._validate(config, frames)
        return {'config': config, 'frames': frames}

    def restore(self, values):
        if set(values) != {'config', 'frames'}:
            raise ValueError('Layer1 保存形式には config と frames だけが必要です')
        config, frames = values['config'], values['frames']
        self._validate(config, frames)
        config_ptr = self._new_container(config, CONF_TYPES)
        try:
            chunk = self.lib.llsm_create_chunk(config_ptr, 0)
        finally:
            self.lib.llsm_delete_container(config_ptr)
        if not chunk:
            raise ValueError('Layer1 chunk を構築できません')
        try:
            for i, frame in enumerate(frames):
                chunk.contents.frames[i] = self._new_container(frame, FRAME_TYPES)
                if self.lib.llsm_container_get(chunk.contents.frames[i], 1):
                    raise ValueError(f'復元後に元 HM が残っています: {i}')
            return ct.cast(chunk, P).value
        except Exception:
            self.lib.llsm_delete_chunk(chunk)
            raise
