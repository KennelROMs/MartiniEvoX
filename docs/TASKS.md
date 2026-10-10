# 任务与问题台账

更新：2026-10-08。状态为 `TODO`、`IN_PROGRESS`、`PENDING_VALIDATION`、`BLOCKED`、
`DONE`；DONE必须有相应范围的验证记录。提交说明使用任务ID，记录见 `git log`。

最终交付见 [ROADMAP](ROADMAP.md)：一个普通版ROM + 一个配对的KernelSU Next `boot.img`。
**实机验证统一放在全部工作完成之后**，步骤见 [DEVICE-VALIDATION](DEVICE-VALIDATION.md)；
因此需要实机的验收项在此之前只能到 `PENDING_VALIDATION`。

## 控制仓库与上游同步

| ID | 状态 | 交付/验收 | 记录与下一动作 |
| --- | --- | --- | --- |
| REPO-01 | DONE | 公开边界、原创许可、唯一接手入口与本地Git | 基线提交`fd506e5` |
| REPO-02 | DONE | 历史候选的便携锁、补丁清单、普通profile | `20260930`锁与基线保留为历史记录 |
| REPO-03 | DONE | 最小重建脚本及关键功能测试 | `tools/rebuild.py` |
| REPO-04 | DONE | 本地提交与干净clone功能验证 | evidence/control-repository-20261001.json |
| REPO-05 | DONE | 从控制提交实际同步/重建/归档ROM | `7d060c8`：全新init→update→prepare→build，构建与归档成功；见evidence/build-20261001.json（实机属OTA-01/PIXEL-02） |
| SYNC-01 | DONE | 跟随上游的锁刷新 | `tools/refresh_lock.py`；首个刷新锁`20261001-upstream`（1268项目），全部补丁在真实源码上`prepare`通过；2026-10-08刷新为`20261008`（1269项目），基础变化的vendor/lineage与frameworks/base补丁经`git apply --check`通过 |
| SRC-01 | DONE | SettingsGoogle外部输入 | 上游SettingsGoogle已含同一修复（文件SHA256一致），当前锁无外部输入；历史bundle描述保留 |
| LIC-01 | DONE | 公开范围与第三方边界 | 见PROVENANCE；PixelOS所用OnePlus公开blob经维护者确认可取用 |

## 功能

| ID | 状态 | 交付/验收 | 记录与下一动作 |
| --- | --- | --- | --- |
| PIXEL-01 | DONE | 完整差异/来源/依赖台账 | [PIXELOS](PIXELOS.md)，逐项结论 |
| PIXEL-02 | PENDING_VALIDATION | 可行项整合及范围内验证 | 已进入交付ROM并构建成功；实机检查见DEVICE-VALIDATION第2节 |
| KSU-01 | DONE | legacy源码、手动hooks、兼容回移植 | legacy `cd739c78`；独立编译通过；evidence/ksu-kernel-compile-20261001.json |
| KSU-02 | PENDING_VALIDATION | 与普通ROM配对的KSU `boot.img` | 已构建；CRC一致、boot仅内核不同；实机临时启动与授权/拒绝见DEVICE-VALIDATION第4节 |
| OTA-01 | PENDING_VALIDATION | OTA包与升级验证 | 离线：整包与payload签名、错误密钥拒绝、设备断言/SPL/时间戳均通过；`tools/ota_json.py`生成Updater条目；实机升级待最终阶段 |
| FIX-01 | IN_PROGRESS | 集中修复开放问题并回归 | 2026-10-05维护者回报此前问题均已解决；ISSUE-DISPLAY-02的修正（20261005版）2026-10-08实机确认生效；2026-10-09新增ISSUE-SIM-01、ISSUE-USB-01（20261009版实机生效）；2026-10-10新增ISSUE-DISPLAY-03 |
| CRAVE-01 | IN_PROGRESS | 以crave.io取代自有构建服务器，产物发布到SourceForge | `tools/crave.sh`（构建、配对核对、上传、Updater条目）与`ota/0001`（Updater指向本仓库`ota/martini.json`）已完成，离线测试通过；待维护者给出crave基础项目和SourceForge项目后试编，对照20261005版核对OTA证书与模块CRC，通过后再停用Hetzner |
| DELIVERY-01 | TODO | 发布前同步上游、最终构建、发布说明 | 维护者决定（2026-10-08）：控制仓库公开于KennelROMs/MartiniEvoX；ROM在crave.io构建、沿用现有签名私钥（仅放crave工作区）；ZIP托管SourceForge，Updater JSON放公开GitHub。构建与上传见CRAVE-01 |

