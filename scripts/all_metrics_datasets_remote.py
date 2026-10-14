"""研究用データのZIP索引と必要メンバーのみを正式取得する。"""
from __future__ import annotations

import hashlib
import json
import logging
import struct
import urllib.error
import urllib.request
import zlib

from all_metrics_common import ROOT, RUN

OUT = RUN / 'corpora'
CACHE = ROOT / '.cache/metric-corpora'
URLS = {
    'vctk': 'https://datashare.ed.ac.uk/server/api/core/bitstreams/535f4286-e54c-4038-838c-a02285e32cb2/content',
    'abxls': 'https://download.zerospeech.com/datasets/abxLS.datasets.zip',
    'jvs': 'https://drive.usercontent.google.com/download?id=19oAw8wWn3Y7z6CKChRdAyGOB9yupL_Xt&export=download&confirm=t',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


class RemoteZip:
    """HTTP 206のみ許容し、ZIP64索引・CRCを保持する。"""

    def __init__(self, name):
        self.name, self.url = name, URLS[name]
        self.cache = CACHE / name
        self.cache.mkdir(parents=True, exist_ok=True)
        self.size = None
        self.index = self.cache / 'index.json'
        if self.index.exists():
            data = json.loads(self.index.read_text())
            self.size, self.entries = data['archive_bytes'], data['entries']
        else:
            self.entries = self._index()
        self.by_name = {e['member']: e for e in self.entries}

    def read_range(self, start, length):
        if not length:
            return b''
        end = start + length - 1
        request = urllib.request.Request(self.url, headers={'Range': f'bytes={start}-{end}'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    expected = f'bytes {start}-{end}/{self.size}'
                    if response.status != 206 or response.headers.get('Content-Range') != expected:
                        raise RuntimeError(f'Unexpected range: {response.status} {response.headers.get("Content-Range")} expected {expected}')
                    data = response.read(length + 1)
                if len(data) != length:
                    raise RuntimeError('Incomplete range response')
                return data
            except urllib.error.HTTPError as error:
                logging.exception('%s Range %d-%d attempt %d', self.name, start, end, attempt + 1)
                if error.code in (401, 403) or attempt == 2:
                    raise
            except Exception:
                logging.exception('%s Range %d-%d attempt %d', self.name, start, end, attempt + 1)
                if attempt == 2:
                    raise
        raise RuntimeError('Unreachable')

    def _index(self):
        request = urllib.request.Request(self.url, headers={'Range': 'bytes=-65557'})
        with urllib.request.urlopen(request, timeout=120) as response:
            cr = response.headers.get('Content-Range', '')
            if response.status != 206 or not cr.startswith('bytes '):
                raise RuntimeError(f'Range request unsupported: {response.status} {cr}')
            self.size = int(cr.rsplit('/', 1)[1])
            tail = response.read(65558)
        (self.cache / 'zip-tail.bin').write_bytes(tail)
        position = tail.rfind(b'PK\x05\x06')
        if position < 0:
            raise ValueError('ZIP end record not found')
        eocd = struct.unpack_from('<4s4H2IH', tail, position)
        count, cd_length, cd_offset = eocd[4:7]
        if 0xffffffff in (cd_length, cd_offset) or count == 65535:
            locator = struct.unpack_from('<4sIQI', tail, position - 20)
            if locator[0] != b'PK\x06\x07':
                raise ValueError('ZIP64 locator not found')
            record = self.read_range(locator[2], 56)
            fields = struct.unpack('<4sQ2H2I4Q', record)
            count, cd_length, cd_offset = fields[7:10]
        cd = self.read_range(cd_offset, cd_length)
        (self.cache / 'central-directory.bin').write_bytes(cd)
        entries, cursor = [], 0
        while cursor < len(cd):
            h = struct.unpack_from('<4s6H3I5H2I', cd, cursor)
            if h[0] != b'PK\x01\x02':
                raise ValueError(f'Bad ZIP central header at {cursor}')
            name = cd[cursor + 46:cursor + 46 + h[10]].decode('utf-8' if h[3] & 2048 else 'cp437')
            extra = cd[cursor + 46 + h[10]:cursor + 46 + h[10] + h[11]]
            size, packed, offset = h[9], h[8], h[16]
            pos = 0
            while pos + 4 <= len(extra):
                tag, length = struct.unpack_from('<HH', extra, pos)
                payload = extra[pos + 4:pos + 4 + length]
                if tag == 1:
                    k = 0
                    if size == 0xffffffff:
                        size = struct.unpack_from('<Q', payload, k)[0]
                        k += 8
                    if packed == 0xffffffff:
                        packed = struct.unpack_from('<Q', payload, k)[0]
                        k += 8
                    if offset == 0xffffffff:
                        offset = struct.unpack_from('<Q', payload, k)[0]
                pos += 4 + length
            entries.append({'member': name, 'header_offset': offset, 'compressed_bytes': packed,
                            'uncompressed_bytes': size, 'compression': h[4], 'crc32': h[7]})
            cursor += 46 + h[10] + h[11] + h[12]
        if len(entries) != count:
            raise ValueError(f'ZIP entry count differs: {len(entries)} != {count}')
        save_json(self.index, {'url': self.url, 'archive_bytes': self.size,
                              'central_directory_offset': cd_offset, 'central_directory_bytes': cd_length,
                              'central_directory_sha256': sha(cd), 'entries': entries})
        return entries

    def member(self, entry, destination=None):
        name = entry['member']
        path = destination or self.cache / 'members' / name
        if path.exists():
            data = path.read_bytes()
        else:
            prefix = self.read_range(entry['header_offset'], 30)
            header = struct.unpack('<4s5H3I2H', prefix)
            if header[0] != b'PK\x03\x04':
                raise ValueError('Bad member local header')
            offset = entry['header_offset'] + 30 + header[-2] + header[-1]
            packed = self.read_range(offset, entry['compressed_bytes'])
            if entry['compression'] == 8:
                data = zlib.decompress(packed, -15)
            elif entry['compression'] == 0:
                data = packed
            else:
                raise ValueError(f'Unsupported compression {entry["compression"]}')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if len(data) != entry['uncompressed_bytes'] or zlib.crc32(data) != entry['crc32']:
            raise ValueError(f'ZIP member integrity mismatch: {name}')
        return path, {'source': {'archive_url': self.url, 'archive_bytes': self.size, **entry},
                      'source_sha256': sha(data), 'local_source': str(path.relative_to(ROOT))}


if __name__ == '__main__':
    import concurrent.futures
    import sys
    OUT.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), logging.FileHandler(OUT / 'acquisition.log')])
    def acquire(name):
        try:
            source = RemoteZip(name)
            metadata = [e for e in source.entries if not e['member'].endswith('/') and not e['member'].lower().endswith(('.wav', '.flac', '.mp3'))]
            save_json(OUT / f'{name}-metadata-locators.json', metadata)
            logging.info('%s: %d entries, %d metadata files, %d bytes', name, len(source.entries), len(metadata), source.size)
            return {'name': name, 'status': 'ok', 'entries': len(source.entries), 'metadata': metadata[:40]}
        except Exception as error:
            logging.exception('Cannot acquire %s', name)
            return {'name': name, 'status': 'failed', 'error': str(error)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(acquire, sys.argv[1:] or list(URLS)))
    save_json(OUT / 'archive-discovery.json', results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
