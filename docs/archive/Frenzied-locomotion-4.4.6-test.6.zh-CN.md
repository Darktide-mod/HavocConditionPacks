# 狂暴攻势：移动过渡与翻越修复

HCM **4.4.6-test.6**，词条包 **1.6.3**，Optional Files。保留常规移动、枪械、近战和特殊攻击 +100% 测试值；跨障碍动作改为原生时序。此轮仅生成发布产物，未写入游戏、Vortex 或 AppData 安装。

## 日志结论

最新日志为 `console-2026-09-12-07.14.29-6a5d1e6b-9b6e-45f2-ad28-6fcd6c10f620.log`。

- 第 503 行确认 HCM 4.4.6-test.5。
- 第 1892 行确认狂暴攻势 1.6.2 已激活，包自身移动倍率为 2，近战和远程属性加成为 +1。
- 第 2426 行有 5 个单位、12 个层通过动画时间读回检查；第 2427 行同次更新报告 38 个层恢复失败。
- 第 2433、2434 行记录当前近战总倍率 3.00、射击总倍率 2.30。原实现读取当前属性，包含本包及同时生效的原生加成。

本轮没有发现 HCM 脚本异常或版本切换拒绝。动画时间验证只证明部分层的播放点发生改变，不代表动画过渡、位移或终点判定正确；38 个失败层的日志没有单位和状态明细，无法据此定位截图中的每个敌人。

## 原因

旧动画同步使用 `set_time → set_animation → set_state` 在每帧恢复播放点。上轮对本机引擎的只读核查已确认，最后一步会清理并重建目标层，丢弃其旧的混合状态。即使 state 和 clip 编号没有变化，也不能证明混合已结束。这解释了时间提速有效而起停动作突兀的机制。此次回归补上“时间前进但过渡被清空”的反例，避免仅检查时钟便判定成功。

原生 `BtClimbAction` 和 `BtJumpAcrossAction` 会取得导航智能对象控制权，按入口、出口及障碍高度计算水平和垂直动画位移比例，随后按混合时点启用动画驱动，最后落位并释放导航。旧包把这些动作归入普通移动、缩短时序，并将计算出的 XYZ 位移再乘 2。动画层重建和额外位移倍增都会破坏这条流程；围栏下落尤其依赖当前位置和速度判断何时落地。

普通起步还存在一条反馈路径：原生 `MinionMovement.apply_animation_wanted_movement_speed` 从动画期望根位置算出速度，再交给导航。切换到原生动画提速后，这个速度已经包含播放提速，不能再次套用本包的导航倍率。

## 修改

- 走跑和移动过渡停止使用动画层恢复，改用原生 `anim_move_speed` 变量。保留起步、停止、转向与混合的原生时序。
- 记录原生变量写入，支持原生毒气、冲锋等路径的值更新；不把自身上次写入值当作新的基数。待机、受击反应、跨障碍和任务清理时恢复基数。
- 保留常规导航 +100%。原生移动播放不再叠加攻击路径的动画位移补偿；从动画计算出的起步速度会抵消本包在导航侧的重复倍增。
- 攀爬、翻越、跨沟和落地使用原生动作数据、位移比例及播放时钟。它们保持原速，完成后恢复普通移动提速。
- 攻击保留现有提速与同步路径。若某层恢复读回失败，同一状态/片段不再每帧重试；不同原生状态/片段可以重新尝试。此措施避免失败层被持续重建，不代表该层仍保证完整动画提速。
- 保留上一版的游戏内包更新；新任务替换本模组的回调，旧任务使用自己的快照。

## 原生依据

本机游戏源码使用 HEAD `0f0cb45991e9305ef4a7b925370792d7d6035f95`，读取 Git 中的原始版本，未修改原生源码。

- `scripts/extension_systems/behavior/nodes/actions/bt_melee_follow_target_action.lua`：移动变量、起步时间窗和动画根位置反馈。
- `scripts/extension_systems/animation/minion_animation_extension.lua`：移动变量设置、边界及网络同步接口。
- `scripts/extension_systems/behavior/nodes/actions/bt_climb_action.lua`、`bt_jump_across_action.lua`：障碍尺度、混合、下落、落地和结束流程。
- `scripts/extension_systems/navigation/minion_navigation_extension.lua`：智能对象控制权申请与释放。
- `scripts/utilities/minion_movement.lua`：动画期望位移换算为导航速度。

引擎文档将状态机变量用于控制动画行为，并区分状态恢复与手工 crossfade 播放接口。[Stingray 动画脚本接口](https://help.autodesk.com/cloudhelp/ENU/Stingray-Help/stingray_help/animation/script_interface.html)，[Clip State 播放速率](https://help.autodesk.com/cloudhelp/ENU/Stingray-Help/stingray_help/animation/animation_controllers/clip_state_properties.html)。这些文档不证明 Darktide 每个动画片段都使用同一个速度变量，因此画面效果仍需游戏验证。

## 验证与更新

回归使用真实 DMF 注册器和游戏原生动作代码，验证移动变量、走跑停止的混合保留、起步速度不重复倍增、上台阶/围栏/跨沟的原生时序与 XYZ 比例、下落与落地、出口落位及导航控制释放。失败层连续十帧不再重建；改变状态后可恢复重试。既有 374 个近战事件、8 个投弹动作、枪械和变种人检查继续保留。

这些检查中的引擎动画和几何查询由离线替身提供，不能替代实机画面、复杂碰撞地形及联机客户端测试。

安装新 ZIP 后，在大厅点击「解压模板DIY词条」把外部包更新到 **1.6.3**，再开始下一局。直接更新外部包文件时点击「刷新包」。无需退出游戏。激活日志新增 `movement_animation=native_variable traversal=native attack_animation=layer_restore`，可用于确认已加载此实现。
