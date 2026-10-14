"""短い公開音声の既存許諾範囲。測定方式や数値順位には適用しない。"""
from __future__ import annotations

from html import escape
import json

from all_metrics_common import ROOT

PUBLIC_IDS = ('librispeech_1089-134686-0008', 'librispeech_1188-133604-0003')
PUBLIC_METHODS = ('original', 'hnm', 'world_harvest', 'facodec', 'hifiglot', 'llsm2', 'magphase')
WITHHELD = {
    'golf': '固定checkpointに適用される重み固有の許諾が未確認のため、音声の公開を保留。',
    'sifigan': '固定配布archiveに重み固有のLICENSE/NOTICEがなく、明示許諾未確認のため、音声の公開を保留。',
}
TERMS_SHA256 = '5e271387d1fb18b156f33a3e2bc3e8641a7bacf516d9cdc64768a00d85d05048'
CREDITS_NAME = 'audio_credits.html'
CREDITS_TEMPLATE = ROOT / 'docs/audio_credits_ja.html'


def public_ids(dataset):
    selected = dataset['public_audio_example_ids']
    if len(selected) != 2 or set(selected) != set(PUBLIC_IDS):
        raise ValueError('公開音声は既存許諾の固定2 IDだけです')
    return selected


def credits_html(samples, excluded):
    """音声bytesやローカルpathを含めず、実例の出典・変更・区間・hashを表示する。"""
    records = {'samples': [{key: value for key, value in sample.items() if key != 'data_uri'}
                           for sample in samples], 'excluded': excluded}
    template = CREDITS_TEMPLATE.read_text(encoding='utf-8')
    marker = '{{AUDIO_RECORDS_JSON}}'
    if template.count(marker) != 1:
        raise ValueError('音声帰属テンプレートに実ファイル情報の挿入位置が必要です')
    return template.replace(marker, escape(json.dumps(records, ensure_ascii=False, indent=2)))
