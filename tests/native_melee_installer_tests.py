"""Exercise the shipped Windows installer in isolated fake game directories.

Uses small synthetic containers/database metadata. Never changes the real game.
"""
from pathlib import Path
import copy, hashlib, json, shutil, struct, subprocess, tempfile
from project_env import PROJECT, CHECKS
SOURCE=PROJECT/'src/HavocConditionPacks/native-melee/legacy'
sha=lambda b:hashlib.sha256(b).hexdigest()

def row(name,stream='',opaque=bytes(29)):
    a=name.encode('ascii');b=stream.encode('ascii')
    return struct.pack('<II',4,len(a))+a+struct.pack('<I',len(b))+b+opaque

def database(extra=False):
    rows=[row('0000000000000001','0000000000000001.stream',b'x'*29)]
    if extra:rows.append(row('foreign.patch_999','foreign.stream.patch_999',b'z'*29))
    return struct.pack('<IIQI',6,1,1,len(rows))+b''.join(rows)+b'opaque-tail-preserved'

with tempfile.TemporaryDirectory(prefix='native-melee-installer-',dir=CHECKS) as tmp:
    root=Path(tmp);payload=root/'payload';payload.mkdir()
    shutil.copyfile(SOURCE/'Install.ps1',payload/'Install.ps1')
    (payload/'resources').mkdir();(payload/'package').mkdir()
    resource=b'fake-controller';(payload/'resources/0000000000000001.patch_996').write_bytes(resource)
    (payload/'package/package.json').write_text('{"package_version":"2.2.0"}')
    game=root/'game';(game/'bundle').mkdir(parents=True);(game/'binaries').mkdir()
    (game/'binaries/Darktide.exe').write_bytes(b'fake-executable')
    (game/'bundle/0000000000000001').write_bytes(b'fake-base')
    db=game/'bundle/bundle_database.data';db.write_bytes(database())
    package_root=root/'app/diy/packages'
    package=package_root/'starter-conditions-frenzied_assault';package.mkdir(parents=True)
    before=b'{"package_version":"2.1.1"}';(package/'package.json').write_bytes(before)
    manifest=dict(executable_sha256=sha(b'fake-executable'),
        source_bundles={'0000000000000001':sha(b'fake-base')},
        patches=[dict(file='0000000000000001.patch_996',sha256=sha(resource))],
        package_files=['package.json'],package_sha256={'package.json':sha((payload/'package/package.json').read_bytes())},package_version='2.2.0')
    (payload/'manifest.json').write_text(json.dumps(manifest))
    def run(mode='Install',good=True,script=None):
        result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script or payload/'Install.ps1'),
            '-GameDirectory',str(game),'-PackageRoot',str(package_root),'-Mode',mode],
            capture_output=True,text=True,encoding='utf-8',errors='replace')
        assert (result.returncode==0)==good,(mode,result.stdout,result.stderr)
        return result.stdout
    assert 'No files changed' in run('Check')
    assert db.read_bytes()==database() and (package/'package.json').read_bytes()==before
    run()
    installed=db.read_bytes();assert b'0000000000000001.patch_996' in installed
    assert installed.endswith(b'opaque-tail-preserved')
    assert 'already installed' in run()
    assert db.read_bytes()==installed
    # Later unrelated database changes survive removal.
    key=struct.pack('<QI',1,2)
    assert installed.count(key)==1
    db.write_bytes(installed.replace(key,struct.pack('<QI',1,3),1).replace(b'opaque-tail-preserved',
        row('foreign.patch_999','foreign.stream.patch_999',b'z'*29)+b'opaque-tail-preserved'))
    run('Uninstall')
    assert db.read_bytes()==database(extra=True)
    assert (package/'package.json').read_bytes()==before
    assert not (game/'bundle/0000000000000001.patch_996').exists()
    # Fresh game + no pre-existing external package; install/remove exact.
    (package/'package.json').unlink();db.write_bytes(database())
    run();run('Uninstall')
    assert db.read_bytes()==database() and not (package/'package.json').exists()
    # Adoption of matching experimental files and registration is idempotent.
    (package/'package.json').write_bytes(before)
    (game/'bundle/0000000000000001.patch_996').write_bytes(resource);db.write_bytes(installed)
    run();assert db.read_bytes()==installed
    run('Uninstall');assert db.read_bytes()==database() and (package/'package.json').read_bytes()==before
    # Wrong game, occupied resource filename, unknown user file, corrupt source.
    (game/'binaries/Darktide.exe').write_bytes(b'wrong');run(good=False)
    (game/'binaries/Darktide.exe').write_bytes(b'fake-executable')
    patch=game/'bundle/0000000000000001.patch_996';patch.write_bytes(b'foreign');run(good=False);assert patch.read_bytes()==b'foreign';patch.unlink()
    (package/'custom.lua').write_text('custom');run(good=False);assert (package/'custom.lua').read_text()=='custom';(package/'custom.lua').unlink()
    (payload/'resources/0000000000000001.patch_996').write_bytes(b'damaged');run(good=False)
    (payload/'resources/0000000000000001.patch_996').write_bytes(resource)
    assert db.read_bytes()==database() and (package/'package.json').read_bytes()==before
    # A failure immediately before database commit rolls all package/resources back.
    fault=payload/'fault.ps1'
    text=(payload/'Install.ps1').read_text()
    text=text.replace("if ((Hash-File $database) -ne $databaseHash) { throw 'Concurrent database change.' }",
                      "throw 'injected commit failure'")
    fault.write_text(text)
    run(good=False,script=fault)
    assert db.read_bytes()==database() and (package/'package.json').read_bytes()==before and not patch.exists()
    # Upgrade a managed 2.2.0 install directly, preserving the original uninstall
    # backup chain. A failed upgrade must retain the complete old installation.
    run()
    state_path=root/'app/native-melee-installation.json'
    old_state=state_path.read_bytes();old_package=(package/'package.json').read_bytes()
    old_resource=patch.read_bytes();old_database=db.read_bytes()
    upgraded=b'fixed-controller-reserved-tail'
    (payload/'resources/0000000000000001.patch_996').write_bytes(upgraded)
    (payload/'package/package.json').write_text('{"package_version":"2.2.1"}')
    manifest['package_version']='2.2.1'
    manifest['patches'][0]['sha256']=sha(upgraded)
    manifest['package_sha256']['package.json']=sha((payload/'package/package.json').read_bytes())
    (payload/'manifest.json').write_text(json.dumps(manifest))
    run('Check')
    assert patch.read_bytes()==old_resource and state_path.read_bytes()==old_state
    run(good=False,script=fault)
    assert patch.read_bytes()==old_resource and (package/'package.json').read_bytes()==old_package
    assert state_path.read_bytes()==old_state and db.read_bytes()==old_database
    # Changed payload, forged ledger paths and damaged original backup refuse
    # upgrades without touching the installed files or database.
    patch.write_bytes(b'user-resource');run(good=False);assert patch.read_bytes()==b'user-resource';patch.write_bytes(old_resource)
    forged=json.loads(old_state);forged['rows'][0]['path']=str(root/'outside')
    state_path.write_text(json.dumps(forged));run(good=False);state_path.write_bytes(old_state)
    previous=json.loads(old_state)
    original_backup=root/'app'/next(r['backup'] for r in previous['rows'] if r['backup'])
    original_bytes=original_backup.read_bytes();original_backup.write_bytes(b'damaged')
    run(good=False);original_backup.write_bytes(original_bytes)
    run()
    new_state=json.loads(state_path.read_bytes())
    assert new_state['package_version']=='2.2.1' and patch.read_bytes()==upgraded
    for a,b in zip(previous['rows'],new_state['rows']):
        assert (a['path'],a['backup'],a['original_sha256'])==(b['path'],b['backup'],b['original_sha256'])
    assert db.read_bytes()==old_database
    unchanged_state=state_path.read_bytes()
    assert 'already installed' in run() and state_path.read_bytes()==unchanged_state
    manifest['package_version']='2.2.0';(payload/'manifest.json').write_text(json.dumps(manifest))
    run(good=False);assert state_path.read_bytes()==unchanged_state and patch.read_bytes()==upgraded
    manifest['package_version']='2.2.1';(payload/'manifest.json').write_text(json.dumps(manifest))
    run('Uninstall')
    assert db.read_bytes()==database() and not patch.exists() and (package/'package.json').read_bytes()==before
    # Modified installed files block removal rather than overwriting user edits.
    run();(package/'package.json').write_bytes(b'user-change')
    run('Uninstall',good=False);assert (package/'package.json').read_bytes()==b'user-change'
report=dict(windows_powershell=True,synthetic_only=True,checks=[
    'read-only preflight','fresh install/remove','repeat install is idempotent','preserve later third-party registration',
    'adopt experiment and restore previous package','wrong game refusal','resource name conflict',
    'unknown package file refusal','corrupt payload refusal','failed commit rollback','edited file refusal',
    'managed upgrade preflight','failed upgrade preserves old install and ledger',
    'managed upgrade and original uninstall backup chain','upgraded install is idempotent',
    'downgrade refusal','modified resource refusal','forged ledger path refusal','damaged original backup refusal'])
(CHECKS/'native-melee-installer.json').write_text(json.dumps(report,indent=2))
print('Native melee Windows installer: '+', '.join(report['checks'])+': PASS')
