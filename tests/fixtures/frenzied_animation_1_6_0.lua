-- Darktide's Unit.animation_get_time/set_time API works with one time per
-- animation layer (the same API used by PlayerUnitAnimationState). There is
-- no generic Unit.set_animation_speed API. Advance the measured playheads;
-- never restart an event, reset a state machine or accelerate the world.
local A={}
local function capture(snapshot,unit,rate)
    snapshot=snapshot or {times={},states={},animations={},next_times={},next_states={},next_animations={}}
    snapshot.unit,snapshot.rate=unit,rate
    snapshot.times,snapshot.count=Unit.animation_get_time(unit,snapshot.times)
    snapshot.states=Unit.animation_get_state(unit,snapshot.states)
    snapshot.animations=Unit.animation_get_animation(unit,snapshot.animations)
    return snapshot
end
function A.available()
    return type(Unit.animation_get_time)=="function" and type(Unit.animation_set_time)=="function"
        and type(Unit.animation_get_state)=="function" and type(Unit.animation_get_animation)=="function"
end
function A.before(current,world,dt)
    if dt<=0 or world~=current.world or not World.get_data(world,"active") or World.get_data(world,"paused") then return end
    -- Keep the per-unit buffers between frames. A horde must not allocate
    -- six new Lua arrays per enemy on every animation update.
    local snapshots=current.animation_snapshots or {};current.animation_snapshots=snapshots
    local seen=current.animation_seen or {};current.animation_seen=seen
    local records=current.animation_records or {};current.animation_records=records
    table.clear(snapshots);table.clear(seen)
    local function add(unit,rate)
        if unit and ALIVE[unit] and not seen[unit] and Unit.has_animation_state_machine(unit) then
            seen[unit]=true
            local snapshot=capture(records[unit],unit,rate);records[unit]=snapshot
            snapshots[#snapshots+1]=snapshot
        end
    end
    for unit,record in pairs(current.moves)do
        if ALIVE[unit] then
            local rate=current:animation_rate(record.brain)
            if rate~=1 then
                add(unit,rate)
                -- Only an actual paired victim, still owned by this minion,
                -- shares the attack animation clock. Free players never do.
                local pad=record.brain and record.brain._scratchpad
                local victim=pad and (pad.grabbed_target or pad.grabbed_unit or pad.target_unit
                    or pad.pounce_component and pad.pounce_component.pounce_target
                    or pad.perception_component and pad.perception_component.target_unit)
                local data=victim and ALIVE[victim] and ScriptUnit.has_extension(victim,"unit_data_system")
                local breed=data and data:breed()
                local disabled=breed and breed.breed_type=="player" and data:read_component("disabled_character_state")
                if disabled and disabled.disabling_unit==unit then
                    add(victim,rate)
                    local first_person=ScriptUnit.has_extension(victim,"first_person_system")
                    if first_person then add(first_person:first_person_unit(),rate)end
                end
            end
        else current.moves[unit]=nil;records[unit]=nil end
    end
    for unit in pairs(records)do if not seen[unit] then records[unit]=nil end end
    return snapshots
end
function A.after(snapshots)
    local updated=0
    for _,snapshot in ipairs(snapshots or {})do
        local unit=snapshot.unit
        if ALIVE[unit] then
            local times,count=Unit.animation_get_time(unit,snapshot.next_times)
            local states=Unit.animation_get_state(unit,snapshot.next_states)
            local animations=Unit.animation_get_animation(unit,snapshot.next_animations)
            snapshot.next_times,snapshot.next_states,snapshot.next_animations=times,states,animations
            local changed=false
            for i=1,count do
                local before,now=snapshot.times[i],times[i]
                -- A transition or loop establishes a new playhead. Do not
                -- import elapsed time from an unrelated animation/layer.
                if before and now and now>=before and states[i]==snapshot.states[i]
                    and animations[i]==snapshot.animations[i] then
                    times[i]=now+(now-before)*(snapshot.rate-1);changed=changed or now>before
                end
            end
            if changed then Unit.animation_set_time(unit,unpack(times,1,count));updated=updated+1 end
        end
    end
    return updated
end
return A
