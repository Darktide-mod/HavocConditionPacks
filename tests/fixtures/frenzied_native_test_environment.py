"""Run the scripted package through the actual loader, AI brain and timing methods."""
from project_env import PROJECT, GAME, FIXTURES
from pathlib import Path
from ctypes import c_float
import subprocess
import re
import json
from lupa.luajit21 import LuaRuntime

L = LuaRuntime(unpack_returned_tuples=True)
L.globals().engine_float32 = lambda value: c_float(value).value
L.globals().real_ffi = L.eval("require('ffi')")


def native(path):
    return subprocess.check_output(['git','-c','gc.auto=0','show','HEAD:'+path],cwd=GAME).decode('utf-8-sig')


L.execute(r'''
modules={ffi=real_ffi}
settings=function(_,value)return value end
require=function(path) modules[path]=modules[path] or {};return modules[path] end
class=function(name) local cls={};cls.__index=cls;_G[name]=cls;return cls end
table.clear=function(t)for k in pairs(t)do t[k]=nil end end
table.enum=function(...)local t={};for _,v in ipairs({...})do t[v]=v end;return t end
math.two_pi=2*math.pi;math.degrees_to_radians=math.rad
table.index_lookup_table=function(...)local out={};for i,v in ipairs({...})do out[v]=i end;return out end
math.random_range=function(a,b)return (a+b)/2 end
math.clamp=function(v,a,b)return math.max(a,math.min(v,b))end
ALIVE=setmetatable({},{__index=function(_,u)return u and u.alive~=false end})
HEALTH_ALIVE=ALIVE
POSITION_LOOKUP=setmetatable({},{__index=function(_,u)return Vector3(unpack(u.position or {0,0,0}))end})
frame=0
local vector_mt={}
local function vector(x,y,z)return setmetatable({values={x,y,z},frame=frame},vector_mt)end
function vector_mt.__index(v,k)
    assert(v.frame==frame,'Expired temporary Vector3 accessed across frames')
    return v.values[k=='x' and 1 or k=='y' and 2 or 3]
end
function vector_mt.__mul(v,n)if type(v)=='number' then v,n=n,v end;return vector(v.x*n,v.y*n,v.z*n)end
function vector_mt.__div(v,n)return v*(1/n)end
function vector_mt.__add(a,b)return vector(a.x+b.x,a.y+b.y,a.z+b.z)end
function vector_mt.__sub(a,b)return vector(a.x-b.x,a.y-b.y,a.z-b.z)end
Vector3=setmetatable({zero=function()return vector(0,0,0)end,down=function()return vector(0,0,-1)end,
    forward=function()return vector(0,1,0)end,length_squared=function(v)return v.x*v.x+v.y*v.y+v.z*v.z end},
    {__call=function(_,x,y,z)return vector(x,y,z)end})
Vector3.length=function(v)return math.sqrt(Vector3.length_squared(v))end
Vector3.flat=function(v)return vector(v.x,v.y,0)end
Vector3.normalize=function(v)local n=Vector3.length(v);return n>0 and v*(1/n) or Vector3.zero()end
Vector3.distance=function(a,b)return Vector3.length(a-b)end
Vector3.up=function()return vector(0,0,1)end
Vector3.cross=function(a,b)return vector(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x)end
Vector3Box=function(v,y,z)
    if v==nil then v=Vector3.zero()elseif type(v)=='number' then v=Vector3(v,y,z)end
    local box={}
    function box:store(value)self.values={value.x,value.y,value.z}end
    function box:unbox()return vector(unpack(self.values))end
    box:store(v);return box
end
Quaternion={look=function()return {}end,forward=function()return Vector3(0,1,0)end}
Unit={set_local_rotation=function()end,local_rotation=function()return {}end,
    world_position=function(u)return POSITION_LOOKUP[u]end,node=function()return 1 end}
Unit.animation_get_variable=function(u,index)return u.animation_variables and u.animation_variables[index] or 1 end
Unit.animation_set_variable=function(u,index,value)u.animation_variables=u.animation_variables or {};u.animation_variables[index]=value;u.last_anim_variable=value end
Unit.animation_wanted_root_pose=function(u)return Vector3(unpack(u.wanted_root_position))end
Matrix4x4={translation=function(value)return value end}
local function array(t,out) out=out or {};table.clear(out);for i,v in pairs(t)do out[i]=v end;return out end
Unit.has_animation_state_machine=function(u)return u.anim~=nil end
Unit.animation_get_time=function(u,out)return array(u.anim.times,out),u.anim.layers end
Unit.animation_get_state=function(u,out)return array(u.anim.states,out),u.anim.layers end
Unit.animation_get_animation=function(u,out)return array(u.anim.ids,out),u.anim.layers end
-- The real engine separates pending restore data from live animation layers.
-- set_time/set_animation fill one pending restore entry per layer; neither
-- changes live getters or evaluated bones. set_state consumes that data,
-- including when the state id is unchanged. See the read-only engine audit.
local animation_job_running=false
Unit.animation_set_time=function(u,...)
    assert(not animation_job_running,'Animation mutation during the parallel animation callback')
    local a=u.anim;a.writes=(a.writes or 0)+1;a.pending_times={...}
    for i,value in pairs(a.pending_times)do a.pending_times[i]=engine_float32(value)end
end
Unit.animation_set_animation=function(u,...)
    assert(not animation_job_running,'Animation mutation during the parallel animation callback')
    u.anim.pending_ids={...}
end
Unit.animation_set_state=function(u,...)
    assert(not animation_job_running,'Animation mutation during the parallel animation callback')
    local a=u.anim;local states={...};a.restores=a.restores or {}
    for i=1,select('#',...)do
        if states[i]~=nil then
            a.restores[i]=(a.restores[i] or 0)+1
            a.blend_remaining=0 -- Restoring a layer discards its outgoing blend.
            a.states[i]=states[i]
            local id=a.pending_ids and a.pending_ids[i]
            if id~=nil then
                a.ids[i]=id;a.times[i]=a.pending_times and a.pending_times[i] or 0
            else
                -- Without the pending animation id, set_state takes the
                -- ordinary start path and does not consume pending time.
                a.times[i]=0
            end
        end
    end
    a.pending_times=nil;a.pending_ids=nil
end
native_dt={enabled=false,rates={},traced=false}
animation_units={}
level_world={active=true}
World={get_data=function(w,k)return w[k]end,update_timer=function()end}
World.update_animations=function(_,dt)
    for _,u in ipairs(animation_units)do
        if ALIVE[u] and u.anim then
            local native_dt=dt*(native_dt.enabled and native_dt.rates[u] or 1)
            local move=u.anim.uses_move_variable and Unit.animation_get_variable(u,1) or 1
            for i=1,u.anim.layers do if u.anim.times[i] then u.anim.times[i]=u.anim.times[i]+native_dt*(u.anim.native_rate or 1)*move end end
            if u.anim.blend_remaining then u.anim.blend_remaining=math.max(0,u.anim.blend_remaining-native_dt)end
            if u.anim.change then u.anim.change(u.anim)end
            u.anim.evaluated_pose_times=array(u.anim.times,u.anim.evaluated_pose_times)
        end
    end
end
World.update_animations_with_callback=function(w,dt,fn)
    animation_job_running=true;fn();animation_job_running=false
    World.update_animations(w,dt)
end
World.update_scene=function()
    for _,u in ipairs(animation_units)do
        if ALIVE[u] and u.anim then u.anim.pose_times=array(u.anim.evaluated_pose_times or {},u.anim.pose_times)end
    end
end
World.update_scene_with_callback=function(w,dt,fn)fn();World.update_scene(w,dt)end
PhysicsWorld={immediate_overlap=function()return nil,1 end}
ScriptUnit={has_extension=function(u,name)return u and u.ext[name]end,extension=function(u,name)return assert(u.ext[name],name)end}
NetworkConstants={move_speed={min=0,max=100}}
Network={game_session=function()return true end}
GameSession={set_game_object_field=function(session,id,key,v)session[key]=v end}
GwNavBot={set_max_desired_linear_speed=function(bot,speed)bot.speed=speed end}
MinionLocomotion={set_animation_translation_scale=function(id,value)
    assert(getmetatable(value)==vector_mt,'Vector3 expected');id.scale={value.x,value.y,value.z}
end,animation_translation_scale=function(id)return Vector3(unpack(id.scale))end,
rotation_speed=function()return 1 end,set_rotation_speed=function()end,use_lerp_rotation=function()end,
set_animation_driven=function()end,velocity=function()return Vector3.zero()end,
set_wanted_velocity=function(id,v)id.velocity={v.x,v.y,v.z}end,
set_wanted_velocity_flat=function(id,v)id.velocity={v.x,v.y,v.z}end,set_wanted_rotation=function()end}
Log={warning=function()end}
Managers={state={game_session={},player_unit_spawn={owner=function()return nil end}}}
Managers.world={world=function(_,name)assert(name=='level_world');return level_world end}
Managers.state.extension={system=function(_,name)
    if name=='slot_system' then return {is_slot_searching=function()return false end}end
    if name=='side_system' then return {side_by_unit={}}end
    if name=='fx_system' then return {start_template_effect=function()return 1 end,stop_template_effect=function()end}end
end}
Managers.state.difficulty={get_table_entry_by_challenge=function(_,v)return type(v)=='table' and v[1] or v end}
Managers.state.unit_spawner={spawn_network_unit=function()projectiles=(projectiles or 0)+1 end}
DMFMod={}
function DMFMod:is_enabled()return true end
function DMFMod:get_name()return self.name end
function DMFMod:get_internal_data(key)return self._internal[key]end
function DMFMod:info(message,...)
    if message=='(%s): Hooking \'%s\' from [%s] (Origin: %s)' then
        self.hook_count=(self.hook_count or 0)+1
        if self.fail_hook_at==self.hook_count then error('injected rehook registration failure',0)end
    end
end
function DMFMod:warning(message,...)self.warnings[#self.warnings+1]=string.format(message,...)end
function DMFMod:error(message,...)error(string.format(message,...),0)end
function new_mod(name)return setmetatable({name=name,_internal={},warnings={},hook_count=0},{__index=DMFMod})end
dmf=new_mod('DMF')
dmf.check_wrong_argument_type=function()return false end
dmf.safe_call_nr=function(_,_,fn,...)return fn(...)end
dmf.set_internal_data=function(owner,key,value)owner._internal[key]=value end
CLASS={InputService={start_simulate_action=function()end,stop_simulate_action=function()end},InputManager={update=function()end}}
table.is_empty=function(t)return next(t)==nil end
mod=new_mod('HavocConditionManager');mod.authority=true
function mod.has_local_gameplay_authority()return mod.authority end
get_mod=function(name)return name=='DMF' and dmf or mod end
modules['scripts/utilities/animation']={random_event=function(e)return type(e)=='table' and e[1] or e end}
modules['scripts/utilities/minion_movement']={target_velocity=function()return Vector3.zero()end,
    get_relative_direction_name=function()return 'fwd'end,get_moving_direction_name=function()return 'fwd'end}
modules['scripts/utilities/attack/attack']={execute=function()return 1 end}
modules['scripts/settings/damage/damage_settings']={damage_types=setmetatable({},{__index=function(_,k)return k end})}
modules['scripts/utilities/attack/block']={attack_is_blockable=function()return true end}
modules['scripts/utilities/minion_shield']={init_block_timings=function()end,update_block_timings=function()end}
modules['scripts/settings/minion_backstab/minion_backstab_settings']={}
modules['scripts/settings/damage/attack_settings']={attack_types={sweep='sweep'}}
modules['scripts/settings/breed/breed_settings']={types={minion='minion'}}
modules['scripts/utilities/minion_perception']={set_target_lock=function()end}
modules['scripts/extension_systems/blackboard/utilities/blackboard']={write_component=function(bb,key)return assert(bb[key],key)end}
modules['scripts/utilities/items']={base_unit=function()return 'test_grenade'end}
modules['scripts/backend/master_items']={get_cached=function()return setmetatable({},{__index=function()return {}end})end}
modules['scripts/settings/damage/stagger_settings']={stagger_impact_comparison={light=1}}
modules['scripts/utilities/nav_queries']={movement_check=function()end}
modules['scripts/utilities/breed']={is_player=function(b)return b.breed_type=='player'end}
modules['scripts/utilities/vo']={enemy_generic_vo_event=function()end}
modules['scripts/settings/fx/effect_templates']={renegade_grenadier_grenade={},cultist_grenadier_grenade={}}
''')

