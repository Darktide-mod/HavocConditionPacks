"""Formal native-controller package: real Lua timings, loader and DMF lifecycle."""
from project_env import PROJECT, HCM
import json, runpy, sys
package=PROJECT/'src/HavocConditionPacks/diy/packages/starter-conditions-frenzied_assault'
check=PROJECT/'tools/verify_experiment.py'
previous=sys.argv
sys.argv=[str(check),'--package',str(package),'--rate','1.2','--reload-check','--report','formal-lua-report.json']
try: env=runpy.run_path(str(check))
finally: sys.argv=previous
L=env['L']
runtime=HCM/'src/HavocConditionManager/scripts/mods/HavocConditionManager/diy'
files={p.relative_to(package).as_posix():p.read_text(encoding='utf-8') for p in package.rglob('*') if p.is_file()}
assert json.loads(files['package.json'])['package_version']=='2.2.1'
assert set(files)=={'package.json','definitions.json','lua/main.lua','lua/timing.lua','lua/resources.lua','lua/legacy_cleanup.lua'}
for alias,name in [('E','engine'),('Scripts','scripts')]:
    L.globals()[alias]=L.execute((runtime/f'diy_{name}.lua').read_text(encoding='utf-8'))
L.globals().files=L.table_from(files)
L.execute(r'''
function mod:persistent_table(key)self.saved=self.saved or {};self.saved[key]=self.saved[key] or {};return self.saved[key]end
api={key=function()return 'unit'end,info=function()return {kind='minions'}end,
alive=function(u)return HEALTH_ALIVE[u]end,context=function()return {}end,
units=function()return {}end,action=function()return true end,error=function(e)error(e)end}
A=P.new(S,C,H)
checked=assert(A.validate(files,K,'conditions','starter-conditions-frenzied_assault'))
snapshot=A.compose({['starter-conditions-frenzied_assault']=checked},K,'conditions')
local id=snapshot.document.entries[1].id
local engine=Scripts.attach(E.new(snapshot.document,K,api,1),snapshot,{Schema=S,Packages=P,
    PackageAPI=A,Engine=E,native=api,catalog=K,log=function()error('Unexpected routine log')end})
engine.set_global({id})
assert(mod._diy_native_melee_20.enabled)
assert(not engine.needs_minion_updates(),'Native-only package must not force per-unit DIY updates')
local u,b=attacker(true);local pad,data,bb=enter_case(u,b)
close(pad.attack_duration,11);close(pad.attack_timing,10.5)
engine.finish()
assert(not mod._diy_native_melee_20.enabled)
BtMeleeAttackAction.leave(BtMeleeAttackAction,u,b,bb,pad,data,11.1,'done',false)
assert(not next(mod._diy_native_melee_20.units))
''')
print('Formal Frenzied assault: direct package validation, real script activation/cleanup, +20% native timing and no DIY unit update dependency: PASS')