## 问题

| ID | 状态 | 已知事实 | 下一动作 |
| --- | --- | --- | --- |
| ISSUE-DISPLAY-01 | DONE | 配置正确：peak 120、默认0、内容检测+4秒空闲计时器，空闲/60fps内容时回落60Hz属设计行为；Evo设置可把最低刷新率设为120 | 维护者日用回报已解决（2026-10-05） |
| ISSUE-CAMERA-01 | DONE | 整合的OplusCamera覆盖Aperture/Camera2；原0.9×最可能是Aperture把定焦微距镜头按焦距标为辅助镜头 | 维护者日用回报已解决（2026-10-05） |
| ISSUE-CAMERA-02 | DONE | 实机：OPlus Camera启动即崩溃，`ClassNotFoundException: com.oplus.util.OplusTypeCastingHelper` | 20261002版引入PixelOS frameworks/base兼容桩后，维护者实机确认相机完全正常（2026-10-03） |
| ISSUE-POWER-01 | DONE | 实机：libperfmgr正常运行（root dumpsys可见节点）；DisplayWakeup写`early_wakeup`遭DAC拒绝（节点root只写）；普通shell dumpsys因策略只认dumpstate fd而`FAILED_TRANSACTION`属预期 | 维护者日用回报已解决（2026-10-05，20261002版） |
| ISSUE-CHARGE-01 | DONE | 实机数据（原厂65W充电器，69%）：`voocchg_ing=1`、`fast_charge=1`、`fast_chg_type=0x14`、ADSP `fastchg ongoing`、`cool_down=0`；martini为双电芯串联（DTS `vbatt_num=2`），单芯4.45–4.49V已到恒压段，1.4–1.8A≈13–16W属正常尾段；`dumpsys battery`的5V/2A只是USB电源描述 | 维护者日用回报已解决（2026-10-05） |
| ISSUE-DISPLAY-02 | DONE | 实机：挖孔进度环比物理挖孔偏上几个像素。环（frameworks/base `cutoutprogress/ring/CutoutRingView`）以`config_mainBuiltInDisplayCutout`路径中心定位，该值来自PixelOS `60c876f`（圆心(98,67)、r 29；原LineageOS (99,68.5)、r 34）。维护者用Evolver进度环Y偏移标定为+1.0 dp（密度480，=+3 px）；`fixes/0002`把圆心改为(98,70)，半径不变 | 维护者实机确认20261005版的3 px下移生效（2026-10-08） |

重启、加密解锁、完整硬件矩阵、长期稳定性是**未验收项**，不是已确认缺陷。
AVB测试身份、未演练回退是**已知边界**。

## 每项任务的交接记录

