"""Native Lua timing regression + isolated hook lifecycle/operation counts.

This does NOT execute the graphics engine or validate loading binary resources.
"""
from pathlib import Path
import argparse, json, os, runpy, sys
HERE=Path(__file__).parent
PROJECT=HERE.parent
sys.path.insert(0,str(PROJECT/'tests'))
os.environ.setdefault('DARKTIDE_TEST_RUNTIME',str(PROJECT.parents[1]/'dev-support/test-runtime-py312'))
env=runpy.run_path(str(PROJECT/'tests/fixtures/frenzied_native_test_environment.py'))
L=env['L']
parser=argparse.ArgumentParser()
parser.add_argument('--experiment',default='native-melee-20')
parser.add_argument('--rate',type=float,default=1.2)
parser.add_argument('--report',default='lua-experiment-report.json')
parser.add_argument('--package',type=Path)
parser.add_argument('--reload-check',action='store_true')
args=parser.parse_args()
EXPERIMENT=args.package or PROJECT/'src/HavocConditionPacks/diy/packages/starter-conditions-frenzied_assault'
timing=L.execute((EXPERIMENT/'lua/timing.lua').read_text(encoding='utf-8'))
assert timing['rate']==args.rate, 'Configured attack rate differs from requested rate'
resources=L.execute((EXPERIMENT/'lua/resources.lua').read_text(encoding='utf-8'))
runtime=Path(os.environ.get('HCM_PROJECT',PROJECT.parent/'HavocConditionManager'))/'src/HavocConditionManager/scripts/mods/HavocConditionManager/diy'
for alias,name in [('S','schema'),('C','codec'),('K','catalog'),('P','packages'),('H','sha256')]:
    L.globals()[alias]=L.execute((runtime/f'diy_{name}.lua').read_text(encoding='utf-8'))
package_files={p.relative_to(EXPERIMENT).as_posix():p.read_text(encoding='utf-8')
               for p in EXPERIMENT.rglob('*') if p.is_file() and p.suffix in ('.lua','.json')}
L.globals().package_files=L.table_from(package_files)
L.execute("local pack,why=P.new(S,C,H).validate(package_files,K,'conditions');assert(pack,why)")
L.globals().Timing=timing
L.globals().Resource=resources
L.globals().ExpectedRate=args.rate
L.execute('''
function close(a,b)assert(math.abs(a-b)<1e-8,tostring(a)..' / '..tostring(b))end
function native_case(data)
    local u,breed=unit()
    local pad={}
    BtMeleeAttackAction.enter(BtMeleeAttackAction,u,breed,{perception={target_unit=target},behavior={},spawn={}},pad,data,10)
    return pad.attack_timing or pad.start_sweep_t,pad.attack_duration,pad,u
end
''')
def convert(value):
    if isinstance(value,dict):return L.table_from({k:convert(v) for k,v in value.items()})
    if isinstance(value,list):return L.table_from([convert(v) for v in value])
    return value
cases=json.loads((PROJECT/'tests/fixtures/native-melee-comparison.json').read_text(encoding='utf-8'))['cases']
verified=0;unchanged=[]
for case in cases:
    event=case['event']
    data=dict(attack_anim_events=[event],attack_anim_durations={event:case['base_duration']},
              damage_profile={},attack_intensities={},attack_type=case['type'])
    if case['type']=='sweep':
        data['attack_sweep_damage_timings']={event:case['sweep_windows']}
    else:
        data['attack_anim_damage_timings']={event:case['multi_hit_timings'] or case['first_hit_or_sweep_start']}
    data=convert(data)
    prepared=timing.prepare(data,resources['events'])
    base=L.globals().native_case(data)
    fast=L.globals().native_case(prepared)
    rate=args.rate if resources['events'][event] else 1
    assert abs((fast[0]-10)-(base[0]-10)/rate)<1e-9,(case,base[:2],fast[:2])
    assert abs((fast[1]-10)-(base[1]-10)/rate)<1e-9
    for name in ['attack_timings','attack_sweep_timings']:
        a,b=base[2][name],fast[2][name]
        if a is None:continue
        for i in range(1,len(a)+1):
            if name=='attack_timings':assert abs(b[i]-a[i]/rate)<1e-9
            elif L.eval('type')(a[i])=='table':
                assert abs(b[i][1]-a[i][1]/rate)<1e-9
                assert abs(b[i][2]-a[i][2]/rate)<1e-9
                assert b[i][3]==a[i][3]
            else:assert abs(b[i]-a[i]/rate)<1e-9
    if rate==1:unchanged.append([case['breed'],event])
    else:verified+=1

