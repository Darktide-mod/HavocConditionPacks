# 狂暴攻势 1.6.1：动画时间恢复修复测试版

随 HavocConditionManager **4.4.6-test.4** 发布，类别为 **Optional Files**；稳定版继续为 **4.4.1**。本轮只生成发布文件，不修改当前游戏、Vortex 或 AppData 安装。

## 本轮日志结论

2026-09-12 14:13:26 启动的进程使用 HCM 4.4.6-test.3。14:15 和 14:16 开始的两局均为 Realms 本地监听主机，并成功激活狂暴攻势 1.6.0。外部 DIY 包在进程启动前已经更新；日志没有此前的版本保护失败，因此本次“移速生效、动画看起来仍为原速”不能归因于旧词条仍未更新。

两局分别出现 `animation_clock=running updated_units=6` 和 `updated_units=7`。旧实现是在调用动画时间写入接口后累计计数，并只打印整局第一次记录。它没有检查下一帧是否保留写入、画面姿态是否改变或播放周期是否缩短。该消息只说明相关调用执行过，不能证明动画实际提速，也不能证明攻击频率。

本轮详细日志行号、时间和安装文件哈希记录在工程审计报告 `docs/Frenzied-assault-animation-log-audit-20260912.zh-CN.md`。两个会话的动画表现尚没有可用的帧级测量。

## 已确认的原因与修复

本机引擎接口核查确认，`Unit.animation_set_time` 只把时间写入“待恢复”数据，并不直接改变 `animation_get_time` 读取的实时播放时间。旧实现只调用这一步，因此接口调用成功但画面仍沿原有时钟播放。旧离线测试错误地把此 setter 模拟成直接修改实时播放时间，掩盖了这个问题。

1.6.1 使用原版玩家动画恢复所采用的完整顺序：`set_time → set_animation → set_state`。最后一步会同步提交待恢复数据并重建指定层，之后可即时读回实时动画时间。并非单独换一个倍率或等待后续更新即可修复。

恢复在本帧 World 动画求值前执行，根据前一帧测得的原生时间增量推进仍在连续播放的层。状态、动画片段或循环发生变化时先重新采样，非目标层用 nil 跳过。实现不在并行动画回调中修改动画。

提交后的即时读回与本帧后续自然推进均通过检查，才会记录新的验证消息。详细引擎证据和边界见工程报告 `docs/Frenzied-engine-animation-contract-20260912.zh-CN.md`。

`set_state` 会重建对应层，包括同一个状态再次设置的情况。因此本修复仍需实机观察过渡混合、成对动作和动画进入事件，不能描述成“完全不重建状态”或“所有音画事件已保证同步”。


## 保留的测试倍率

| 项目 | 目标倍率 |
| --- | --- |
| 全体敌人移速 | 2.00 倍，提升 100% |
| 常规枪械攻速 | 2.00 倍，提升 100% |
| 近战攻击速度 | 2.00 倍，提升 100% |
| 投弹、扑咬、抓取、砸击等特殊动作 | 2.00 倍，提升 100% |
| 对应前摇、命中／释放时点、后摇、攻击冷却 | 原时长的 50% |

被动 `melee_attack_speed`、`ranged_attack_speed` 均为 +1.0；其他原生攻速增益继续按原生属性方式叠加。受击硬直、撞墙眩晕和原版围攻限制继续保留。表格给出测试目标和配置含义，并非实测动画或攻击频率。

## 更新已解压的词条

模组 ZIP 中的内置模板和 AppData 中已经解压的 DIY 实例是两份文件。仅更新 ZIP 不会替换已有外部实例。

1. 退出游戏，安装 HCM 4.4.6-test.4 ZIP。
2. 启动游戏，进入「DIY 管理」，点击「解压模板DIY词条」，将外部狂暴攻势更新为 **1.6.1**。同名旧包按原有流程保留备份。
3. 再次完全退出并重新启动游戏，确认已启用、勾选狂暴攻势，然后进入新任务。

默认外部实例位置为：

`%APPDATA%\Fatshark\Darktide\HavocConditionManager\diy\packages\starter-conditions-frenzied_assault`

应检查该目录 `package.json` 的 `package_version` 为 `1.6.1`，任务激活日志也显示 `[Frenzied assault 1.6.1]`。只看到 HCM 版本号不能证明外部词条已更新。更新脚本后需重启，让现有钩子和新词条使用同一版本；版本不一致时继续显示三语重启提示。

## 新版诊断消息

任务成功激活时，日志应包含：

```text
[Frenzied assault 1.6.1] move=2.00 melee=+1.00 ranged=+1.00 special=2.00 stagger=native animation=layer_restore scope=local_authority
```

观察到完整恢复生效且动画继续推进后，才会出现以下格式，数量由该次实际检查决定：

```text
animation_clock=verified restored_units=.. restored_layers=.. readback=live_clock phase=before_animation
```

这里的 verified 指抽样动画层的实时播放时间通过了读回和继续推进检查，不能扩大解释为画面质量、所有敌人或远端客户端都已验证。若恢复不能验证，会出现 `animation_clock=restore_failed`；这与旧版仅统计 setter 调用的 running 有明确区别。


此外，每局分别在原生近战和射击动作运行后各记录一次计时样本，格式如下；秒数来自当时品种和动作的原生运行数据：

```text
attack_timing=melee rate=2.00 first_hit_delay=.. action_end_delay=..
attack_timing=shoot rate=2.00 first_shot_delay=..
```

`first_hit_delay` 是该次近战计划开始伤害窗口或扫击的延迟，`action_end_delay` 是该次动作计划结束的延迟，`first_shot_delay` 是该次射击计划首次开火的延迟。它们可以独立于动画日志确认游戏采用的动作窗口；并不记录实际命中或伤害事件，也不能把一次首击延迟当成整套攻击频率。原版围攻许可和再次获得攻击机会的条件仍然生效。


## 验证边界

离线源码和回归检查不能代替游戏引擎实际渲染。敌人可见动画、根运动、声音事件、成对抓取动画和远端客户端仍需要实机复测；动作命中或发射的时间应与动画表现分别观察。本版继续作为测试文件发布。
