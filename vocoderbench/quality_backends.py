"""ローカル資産だけから構築する品質・話者評価器。符号化には使わない。"""
from __future__ import annotations

import importlib.metadata
import json
import random

import numpy as np

from .quality_core import Unavailable, file_asset, package_versions


class ErbDistance:
    """軽量な追加診断。ERB三角帯域の差であり知覚評定値ではない。"""
    label, unit, direction = 'ERB帯域の対数包絡差', 'dB', 'lower'

    def __init__(self, options, base, work, threads):
        self.provenance = {'algorithm': 'erb-triangular-stft-v1', 'bands': 32,
                           'window_ms': 20, 'hop_ms': 5, 'reference_power_floor_ratio': 1e-6}

    def score(self, x, y, sr):
        from scipy import signal
        size, hop = round(sr * .020), round(sr * .005)
        if size < 2 or hop < 1:
            raise ValueError('ERB計測に対しサンプルレートが低すぎます')
        def transform(z):
            _, _, stft = signal.stft(z, fs=sr, window='hann', nperseg=size,
                                    noverlap=size-hop, boundary=None, padded=False)
            return np.abs(stft) ** 2
        grid = np.fft.rfftfreq(size, 1 / sr)
        edges = (10 ** (np.linspace(0, 21.4*np.log10(1+.00437*(sr/2)), 34) / 21.4) - 1) / .00437
        bank = np.maximum(0, np.minimum((grid[None, :] - edges[:-2, None]) / np.diff(edges)[:-1, None],
                                       (edges[2:, None] - grid[None, :]) / np.diff(edges)[1:, None]))
        supported = bank.sum(axis=1) > 0
        bank = bank[supported]
        if not len(bank):
            raise ValueError('FFT格子上に有効なERB帯域がありません')
        bank /= bank.sum(axis=1, keepdims=True)
        a, b = bank @ transform(x), bank @ transform(y)
        floor = max(float(a.max()) * 1e-6, 1e-20)
        difference = np.abs(10*np.log10(np.maximum(a, floor)) - 10*np.log10(np.maximum(b, floor)))
        return float(difference.mean()), {'p95_db': float(np.percentile(difference, 95)),
                                         'supported_bands': int(supported.sum()), 'frames': a.shape[1]}


def torch_modules(threads):
    import torch
    import torchaudio
    torch.set_num_threads(threads)
    return torch, torchaudio


def wave16(x, sr, torch, torchaudio):
    wave = torch.from_numpy(x.astype(np.float32)).unsqueeze(0)
    return torchaudio.functional.resample(wave, sr, 16000) if sr != 16000 else wave


class ScoreqReference:
    label, unit, direction = 'SCOREQ参照あり距離', 'distance', 'lower'

    def __init__(self, options, base, work, threads):
        self.provenance = {'algorithm': 'SCOREQ-ONNX-ref', 'domain': options.get('domain', 'natural'),
                           'source': 'https://github.com/alessandroragano/scoreq',
                           'sample_rate': 16000, 'padding_multiple': 320, 'reference_cache': False}
        if self.provenance['domain'] not in ('natural', 'synthetic'):
            raise ValueError('SCOREQ domainはnaturalまたはsyntheticです')
        path = file_asset(options, 'model', base, self.provenance)
        expected_name = 'fixed_nmr_telephone.onnx' if self.provenance['domain'] == 'natural' else 'fixed_nmr_synthetic.onnx'
        if path.name != expected_name:
            raise ValueError(f'参照ありモデルは{expected_name}を指定してください')
        import onnxruntime as ort
        self.torch, self.torchaudio = torch_modules(threads)
        settings = ort.SessionOptions()
        settings.intra_op_num_threads, settings.inter_op_num_threads = threads, 1
        self.session = ort.InferenceSession(str(path), sess_options=settings, providers=['CPUExecutionProvider'])
        inputs = self.session.get_inputs()
        if len(inputs) != 1 or len(inputs[0].shape) != 2 or inputs[0].type != 'tensor(float)':
            raise ValueError('SCOREQ ONNXの入力契約が想定と異なります')
        self.input_name = inputs[0].name
        self.provenance['packages'] = package_versions(('onnxruntime', 'torch', 'torchaudio'))

    def score(self, x, y, sr):
        def embedding(z):
            wave = wave16(z, sr, self.torch, self.torchaudio)
            wave = self.torch.nn.functional.pad(wave, (0, (-wave.shape[-1]) % 320))
            value = np.asarray(self.session.run(None, {self.input_name: wave.numpy()})[0])
            if value.ndim != 2 or value.shape[0] != 1 or value.shape[1] < 2 or not np.isfinite(value).all():
                raise ValueError('参照あり埋め込みではない出力または非有限値です')
            return value
        a, b = embedding(x), embedding(y)
        return float(np.linalg.norm(a-b)), {'embedding_dimension': a.shape[-1]}


