# Havoc Condition Packs · 浩劫扩展词条集

HCM 的可选词条集合，独立分发需要额外动画资源的内容。首版包含「狂暴攻势」：全体敌人的常规近战攻击与动画额外加速 20%，同步命中、连击、扫击和动作时长。仅支持本地单人 / 机器人房间；两处未匹配的首领连招保留原版行为。

## 安装

1. 安装 HavocConditionManager 4.5.0 或更新版本。
2. 把发行包中的 `HavocConditionPacks` 放入游戏 `mods` 目录，在 `mod_load_order.txt` 中排在 `HavocConditionManager` 之后。
3. 首次安装动画资源时，关闭游戏，运行本集合目录中的 `Install-native-melee.cmd`。安装器核对游戏版本及资源指纹，只安装动画资源与资源登记，不解压或复制 DIY 词条。资源不匹配时停止。
4. 启动游戏，HCM 自动读取本集合 `diy/packages` 里的词条。在 HCM 的词条配置中勾选狂暴攻势。

HCM 主包不携带此安装器或动画补丁。HCM 的禁止医疗、总体调节与普通外部 DIY 均不依赖本集合。本集合包含 PowerShell/CMD 与游戏动画二进制补丁，不能据此声称它已经通过 Nexus 扫描。

已经通过旧 HCM 安装过相同动画资源时，安装器会验证并复用它们，保留旧安装记录。升级 HCM 时不必先卸载这些匹配的资源。旧 AppData 词条保留，但同 ID 时优先读取本集合；不会加载两次。没有安装本集合的用户仍能通过 HCM 原有外部目录加载自己的词条。

## 更新和卸载

仅修改词条 JSON / Lua 后，在大厅刷新 HCM 即可，下一局采用新版本；正在运行的任务保留开局快照。修改动画二进制资源需要关闭游戏后安装。

要移除动画资源，请关闭游戏并运行 `Uninstall-native-melee.cmd`，随后移除本集合的加载顺序项和模组目录。安装器只移除受管理的动画资源登记和文件，保留其他资源登记。旧 HCM 安装记录由随附的旧版卸载路径处理；它按原记录恢复以前的外部词条。若不再需要恢复出的旧词条，可在 HCM 外部包管理中停用它。

## 目录与接口

- `src/HavocConditionPacks/diy/packages`：直接加载的词条源码。
- `src/HavocConditionPacks/diy/index.json`：声明随附的词条包 ID。
- `src/HavocConditionPacks/native-melee`：动画补丁、校验清单、资源安装器和旧安装卸载兼容代码。
- `tools`：动画格式读取、修改与离线重建代码；不会写入游戏文件。
- `tests`：近战时序、动画变量、任务清理与安装回退验证。

独立词条集合通过 HCM 的 `diy_api.register_package_source("HavocConditionPacks")` 注册自己的声明目录；卸载集合时调用 `unregister_package_source`。注册不勾选效果，不改变当前任务的冻结快照，不执行包内 Lua；只有已选词条进入任务时才执行其生命周期。

## 源码与验证

把本仓库与 HCM 仓库放在同一父目录。验证使用 Python、LuaJIT 的 Lupa、Windows PowerShell、本机暗潮原始资源及对应游戏 Lua 源码。原始游戏文件、游戏 DLL、用户配置和运行日志不随仓库分发。`HCM_PROJECT`、`DARKTIDE_GAME`、`DARKTIDE_SOURCE`、`DARKTIDE_DEV_SUPPORT` 可覆盖默认开发路径。

`python tools/rebuild.py` 只从已安装游戏读取受验证的原始资源，在 `build/rebuilt` 重建补丁并核对发行指纹。`python tests/run.py` 运行检查。测试中的旧版异常对照读取相邻 HCM 仓库保留的旧发行包。这里的离线验证不能替代游戏内整局测试。

## English

Optional DIY conditions for HavocConditionManager 4.5.0+. Frenzied assault provides +20% ordinary enemy melee attack and animation speed in local solo/bot sessions. Install this folder under `mods`, load it after HCM, and run the included animation installer with Darktide closed. Condition files are read directly; the installer only registers matching animation resources. Old matching HCM installations are verified and reused with their rollback records intact.

HCM itself contains neither this installer nor these binary patches. Lua-only updates can be refreshed in the hub for the next mission. Run the uninstaller before removing animation resources. Game resources and systems belong to Fatshark; source references include Aussiemon/Darktide-Source-Code and Bitsquid's state-machine format documentation. No antivirus approval is claimed.
