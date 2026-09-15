"""Validate and publish an immutable standalone condition collection ZIP."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile,zipfile
ROOT=Path(__file__).resolve().parents[1]
NAME='HavocConditionPacks'
source=ROOT/'src'/NAME
version=json.loads((source/'info.json').read_text(encoding='utf-8'))['version']
config=json.loads((ROOT/'publishing/release.json').read_text(encoding='utf-8'))
release_id=config['release_id']
assert re.fullmatch(re.escape(version)+r'(?:-r[0-9]+)?',release_id)
output=ROOT/'release'/release_id
files={p.relative_to(ROOT/'src').as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file()}
assert all(Path(name).suffix.lower() in {'.lua','.json','.mod','.md','.txt','.cmd','.ps1','.patch_996'} for name in files)
assert not any(zipfile.is_zipfile(__import__('io').BytesIO(data)) for data in files.values())
manifest=json.loads(files[NAME+'/native-melee/manifest.json'])
assert manifest['package_files']==[] and len(manifest['patches'])==54
for row in manifest['patches']:
    assert hashlib.sha256(files[NAME+'/native-melee/resources/'+row['file']]).hexdigest()==row['sha256']
notes=(ROOT/'publishing/release-notes.md').read_text(encoding='utf-8')
def validate(folder):
    archive=folder/(NAME+'-'+version+'.zip')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and len(z.namelist())==len(files)
        assert {n:z.read(n) for n in z.namelist()}==files
    expected=hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n'
    assert (folder/'SHA256SUMS.txt').read_text(encoding='utf-8')==expected
    assert (folder/'release-notes.txt').read_text(encoding='utf-8')==notes
if not output.exists():
    subprocess.run([sys.executable,str(ROOT/'tests/run.py')],cwd=ROOT,check=True,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
    output.parent.mkdir(exist_ok=True)
    (ROOT/'build').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='release-',dir=ROOT/'build') as temp:
        staged=Path(temp)/release_id;staged.mkdir()
        archive=staged/(NAME+'-'+version+'.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,data in sorted(files.items()):
                info=zipfile.ZipInfo(name,(2026,9,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,data,compresslevel=9)
        (staged/'SHA256SUMS.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n',encoding='utf-8')
        (staged/'release-notes.txt').write_text(notes,encoding='utf-8')
        validate(staged);staged.rename(output)
validate(output)
print('Release ready:',output,'| Files:',len(files))