for path in [
    'scripts/foundation/utilities/script_world',
    'scripts/settings/difficulty/minion_difficulty_settings',
    'scripts/utilities/attack_intensity',
    'scripts/extension_systems/behavior/ai_brain',
    'scripts/extension_systems/animation/minion_animation_extension',
    'scripts/extension_systems/attack_intensity/minion_attack_intensity_extension',
    'scripts/extension_systems/locomotion/minion_locomotion_extension',
    'scripts/extension_systems/navigation/minion_navigation_extension',
    'scripts/utilities/minion_attack',
    'scripts/extension_systems/behavior/nodes/actions/bt_melee_attack_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_melee_follow_target_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_shoot_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_blocked_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_chaos_hound_leap_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_leap_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_grenadier_throw_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_quick_grenade_throw_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_stagger_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_mutant_charger_charge_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_chaos_daemonhost_warp_sweep_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_climb_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_jump_across_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_exit_spawner_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_open_door_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_poxwalker_bomber_approach_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_chaos_poxwalker_explode_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_in_cover_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_dash_action',
    'scripts/extension_systems/behavior/nodes/actions/bt_renegade_flamer_patrol_action',
]:
    L.globals().modules[path] = L.execute(native(path+'.lua'))

L.globals().mutant_actions = L.execute(native('scripts/settings/breed/breed_actions/cultist/cultist_mutant_actions.lua'))
movement_source = native('scripts/utilities/minion_movement.lua')
for method in ('get_animation_wanted_movement_speed', 'apply_animation_wanted_movement_speed'):
    function_source = re.search(r'MinionMovement\.' + method + r' = function.*?^end', movement_source, re.S | re.M).group()
    L.execute("local MinionMovement=modules['scripts/utilities/minion_movement'];" + function_source)

