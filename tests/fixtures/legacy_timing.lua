-- Prepare once per native action definition; retain all non-timing values.
-- The returned tables are private to this package, including combo windows.
local T={rate=1.2}
local event_fields={
    "attack_anim_durations","attack_anim_damage_timings","move_start_timings",
    "melee_attack_rotation_durations","effect_template_start_timings",
    "disable_shield_block_timing","enable_shield_block_timing",
}
local function times(value)
    if type(value)=="number" then return value/T.rate end
    if type(value)~="table" then return value end
    local out={}
    for k,v in pairs(value)do out[k]=times(v)end
    return out
end
local function sweep(value)
    local out={}
    for k,v in pairs(value)do out[k]=v end
    if type(value[1])=="table" then
        for i,window in ipairs(value)do out[i]=sweep(window)end
    else
        -- A third field is a sweep node override, not a duration.
        out[1]=value[1]/T.rate;out[2]=value[2]/T.rate
    end
    return out
end
local function events(source,supported,transform)
    local out={}
    for event,value in pairs(source)do
        out[event]=supported[event] and transform(value) or value
    end
    return out
end
function T.prepare(source,supported)
    local out={}
    for k,v in pairs(source)do out[k]=v end
    for _,key in ipairs(event_fields)do
        if source[key] then out[key]=events(source[key],supported,times)end
    end
    if source.attack_sweep_damage_timings then
        out.attack_sweep_damage_timings=events(source.attack_sweep_damage_timings,supported,sweep)
    end
    local impact=source.sweep_ground_impact_fx_timing
    if type(impact)=="table" then out.sweep_ground_impact_fx_timing=events(impact,supported,times)
    elseif impact then out.sweep_ground_impact_fx_timing=impact/T.rate end
    return out
end
return T
