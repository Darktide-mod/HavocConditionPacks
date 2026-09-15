-- Native-controller melee acceleration. Matching animation resources are
-- required; this implementation supports local solo/bot sessions.
local mod=get_mod("HavocConditionManager")
local Timing=require("./timing.lua")
local Resource=require("./resources.lua")
local Melee=require("scripts/extension_systems/behavior/nodes/actions/bt_melee_attack_action")
local function weak()return setmetatable({},{__mode="k"})end
local function local_session()
    if not mod.has_local_gameplay_authority() then return false end
    for _,player in pairs(Managers.player:human_players())do
        if player.remote then return false end
    end
    return true
end
local function restore(driver,unit,record)
    if ALIVE[unit] then
        for i,index in ipairs(record.indices)do
            -- Do not undo an independent subsequent variable change.
            local current=Unit.animation_get_variable(unit,index)
            if math.abs(current-record.values[i])<0.000001 then
                Unit.animation_set_variable(unit,index,record.defaults[i])
            end
        end
    end
    driver.units[unit]=nil
end
local function bind(driver,unit)
    local existing=driver.units[unit]
    if existing and existing.rate==driver.timing.rate then return existing end
    if existing then restore(driver,unit,existing)end
    if driver.unsupported[unit] then return end
    if not Unit.has_animation_state_machine(unit) then return end
    local record={indices={},defaults={},values={},rate=driver.timing.rate,pad=setmetatable({},{__mode="v"})}
    -- One bounded discovery when this enemy first attacks. Native playback
    -- then consumes the variables; no timer, layer scan, or raw memory access.
    for _,v in ipairs(driver.resource.variables)do
        local ok,index=pcall(Unit.animation_find_variable,unit,v.name)
        if ok and type(index)=="number" and index>=0 and index<256 and index%1==0 then
            local current=Unit.animation_get_variable(unit,index)
            if type(current)~="number" or current~=current or math.abs(current-v.default)>0.000001 then
                driver.unsupported[unit]=true;return
            end
            record.indices[#record.indices+1]=index
            record.defaults[#record.defaults+1]=current
            record.values[#record.values+1]=current*driver.timing.rate
        end
    end
    if #record.indices==0 then driver.unsupported[unit]=true;return end
    -- Discovery is transactional: a missing/conflicting variable never leaves
    -- a partially changed unit or advances only its damage timings.
    for i,index in ipairs(record.indices)do
        Unit.animation_set_variable(unit,index,record.values[i])
    end
    driver.units[unit]=record
    return record
end
local installed_driver
local function install()
    if installed_driver then return installed_driver end
    local driver=mod._diy_native_melee_20
    driver=driver or {units=weak(),cache=weak(),unsupported=weak()}
    mod._diy_native_melee_20=driver
    -- Replace this mod's three handlers once per freshly loaded module. Keep
    -- the shared driver so an old in-flight swing can drain on its own times.
    -- DMF replaces handlers in place; refresh does not add another hook layer.
    local dmf=get_mod("DMF")
    local previous=mod:get_internal_data("allow_rehooking")
    dmf.set_internal_data(mod,"allow_rehooking",true)
    local ok,why=pcall(function()
    mod:hook(Melee,"enter",function(fn,self,unit,breed,blackboard,pad,data,t,...)
        pad._hcm_native_melee_data=nil
        local session=Managers.state and Managers.state.game_session
        if driver.enabled and driver.session==session and local_session() then
            local record=bind(driver,unit)
            if record then
                local prepared=driver.cache[data]
                if not prepared then
                    prepared=driver.timing.prepare(data,driver.resource.events)
                    driver.cache[data]=prepared
                end
                pad._hcm_native_melee_data=prepared
                record.pad[1]=pad
                data=prepared
            end
        elseif driver.units[unit] then
            restore(driver,unit,driver.units[unit])
        end
        return fn(self,unit,breed,blackboard,pad,data,t,...)
    end)
    mod:hook(Melee,"run",function(fn,self,unit,breed,blackboard,pad,data,dt,t,...)
        -- One field selection; all updates, collisions, and animations remain
        -- native. Needed to keep later combo impact FX on the prepared times.
        return fn(self,unit,breed,blackboard,pad,pad._hcm_native_melee_data or data,dt,t,...)
    end)
    mod:hook(Melee,"leave",function(fn,self,unit,breed,blackboard,pad,data,t,...)
        fn(self,unit,breed,blackboard,pad,pad._hcm_native_melee_data or data,t,...)
        pad._hcm_native_melee_data=nil
        local record=driver.units[unit]
        if record and record.pad[1]==pad then
            record.pad[1]=nil
            if not driver.enabled or driver.session~=Managers.state.game_session or not local_session() then
                restore(driver,unit,record)
            end
        end
    end)
    end)
    dmf.set_internal_data(mod,"allow_rehooking",previous)
    assert(ok,why)
    installed_driver=driver
    return driver
end
local function activate(ctx)
    assert(local_session(),"原生近战 +20% 仅支持本地单人/机器人房间。")
    assert(Unit.animation_find_variable and Unit.animation_set_variable,
        "当前引擎没有所需的原生动画变量接口。")
    require("./legacy_cleanup.lua")()
    local driver=install()
    driver.timing=Timing;driver.resource=Resource;driver.cache=weak();driver.unsupported=weak()
    driver.enabled=true;driver.session=Managers.state.game_session;driver.owner=ctx
    ctx:on_cleanup(function()
        if driver.owner~=ctx then return end
        driver.enabled=false;driver.owner=nil;driver.cache=weak();driver.unsupported=weak()
        -- Let an in-progress swing complete on its matching animation/timing
        -- pair. Its native leave callback restores the variables afterwards.
        for unit,record in pairs(driver.units)do
            if not record.pad[1] then restore(driver,unit,record)end
        end
    end)
end
return {api_version={major=1,minor=0},entries={frenzied_assault={on_activate=activate}}}
