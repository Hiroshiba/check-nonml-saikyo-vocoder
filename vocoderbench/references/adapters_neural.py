"""PR #24で実測した構成の解析・合成アダプター。操作・学習のAPIではない。"""
from __future__ import annotations
import json
import sys
from types import SimpleNamespace
import numpy as np
import torch
from .common import digest

def total_params(*models):
    return sum((p.numel() for model in models for p in model.parameters()))

def build_dac(src, models, out):
    sys.path.insert(0, str(src / 'dac'))
    import dac
    path = models / 'dac/weights.pth'
    model = dac.DAC.load(path).eval()

    def enc(x, p):
        return model.encode(model.preprocess(torch.from_numpy(x.astype(np.float32))[None, None], model.sample_rate))[0]
    return SimpleNamespace(sr=model.sample_rate, encode=enc, decode=model.decode, info=dict(variant='44khz official pretrained; full RVQ', parameter_count=total_params(model), checkpoint_sha256=digest(path), n_codebooks=model.n_codebooks))

def build_facodec(src, models, out):
    sys.path.insert(0, str(src / 'facodec'))
    from ns3_codec import FACodecEncoder, FACodecDecoder
    ep = models / 'naturalspeech3_facodec/ns3_facodec_encoder.bin'
    dp = models / 'naturalspeech3_facodec/ns3_facodec_decoder.bin'
    enc = FACodecEncoder(ngf=32, up_ratios=[2, 4, 5, 5], out_channels=256)
    dec = FACodecDecoder(in_channels=256, upsample_initial_channel=1024, ngf=32, up_ratios=[5, 5, 4, 2], vq_num_q_c=2, vq_num_q_p=1, vq_num_q_r=3, vq_dim=256, codebook_dim=8, codebook_size_prosody=10, codebook_size_content=10, codebook_size_residual=10, use_gr_x_timbre=True, use_gr_residual_f0=True, use_gr_residual_phone=True)
    enc.load_state_dict(torch.load(ep, map_location='cpu', weights_only=False))
    dec.load_state_dict(torch.load(dp, map_location='cpu', weights_only=False))
    enc.eval()
    dec.eval()

    def encode(x, p):
        x = torch.from_numpy(x.astype(np.float32))[None, None]
        x = torch.nn.functional.pad(x, (0, -x.shape[-1] % 200))
        z, codes, _, quantized, spk = dec(enc(x), eval_vq=False, vq=True)
        return (z, spk)
    return SimpleNamespace(sr=16000, encode=encode, decode=lambda z: dec.inference(*z), info=dict(variant='FACodec v1 all six codebooks incl. residual', parameter_count=total_params(enc, dec), checkpoint_sha256=[digest(ep), digest(dp)]))

def build_hifiglot(src, models, out):
    sys.path.insert(0, str(src / 'hifiglot/src'))
    from neural_formant_synthesis.third_party.hifi_gan.env import AttrDict
    from neural_formant_synthesis.feature_extraction import feature_extractor, Normaliser, MedianPool1d
    from neural_formant_synthesis.models import SourceFilterFormantSynthesisGenerator
    from safetensors.torch import load_file
    h = AttrDict(json.loads((src / 'hifiglot/configs/hifiglot/config_hifigan.json').read_text()))
    fm = AttrDict(json.loads((src / 'hifiglot/configs/hifiglot/config_feature_map.json').read_text()))
    path = next((models / 'HiFi-Glot/hifiglot').rglob('model.safetensors'))
    model = SourceFilterFormantSynthesisGenerator(fm_config=fm, g_config=h, pretrained_fm=None, freeze_fm=False)
    model.load_state_dict(load_file(str(path)))
    model.eval()
    extractor = feature_extractor(sr=h.sampling_rate, window_samples=h.win_size, step_samples=h.hop_size, formant_ceiling=10000, max_formants=4)
    mf = MedianPool1d(kernel_size=7, stride=1, padding=0, same=True)
    norm = Normaliser()

    def encode(x, p):
        formants, energy, centroid, tilt, pitch, voicing = extractor(torch.from_numpy(x))
        formants = mf(formants.T.unsqueeze(1)).squeeze(1).T
        pitch = pitch.squeeze(0)
        voicing = voicing.squeeze(0)
        linear_pitch = pitch
        pitch, formants, tilt, centroid, energy = norm(pitch, formants, tilt, centroid, energy)
        feat = torch.cat((pitch.unsqueeze(1), formants, tilt.unsqueeze(1), centroid.unsqueeze(1), energy.unsqueeze(1), voicing.unsqueeze(1)), dim=-1).T.float()[None]
        return (feat, linear_pitch[None])
    return SimpleNamespace(sr=h.sampling_rate, encode=encode, decode=lambda z: model(*z)[0], info=dict(variant='official HiFi-Glot44.1k inference recipe', parameter_count=total_params(model), checkpoint=str(path), checkpoint_sha256=digest(path)))
