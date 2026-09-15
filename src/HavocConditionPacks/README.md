# Havoc Condition Packs · 浩劫扩展词条集

[简体中文](#简体中文) · [English](#english)

[ConditionPacks 源码 / Source](https://github.com/Darktide-mod/HavocConditionPacks) · [下载 / Downloads](https://github.com/Darktide-mod/HavocConditionPacks/releases) · [HCM 源码 / Source](https://github.com/Darktide-mod/HavocConditionManager) · [HCM 下载 / Downloads](https://github.com/Darktide-mod/HavocConditionManager/releases)

## 简体中文

HCM 的可选词条集合，独立分发需要额外动画资源的内容。首版包含「狂暴攻势」：全体敌人的常规近战攻击与动画额外加速 20%，同步命中、连击、扫击和动作时长。仅支持本地单人 / 机器人房间；两处未匹配的首领连招保留原版行为。

HCM 负责词条管理和总体强度调节，也提供内置「禁止医疗」及外部 DIY 加载。这些功能不需要安装本集合。本次 r2 仅补充说明，模组仍为 1.0.0，狂暴攻势仍为 2.2.1、加速 20%。

### 安装

从 [Releases](https://github.com/Darktide-mod/HavocConditionPacks/releases) 下载 `HavocConditionPacks-1.0.0.zip`。GitHub 的 `Source code (zip)` 包含开发资料及历史发布，请勿作为安装包使用。

1. 安装 [HavocConditionManager](https://github.com/Darktide-mod/HavocConditionManager/releases) 4.5.0 或更新版本，以及 HCM 所需前置。
2. 把发行包中的 `HavocConditionPacks` 放入游戏 `mods` 目录，在 `mod_load_order.txt` 中排在 `HavocConditionManager` 之后。
3. 首次安装动画资源时，关闭游戏，运行本集合目录中的 `Install-native-melee.cmd`。安装器核对游戏版本及资源指纹，只安装动画资源与资源登记，不解压或复制 DIY 词条。资源不匹配时停止。
4. 启动游戏，HCM 自动读取本集合 `diy/packages` 里的词条。在 HCM 的词条配置中勾选狂暴攻势。

HCM 主包不携带此安装器或动画补丁。HCM 的禁止医疗、总体调节与普通外部 DIY 均不依赖本集合。本集合包含 PowerShell/CMD 与游戏动画二进制补丁，不能据此声称它已经通过 Nexus 扫描。

已经通过旧 HCM 安装过相同动画资源时，安装器会验证并复用它们，保留旧安装记录。升级 HCM 时不必先卸载这些匹配的资源。旧 AppData 词条保留，但同 ID 时优先读取本集合；不会加载两次。没有安装本集合的用户仍能通过 HCM 原有外部目录加载自己的词条。

### 更新和卸载

仅修改词条 JSON / Lua 后，在大厅刷新 HCM 即可，下一局采用新版本；正在运行的任务保留开局快照。修改动画二进制资源需要关闭游戏后安装。

要移除动画资源，请关闭游戏并运行 `Uninstall-native-melee.cmd`，随后移除本集合的加载顺序项和模组目录。安装器只移除受管理的动画资源登记和文件，保留其他资源登记。旧 HCM 安装记录由随附的旧版卸载路径处理；它按原记录恢复以前的外部词条。若不再需要恢复出的旧词条，可在 HCM 外部包管理中停用它。

### 目录与接口

- `src/HavocConditionPacks/diy/packages`：直接加载的词条源码。
- `src/HavocConditionPacks/diy/index.json`：声明随附的词条包 ID。
- `src/HavocConditionPacks/native-melee`：动画补丁、校验清单、资源安装器和旧安装卸载兼容代码。
- `tools`：动画格式读取、修改与离线重建代码；不会写入游戏文件。
- `tests`：近战时序、动画变量、任务清理与安装回退验证。

独立词条集合通过 HCM 的 `diy_api.register_package_source("HavocConditionPacks")` 注册自己的声明目录；卸载集合时调用 `unregister_package_source`。注册不勾选效果，不改变当前任务的冻结快照，不执行包内 Lua；只有已选词条进入任务时才执行其生命周期。

### 源码与验证

[HCM 公开源码仓库](https://github.com/Darktide-mod/HavocConditionManager) 提供加载器及 DIY 接口实现；[本仓库](https://github.com/Darktide-mod/HavocConditionPacks) 提供集合、安装器和资源重建代码。

把本仓库与 HCM 仓库放在同一父目录。验证使用 Python、LuaJIT 的 Lupa、Windows PowerShell、本机暗潮原始资源及对应游戏 Lua 源码。原始游戏文件、游戏 DLL、用户配置和运行日志不随仓库分发。`HCM_PROJECT`、`DARKTIDE_GAME`、`DARKTIDE_SOURCE`、`DARKTIDE_DEV_SUPPORT` 可覆盖默认开发路径。

`python tools/rebuild.py` 只从已安装游戏读取受验证的原始资源，在 `build/rebuilt` 重建补丁并核对发行指纹。`python tests/run.py` 运行检查。测试中的旧版异常对照读取相邻 HCM 仓库保留的旧发行包。`python tools/release.py` 按 `publishing/release.json` 生成发布包，保留已有发布。这里的离线验证不能替代游戏内整局测试。游戏系统及资源归 Fatshark 所有，格式参考代码及许可保留在 `tools/vendor`；游戏 Lua 源码参考 Aussiemon/Darktide-Source-Code。

## English

HavocConditionPacks is an optional DIY condition collection for HavocConditionManager (HCM). It distributes conditions that need additional animation resources. The current condition, Frenzied assault, increases ordinary enemy melee attack and animation speed by 20%, with matching hit, combo, sweep and action timings. It supports local solo/bot sessions only; two unmatched boss combos retain native behavior.

HCM manages conditions and overall intensity. Its built-in No healing condition and external DIY loading work without this collection. This r2 revision updates documentation only: the mod remains 1.0.0, and Frenzied assault remains 2.2.1 with a 20% increase.

### Installation

Download `HavocConditionPacks-1.0.0.zip` from [Releases](https://github.com/Darktide-mod/HavocConditionPacks/releases). GitHub's `Source code (zip)` contains development files and historical releases; it is not an installation package.

1. Install [HavocConditionManager](https://github.com/Darktide-mod/HavocConditionManager/releases) 4.5.0 or later and its required dependencies.
2. Place the archive's `HavocConditionPacks` folder under the game's `mods` directory. Add `HavocConditionPacks` to `mods/mod_load_order.txt`, after `HavocConditionManager`.
3. For the first animation-resource installation, close Darktide and run `Install-native-melee.cmd` inside the collection folder. The installer checks game and resource fingerprints, then installs animation patches and their resource registration. It does not extract or copy DIY condition files and stops if fingerprints do not match.
4. Start the game. HCM reads the collection's `diy/packages` directory directly. Select Frenzied assault on HCM's Conditions page.

HCM's own installation package contains none of this collection's CMD/PowerShell installers or binary animation patches. Separate distribution does not establish Nexus scanning approval.

If an older HCM installation already installed identical animation resources, the installer verifies and reuses them while preserving the old installation and rollback records. Older AppData condition files also remain on disk. For the same package ID, the collection takes precedence and the older copy does not load twice. Other external DIY packages retain their location under `%APPDATA%/Fatshark/Darktide/HavocConditionManager/diy/packages`.

### Updates and removal

After a JSON/Lua update, refresh HCM in the hub. The next mission uses the new files; an active mission retains its starting snapshot. Animation-resource changes require installing with the game closed, then restarting it.

To remove animation resources, close the game and run `Uninstall-native-melee.cmd`, then remove the collection from the load order and delete its mod folder. The installer handles only its managed resources and preserves other resource registrations. For an older HCM installation, the original records also restore the previous external condition files. Disable that package in HCM if you no longer need it.

### Files and author interface

- `src/HavocConditionPacks/diy/packages` contains condition sources; `diy/index.json` lists the included package IDs.
- `src/HavocConditionPacks/native-melee` contains 54 animation patches, checksums, the installer and legacy removal support.
- `tools` contains offline rebuild tools, and `tests` checks melee timings, animation variables, lifecycle and installation rollback.

The collection registers its declared directory through HCM's `diy_api.register_package_source("HavocConditionPacks")` and removes that registration through `unregister_package_source`. Registration reads and validates packages without executing their Lua, selecting effects or changing active mission snapshots. Selected conditions run their lifecycle when a mission starts.

### Source code and development checks

The [public HCM repository](https://github.com/Darktide-mod/HavocConditionManager) contains the loader and DIY interfaces. [This repository](https://github.com/Darktide-mod/HavocConditionPacks) contains the collection, installers and resource rebuild code.

Place the two repositories under the same parent directory. Development checks need Python, the LuaJIT build of Lupa, Windows PowerShell, locally installed Darktide resources and matching game Lua sources. Set `HCM_PROJECT`, `DARKTIDE_GAME`, `DARKTIDE_SOURCE` and `DARKTIDE_DEV_SUPPORT` to override dependency paths. Game DLLs, complete original resources, user settings and logs are not distributed here.

Run `python tools/rebuild.py` to read the installed game's original resources, rebuild patches under `build/rebuilt` and verify their fingerprints without changing game files. `python tests/run.py` runs the checks. Historical regression checks read older releases in the adjacent HCM repository. `python tools/release.py` builds the release configured in `publishing/release.json` and preserves existing releases. Offline checks do not replace in-game tests.

Game systems and resources belong to Fatshark. Format reference code and its license are retained under `tools/vendor`; the game Lua source reference is Aussiemon/Darktide-Source-Code.
