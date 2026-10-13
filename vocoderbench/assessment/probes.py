"""既知の音響変換を用いた測定器の適用範囲・制御追従の研究入力を生成する。"""
from pathlib import Path
import json

import numpy as np
from scipy.io import wavfile

from ..logging_utils import LoggedArgumentParser, run_cli


def generate(output):
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    sr, duration = 48000, 1.2
    n = round(sr * duration)
    t = np.arange(n) / sr

    def wav(name, audio):
        wavfile.write(root / name, sr, np.asarray(audio, dtype=np.float32))

    x = .2 * np.sin(2 * np.pi * 220 * t)
    wav('original.wav', x)
    # 線形cent軌跡に対する解析的位相。参照推定との差と既知F0との差を区別する。
    cents_per_second = 300 / duration
    exponent = np.log(2) * cents_per_second / 1200
    phase = 2 * np.pi * 220 * np.expm1(exponent * t) / exponent
    wav('pitch-ramp.wav', .2 * np.sin(phase))
    wav('gain-ramp.wav', x * 10 ** ((6 * t / duration) / 20))
    for db in (-1, 1, 3):
        wav(f'gain{db:g}.wav', x * 10 ** (db / 20))

    noise = .02 * np.random.default_rng(42).normal(size=n)
    frequencies = np.fft.rfftfreq(n, 1 / sr)
    slope_filter = (np.maximum(frequencies, 40) / 1000) ** (3 / (20 * np.log10(2)))
    wav('noise.wav', noise)
    wav('tilted.wav', np.fft.irfft(np.fft.rfft(noise) * slope_filter, n=n))

    events = [.2, .6, 1.0]
    source_times, output_times = [0, .4, .8, duration], [0, .5, .9, 1.4]
    warped_events = np.interp(events, source_times, output_times)
    output_t = np.arange(round(sr * output_times[-1])) / sr
    wav('events.wav', sum(.3 * np.exp(-((t - z) / .003) ** 2) for z in events))
    wav('events-warp.wav', sum(.3 * np.exp(-((output_t - z) / .003) ** 2) for z in warped_events))

    jobs = []

    def job(metric, identifier, purpose, **conditions):
        jobs.append({'id': identifier, 'metric': metric, 'method': 'analytic-transformation',
                     'case': 'research-' + metric, 'condition': 'declared-operation', 'seed': 0,
                     'speaker': 'not_applicable', 'language': 'not_applicable', 'style': 'synthetic',
                     'kind': 'artificial_probe', 'research_question': purpose, **conditions})

    job('auditory_local', 'erb-gain', '狭帯域信号の既知ゲインに対する帯域平均・局所値・有効セル数の感度',
        reference='original.wav', output='gain3.wav',
        intervals=[{'start': .3, 'end': .5, 'label': '事前固定区間'}])
    # 10 ms刻みの既知軌跡。実測F0を正解軌跡へ流用しない。
    truth_times = np.linspace(0, duration, 121)
    job('pitch_tracking', 'pitch-dynamic', '80 ms窓のF0推定器に対する連続音高変化の推定誤差',
        reference='original.wav', output='pitch-ramp.wav',
        target_cents={'times': [0, duration], 'values': [0, 300]},
        target_f0_hz={'times': truth_times.tolist(),
                      'values': (220 * np.exp2(cents_per_second * truth_times / 1200)).tolist()})
    job('gain_tracking', 'gain-dynamic', '既知の連続振幅変化に対する窓内RMSの追従誤差',
        reference='original.wav', output='gain-ramp.wav',
        target_gain_db={'times': [0, duration], 'values': [0, 6]})
    job('local_time', 'local-events', '非一様な既知時間写像に対する孤立イベントの時刻推定誤差',
        reference='events.wav', output='events-warp.wav', probe_kind='isolated_energy_events',
        time_map={'reference_seconds': source_times, 'output_seconds': output_times},
        event_seconds=events, search_half_width_seconds=.05, minimum_peak_ratio=.2)
    job('timbre_tracking', 'spectral-slope', '固定帯域で既知のスペクトル傾斜変化を推定する際の誤差',
        reference='noise.wav', output='tilted.wav', low_hz=300, high_hz=3000,
        target_delta_db_per_octave=3)
    job('interference', 'gain-interference', '既知ゲイン操作が他の音響属性推定へ与える応答',
        low_hz=300, high_hz=3000,
        attribute_scales={'pitch_cents': 100, 'level_db': 1,
                          'slope_db_per_octave': 1, 'duration_seconds': .1},
        sweeps=[{'control': 'gain', 'control_unit': 'dB', 'delta': 1, 'control_scale': 1,
                 'minus': 'gain-1.wav', 'plus': 'gain1.wav',
                 'expected_response': {'pitch_cents': 0, 'level_db': 1,
                                       'slope_db_per_octave': 0, 'duration_seconds': 0}}])
    manifest = {
        'schema_version': 1, 'baseline_method': 'unselected',
        'scope': '既知変換による測定器の適用範囲・制御追従研究。実方式の品質比較ではない。'
                 '原音自己比較・異常入力による動作確認は行わない。各研究目的はjobへ記録する。',
        'generation': {'revision': 'acoustic-transformations-v2', 'sample_rate': sr,
                       'noise_rng_seed': 42, 'job_seed_meaning': '固定人工条件の識別ラベル',
                       'pitch_truth_interpolation': '10 ms刻みの既知F0を線形補間。測定F0とは独立'},
        'jobs': jobs,
    }
    (root / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(root, 'research conditions', len(jobs))


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    generate(parser.parse_args().output)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'assessment-probes'))
