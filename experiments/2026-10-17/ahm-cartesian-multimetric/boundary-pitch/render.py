"""Render completed same-host pitch observations without additional measurements."""
import base64
import hashlib
import html as html_lib
import json
from pathlib import Path

ROOT=Path('boundary-pitch-report-20261018')
d=json.loads((ROOT/'statistics.json').read_text())
NAMES={'boundary_hold':'境界保持修正版','original_candidate':'旧Cartesian候補','pml':'現PML'}
LABELS={'mae_cents':'音高追従MAE（cent）','missing_voiced_fraction':'基準有声の未検出率',
        'false_voiced_fraction':'基準無声の有声検出率','out_of_range_fraction':'測定範囲外の割合',
        'gross_over600_fraction':'両有声で600cent超の割合','near_octave_error_fraction':'両有声で1200±100centの割合'}


def number(v):
    return f'{v:.6f}'


def interval(v):
    return '['+', '.join(number(x) for x in v)+']'


def table(items):
    rows=[]
    for r in items:
        q='−3半音' if r['semitones']==-3 else '＋3半音'
        common=r['comparisons']['all_three']
        cells=[LABELS[r['metric']]+'<br>'+q,f'{common["recordings"]}/120録音<br>{common["speakers"]}話者']
        for m in NAMES:
            v=common['methods'][m]
            rank=v['descriptive_rank']
            tag=f'<span class="rank r{rank}">{rank}位</span>' if rank is not None else ''
            cells.append(tag+number(v['value'])+'<small>'+interval(v['ci95'])+'</small>')
        rows.append('<tr>'+''.join('<td>'+x+'</td>' for x in cells)+'</tr>')
    return '<div class="scroll"><table><thead><tr><th>指標</th><th>3方式共通支持</th>'+''.join('<th>'+n+'</th>' for n in NAMES.values())+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def audio_section():
    base=Path('boundary-pitch-previews-20261018/unpacked')
    manifest=json.loads((base/'audio-manifest.json').read_text())
    lookup={}
    public=[]
    for i,item in enumerate(manifest['samples']):
        row=dict(item)
        identity=f'preview-{i}'
        if row['status']=='available':
            blob=(base/row['file']).read_bytes()
            if hashlib.sha256(blob).hexdigest()!=row['wav_sha256'] or len(blob)!=row['bytes']:
                raise ValueError('Preview identity changed')
            source='data:audio/wav;base64,'+base64.b64encode(blob).decode('ascii')
            audio=f'<audio id="{identity}" controls preload="none" src="{source}"></audio>'
            row['original_export_basename']=row.pop('file')
            row['embedded_html_element_id']=identity
        else:
            audio='利用できません：'+html_lib.escape(row['reason'])
        lookup[row['case'],row['method'],row['semitones']]=audio
        public.append(row)
    metadata={k:v for k,v in manifest.items() if k not in ('samples','attribution_source')}
    metadata['storage']='WAV bytes embedded in index.html; separate WAV files are not published here'
    metadata['samples']=public
    metadata['license']='https://creativecommons.org/licenses/by/4.0/'
    metadata['source']='https://www.openslr.org/12/'
    (ROOT/'audio-manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    result='<h2>同じ2録音の短い試聴コピー</h2><p>それぞれ先頭2秒、16kHz mono。原音・現PML・境界保持修正版を並べ、編集音と旧候補は折りたたんでいます。修正版は未採用の候補です。各例のRTFは表示しません。</p>'
    for case in dict.fromkeys(r['case'] for r in public):
        result+='<section><h3>'+html_lib.escape(case)+'</h3><div class="audio-grid">'
        for method,label in [('original','原音'),('pml','現PML'),('boundary_hold','境界保持修正版')]:
            result+='<div><b>'+label+'</b><br>'+lookup[case,method,0]+'</div>'
        result+='</div><details><summary>±3半音の編集音を開く</summary>'
        for q in (-3,3):
            result+='<h4>'+('−3半音' if q==-3 else '＋3半音')+'</h4><div class="audio-grid">'
            for method in ('pml','boundary_hold'):
                result+='<div><b>'+NAMES[method]+'</b><br>'+lookup[case,method,q]+'</div>'
            result+='</div>'
        result+='</details><details><summary>旧Cartesian候補の音声を開く</summary><div class="audio-grid">'
        for q in (0,-3,3):
            result+='<div><b>'+('無編集' if q==0 else str(q)+'半音')+'</b><br>'+lookup[case,'original_candidate',q]+'</div>'
        result+='</div></details></section>'
    result+='<h3>出典・帰属・変換</h3><p>LibriSpeech (c) 2014 Vassil Panayotov。作成者：Vassil Panayotov、Guoguo Chen、Daniel Povey、Sanjeev Khudanpur。LibriVoxの朗読とProject Gutenberg由来の文章を含む<a href="https://www.openslr.org/12/">OpenSLR SLR12 test-clean</a>の同じ2録音です。配布条件は<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>（<a href="https://creativecommons.org/licenses/by/4.0/legalcode">法文</a>）。2026-10-18に公式表示を再確認しました。</p>'
    result+='<p>既存float64音声の先頭[0,32000)を抜粋し、全条件同じ変換round(x×32767)でPCM16 WAVにしました。原音を含め量子化があり、旧レポートの×32768変換とbytes同一ではありません。音量正規化・クリップ・リサンプリング・整列・無音除去は行っていません。0/±3半音の再合成・編集を含み、20枠すべて生成済みの保存音声を使用しました。測定用NPYと指標値は変更していません。</p>'
    result+='<p>短い掲載範囲自体が利用許諾の根拠ではありません。著作者・配布元・話者が本比較を推奨していることを意味せず、追加制限やDRMを設けません。入力音声の許諾と手法のソフトウェアライセンスを同一視しません。<a href="audio-manifest.json">音声のSHA・条件・変換情報</a>を保存しています。ブラウザでの実再生確認は未完了です。</p>'
    return result


audio_content=audio_section()

primary=[r for r in d['results'] if r['metric'] in ('mae_cents','missing_voiced_fraction')]
extra=[r for r in d['results'] if r not in primary]
parts=[]
for r in primary:
    q='−3半音' if r['semitones']==-3 else '＋3半音'
    row=[LABELS[r['metric']]+'<br>'+q]
    for scope in ('boundary_vs_pml','boundary_vs_old'):
        v=r['comparisons'][scope]
        pair=v['first_minus_second']
        row.append(number(pair['value'])+'<small>'+interval(pair['ci95'])+f'</small><small>{v["recordings"]}/120録音・{v["speakers"]}話者</small>')
    parts.append('<tr>'+''.join('<td>'+c+'</td>' for c in row)+'</tr>')
paired='<div class="scroll"><table><thead><tr><th>指標</th><th>修正版−PML</th><th>修正版−旧候補</th></tr></thead><tbody>'+''.join(parts)+'</tbody></table></div>'
html='''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>境界保持修正版の音高追従：同一環境の追加評価</title><style>:root{color-scheme:light dark;--bg:#f6f8fa;--paper:#fff;--ink:#223247;--muted:#526477;--line:#d8dfe7}body{background:var(--bg);color:var(--ink);font:16px/1.7 system-ui;max-width:1250px;margin:30px auto;padding:0 22px}h2{margin-top:32px}.audio-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}audio{width:100%;max-width:340px}details{margin:14px 0;padding:12px;border:1px solid var(--line)}section{margin:22px 0}.scroll{overflow:auto}table{border-collapse:collapse;background:var(--paper);width:100%}td,th{padding:12px;vertical-align:top;text-align:left;border-bottom:1px solid var(--line);min-width:160px}small{display:block;color:var(--muted);font-size:12px}.note{padding:16px;border-left:4px solid #9b7840;background:#a97d1920}.rank{display:inline-block;padding:1px 7px;margin-right:7px;border-radius:5px;font-weight:bold}.r1{background:#f5df9d;color:#392900}.r2{background:#e2e8ee;color:#263646}.r3{background:#edceb8;color:#493020}a{color:#1762a6}@media(prefers-color-scheme:dark){:root{--bg:#17212c;--paper:#202d3b;--ink:#e4edf5;--muted:#b6c4d3;--line:#425164}a{color:#9acaff}}</style><h1>境界保持修正版の音高追従</h1><p>比較基準は現PML。保存済みの3方式を同じ環境で追加測定しました。修正版は全120録音の両編集を測定できましたが、旧候補との差の95%区間は主要4比較すべてで0を含みます。追従の改善や同等性を確証した結果ではありません。</p><p class="note">720予定枠：測定成功712、旧候補の既知の生成失敗8。新しい音声合成やMOS・ECAPA推論ではありません。F0推定器に対する相対的追従で、絶対F0真値・自然さ・数msの破裂音の忠実度を測っているわけではありません。</p><h2>3方式共通の録音での比較</h2><p>値は小さいほど追従誤差・未検出率が低い方向です。順位は同じ支持上の点推定だけの記述的順位で、区間は各方式自身の95%区間です。総合順位を作りません。</p>'''+table(primary)+'''<h2>対応差と全120件の比較</h2><p>修正版−対照。負なら修正版の値が小さい方向。修正版とPMLは全120件、旧候補との比較は共通117/115件です。上表の3方式共通支持のPML平均と、全120件のPML平均を混ぜないでください。</p>'''+paired+'''<details><summary>範囲外・誤有声・大誤差などの追加診断</summary><p>割合は録音単位で計算し、話者内平均、話者等重みで集約しています。全フレームを単純に合算した割合ではありません。「基準有声/無声」は無編集出力へのYIN推定で、音素の正解ラベルではありません。これらの診断に性能順位は付けません。</p>'''+table(extra)+'''</details>'''+audio_content+'''<h2>条件・限界</h2><ul><li>参照は各方式自身の無編集出力。期待F0はその推定値に±300centを適用したものです。原音のF0真値に対する誤差ではありません。</li><li>既存YIN型推定器：65–700Hz、80ms完全窓、10ms間隔、2kHz前処理。範囲外・未検出・両有声の誤差を分けています。</li><li>全長、音量正規化・時間整列・無音除去なし。同一の保存入力SHAと科学ソース、CPU2 threads。旧候補とPMLをこの環境で計算し直し、別環境の品質平均へ混ぜていません。</li><li>録音内→話者内平均→40話者等重み。話者bootstrap2,000回、seed20261018、95%記述区間、多重比較未補正。</li><li>元の固定開発集合です。独立した最終検証ではなく、base採用・全79軸の再評価・速度比較もしていません。</li></ul><h2>出典</h2><p><a href="statistics.json">全集約値・方式別の支持・SHA</a> ／ <a href="../boundary-primary/report.html">同じ保存候補のMOS・ECAPA</a> ／ <a href="../ordinary/ordinary.html">旧候補の全79軸・短音声</a></p><p>実計測：2026-10-18 04:59:03–05:02:33 UTC。最初の集約では順位のNumPy整数をJSONへ保存できず停止しました。部分ファイルを残し、整数への型変換だけを直して同じ保存値・同じ条件で再集約しました。音声の再計測や数値条件の変更はありません。</p></html>'''
(ROOT/'index.html').write_text(html)
print(len(html.encode()))