# Non-timing fields, sweep node IDs, shield/FX/movement start synchronization.
L.execute('''
local source={attack_anim_durations={attack=3},attack_anim_damage_timings={attack={.6,1.2}},
    attack_sweep_damage_timings={attack={{.6,1.2,99},{1.8,2.4,"hand"}}},
    move_start_timings={attack=.6},melee_attack_rotation_durations={attack=1.2},
    effect_template_start_timings={attack=.6},sweep_ground_impact_fx_timing={attack={.6,1.2}},
    disable_shield_block_timing={attack=.6},enable_shield_block_timing={attack=1.2},
    move_speed=5,weapon_reach=3,dodge_window=.5,damage_profile={damage=10}}
local out=Timing.prepare(source,{attack=true})
close(out.attack_anim_durations.attack,3/ExpectedRate)
close(out.attack_sweep_damage_timings.attack[1][1],.6/ExpectedRate)
close(out.attack_sweep_damage_timings.attack[1][2],1.2/ExpectedRate)
assert(out.attack_sweep_damage_timings.attack[1][3]==99)
assert(out.attack_sweep_damage_timings.attack[2][3]=='hand')
close(out.move_start_timings.attack,.6/ExpectedRate)
close(out.melee_attack_rotation_durations.attack,1.2/ExpectedRate)
close(out.effect_template_start_timings.attack,.6/ExpectedRate)
close(out.sweep_ground_impact_fx_timing.attack[2],1.2/ExpectedRate)
close(out.disable_shield_block_timing.attack,.6/ExpectedRate)
close(out.enable_shield_block_timing.attack,1.2/ExpectedRate)
assert(out.move_speed==5 and out.weapon_reach==3 and out.dodge_window==.5)
assert(out.damage_profile==source.damage_profile and source.attack_anim_durations.attack==3)
''')

