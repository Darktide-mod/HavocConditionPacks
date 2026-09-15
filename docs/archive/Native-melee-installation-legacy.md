# 近战动画安装 / Melee animation installation

## 简体中文

狂暴攻势提供常规近战攻速与动画 +20%，同步命中、连击和扫击时机。仅适用于本地单人/机器人房间。两处尚未匹配的首领连招保留原版行为。禁止医疗保持原样。

这 20% 是词条提供的额外加速。浩劫、污染兴奋剂等原版效果仍由游戏处理，可能进一步缩短命中后的等待。

1. 按通常方式将 HavocConditionManager 安装到游戏 mods 目录。
2. 关闭游戏，双击 mods/HavocConditionManager/Install-native-melee.cmd。安装器会核对游戏版本和资源文件，安装动画资源，并更新 AppData 中的狂暴攻势词条包。Vortex 部署后同样需要此步骤。
3. 启动游戏，在 HCM 的 DIY 列表中启用狂暴攻势并开始新任务。

安装器使用 Windows 自带 PowerShell，无需 Python 或 SimpleAssets。当前动画资源对应游戏 1.12.5；文件不匹配时拒绝安装。游戏更新后需要对应的新动画资源，不能忽略此检查。安装器保留其他资源登记，遇到同名文件冲突时停止。

移除动画资源时，关闭游戏，运行 Uninstall-native-melee.cmd，再卸载模组。安装器仅移除自己的资源登记和文件，并恢复此前的外部词条包。安装后被手动修改的文件不会被直接覆盖。备份保存在 AppData/Roaming/Fatshark/Darktide/HavocConditionManager/native-melee-backups，安装记录为同目录下的 native-melee-installation.json。

以后仅更新词条 Lua 时，可以在大厅刷新包，下一局生效；动画资源变更需要关闭游戏安装。无需删除着色器缓存。资源缺失或冲突的敌人保留原速，避免只加速命中判定。

升级时，关闭游戏后再次运行安装器即可。它会核对已安装文件和备份，直接替换受管理的旧资源；升级失败会回退，卸载仍恢复最初安装前的词条包。修复同一敌人不同攻击动画速度异常的版本必须更新动画资源，仅刷新词条 Lua 不够。

## English

Frenzied assault provides +20% ordinary melee attack and animation speed with matching hit, combo and sweep timings. It supports local solo/bot sessions. Two unmatched captain combos retain native behavior. No healing is unchanged.

This is an additional 20% from the condition. Native Havoc and stimmed-enemy effects remain active and can further shorten recovery after a hit.

1. Install HavocConditionManager into the game's mods directory.
2. Close Darktide and double-click mods/HavocConditionManager/Install-native-melee.cmd. This verifies the game files, installs the animation resources and updates the extracted AppData Frenzied assault package. This step is also required after Vortex deployment.
3. Start the game, enable Frenzied assault in HCM's DIY selection and begin a new mission.

The installer uses Windows PowerShell; Python and SimpleAssets are not required. These resources match game 1.12.5. Mismatched game files or occupied patch filenames stop installation. Other resource registrations are preserved.

To remove the animation resources, close the game and run Uninstall-native-melee.cmd before uninstalling HCM. It removes owned resource registrations/files and restores the previous extracted package. It refuses to overwrite files edited since installation. Backups and the installation record are under AppData/Roaming/Fatshark/Darktide/HavocConditionManager.

Later Lua-only changes may be refreshed in the hub for the next mission. Compiled animation resource changes require installation with the game closed. Shader cache deletion is unnecessary. Enemies with missing or conflicting animation resources retain native timing.

To upgrade, close the game and run the installer again. It verifies managed files and backups, replaces the previous resources directly, and rolls back a failed upgrade. Uninstall still restores the package from before the original installation. The fix for inconsistent attack animation speeds requires updated animation resources; refreshing the Lua package alone is insufficient.

## 繁體中文

狂暴攻勢提供常規近戰攻速與動畫 +20%，同步命中、連擊和掃擊時機。僅適用於本地單人/機器人房間；兩處尚未匹配的首領連招保留原版行為，禁止醫療保持原樣。

將模組安裝到遊戲 mods 目錄後，關閉遊戲，雙擊 mods/HavocConditionManager/Install-native-melee.cmd。Vortex 部署後也需要執行。安裝器核對遊戲版本與資源、保留其他資源登記、備份並更新 AppData 的外部詞條包。啟動遊戲後，在 HCM 的 DIY 清單中啟用狂暴攻勢，開始新任務。

安裝器使用 Windows PowerShell，不需要 Python 或 SimpleAssets。資源對應遊戲 1.12.5，不匹配時停止安裝。移除模組前，先關閉遊戲並執行 Uninstall-native-melee.cmd；安裝後被修改的檔案不會被直接覆寫。備份與安裝記錄位於 AppData/Roaming/Fatshark/Darktide/HavocConditionManager。

以後僅更新 Lua 時可在大廳重新整理，下一局生效；已編譯動畫資源變更需要關閉遊戲安裝。不需要刪除著色器快取。

這 20% 為詞條額外加速，浩劫與污染興奮劑等原版效果仍可能進一步縮短命中後的等待。升級時關閉遊戲並再次執行安裝器即可；它會核對檔案與備份、直接更新受管理的資源，失敗時回復舊安裝。解除安裝仍恢復最初的詞條包。修正同一敵人不同攻擊動畫速度異常必須更新動畫資源，僅重新整理 Lua 不足以生效。