# Keep the shipped 1.6.0 implementation as a negative regression. A permissive
# mock that writes directly to live time would incorrectly make it pass.
L.globals().legacy_animation = L.execute((PROJECT/'tests/fixtures/frenzied_animation_1_6_0.lua').read_text(encoding='utf-8'))
L.execute(r'''
do
    local function near(a,b)assert(math.abs(a-b)<1e-8,tostring(a)..' / '..tostring(b))end
    local u={anim={times={1,2,3},states={1,2,3},ids={10,20,30},layers=3}}
    Unit.animation_set_time(u,4,nil,6)
    Unit.animation_set_animation(u,10,nil,30)
    near(Unit.animation_get_time(u)[1],1)
    assert(u.anim.restores==nil,'Setting pending time and animation must not restore a layer')
    Unit.animation_set_state(u,1,nil,3)
    near(Unit.animation_get_time(u)[1],4);near(u.anim.times[2],2);near(u.anim.times[3],6)
    assert(u.anim.restores[1]==1 and u.anim.restores[2]==nil and u.anim.restores[3]==1,
        'Same-state restore rebuilds included layers; a nil state leaves that layer untouched')
    assert(u.anim.pending_times==nil and u.anim.pending_ids==nil,'set_state consumes the pending arrays')
    Unit.animation_set_time(u,9)
    Unit.animation_set_state(u,1)
    near(u.anim.times[1],0)
    assert(u.anim.restores[1]==2,'Time without the animation id follows the ordinary state-start path')

    local old={anim={times={0,nil,.2},states={1,2,3},ids={10,20,30},layers=3}}
    local controller={world=level_world,moves={[old]={brain={}}},animation_rate=function()return 2 end}
    animation_units={old}
    local write_frames=0
    for _=1,60 do
        local snapshots=legacy_animation.before(controller,level_world,1/60)
        modules['scripts/foundation/utilities/script_world'].update(level_world,1/60)
        write_frames=write_frames+legacy_animation.after(snapshots)
    end
    near(old.anim.times[1],1);near(old.anim.pose_times[1],1)
    near(Unit.animation_get_time(old)[1],1)
    assert(write_frames==60 and old.anim.writes==60 and old.anim.pending_times[1]>old.anim.times[1],
        '1.6.0 reports writes on every frame while live playback and visible pose remain at native speed')
    assert(old.anim.restores==nil,'The old implementation never commits its pending animation time')
    animation_units={}
end
''')