# Native class timing enters above remain real. Only graphics variable storage,
# optional lifecycle services and the rest-of-frame workload below are stubbed.
L.execute('''
Managers.player={human_players=function()return remote_joined and {{remote=true}} or {}end}
variable_reads=0;variable_writes=0;variable_finds=0
Unit.has_animation_state_machine=function(u)return u.resource~=nil end
Unit.animation_find_variable=function(u,name)
    variable_finds=variable_finds+1;return u.resource and u.resource[name]
end
Unit.animation_get_variable=function(u,index)variable_reads=variable_reads+1;return u.values[index]end
Unit.animation_set_variable=function(u,index,value)variable_writes=variable_writes+1;u.values[index]=value end
for _,name in ipairs({'animation_get_state','animation_get_time','animation_set_state','animation_set_time'})do
    Unit[name]=function()error('Unexpected animation maintenance')end
end
modules['./timing.lua']=Timing;modules['./resources.lua']=Resource
modules['./legacy_cleanup.lua']=function()end
function context()
    return {on_cleanup=function(self,fn)self.cleanup=fn end}
end
function attacker(patched)
    local u,b=unit();u.resource={};u.values={}
    if patched then
        for i=1,4 do
            local v=Resource.variables[i]
            u.resource[v.name]=i-1;u.values[i-1]=v.default
        end
    end
    return u,b
end
local M=BtMeleeAttackAction
native_run=M.run
-- Verify wrapper work independently of physics/AI; no variable API may be
-- used by run. Preserve the native class's enter implementation.
M.run=function(self,u,b,bb,pad,data,dt,t)
    close(data.attack_anim_durations.attack_02,pad.expected_duration)
    return 'running'
end
M.leave=function()end
function enter_case(u,b)
    local pad={}
    local data={attack_anim_events={'attack_02'},attack_anim_damage_timings={attack_02=.6},
        attack_anim_durations={attack_02=1.2},damage_profile={},attack_intensities={}}
    local bb={perception={target_unit=target},behavior={},spawn={}}
    M.enter(M,u,b,bb,pad,data,10)
    pad.expected_duration=pad._hcm_native_melee_data and 1.2/ExpectedRate or 1.2
    return pad,data,bb
end
''')
L.globals().Experiment=L.execute((EXPERIMENT/'lua/main.lua').read_text(encoding='utf-8'))
L.execute('''
ctx=context();Experiment.entries.frenzied_assault.on_activate(ctx)
u,b=attacker(true);pad,data,bb=enter_case(u,b)
close(pad.attack_timing,10+.6/ExpectedRate);close(pad.attack_duration,10+1.2/ExpectedRate)
for i=1,4 do close(u.values[i-1],Resource.variables[i].default*ExpectedRate)end
assert(variable_writes==4)
local writes,reads,finds=variable_writes,variable_reads,variable_finds
for i=1,10000 do BtMeleeAttackAction.run(BtMeleeAttackAction,u,b,bb,pad,data,.016,10.2)end
assert(variable_writes==writes and variable_reads==reads and variable_finds==finds)
run_frames_without_variable_access=10000
ctx:cleanup()
assert(variable_writes==writes,'Active swing must finish before restoring playback')
BtMeleeAttackAction.run(BtMeleeAttackAction,u,b,bb,pad,data,.016,10.7)
BtMeleeAttackAction.leave(BtMeleeAttackAction,u,b,bb,pad,data,11.1,'done',false)
assert(variable_writes==writes+4)
for i=1,4 do close(u.values[i-1],Resource.variables[i].default)end
assert(not next(mod._diy_native_melee_20.units))
ctx=context();Experiment.entries.frenzied_assault.on_activate(ctx)
unpatched,b2=attacker(false);pad2,data2,bb2=enter_case(unpatched,b2)
close(pad2.attack_timing,10.6);close(pad2.attack_duration,11.2)
local missing_finds=variable_finds
enter_case(unpatched,b2)
assert(variable_finds==missing_finds,'Negative resource result must be cached until refresh')
-- A late remote player cannot leave fast animation paired with normal damage.
u,b=attacker(true);pad,data,bb=enter_case(u,b)
BtMeleeAttackAction.leave(BtMeleeAttackAction,u,b,bb,pad,data,11.1,'done',false)
remote_joined=true
pad,data,bb=enter_case(u,b)
close(pad.attack_timing,10.6);close(pad.attack_duration,11.2)
for i=1,4 do close(u.values[i-1],Resource.variables[i].default)end
remote_joined=false
ctx:cleanup()
-- Refresh clears stale action and missing-resource caches, without hook piles.
local hooks=mod.hook_count
ctx=context();Experiment.entries.frenzied_assault.on_activate(ctx)
assert(mod.hook_count==hooks)
local before_find=variable_finds
enter_case(unpatched,b2)
assert(variable_finds>before_find)
ctx:cleanup()
-- Guards reject remote-only/unauthorized use before installing effects.
remote_joined=true
assert(not pcall(Experiment.entries.frenzied_assault.on_activate,context()))
remote_joined=false
mod.authority=false
assert(not pcall(Experiment.entries.frenzied_assault.on_activate,context()))
mod.authority=true
''')
if args.experiment=='native-melee-100' or args.reload_check:
    # Exercise separate module generations, not repeated activation of the
    # same cached module. Generation 1 deliberately has different helpers and
    # +20% timing; generation 2 must replace those closures and use +100%.
    source=(EXPERIMENT/'lua/main.lua').read_text(encoding='utf-8')
    old_timing=L.execute((PROJECT/'tests/fixtures/legacy_timing.lua').read_text(encoding='utf-8'))
    L.globals().modules['./timing.lua']=old_timing
    L.globals().OldGeneration=L.execute(source.replace(
        'local function bind(driver,unit)',
        'local function bind(driver,unit) old_bind_calls=(old_bind_calls or 0)+1'))
    L.execute('''
old_ctx=context();OldGeneration.entries.frenzied_assault.on_activate(old_ctx)
refresh_unit,refresh_breed=attacker(true)
old_pad,old_data,old_bb=enter_case(refresh_unit,refresh_breed)
old_pad.expected_duration=1
close(old_pad.attack_duration,11)
missing_unit,missing_breed=attacker(false)
enter_case(missing_unit,missing_breed)
old_ctx:cleanup()
old_bind_count=old_bind_calls
hook_count_before_reload=mod.hook_count
enter_wrapper=BtMeleeAttackAction.enter
run_wrapper=BtMeleeAttackAction.run
leave_wrapper=BtMeleeAttackAction.leave
''')
    L.globals().modules['./timing.lua']=timing
    L.globals().NewGeneration=L.execute(source.replace(
        'local function bind(driver,unit)',
        'local function bind(driver,unit) new_bind_calls=(new_bind_calls or 0)+1'))
    L.execute('''
fresh_ctx=context();NewGeneration.entries.frenzied_assault.on_activate(fresh_ctx)
assert(mod.hook_count==hook_count_before_reload+3)
assert(BtMeleeAttackAction.enter==enter_wrapper and BtMeleeAttackAction.run==run_wrapper
    and BtMeleeAttackAction.leave==leave_wrapper,'Refresh must replace handlers without adding hook layers')
assert(mod:get_internal_data('allow_rehooking')==nil)
assert(not next(mod._diy_native_melee_20.cache) and not next(mod._diy_native_melee_20.unsupported))
old_ctx:cleanup();assert(mod._diy_native_melee_20.enabled,'An old owner cannot disable the fresh generation')
-- The old swing still uses +20% until it ends; the next swing uses +100%.
for i=1,4 do close(refresh_unit.values[i-1],Resource.variables[i].default*1.2)end
BtMeleeAttackAction.run(BtMeleeAttackAction,refresh_unit,refresh_breed,old_bb,old_pad,old_data,.016,10.7)
BtMeleeAttackAction.leave(BtMeleeAttackAction,refresh_unit,refresh_breed,old_bb,old_pad,old_data,11.1,'done',false)
local fresh_pad,fresh_data,fresh_bb=enter_case(refresh_unit,refresh_breed)
close(fresh_pad.attack_duration,10+1.2/ExpectedRate)
assert(old_bind_calls==old_bind_count and new_bind_calls==1,'Refreshed helper closure was not applied exactly once')
for i=1,4 do close(refresh_unit.values[i-1],Resource.variables[i].default*ExpectedRate)end
-- Previously missing resources can be discovered after a fresh generation.
local replacement=attacker(true);missing_unit.resource=replacement.resource;missing_unit.values=replacement.values
local missing_pad,missing_data,missing_bb=enter_case(missing_unit,missing_breed)
close(missing_pad.attack_duration,10+1.2/ExpectedRate)
fresh_ctx:cleanup()
BtMeleeAttackAction.leave(BtMeleeAttackAction,refresh_unit,refresh_breed,fresh_bb,fresh_pad,fresh_data,11.1,'done',false)
BtMeleeAttackAction.leave(BtMeleeAttackAction,missing_unit,missing_breed,missing_bb,missing_pad,missing_data,11.1,'done',false)
assert(not next(mod._diy_native_melee_20.units))
assert(#mod.warnings==0,'Unexpected rehook warnings')
''')
report=dict(rate=args.rate,native_lua_cases=len(cases),accelerated=verified,unresolved_kept_original=unchanged,
    hcm_package_validation=True,
    native_source_revision='0f0cb45991e9305ef4a7b925370792d7d6035f95',
    run_frames_without_variable_api=L.globals().run_frames_without_variable_access,
    lifecycle_checks=['native timing tables','combo and sweep arrays','non-timing fields',
        'in-progress cleanup','missing-resource fallback and cache','late remote join',
        'refresh without accumulating hooks','authority and local-session guards'],
    limitation='Graphics, resource loader, gameplay and FPS are not validated by this test.')
if args.experiment=='native-melee-100' or args.reload_check:
    report['lifecycle_checks'].extend(['new module replaces captured helpers',
        'reload to requested rate without stacking','old swing drains at its original rate',
        'stale cleanup cannot disable new owner','negative resource cache cleared on reload'])
report_dir=PROJECT/'build/checks';report_dir.mkdir(parents=True,exist_ok=True)
(report_dir/Path(args.report).name).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
