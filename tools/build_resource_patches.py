"""Offline sparse-patch build and database round trip. No installation option.

Only write below this script's directory. Original bundles/database stay read
only. Reuse resource headers and opaque container metadata from installed data.
"""
from pathlib import Path
import collections, ctypes as C, hashlib, json, math, struct as S, sys
from inspect_controllers import h, ROOT
sys.path.insert(0, str(ROOT))
from audit_enemy_assets import BUNDLE, GAME, index, extract

HERE = Path(__file__).parent
OUTPUT = HERE.parent/'build/container-experiment'
CHUNK = 0x80000
SUFFIX = '.patch_996'


def raw_records(path):
    lib = C.CDLL(str(GAME/'binaries/oo2core_9_win64.dll'))
    dec = lib.OodleLZ_Decompress
    dec.argtypes = [C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.c_int,C.c_int,C.c_int,
        C.c_void_p,C.c_size_t,C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_int]
    dec.restype = C.c_size_t
    with path.open('rb') as f:
        magic, count = S.unpack('<QI', f.read(12))
        assert magic in (0x00000003f0000008, 0x00000003f0000007)
        metadata = f.read(256)
        f.seek(count*20, 1)
        chunks = S.unpack('<I', f.read(4))[0]
        assert chunks <= 2048
        f.seek(chunks*4, 1)
        f.seek((f.tell()+15)//16*16)
        total, zero = S.unpack('<II', f.read(8))
        assert total <= CHUNK*chunks and total < 1024*1024*1024 and zero == 0, (path.name,total,chunks,zero)
        parts = []
        for _ in range(chunks):
            size = S.unpack('<I', f.read(4))[0]
            assert 0 < size <= CHUNK
            f.seek((f.tell()+15)//16*16)
            data = f.read(size)
            assert len(data) == size
            if size == CHUNK:
                parts.append(data)
            else:
                out = C.create_string_buffer(CHUNK)
                assert dec(data,size,out,CHUNK,1,0,0,None,0,None,None,None,0x180000,3) == CHUNK
                parts.append(out.raw)
    data = b''.join(parts)[:total]
    offset = 0
    rows = []
    while offset < total:
        start = offset
        ext, name, variants, flags = S.unpack_from('<QQII', data, offset)
        offset += 24
        assert 0 < variants < 100
        headers = []
        for _ in range(variants):
            headers.append(S.unpack_from('<IBIBI', data, offset))
            offset += 14
        body_start = offset
        size = sum(r[2]+r[4] for r in headers)
        offset += size
        assert offset <= total
        rows.append(dict(ext=ext,name=name,flags=flags,headers=headers,
                         body=data[body_start:offset], record=data[start:offset]))
    return metadata, rows


def container(metadata, records):
    payload = b''.join(r['record'] for r in records)
    count = math.ceil(len(payload)/CHUNK)
    result = bytearray(S.pack('<QI',0x00000003f0000008,len(records)) + metadata)
    for row in records:
        result += S.pack('<QQI',row['ext'],row['name'],0)
    result += S.pack('<I',count) + S.pack('<I',CHUNK)*count
    result += bytes((-len(result))%16)
    result += S.pack('<II',len(payload),0)
    for i in range(count):
        result += S.pack('<I',CHUNK)
        result += bytes((-len(result))%16)
        result += payload[i*CHUNK:(i+1)*CHUNK].ljust(CHUNK,b'\0')
    return bytes(result)


def database_entries(data):
    version, count = S.unpack_from('<II',data)
    assert version == 6 and 0 < count < 100000
    pos = 8
    entries = []
    for _ in range(count):
        start = pos
        key, variants = S.unpack_from('<QI',data,pos)
        pos += 12
        assert 0 < variants < 1000
        rows = []
        for _ in range(variants):
            vstart = pos
            ver, = S.unpack_from('<I',data,pos)
            pos += 4
            assert ver == 4
            names = []
            for _ in range(2):
                n, = S.unpack_from('<I',data,pos)
                pos += 4
                assert n < 256
                names.append(data[pos:pos+n].decode('ascii'))
                pos += n
            pos += 29
            assert pos <= len(data)
            rows.append(dict(names=names,data=data[vstart:pos]))
        entries.append(dict(key=key, rows=rows, data=data[start:pos]))
    return entries, data[pos:]


def add_database_patches(data, bundles):
    entries, tail = database_entries(data)
    wanted = {int(b,16) for b in bundles}
    result = bytearray(data[:8])
    found = set()
    for entry in entries:
        key = entry['key']
        if key not in wanted:
            result += entry['data']
            continue
        assert not any(SUFFIX in name for r in entry['rows'] for name in r['names'])
        found.add(key)
        names = [f'{key:016x}'+SUFFIX, f'{key:016x}.stream'+SUFFIX]
        record = S.pack('<I',4)
        for name in names:
            value = name.encode('ascii')
            record += S.pack('<I',len(value)) + value
        record += bytes(29)
        result += S.pack('<QI',key,len(entry['rows'])+1)
        result += b''.join(r['data'] for r in entry['rows']) + record
    assert found == wanted
    result += tail
    after, after_tail = database_entries(result)
    assert after_tail == tail
    undone = bytearray(data[:8])
    for old, new in zip(entries, after):
        assert old['key'] == new['key']
        if old['key'] in wanted:
            assert [r['data'] for r in new['rows'][:-1]] == [r['data'] for r in old['rows']]
            undone += S.pack('<QI',old['key'],len(old['rows']))
            undone += b''.join(r['data'] for r in new['rows'][:-1])
        else:
            assert old['data'] == new['data']
            undone += new['data']
    undone += after_tail
    assert bytes(undone) == data
    return bytes(result)


def main():
    manifest = json.loads((HERE/'variable-resources/manifest.json').read_text())
    versions = json.loads((HERE/'asset-versions.json').read_text())
    wanted = collections.defaultdict(set)
    for resource in manifest['resources']:
        for name, mode in versions[resource]:
            assert len(name) == 16 and mode == 0, (name,mode)
            wanted[name].add(resource)
    OUTPUT.mkdir(exist_ok=True)
    rows = []
    for bundle, resources in sorted(wanted.items()):
        assert not (BUNDLE/(bundle+SUFFIX)).exists(), 'patch number already occupied'
        metadata, records = raw_records(BUNDLE/bundle)
        selected = []
        for row in records:
            key = f'{row["name"]:016x}'
            if row['ext'] != h('state_machine') or key not in resources:
                continue
            # Reject alternate/streaming variants, differing duplicate versions.
            assert len(row['headers']) == 1 and row['headers'][0][4] == 0
            assert hashlib.sha256(row['body']).hexdigest() == manifest['resources'][key]['source_sha256']
            body = (HERE/'variable-resources'/(key+'.state_machine')).read_bytes()
            kind, unknown1, _, unknown2, tail = row['headers'][0]
            row['body'] = body
            row['record'] = S.pack('<QQII',row['ext'],row['name'],1,row['flags'])
            row['record'] += S.pack('<IBIBI',kind,unknown1,len(body),unknown2,tail) + body
            selected.append(row)
        assert {f'{r["name"]:016x}' for r in selected} == resources
        patch = container(metadata,selected)
        dest = OUTPUT/(bundle+SUFFIX)
        dest.write_bytes(patch)
        assert index(dest) == [(r['ext'],r['name'],0) for r in selected]
        assert list(extract(dest)) == [(r['ext'],r['name'],r['body']) for r in selected]
        rows.append(dict(file=dest.name,resources=sorted(resources),bytes=len(patch),
            sha256=hashlib.sha256(patch).hexdigest(),extraction_round_trip=True))
    database = (BUNDLE/'bundle_database.data').read_bytes()
    patched = add_database_patches(database,wanted)
    (OUTPUT/'bundle_database.data.EXPERIMENT-DO-NOT-INSTALL').write_bytes(patched)
    report = dict(status='offline format checks only; native loader not verified',rate=manifest['rate'],
        patches=rows,source_database_sha256=hashlib.sha256(database).hexdigest(),
        original_database_still_identical=(BUNDLE/'bundle_database.data').read_bytes()==database,
        database_undo_byte_exact=True,existing_mod_loader_preserved=True)
    (OUTPUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='patches'},indent=2))
    print('patch files',len(rows),'resource copies',sum(len(r['resources']) for r in rows),flush=True)


if __name__ == '__main__':
    main()
