"""固定したUTMOSv2による予測MOS。音声の符号化・合成には使用しない。"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import logging
import math
import os
from contextlib import contextmanager
from pathlib import Path
import random
import tempfile
from threading import Lock
import time
from types import SimpleNamespace
import urllib.request

import numpy as np

SOURCE_COMMIT = "cc2700db57bb83ee13dc31ebe1b868c254e15d09"
MODEL_REVISION = "506474f2b33dc77c234d668cc419be1861899cad"
CHECKPOINT_SHA256 = "c8149d988e4bbf3f347e6966b5d769de347a5f8c59ffca1dc4bd4bf5b8585e57"
CONFIG_REVISION = "0b5b8e868dd84f03fd87d01f9c4ff0f080fecfe8"
CONFIG_HASHES = {
    "config.json": "4937977e24d12d1bba70cdce8709c3c04807a8e4ae8ddac4229c48c436ae99ae",
    "preprocessor_config.json": "b225d617c025463b9e157e06afea8b90dc7078fc70b013c533328423e0486b4a",
}
CHECKPOINT_NAME = "fold0_s42_best_model.pth"
_BUILD_LOCK = Lock()
_NATIVE_LOCK = Lock()


@contextmanager
def _native_diagnostics(directory):
    """標準エラーをログへ残し、ライブラリの一時生成物をcacheへ置く。"""
    Path(directory).mkdir(parents=True, exist_ok=True)
    with _NATIVE_LOCK, tempfile.TemporaryFile(dir=directory) as output:
        temporary_root = (Path(directory) / "tmp").resolve()
        temporary_root.mkdir(parents=True, exist_ok=True)
        previous_tempdir = tempfile.tempdir
        tempfile.tempdir = str(temporary_root)
        saved = os.dup(2)
        try:
            os.dup2(output.fileno(), 2)
            yield
        finally:
            os.dup2(saved, 2)
            os.close(saved)
            tempfile.tempdir = previous_tempdir
            output.seek(0)
            diagnostics = output.read().decode("utf-8", errors="replace").strip()
            if diagnostics:
                logging.warning("MOS計算ライブラリの標準エラー出力:\n%s", diagnostics, stack_info=True)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url, path, expected_hash=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_suffix(path.suffix + f".{os.getpid()}.part")
        logging.info("MOS測定器の配布物を取得: %s", url)
        with urllib.request.urlopen(url, timeout=45) as source, temporary.open("wb") as output:
            while chunk := source.read(4 * 1024 * 1024):
                output.write(chunk)
        if expected_hash is not None and _sha256(temporary) != expected_hash:
            raise ValueError(f"MOS配布物のSHA256が一致しません: {path.name}")
        temporary.replace(path)
    actual_hash = _sha256(path)
    if expected_hash is not None and actual_hash != expected_hash:
        raise ValueError(f"MOSキャッシュのSHA256が一致しません: {path.name}")
    return {"url": url, "sha256": actual_hash, "bytes": path.stat().st_size}


def _construct_model(config_dir, checkpoint):
    """最終checkpointで上書きされる学習前backbone重みの再取得を省く。"""
    import timm
    import torch
    import transformers
    import utmosv2
    from utmosv2.model import multi_spec, ssl

    configuration = transformers.AutoConfig.from_pretrained(config_dir, local_files_only=True)
    extractor = transformers.AutoFeatureExtractor.from_pretrained(config_dir, local_files_only=True)

    def image_model(*args, **kwargs):
        kwargs["pretrained"] = False
        return timm.create_model(*args, **kwargs)

    # 公式の構造をそのまま生成し、完全なstate_dictをstrictで読み込む。
    # 置換は構築中だけで、公式の前処理・推論経路には加えない。
    with _BUILD_LOCK:
        original = (ssl.AutoModel, ssl.AutoFeatureExtractor, multi_spec.timm)
        try:
            ssl.AutoModel = SimpleNamespace(from_pretrained=lambda *a, **k: transformers.AutoModel.from_config(configuration))
            ssl.AutoFeatureExtractor = SimpleNamespace(from_pretrained=lambda *a, **k: extractor)
            multi_spec.timm = SimpleNamespace(create_model=image_model, layers=timm.layers)
            model = utmosv2.create_model(pretrained=False, device="cpu")
        finally:
            ssl.AutoModel, ssl.AutoFeatureExtractor, multi_spec.timm = original
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True)
    model.eval()
    return model


class MosEvaluator:
    """波形ごとの予測値と適用条件を返す。失敗を別の指標で埋めない。"""

    def __init__(self, cache_root=None, *, repetitions=1, seed=20261012, threads=4):
        if repetitions < 1 or threads < 1:
            raise ValueError("MOSの反復回数とCPUスレッド数は正の整数にしてください")
        default = Path(__file__).resolve().parents[1] / ".cache" / "mos"
        self.cache_dir = Path(cache_root or os.environ.get("VOCODERBENCH_MOS_CACHE", default))
        self.repetitions, self.seed, self.threads = int(repetitions), int(seed), int(threads)
        self._model, self._attempted, self._error = None, False, None
        self._lock = Lock()
        self.provenance = {
            "name": "UTMOSv2", "quantity": "predicted_mos_not_human_rating",
            "source_repository": "https://github.com/sarulab-speech/UTMOSv2",
            "source_commit": SOURCE_COMMIT, "checkpoint_revision": MODEL_REVISION,
            "checkpoint_sha256": CHECKPOINT_SHA256, "fold": 0, "device": "cpu",
            "configuration": "fusion_stage3", "predict_dataset": "bvcc",
            "repetitions": self.repetitions, "extraction_seed": self.seed,
            "cpu_threads": self.threads, "remove_silent_section": False,
            "nnpack_enabled": False,
            "internal_sample_rate": 16000, "ssl_crop_seconds": 3.0,
            "spectrogram_crop_seconds": 1.4, "spectrogram_frames_per_repetition": 2,
            "spectrogram_inner_mixup": True, "short_input_extension": "tile",
            "code_license": "MIT", "weights_license": "MIT",
            "independent_human_rating_calibration": "not_performed_for_this_project",
            "scope": "JVS/LibriSpeechの再合成への適用は未校正。言語・発声別に集計する。",
            "paper_protocol_difference": "論文の5fold×5抽出平均ではなく、fold0と上記反復数。",
            "initialization": "official_architecture_then_complete_strict_state_dict",
        }

    def prepare(self):
        if self._attempted:
            return self._model is not None
        self._attempted = True
        try:
            distribution = importlib.metadata.distribution("utmosv2")
            installed = json.loads(distribution.read_text("direct_url.json") or "{}")
            if installed.get("vcs_info", {}).get("commit_id") != SOURCE_COMMIT:
                raise ValueError("UTMOSv2は指定commitからuvで導入してください")
            self.provenance["packages"] = {
                name: importlib.metadata.version(name)
                for name in ("torch", "torchaudio", "torchvision", "transformers", "timm", "librosa", "numpy", "utmosv2")
            }
            checkpoint = self.cache_dir / "weights" / CHECKPOINT_NAME
            url = f"https://huggingface.co/sarulab-speech/UTMOSv2/resolve/{MODEL_REVISION}/{CHECKPOINT_NAME}"
            self.provenance["checkpoint"] = _download(url, checkpoint, CHECKPOINT_SHA256)
            config_dir = self.cache_dir / "wav2vec2_config"
            self.provenance["feature_configuration"] = {}
            for filename in ("config.json", "preprocessor_config.json"):
                config_url = f"https://huggingface.co/facebook/wav2vec2-base/resolve/{CONFIG_REVISION}/{filename}"
                self.provenance["feature_configuration"][filename] = _download(config_url, config_dir / filename, CONFIG_HASHES[filename])
            with _native_diagnostics(self.cache_dir):
                import torch
                torch.set_num_threads(self.threads)
                torch.backends.nnpack.set_flags(False)
                self._model = _construct_model(config_dir, checkpoint)
            self.provenance["initialization_status"] = "ready"
            logging.info("固定UTMOSv2をCPUへ読み込みました（fold0・%d反復）", self.repetitions)
            return True
        except Exception as error:
            logging.exception("UTMOSv2の初期化に失敗")
            self._error = f"{type(error).__name__}: {error}"
            self.provenance.update(initialization_status="failed", initialization_error=self._error)
            return False

    def predict(self, waveform, sample_rate, *, kind="natural_speech", language=None, style=None):
        row = {"status": "not_applicable", "value": None, "predicted_mos": None, "model": "UTMOSv2",
               "language": language, "style": style,
               "domain_validation": "未校正の探索的予測", "extraction_seed": self.seed,
               "repetitions": self.repetitions}
        if kind != "natural_speech":
            row["reason"] = "人工診断信号は音声自然性MOSの対象にしません"
            return row
        start = time.perf_counter()
        try:
            signal = np.asarray(waveform, dtype=np.float32)
            if signal.ndim != 1 or len(signal) == 0 or not np.all(np.isfinite(signal)):
                raise ValueError("MOS入力は有限値を持つ空でないモノラル波形にしてください")
            if not isinstance(sample_rate, (int, np.integer)) or sample_rate <= 0:
                raise ValueError("MOS入力のサンプルレートは正の整数にしてください")
            internal_length = math.ceil(len(signal) * 16000 / sample_rate)
            row.update(input_samples=len(signal), input_sample_rate=int(sample_rate),
                       input_seconds=len(signal)/sample_rate,
                       input_float32_sha256=hashlib.sha256(signal.astype("<f4").tobytes()).hexdigest(),
                       internal_samples=internal_length, ssl_processed_samples=48000,
                       spectrogram_processed_samples_per_frame=22400,
                       ssl_tile_repetitions=48000//internal_length+1 if internal_length <= 48000 else 1,
                       spectrogram_tile_repetitions=22400//internal_length+1 if internal_length <= 22400 else 1)
            if not self.prepare():
                raise RuntimeError(self._error or "UTMOSv2の初期化に失敗しました")
            import torch
            with self._lock, torch.random.fork_rng(devices=[]):
                numpy_state, python_state = np.random.get_state(), random.getstate()
                try:
                    np.random.seed(self.seed)
                    random.seed(self.seed)
                    torch.manual_seed(self.seed)
                    with _native_diagnostics(self.cache_dir):
                        prediction = self._model.predict(
                            data=signal, sr=int(sample_rate), device="cpu", batch_size=1,
                            num_workers=0, num_repetitions=self.repetitions,
                            predict_dataset="bvcc", remove_silent_section=False, verbose=False,
                        )
                finally:
                    np.random.set_state(numpy_state)
                    random.setstate(python_state)
            value = float(np.asarray(prediction).reshape(-1)[0])
            if not np.isfinite(value):
                raise ValueError("UTMOSv2が非有限値を返しました")
            row.update(status="measured", value=value, predicted_mos=value, reason=None)
        except Exception as error:
            logging.exception("予測MOSの測定に失敗")
            row.update(status="failed", value=None, predicted_mos=None, reason=f"{type(error).__name__}: {error}")
        row["seconds"] = time.perf_counter()-start
        return row
