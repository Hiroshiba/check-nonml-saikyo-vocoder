"""全件確定集約から日本語HTML。途中値・未測定値を補わない。"""
import base64
import hashlib
import html
import io
from pathlib import Path
import wave

from .chunk_contracts import ContractError, read, sha, validate_plan
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli

METHOD_NAMES = {'pml': '現ベース PML', 'world_harvest': 'WORLD Harvest',
                'ahm_cartesian_node_editor_v1': '候補 aHM＋Cartesian編集', 'original': '原音'}
CONDITION_NAMES = {'native': '無編集', 'pitch_minus3': '−3半音', 'pitch_plus3': '＋3半音'}
ALLOWED_AUDIO_CASES = {'librispeech_1089-134686-0008', 'librispeech_1188-133604-0003'}


def esc(value):
    return html.escape(str(value), quote=True)


def number(value):
    return '—' if value is None else f'{value:.5g}'


def interval(value):
    return '区間なし' if value is None else f'[{number(value[0])}, {number(value[1])}]'


def audio_section(manifest_path):
    if manifest_path is None:
        return '<p>権利確認済み短音声は、この版にはまだ収録していません。</p>'
    manifest = read(manifest_path)
    chunks = []
    seen = set()
    for item in manifest['clips']:
        identity = (item['case'], item['method'], item['condition'])
        if (identity in seen or item['case'] not in ALLOWED_AUDIO_CASES
                or item['method'] not in METHOD_NAMES or item['condition'] != 'native'
                or item['license'] != 'CC-BY-4.0' or item['start_sample'] != 0):
            raise ContractError('公開短音声の許可範囲外です')
        seen.add(identity)
        path = manifest_path.parent / item['path']
        blob = path.read_bytes()
        if hashlib.sha256(blob).hexdigest() != item['sha256']:
            raise ContractError('短音声のSHAが一致しません')
        with wave.open(io.BytesIO(blob), 'rb') as wav:
            if (wav.getnchannels() != 1 or wav.getframerate() != 16000
                    or not 0 < wav.getnframes() <= 32000
                    or wav.getnframes() != item['samples']):
                raise ContractError('短音声は16kHz mono先頭2秒以下に限定します')
        source = item['source_url']
        if not source.startswith('https://www.openslr.org/'):
            raise ContractError('原音の公式出典URLが必要です')
        encoded = base64.b64encode(blob).decode('ascii')
        chunks.append(f'<div class="clip"><strong>{esc(item["case"])} / '
                      f'{esc(METHOD_NAMES[item["method"]])}</strong><br>'
                      f'<audio controls preload="none" src="data:audio/wav;base64,{encoded}"></audio>'
                      f'<p>先頭{item["samples"]/16000:g}秒。<a href="{esc(source)}">LibriSpeech / OpenSLR</a>、'
                      '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>。'
                      f'変更：{esc(item["changes"])}。SHA256: <small>{esc(item["sha256"])}</small></p></div>')
    return ''.join(chunks)


def axis_table(axis):
    name = axis.get('label', axis['id'])
    unit = axis.get('unit', '')
    direction = {'higher': '大きいほど良い', 'lower': '小さいほど良い', 'diagnostic': '診断値・順位なし'}[axis['direction']]
    result = [f'<section><h3>{esc(name)} <small>{esc(unit)} / {direction}</small></h3>',
              f'<p>条件：{esc(CONDITION_NAMES[axis["condition"]])}。主比較の共通支持：'
              f'{axis["common_support"]["common_valid_recordings"]}/120録音、'
              f'{axis["common_support"]["common_valid_speakers"]}/40話者。</p>',
              '<div class="scroll"><table><thead><tr><th>方式</th><th>順位</th><th>共通支持の値</th>'
              '<th>95%区間</th><th>成功／予定</th><th>現PMLとの差（対応支持）</th></tr></thead><tbody>']
    common = axis['common_support']['methods']
    for method in axis['methods']:
        row = common.get(method)
        if method == 'original':
            row = axis['own_support_unranked'][method]
        state = axis['method_states'][method]
        rank = row['rank'] if row else None
        badge = f'<strong class="rank r{rank}">{rank}位</strong>' if rank is not None else '—'
        value = number(row['value']) if row else '比較対象外'
        ci = interval(row['ci95']) if row else '—'
        pair = axis['pairwise_pml'].get(method)
        difference = '—'
        if pair:
            delta = pair['methods'][method]['pml_difference']
            difference = (f'{number(delta["value"])} {interval(delta["ci95"])}'
                          f'（{pair["common_valid_recordings"]}録音）')
        result.append(f'<tr><th>{esc(METHOD_NAMES.get(method, method))}</th><td>{badge}</td>'
                      f'<td>{value}</td><td>{ci}</td><td>{state["measured_recordings"]}/120</td>'
                      f'<td>{difference}</td></tr>')
    result.append('</tbody></table></div><details><summary>欠測・単独支持の参考値</summary><ul>')
    for method in axis['methods']:
        own = axis['own_support_unranked'][method]
        states = axis['method_states'][method]
        reasons = ', '.join(f'{esc(k)}: {v}' for k, v in states['reason_counts'].items())
        result.append(f'<li>{esc(METHOD_NAMES.get(method, method))}：単独支持 {number(own["value"])}、'
                      f'{own["valid_recordings"]}録音/{own["valid_speakers"]}話者。{reasons}</li>')
    excluded = axis['structurally_unsupported_methods']
    if excluded:
        result.append('<li>全120件で操作未対応のため共通比較から除外：'+', '.join(esc(m) for m in excluded)+'</li>')
    result.append('</ul></details></section>')
    return ''.join(result)