# Use DMF's real owner registry, hook chain and replacement rules. A wrapper
# that blindly nests callbacks cannot verify in-process package refreshing.
L.execute((FIXTURES/'mods/dmf/scripts/mods/dmf/modules/core/hooks.lua').read_text(encoding='utf-8'))
L.execute(r'''
do
    local a,b=new_mod('replacement_probe'),new_mod('foreign_probe')
    local target={value=function()return 1 end}
    a:hook(target,'value',function(fn)return fn()+2 end)
    a:hook(target,'value',function(fn)return fn()+4 end)
    assert(target.value()==3 and #a.warnings==1,'Default DMF duplicate registration only warns and retains the first handler')
    dmf.set_internal_data(a,'allow_rehooking',true)
    a:hook(target,'value',function(fn)return fn()+4 end)
    b:hook(target,'value',function(fn)return fn()*3 end)
    assert(target.value()==15)
    a:hook(target,'value',function(fn)return fn()+8 end)
    assert(target.value()==27,'DMF replaces the owner handler in place and retains the foreign hook chain')
end
''')
print('PASS: engine pending/live/pose boundaries; unchanged-state commit and nil-layer behavior; 1.6.0 writes pending time on 60 frames yet remains at native playback speed.')

# Load the grenade action definitions verbatim from the game's source. Only
# projectile asset handles and utility scoring are stubbed in this Lua VM.
L.execute('grenade_actions={}')
for breed in ('renegade', 'cultist'):
    source = native(f'scripts/settings/breed/breed_actions/{breed}/{breed}_grenadier_actions.lua')
    blocks = [re.search(r'\n\t' + key + r' = \{.*?\n\t\},', source, re.S).group()
              for key in ('throw_grenade', 'quick_throw_grenade')]
    L.globals().grenade_actions[breed] = L.execute('''
local MinionDifficultySettings=require('scripts/settings/difficulty/minion_difficulty_settings')
local projectile={locomotion_template={trajectory_parameters={throw={speed_initial=20,locomotion_state='moving'}}}}
local ProjectileTemplates=setmetatable({},{__index=function()return projectile end})
local UtilityConsiderations={}
return {''' + '\n'.join(blocks) + '\n}')

