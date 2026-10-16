"""PRレビュー用に同じ測定レポートと短音声を単体HTMLへ埋め込む。"""
import argparse
import base64
import mimetypes
import re
from pathlib import Path


def embed(source, destination):
    root = source.parent
    text = source.read_text()

    def replace(match):
        attribute, path = match.groups()
        if path.startswith(('https:', 'http:', '#', 'data:')):
            return match.group(0)
        if path.startswith('../pml-fwcep-2026-10-16/'):
            return 'href="#previous-material"'
        local = root / path
        if not local.resolve().is_relative_to(root.resolve()) or not local.is_file():
            raise ValueError(f'埋込み対象ファイルがありません: {path}')
        mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        if path.endswith('.gz'):
            mime = 'application/gzip'
        encoded = base64.b64encode(local.read_bytes()).decode()
        download = f' download="{local.name}"' if attribute == 'href' else ''
        return f'{attribute}="data:{mime};base64,{encoded}"{download}'

    text = re.sub(r'(src|href)="([^"]+)"', replace, text)
    note = ('<section id="previous-material"><h2>以前の説明資料について</h2>'
            '<p>旧研究の仕組み・図・探索経過は、以前お渡しした説明HTMLをご参照ください。'
            'この単体版は新正式測定の本文・固定5例音声・保存JSONを収録しています。'
            'この単体版では公開サイトの状態に依存せず、本文と音声を確認できます。</p></section>')
    text = text.replace('</main>', note + '</main>')
    destination.write_text(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    embed(args.source, args.destination)