def render(plan_path, summary_path, metadata_path, audio_path, expected_summary_sha):
    plan = validate_plan(read(plan_path))
    if sha(summary_path) != expected_summary_sha:
        raise ContractError('確定集約のSHAが一致しません')
    summary = read(summary_path)
    if (summary.get('schema_version') != 2 or summary.get('planned_recordings') != 120
            or summary.get('planned_speakers') != 40
            or {r['chunk_id'] for r in summary.get('chunk_sources', [])} != {r['id'] for r in plan['chunks']}
            or len(summary.get('chunk_sources', [])) != 10):
        raise ContractError('全10区間・120録音・40話者の確定集約が必要です')
    if summary.get('validation_state') != 'validated_end' or summary['run_plan_sha256'] != sha(plan_path):
        raise ContractError('全件確定集約と計画の対応が必要です')
    expected = [(a['id'], a['condition']) for a in plan['axes']]
    if [(a['id'], a['condition']) for a in summary['axes']] != expected:
        raise ContractError('集約軸が計画と一致しません')
    for declared, observed in zip(plan['axes'], summary['axes'], strict=True):
        if any(observed[k] != declared[k] for k in ('methods', 'direction')):
            raise ContractError('集約の方式・順位方向が計画と一致しません')
    metadata = read(metadata_path)
    if (len(metadata['axes']) != len(expected)
            or {(a['id'], a['condition']) for a in metadata['axes']} != set(expected)):
        raise ContractError('表示ラベルの軸に重複・不足があります')
    labels = {(r['id'], r['condition']): r for r in metadata['axes']}
    axes = [{**a, 'label': labels[a['id'], a['condition']]['label'],
             'unit': labels[a['id'], a['condition']]['unit']} for a in summary['axes']]
    body = ''.join(axis_table(a) for a in axes if a['condition'] == 'native')
    edited = ''.join(axis_table(a) for a in axes if a['condition'] != 'native')
    return '''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>aHM固定Cartesian編集と現PMLの多指標比較</title><style>
:root{color-scheme:light dark;font:16px/1.6 system-ui,sans-serif}body{max-width:1200px;margin:24px auto;padding:0 20px}h1{font-size:1.7rem}h2{margin-top:2.4rem}h3{font-size:1.08rem}section{padding:12px 0;border-bottom:1px solid #8885}small{font-weight:normal;overflow-wrap:anywhere}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{text-align:left;padding:8px;border-bottom:1px solid #8885;white-space:nowrap}details{margin:10px 0}summary{cursor:pointer}.rank{display:inline-block;padding:2px 10px;border:2px solid currentColor;border-radius:8px}.r1{background:#f6cd4b;color:#322600}.r2{background:#d0d8e3;color:#243044}.r3{background:#dbaf88;color:#35200e}.clip{padding:12px;border:1px solid #8885;margin:12px 0}audio{width:min(100%,420px)}.note{border-left:4px solid #8597bb;padding:10px 16px;background:#8881}
</style><main><h1>aHM固定Cartesian編集と現PMLの多指標比較</h1>
<p>固定120録音・40話者。現ベースはPML pml-lowband-fwcep60-v1です。候補の採用は未決定です。</p>
<div class="note">各指標で良い点と弱い点を比較します。総合点・平均順位は作りません。予測MOSは新しい人間の聴取評定ではありません。順位は同じ録音の共通支持に限り、欠測を0として埋めません。95%区間は話者bootstrapによる記述的区間です。</div>
<h2>無編集の比較</h2>'''+body+'<h2>短音声の比較</h2>'+audio_section(audio_path)+'''<h2>音高編集の比較</h2>'''+edited+'''<h2>この集約の範囲</h2><p>ここに示すのは通常品質と±3半音の編集評価です。特徴空間ABX・独立trainからの読み出し・実行速度とpayload量は別の測定群であり、このページだけで全研究の完了とは扱いません。</p><details><summary>再現用の識別子</summary><p>計画SHA256: '''+esc(sha(plan_path))+'<br>集約SHA256: '+esc(sha(summary_path))+'''</p></details></main></html>'''


def main():
    parser = LoggedArgumentParser(description=__doc__)
    for key in ('plan', 'summary', 'metadata', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--audio-manifest', type=Path)
    parser.add_argument('--summary-sha256', required=True)
    args = parser.parse_args()
    content = render(args.plan, args.summary, args.metadata, args.audio_manifest, args.summary_sha256)
    if len(content.encode('utf-8')) >= 10*1024*1024:
        raise ContractError('公開HTMLの10MiB上限を超えます')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(content)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'chunk-report'))
