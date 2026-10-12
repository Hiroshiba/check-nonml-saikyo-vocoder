"""PR #24で実測した構成の解析・合成アダプター。操作・学習のAPIではない。"""
from __future__ import annotations
import sys
import time
from types import SimpleNamespace
import numpy as np
import torch
from .common import digest

def total_params(*models):
    return sum((p.numel() for model in models for p in model.parameters()))

def build_golf(src, models, out):
    import yaml
    import pyworld
    from importlib import import_module
    sys.path.insert(0, str(src / 'golf'))
    from ltng.ae import VoiceAutoEncoder
    from models.audiotensor import AudioTensor
    cfg = src / 'golf/ckpts/interspeech24/golf-ff/config.yaml'
    config = yaml.safe_load(cfg.read_text())['model']['init_args']

    def obj(c):
        if isinstance(c, list):
            return [obj(v) for v in c]
        if not isinstance(c, dict):
            return c
        if 'class_path' in c:
            mod, cls = c['class_path'].rsplit('.', 1)
            return getattr(import_module(mod), cls)(**obj(c.get('init_args', {})))
        return {k: obj(v) for k, v in c.items()}
    path = next(cfg.parent.rglob('*.ckpt'))
    model = VoiceAutoEncoder(**obj(config))
    model.load_state_dict(torch.load(path, map_location='cpu', weights_only=False)['state_dict'])
    model.eval()
    sr = model.sample_rate
    adapter = SimpleNamespace(sr=sr, info=dict(variant='GOLF-ff Interspeech24; WORLD DIO F0 included', parameter_count=total_params(model), checkpoint=str(path), checkpoint_sha256=digest(path)), stage_times={})

    def encode(x, p):
        t = time.perf_counter()
        f0, _ = pyworld.dio(x, sr, f0_floor=60, f0_ceil=1000, channels_in_octave=2, frame_period=5)
        f0 = AudioTensor(torch.tensor(f0, dtype=torch.float32)[None], sr // 200)
        adapter.stage_times['external_f0_s'] = time.perf_counter() - t
        a = AudioTensor(torch.tensor(x, dtype=torch.float32)[None])
        params = model.encoder(a, f0=f0)
        params.pop('f0', None)
        params['phase'] = torch.where(f0 == 0, 150, f0) / sr
        if 'voicing_logits' in params:
            params['voicing'] = torch.sigmoid(params.pop('voicing_logits'))
        return params
    adapter.encode = encode
    adapter.decode = lambda z: model.decoder(**z)
    return adapter

def build_sifigan(src, models, out):
    import yaml
    import joblib
    import pyworld as pw
    import pysptk
    from hydra.utils import instantiate
    from omegaconf import OmegaConf
    sys.path.insert(0, str(src / 'sifigan'))
    from sifigan.bin.anasyn import convert_continuos_f0, ALPHA
    from sifigan.utils.features import SignalGenerator, dilated_factor
    path = next((p for p in models.rglob('*.pkl') if 'checkpoint' in p.name))
    stats = next(models.rglob('*.joblib'))
    base = yaml.safe_load((src / 'sifigan/sifigan/bin/config/anasyn.yaml').read_text())
    base.pop('defaults', None)
    gen = yaml.safe_load((src / 'sifigan/sifigan/bin/config/generator/sifigan.yaml').read_text())
    base['generator'] = gen
    base['f0_floor'] = 60
    base['f0_ceil'] = 1000
    config = OmegaConf.create(base)
    model = instantiate(config.generator)
    state = torch.load(path, map_location='cpu', weights_only=False)
    model.load_state_dict(state['model']['generator'])
    model.remove_weight_norm()
    model.eval()
    scaler = joblib.load(stats)
    sg = SignalGenerator(sample_rate=config.sample_rate, hop_size=int(config.sample_rate * config.frame_period * 0.001), sine_amp=config.sine_amp, noise_amp=config.noise_amp, signal_types=config.signal_types)
    adapter = SimpleNamespace(sr=config.sample_rate, info=dict(variant='published24k multispeaker speech+singing; WORLD Harvest included', parameter_count=total_params(model), checkpoint=str(path), checkpoint_sha256=digest(path), stats_sha256=digest(stats), config=OmegaConf.to_container(config, resolve=True)), stage_times={})

    def encode(x, p):
        t0 = time.perf_counter()
        f0, t = pw.harvest(x, config.sample_rate, f0_floor=60, f0_ceil=1000, frame_period=config.frame_period)
        adapter.stage_times['external_f0_s'] = time.perf_counter() - t0
        sp = pw.cheaptrick(x, f0, t, config.sample_rate)
        ap = pw.d4c(x, f0, t, config.sample_rate)
        mcep = pysptk.sp2mc(sp, order=config.mcep_dim, alpha=ALPHA[config.sample_rate])
        mcap = pysptk.sp2mc(ap, order=config.mcap_dim, alpha=ALPHA[config.sample_rate])
        bap = pw.code_aperiodicity(ap, config.sample_rate)
        uv, cf0 = convert_continuos_f0(f0)
        uv = uv[:, None]
        f0 = f0[:, None]
        cf0 = cf0[:, None]
        features = dict(uv=uv, f0=f0, cf0=cf0, mcep=mcep, mcap=mcap, bap=bap)
        c = np.concatenate([scaler[k].transform(features[k]) for k in config.aux_feats], axis=1)
        dfs = [np.repeat(dilated_factor(cf0, config.sample_rate, df), us) for df, us in zip(config.dense_factors, np.cumprod(config.generator.upsample_scales))]
        cf0 = torch.tensor(cf0, dtype=torch.float32).view(1, 1, -1)
        c = torch.tensor(c, dtype=torch.float32).T[None]
        dfs = [torch.tensor(df, dtype=torch.float32).view(1, 1, -1) for df in dfs]
        return (cf0, c, dfs)
    adapter.encode = encode
    adapter.decode = lambda z: model(sg(z[0]).float(), z[1], z[2])[0]
    return adapter
