local mod=get_mod("HavocConditionPacks")
local function register()
    local hcm=get_mod("HavocConditionManager")
    if hcm and hcm.diy_api and hcm.diy_api.register_package_source then
        return hcm.diy_api.register_package_source("HavocConditionPacks")
    end
    mod:error("HavocConditionPacks requires HavocConditionManager 4.5.0 or newer.")
end
mod.on_all_mods_loaded=register
mod.on_enabled=function(initial_call)if not initial_call then register() end end
mod.on_disabled=function()
    local hcm=get_mod("HavocConditionManager")
    if hcm and hcm.diy_api and hcm.diy_api.unregister_package_source then
        hcm.diy_api.unregister_package_source("HavocConditionPacks")
    end
end
