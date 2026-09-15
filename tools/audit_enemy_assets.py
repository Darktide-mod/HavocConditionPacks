"""Read-only local bundle audit. Extract only selected resource types into build."""
from pathlib import Path
import ctypes as C, struct as S, json, re, sys, subprocess, os
ROOT=Path(__file__).resolve().parents[1]/'build'
ROOT.mkdir(exist_ok=True)
GAME=Path(os.environ.get('DARKTIDE_GAME',Path(__file__).resolve().parents[5])).resolve()
BUNDLE=GAME/'bundle'
OUT=ROOT/'enemy-animation-assets'
OUT.mkdir(exist_ok=True)
def h(s):
    b=s.encode();m=0xc6a4a7935bd1e995;mask=(1<<64)-1;v=len(b)*m&mask
    for i in range(0,len(b)//8*8,8):
        k=int.from_bytes(b[i:i+8],'little')*m&mask;k^=k>>47;k=k*m&mask;v=((v^k)*m)&mask
    tail=b[len(b)//8*8:]
    if tail:v=((v^int.from_bytes(tail,'little'))*m)&mask
    v^=v>>47;v=v*m&mask;return v^(v>>47)
def index(p):
    with p.open('rb') as f:
        head=f.read(12)
        if len(head)<12:return
        magic,n=S.unpack('<QI',head)
        if magic not in (0x00000003f0000008,0x00000003f0000007):return
        assert n*20<p.stat().st_size
        f.seek(268);rows=list(S.iter_unpack('<QQI',f.read(n*20)))
    return rows
def extract(p):
    lib=C.CDLL(str(GAME/'binaries/oo2core_9_win64.dll'))
    dec=lib.OodleLZ_Decompress
    dec.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.c_int,C.c_int,C.c_int,C.c_void_p,C.c_size_t,C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_int]
    dec.restype=C.c_size_t
    with p.open('rb') as f:
        f.seek(8);n=S.unpack('<I',f.read(4))[0];f.seek(268+n*20)
        nc=S.unpack('<I',f.read(4))[0];f.seek(nc*4,1);f.seek((f.tell()+15)//16*16)
        total=S.unpack('<I',f.read(4))[0];f.read(4);assert total<512*1024*1024
        chunks=[]
        for _ in range(nc):
            size=S.unpack('<I',f.read(4))[0];f.seek((f.tell()+15)//16*16);data=f.read(size)
            if size==0x80000:chunks.append(data)
            else:
                out=C.create_string_buffer(0x80000)
                assert dec(data,size,out,len(out),1,0,0,None,0,None,None,None,0x180000,3)>0,p
                chunks.append(out.raw)
    data=b''.join(chunks)[:total];pos=0
    while pos+24<=len(data):
        ext,name,nv,flags=S.unpack_from('<QQII',data,pos);pos+=24;size=0
        assert nv<100
        for _ in range(nv):
            kind,u1,body,u2,tail=S.unpack_from('<IBIBI',data,pos);pos+=14;size+=body+tail
        assert pos+size<=len(data)
        yield ext,name,data[pos:pos+size]
        pos+=size
if __name__=='__main__':
    wanted={h(x):x for x in ['state_machine']}
    hits=[]
    for p in BUNDLE.iterdir():
        if not re.fullmatch(r'[0-9a-f]{16}(\.patch_\d+)?',p.name):continue
        rows=index(p)
        if rows:
            matches=[(e,n) for e,n,m in rows if e in wanted]
            if matches:hits.append((p,matches))
    print('bundles with state machines',len(hits),'entries',sum(len(x[1]) for x in hits),flush=True)
    (OUT/'index.json').write_text(json.dumps([(p.name,[(wanted[e],f'{n:016x}') for e,n in rows]) for p,rows in hits],indent=2))
    for p,rows in hits:
        for ext,name,data in extract(p):
            if ext in wanted:
                dest=OUT/(f'{name:016x}.'+wanted[ext]);dest.write_bytes(data)
    print('extracted',len(list(OUT.glob('*.state_machine'))),flush=True)
