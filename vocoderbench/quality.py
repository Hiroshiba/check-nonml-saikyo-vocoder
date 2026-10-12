"""ローカル資産で保存済み再合成音を追加評価し、JSON/HTMLと反復時間を残す。"""
from __future__ import annotations

from datetime import datetime, timezone
import gc
import importlib
import logging
from pathlib import Path
import time

from .quality_core import (NotApplicable, Unavailable, check_pair, environment, load_audio,
                           measure_repeated, offline_environment, read_json, sha256, write_json)
from .quality_inputs import load_benchmark, load_manifest
from .quality_report import render

REGISTRY = {
    'utmosv2': ('quality_backends', 'UtmosLocal'),
    'scoreq': ('quality_backends', 'ScoreqReference'),
    'visqol_audio': ('quality_visqol', 'VisqolAudio'),
    'speaker_ecapa': ('quality_backends', 'EcapaSimilarity'),
    'erb': ('quality_backends', 'ErbDistance'),
}


def evaluate(inputs, settings, settings_directory, output, metrics, repetitions=5, threads=4):
    if not metrics or len(set(metrics)) != len(metrics) or any(m not in REGISTRY for m in metrics):
        raise ValueError('指標IDが空・重複・未対応です')
    if not 1 <= repetitions <= 100 or not 1 <= threads <= 64:
        raise ValueError('反復は1〜100、スレッドは1〜64にしてください')
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('追加評価は既存結果を上書きしません。新しい出力先を指定してください')
    output.mkdir(parents=True)
    directory = Path(__file__).parent
    report = {'schema_version': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'input': inputs, 'settings': settings, 'environment': environment(),
              'requested_metrics': metrics, 'repetitions': repetitions, 'threads': threads,
              'source_sha256': {p.name: sha256(p) for p in sorted(directory.glob('quality*.py'))},
              'metrics': {}, 'rows': [], 'network': 'no_downloads', 'reference_cache': False,
              'input_file_sha256': {}}
    for name in ('mos.py', 'logging_utils.py'):
        if (directory / name).exists():
            report['source_sha256'][name] = sha256(directory / name)
    write_json(output / 'contract.json', {k: v for k, v in report.items() if k not in ('metrics', 'rows')})
    with offline_environment():
        for metric in metrics:
            module, class_name = REGISTRY[metric]
            cls = getattr(importlib.import_module('.' + module, __package__), class_name)
            backend, preparation = None, {'status': 'not_configured', 'seconds': None}
            options = settings.get('metrics', {}).get(metric)
            if options is not None:
                start = time.perf_counter()
                try:
                    backend = cls(options, settings_directory, output / 'work' / metric, threads)
                    preparation.update(status='ready', provenance=backend.provenance)
                except (ImportError, FileNotFoundError, Unavailable) as error:
                    logging.exception('追加指標を準備できません: %s', metric)
                    preparation.update(status='unavailable', reason=f'{type(error).__name__}: {error}')
                except Exception as error:
                    logging.exception('追加指標の初期化失敗: %s', metric)
                    preparation.update(status='failed', reason=f'{type(error).__name__}: {error}')
                preparation['seconds'] = time.perf_counter() - start
            report['metrics'][metric] = preparation
            for case in inputs['cases']:
                methods = {'identity': case['reference'], **case['outputs']}
                for method, filename in methods.items():
                    row = {'metric': metric, 'label': cls.label, 'unit': cls.unit, 'direction': cls.direction,
                           'case': case['id'], 'method': method, 'value': None,
                           'language': case.get('language'), 'style': case.get('style'), 'speaker': case.get('speaker'),
                           'status': preparation['status'] if backend is None else 'pending'}
                    if backend is None:
                        row['reason'] = preparation.get('reason', '資産設定がありません。自動取得はしません')
                    else:
                        try:
                            status = case.get('upstream_status', {}).get(method, 'measured')
                            row['upstream_status'] = status
                            if status != 'measured':
                                raise ValueError(f'元の再合成が未完了または失敗: {status}')
                            x, sr, reference_info = load_audio(case['reference'], case.get('sample_rate'))
                            y, other_sr, output_info = load_audio(filename, case.get('sample_rate'))
                            row.update(reference=reference_info, output=output_info)
                            for info in (reference_info, output_info):
                                hashes = report['input_file_sha256']
                                old = hashes.setdefault(info['path'], info['file_sha256'])
                                if old != info['file_sha256']:
                                    raise ValueError('計測中に入力ファイルが変更されました')
                            if other_sr != sr:
                                raise ValueError('入出力のサンプルレートが一致しません')
                            check_pair(x, y, sr)
                            if case['kind'] == 'artificial_probe' and metric != 'erb':
                                raise NotApplicable('人工診断信号に音声品質・話者指標を適用しません')
                            measurement = measure_repeated(lambda: backend.score(x, y, sr), repetitions)
                            row.update(measurement=measurement, status=measurement['status'], value=measurement['value'])
                        except NotApplicable as error:
                            logging.warning('追加指標の対象外: %s / %s', metric, error)
                            row.update(status='not_applicable', reason=str(error))
                        except Exception as error:
                            logging.exception('追加評価の入力または処理に失敗: %s / %s / %s', metric, case['id'], method)
                            row.update(status='failed', reason=f'{type(error).__name__}: {error}')
                    report['rows'].append(row)
                    write_json(output / 'results.json', report)
                    logging.info('追加評価: %s / %s / %s: %s', metric, case['id'], method, row['status'])
            del backend
            gc.collect()
    render(report, output)
    code = int(any(r['status'] != 'measured' for r in report['rows']))
    return report, code


def main():
    from .logging_utils import LoggedArgumentParser
    parser = LoggedArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--manifest', type=Path, help='任意方式のWAV/NPY入力一覧')
    group.add_argument('--benchmark', type=Path, help='既存固定比較のディレクトリ。保存seed 0波形を使う')
    parser.add_argument('--assets', type=Path, required=True, help='ローカル資産のJSON。パスはこのJSONの位置から解決')
    parser.add_argument('--metrics', nargs='+', choices=tuple(REGISTRY), default=list(REGISTRY))
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    settings = read_json(args.assets)
    if settings.get('schema_version') != 1 or not isinstance(settings.get('metrics'), dict):
        raise ValueError('資産設定はschema_version=1とmetrics辞書が必要です')
    if any(not isinstance(v, dict) and v is not None for v in settings['metrics'].values()):
        raise ValueError('各指標の設定は辞書またはnullにしてください')
    if set(settings['metrics']) - set(REGISTRY):
        raise ValueError('資産設定に未知の指標IDがあります')
    inputs = load_manifest(args.manifest) if args.manifest else load_benchmark(args.benchmark)
    _, code = evaluate(inputs, settings, args.assets.resolve().parent, args.output,
                       args.metrics, args.repetitions, args.threads)
    return code


if __name__ == '__main__':
    from .logging_utils import run_cli
    raise SystemExit(run_cli(main, 'quality-metrics'))
