"""Rebuild matching animation patches offline; never modify game files."""
from pathlib import Path
import collections,hashlib,json,struct as S
from audit_enemy_assets import GAME,h
from build_resource_patches import raw_records,container
from build_variable_resources import transform
ROOT=Path(__file__).resolve().parents[1]
payload=ROOT/'src/HavocConditionPacks/native-melee'
manifest=json.loads((payload/'manifest.json').read_text())
targets=collections.defaultdict(set)
for row in json.loads((ROOT/'tools/melee-state-map.json').read_text())['targets']:
    targets[row['asset']].add((row['layer'],row['index']))
out=ROOT/'build/rebuilt';out.mkdir(parents=True,exist_ok=True)
originals=ROOT/'build/enemy-animation-assets';originals.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
for patch in manifest['patches']:
    key=patch['file'].split('.')[0];source=GAME/'bundle'/key
    assert sha(source.read_bytes())==manifest['source_bundles'][key],('Game resource differs',key)
    metadata,records=raw_records(source);selected=[]
    for row in records:
        asset=f'{row["name"]:016x}'
        if row['ext']!=h('state_machine') or asset not in targets:continue
        assert len(row['headers'])==1 and row['headers'][0][4]==0
        original=originals/(asset+'.state_machine')
        if original.exists():assert original.read_bytes()==row['body'],('Different base controller',asset)
        else:original.write_bytes(row['body'])
        body,_,_=transform(row['body'],targets[asset])
        kind,u1,_,u2,tail=row['headers'][0]
        row['record']=S.pack('<QQII',row['ext'],row['name'],1,row['flags'])+S.pack('<IBIBI',kind,u1,len(body),u2,tail)+body
        row['body']=body;selected.append(row)
    data=container(metadata,selected)
    assert sha(data)==patch['sha256'],('Rebuilt payload differs',key)
    (out/patch['file']).write_bytes(data)
print('Rebuilt and verified',len(manifest['patches']),'animation patches without changing the game')
