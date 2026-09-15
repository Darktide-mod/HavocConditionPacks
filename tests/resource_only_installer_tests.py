"""New installs never write condition files; old installs retain their rollback owner."""
from project_env import PROJECT,CHECKS
import json,hashlib,shutil,tempfile,subprocess,struct
from pathlib import Path
sha=lambda b:hashlib.sha256(b).hexdigest()
def row(name):
 a=name.encode();return struct.pack('<II',4,len(a))+a+struct.pack('<I',0)+bytes(29)
with tempfile.TemporaryDirectory(prefix='resource-only-',dir=CHECKS) as tmp:
 root=Path(tmp);payload=root/'payload';payload.mkdir();game=root/'game';(game/'binaries').mkdir(parents=True);(game/'bundle').mkdir()
 source=PROJECT/'src/HavocConditionPacks/native-melee'
 shutil.copy2(source/'Install.ps1',payload/'Install.ps1');shutil.copytree(source/'legacy',payload/'legacy')
 (payload/'resources').mkdir();(payload/'resources/0000000000000001.patch_996').write_bytes(b'controller')
 (game/'binaries/Darktide.exe').write_bytes(b'game');(game/'bundle/0000000000000001').write_bytes(b'base')
 database=struct.pack('<IIQI',6,1,1,1)+row('0000000000000001')+b'opaque';db=game/'bundle/bundle_database.data';db.write_bytes(database)
 manifest={'executable_sha256':sha(b'game'),'source_bundles':{'0000000000000001':sha(b'base')},'patches':[{'file':'0000000000000001.patch_996','sha256':sha(b'controller')}],'package_files':[],'package_sha256':{},'package_version':'2.2.1'}
 (payload/'manifest.json').write_text(json.dumps(manifest))
 packages=root/'app/diy/packages';old=packages/'starter-conditions-frenzied_assault';old.mkdir(parents=True);(old/'custom.lua').write_bytes(b'user edits')
 def run(mode):
  p=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(payload/'Install.ps1'),'-GameDirectory',str(game),'-PackageRoot',str(packages),'-Mode',mode],capture_output=True,text=True)
  assert p.returncode==0,(p.stdout,p.stderr)
  return p.stdout
 run('Check');assert db.read_bytes()==database
 run('Install');installed=db.read_bytes();assert installed!=database
 assert list(old.iterdir())==[old/'custom.lua'] and (old/'custom.lua').read_bytes()==b'user edits'
 assert json.loads((root/'app/native-melee-resources-installation.json').read_text(encoding='utf-8-sig'))['rows'][0]['path'].endswith('.patch_996')
 assert 'already installed' in run('Install')
 run('Uninstall');assert db.read_bytes()==database and (old/'custom.lua').read_bytes()==b'user edits'
 # Simulate matching old-owned resources. New installer may verify, never adopt.
 (root/'app/native-melee-resources-installation.json').unlink()
 db.write_bytes(installed);(game/'bundle/0000000000000001.patch_996').write_bytes(b'controller')
 legacy=root/'app/native-melee-installation.json';legacy.write_text(json.dumps({'status':'installed','game':str(game),'rows':[]}));before=legacy.read_bytes()
 assert 'legacy animation resources are already installed' in run('Install')
 assert legacy.read_bytes()==before and not (root/'app/native-melee-resources-installation.json').exists()
 assert db.read_bytes()==installed and (old/'custom.lua').read_bytes()==b'user edits'
print('PASS: resource-only install/check/repeat/uninstall, opaque database preservation and legacy ownership')