class EcapaSimilarity:
    label, unit, direction = '話者埋め込みのコサイン類似度', 'cosine', 'higher'

    def __init__(self, options, base, work, threads):
        self.provenance = {'algorithm': 'speechbrain-ecapa-voxceleb-raw-embedding',
                           'source': 'https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb',
                           'sample_rate': 16000, 'normalize_embeddings_with_global_stats': False,
                           'reference_cache': False, 'recipe': 'official-80mel-1024channels-192dim'}
        checkpoint = file_asset(options, 'embedding_model', base, self.provenance)
        self.torch, self.torchaudio = torch_modules(threads)
        from speechbrain.lobes.features import Fbank
        from speechbrain.lobes.models.ECAPA_TDNN import ECAPA_TDNN
        from speechbrain.processing.features import InputNormalization
        self.features = Fbank(n_mels=80).eval()
        self.normalization = InputNormalization(norm_type='sentence', std_norm=False).eval()
        self.encoder = ECAPA_TDNN(input_size=80, channels=[1024, 1024, 1024, 1024, 3072],
                                 kernel_sizes=[5, 3, 3, 3, 1], dilations=[1, 2, 3, 4, 1],
                                 attention_channels=128, lin_neurons=192)
        self.encoder.load_state_dict(self.torch.load(checkpoint, map_location='cpu', weights_only=True), strict=True)
        self.encoder.eval()
        self.provenance['packages'] = package_versions(('speechbrain', 'torch', 'torchaudio'))

    def score(self, x, y, sr):
        def embedding(z):
            wave = wave16(z, sr, self.torch, self.torchaudio)
            lengths = self.torch.ones(1)
            features = self.normalization(self.features(wave), lengths)
            value = self.encoder(features, lengths).reshape(-1)
            if not self.torch.isfinite(value).all() or value.norm() == 0:
                raise ValueError('話者埋め込みが非有限値またはゼロです')
            return value
        with self.torch.inference_mode():
            a, b = embedding(x), embedding(y)
            similarity = self.torch.nn.functional.cosine_similarity(a, b, dim=0).item()
        return similarity, {'embedding_dimension': a.numel(),
                            'interpretation': '同話者・異話者校正なし。知覚類似性の保証ではない。'}


class UtmosLocal:
    label, unit, direction = 'UTMOSv2予測MOS', 'predicted MOS', 'higher'

    def __init__(self, options, base, work, threads):
        from .mos import (CHECKPOINT_SHA256, CONFIG_HASHES, SOURCE_COMMIT,
                          _construct_model, _native_diagnostics)
        self.provenance = {'algorithm': 'UTMOSv2-fusion_stage3-fold0', 'source_commit': SOURCE_COMMIT,
                           'predict_dataset': 'bvcc', 'extraction_seed': 20261012,
                           'extraction_repetitions': 1, 'device': 'cpu', 'remove_silent_section': False,
                           'calibration': '対象ボコーダーでの人間評定校正は未実施'}
        checkpoint = file_asset(options, 'checkpoint', base, self.provenance, CHECKPOINT_SHA256)
        config = file_asset(options, 'config', base, self.provenance, CONFIG_HASHES['config.json'])
        preprocessor = file_asset(options, 'preprocessor_config', base, self.provenance,
                                  CONFIG_HASHES['preprocessor_config.json'])
        if config.name != 'config.json' or preprocessor.name != 'preprocessor_config.json' or config.parent != preprocessor.parent:
            raise ValueError('wav2vec2設定2ファイルを元の名前で同じディレクトリに置いてください')
        distribution = importlib.metadata.distribution('utmosv2')
        origin = json.loads(distribution.read_text('direct_url.json') or '{}')
        if origin.get('vcs_info', {}).get('commit_id') != SOURCE_COMMIT:
            raise Unavailable('UTMOSv2をuv.lockの固定commitから導入してください')
        self.torch, _ = torch_modules(threads)
        self.torch.backends.nnpack.set_flags(False)
        self.work = work
        self.diagnostics = _native_diagnostics
        with self.diagnostics(work):
            self.model = _construct_model(str(config.parent), checkpoint)
        self.provenance['packages'] = package_versions(('utmosv2', 'torch', 'transformers', 'timm', 'librosa'))

    def score(self, x, y, sr):
        state_numpy, state_python = np.random.get_state(), random.getstate()
        with self.torch.random.fork_rng(devices=[]):
            try:
                np.random.seed(20261012)
                random.seed(20261012)
                self.torch.manual_seed(20261012)
                with self.torch.inference_mode(), self.diagnostics(self.work):
                    result = self.model.predict(data=y.astype(np.float32), sr=sr, device='cpu',
                                                batch_size=1, num_workers=0, num_repetitions=1,
                                                predict_dataset='bvcc', remove_silent_section=False, verbose=False)
            finally:
                np.random.set_state(state_numpy)
                random.setstate(state_python)
        values = np.asarray(result).reshape(-1)
        if len(values) != 1:
            raise ValueError('UTMOSv2が単一波形に複数の値を返しました')
        return float(values[0]), {'reference_used': False, 'extraction_seed_reset_each_call': True}