完成或阻塞时补充：控制提交、修改路径、验证命令与退出状态、证据位置、已知局限、
下一项任务。原始设备日志不写进台账。
| ISSUE-SIM-01 | DONE | 实机（20261005版）：双SIM有时只显示一张且无法启用，`gsm.sim.state=ABSENT,ABSENT`，isub在开机后READY约1 ms即翻为ABSENT；modem已注册，重新插拔卡托可能恢复；PixelOS 16.1无此问题。对照：vendor radio HAL集合（IRadio@1.5、IRadioConfig@1.1、uim）、qcril blob与radio属性与PixelOS 16.1一致；UiccController/UiccSlot/RadioConfig与AOSP 17完全相同。Evolution X保留2022年提交`f4b07ee`，在`responseIccCardStatus_1_5`把HAL的`physicalSlotId`覆盖为无效值，卡状态路径只能按phoneId猜槽位；Android 17新增且本构建为ENABLED/READ_ONLY的`slot_port_switch_failure_fix`在槽位/phoneId对应与槽状态路径不一致时对旧phoneId执行`updateCardStateAbsent`。AOSP、LineageOS 24与PixelOS均无此覆盖。`fixes/0003`删除这两行，用HAL报告的物理槽位 | 维护者2026-10-10回报20261009版双卡修正生效；2026-10-09实机日志已证实：槽状态为物理槽0→logicalSlotIndex=1、物理槽1→0（交叉），卡状态两卡均`physicalSlotIndex=-1`，随后两次`phoneId is remapped for the port but CARDSTATE_ABSENT is not received`，62 ms后phoneId 1、0依次`updateSimState ABSENT`。20261009版已构建待实机：确认phone-0卡状态为`physicalSlotIndex=1`、无remapped日志、双卡可识别启用。`SET_SIGNAL_STRENGTH_REPORTING_CRITERIA`错误44来自Evolution X按条拆分HIDL请求，与SIM状态无关，另行处理 |
| ISSUE-USB-01 | DONE | 实机（20261005版）：C-to-C直连Mac约29 s断开USB、2–3 min后重连循环；A-to-C（SDP）稳定。dmesg证实：ADSP对带PD合约的USB主机报USB类型17（新版OPLUS驱动的`POWER_SUPPLY_USB_TYPE_PD_SDP`），本内核的OPLUS驱动不认识，`opchg_get_charger_type()`归为DCP（`charger_type[5]`）；`oplus_chg_fast_switch_check`对DCP尝试VOOC约30 s后进入`RESET_MCU_DELAY_30S`并`enable_qc_detect()`，HVDCP检测驱动D+/D-，10 ms后`USB_STATE=DISCONNECTED`。`fixes/0004`（两份内核）按OPLUS新版驱动（PixelOS seventeen所用）引入PD_SDP类型：数据侧按USB口在线，输入电流用`input_current_charger_ma`（2000 mA，非SDP的500 mA），不进入只针对DCP的VOOC/QC检测；另让usb_type属性回报SDP（未知类型原先使整个power_supply uevent读取失败，PixelOS未处理） | 维护者2026-10-10回报20261009版C-to-C修正生效；20261009版已构建待实机：C-to-C直连30 min无断开、接电脑充电约5 V/2 A。此前recovery经C-to-C sideload的Error 9可能同源 |
| ISSUE-DISPLAY-03 | PENDING_VALIDATION | 实机（20261009版）：重启后第一次解锁明显掉帧，熄屏亮屏后立即流畅。SurfaceFlinger/HWC全程120 Hz、无投票限制；开机后71–111 s负载低时稳定每秒约60次missed frame（120 Hz下隔帧丢），熄屏亮屏后约0。dmesg：开机7.22 s首次`dsi_display_set_mode fps=120`只发`post-panel-on-command`，无`timing-switch-command`；熄屏亮屏时60→120均发送。原因：bootloader以`timing@0`（60 Hz）点亮命令模式面板，OPLUS在`dsi_drm.c`于cont splash期间清除DMS，且`dsi_display_enable()`的splash分支提前返回，面板内部停在60 Hz TE而MDP按120 Hz运行。LineageOS与PixelOS内核均含该OPLUS代码。`fixes/0005`（两份内核）：splash分支记录首个模式与splash（preferred）模式刷新率不同，于`post_enable`补发post-mode-switch与timing-switch；编译通过 | 新构建后开机首次解锁即流畅，dmesg出现`splash timing differs, switching to 120 fps`；`/proc/cmdline`的`msm_drm.dsi_display0`无`:timingN`（2026-10-10维护者确认），splash模式即`timing@0` 60 Hz，判断成立 |