L.execute("function unit(kind,special)\n    local u={ext={}};local breed={breed_type=kind or 'minion',name='test_enemy',tags={special=special},stagger_durations={light=2}}\n    u.ext.unit_data_system={components={},breed=function()return breed end,breed_name=function()return breed.name end,\n        read_component=function(self,k)return self.components[k]end,\n        write_component=function(self,k)self.components[k]=self.components[k] or {};return self.components[k]end}\n    u.ext.buff_system={stat_buffs=function()\n        local stats=engine and kind~='companion' and kind~='player' and engine.effects(u).stats or {}\n        return {movement_speed=u.gas_speed or 1,ranged_attack_speed=1+(stats.ranged_attack_speed or 0),\n            melee_attack_speed=1+(stats.melee_attack_speed or 0)+(u.other_melee_speed or 0)}\n    end}\n    u.ext.navigation_system=setmetatable({_unit=u,_breed=breed,_max_speed=5,_movement_modifier_table_size=8,_num_movement_modifiers=0,\n        _last_movement_modifier_index=1,_movement_modifiers={},_game_session={},_game_object_id=1,_nav_bot={}},MinionNavigationExtension)\n    u.ext.locomotion_system=setmetatable({_unit=u,_engine_extension_id={scale={1,1,1}}},MinionLocomotionExtension)\n    u.ext.animation_system=setmetatable({_unit=u,_is_server=false,_variables={anim_move_speed=1},\n        _animation_variable_bounds={anim_move_speed={0,85}},\n        anim_event=function(_,event)u.last_event=event;if u.anim then u.anim.blend_remaining=.3 end end},MinionAnimationExtension)\n    u.ext.perception_system={}\n    u.ext.health_system={hit_mass=function()return 1 end,set_hit_mass=function()end}\n    u.ext.attack_intensity_system=setmetatable({_breed=breed,_allowed_attacks={melee=false,ranged=false}},MinionAttackIntensityExtension)\n    return u,breed\nend\ntarget=unit('player')\ntarget.ext.attack_intensity_system={attack_allowed=function()return false end,add_intensity=function()end,set_attacked=function()end}\nbase_data={attack_anim_events={'attack'},attack_anim_damage_timings={attack=.6},attack_anim_durations={attack=1.2},\n    attack_type='melee',damage_profile={},shoot_cooldown={2,4},shoot_template={scope_reflection_timing=.5},aim_duration={aim={.4,.8}},\n    attack_intensities={melee=1},range=8,damage=50}\nnode=setmetatable({identifier='melee',tree_node={'BtMeleeAttackAction',action_data=base_data}},BtMeleeAttackAction)\nfunction node:children()return {}end\nfunction node:enter(u,breed,blackboard,pad,data,t)\n    BtMeleeAttackAction.enter(self,u,breed,blackboard,pad,data,t)\n    observed={attack=pad.attack_timing-t,duration=pad.attack_duration-t,cooldown=data.shoot_cooldown[1],aim=data.aim_duration.aim[1],scope=data.shoot_template.scope_reflection_timing,\n        range=data.range,damage=data.damage,intensity=data.attack_intensities.melee}\nend\nfunction node:run()if break_ai then error('simulated native failure')end;return 'running',false end\nfunction node:leave()end\ntree={root=function()return node end}\nfunction brain(u,breed)\n    return setmetatable({_unit=u,_breed=breed,_blackboard={perception={target_unit=target},behavior={},spawn={}},_behavior_tree=tree,_node_data={},_scratchpad={},_running_child_nodes={},_old_running_child_nodes={},\n        _running_leaf_node_result='running',_evaluate_utility=true},AiBrain)\nend\n")
