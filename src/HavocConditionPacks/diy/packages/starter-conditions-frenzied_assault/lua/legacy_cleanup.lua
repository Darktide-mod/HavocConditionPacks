-- Migration only. Never load/install the retired native driver or read memory.
return function()
    local mod=get_mod("HavocConditionManager")
    local previous=mod._diy_frenzied_assault_hooks_v1
    assert(not (previous and previous.current and previous.current.active),
        "Finish the active mission before replacing Frenzied assault")
    local saved=mod:persistent_table("diy_frenzy_native_timestep_v1")
    if saved.driver then
        local ok,why=saved.driver:disable()
        assert(ok~=false,"Retired animation hook cleanup failed: "..tostring(why))
    end
    if not previous and not mod._diy_frenzied_retired_hooks then return end
    local actions="scripts/extension_systems/behavior/nodes/actions/"
    for _,spec in ipairs({
        {"scripts/extension_systems/behavior/ai_brain","update"},
        {actions.."bt_melee_attack_action","_start_attack_anim"},
        {actions.."bt_chaos_hound_leap_action","_check_leap_for_collisions"},
        {actions.."bt_leap_action","_check_leap_for_collisions"},
        {"scripts/extension_systems/locomotion/minion_locomotion_extension","set_wanted_velocity"},
        {"scripts/extension_systems/locomotion/minion_locomotion_extension","set_wanted_velocity_flat"},
        {"scripts/utilities/minion_attack","start_shooting"},
        {"scripts/foundation/utilities/script_world","update"},
    })do mod:hook_disable(require(spec[1]),spec[2])end
    mod._diy_frenzied_assault_hooks_v1=nil
    mod._diy_frenzied_retired_hooks=true
    -- Keep the disabled driver's storage pinned until process exit.
end
