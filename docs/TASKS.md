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
| FIX-01 | DONE | 集中修复开放问题并回归 | 2026-10-05维护者回报此前问题均已解决；ISSUE-DISPLAY-02的修正（20261005版，evidence/build-20261005.json）2026-10-08实机确认生效；问题表无未结项 |
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
