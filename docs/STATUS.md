# 当前状态

更新日期：2026-10-10。本文是当前状态入口；历史时间点的报告不能覆盖较新的
实机回报。状态变化同时更新 [任务台账](TASKS.md)，不得用未验证的推测填 PASS。

## 一句话定位

**交付物（控制`72c9836`，20261005版）已构建：整合PixelOS增强、跟随上游的普通ROM，以及配对的
KernelSU Next `boot.img`；离线OTA签名与元数据核对通过。维护者已日用数日，此前登记的问题
（高刷、相机、电源HAL节点、快充）均回报已解决。20261005版修正挖孔进度环偏上（ISSUE-DISPLAY-02），已实机确认生效；
尚无记录的是OTA保数据升级等验收层。**

## 当前交付物（未实机验证）

| 产物 | SHA256 | 归档（构建服务器 `~/martini/artifacts/`） |
| --- | --- | --- |
| `EvolutionX-17.0-20261010-martini-12.3-Unofficial.zip`（3741208017字节） | `1fac2c5f7250ce5ea974265142254d642b97dc44aed27e3e9692bd8ffe3ed613` | `run-20261010T030733Z-cqe359ju`（含target-files） |
| `EvolutionX-17.0-20261010-martini-12.3-Unofficial-ksu-boot.img` | `cc2fd613f292523a47b9317ccc8b1b173a49de99e9765b8226735550cc12dc56` | `run-20261010T032659Z-uacan9q7` |

20261010版（控制`a52c187`，锁`20261008`）在20261009版上只加`fixes/0005`（ISSUE-DISPLAY-03）；两份内核源码与
`msm_drm.ko`均含该修正，OTA证书与验签结果同前，模块CRC一致（14610项），post-timestamp晚于20261009版，
见[记录](evidence/build-20261010.json)。尚未发布；2026-10-10维护者实机回报开机掉帧修正生效。
上一版20261009（控制`1409caf`，锁`20261008`）为早测版：含ISSUE-SIM-01与ISSUE-USB-01修正及Updater地址，
OTA证书同前、整包与payload对项目证书验签通过、对AOSP测试证书拒绝，模块CRC一致（14610项），
post-timestamp晚于20261005版，ZIP `664a74ae…`、KSU boot `b489c803…`，见[记录](evidence/build-20261009.json)。2026-10-10维护者实机回报双卡与C-to-C修正生效。
上一版20261005（控制`72c9836`）：ZIP `fa61b1b1…`、KSU boot `fe8a967f…`，见[记录](evidence/build-20261005.json)。

20261002版（控制`b394ff9`）修复实机发现的OPlus Camera启动崩溃与DisplayWakeup节点权限，见
[记录](evidence/build-20261002.json)。20261001版已实机验证：KSU内核、高刷、SELinux Enforcing、
相机以外的PixelOS增强符合预期。2026-10-05维护者回报：20261002版日用数日，此前问题均已解决。
20261005版（控制`72c9836`）只把挖孔圆心下移3 px，2026-10-08维护者实机确认生效，见[记录](evidence/build-20261005.json)；
ODM overlay已含新路径，模块CRC一致（14610项），OTA验签同前，post-timestamp晚于20261002版。

两者内核模块CRC一致（14610项），boot仅内核不同；OTA证书与`a8114027`相同，payload对项目公钥
验签通过、对错误密钥拒绝，post-timestamp晚于候选。详见[构建记录](evidence/build-20261001.json)。

## 历史首刷候选（`a8114027`）

| 项目 | 当前记录 |
| --- | --- |
| 设备 | OnePlus 9RT 国行 MT2110，martini；运行时别名 MT2111_IND |
| 包名 | `EvolutionX-17.0-20260930-martini-12.2-Unofficial.zip` |
| ZIP SHA256 | `a8114027f2a22ff1f16ef042a3fd4562487f03599844d9525d95e3668bfce9a8` |
| ZIP 字节数 | 3648582850 |
| 内核 | 普通内核，无 KSU；源码基线 `abd4ede9ec6463110b40360a4a772e1285e995dd` |
| 目标 | Android 17 / SDK 37，Full GApps |

同名旧包存在，不以文件名判断候选。新构建也不要求与上述 ZIP 字节相同；
它需要自己的构建记录、哈希、签名身份和配套镜像。

## 已有证据及范围

| 结论 | 证据类型 | 边界 |
| --- | --- | --- |
| 完整构建、target-files归档与有限静态验收通过 | 2026-09-30 历史服务器记录 | 不是本次从Git干净重建 |
| Recovery、完整sideload、设置向导/桌面成功 | 用户实机回报 | 不是OTA后续升级验证 |
| Android17/SDK37、A槽、boot_completed=1 | 2026-10-01 用户提供的运行时结果 | 本控制机未直接连接手机 |
| SELinux Enforcing | 同上 | 不扩大为完整安全认证 |
| 六项只读分区EROFS、ro挂载 | 同上 | 不等于全部存储/升级场景通过 |
| 原控制回归38/38通过 | 仓库工程化前的本地实跑 | 新工具与新clone需另行验收 |

公开摘要：[首启记录](evidence/first-boot-20261001.json)、
[候选构建记录](evidence/candidate-20260930.json)。摘要不是重新生成的原始终端日志。

## 尚未通过或存在问题

- 正常重启/冷启动、设置密码后的解锁、完整硬件矩阵、长期待机/温控未验收。
- OTA/snapshot、保留数据的升级和可选KSU升级行为未验证。
- 旧PixelOS回退材料已有准备记录，但未实测回退；另一槽不是保证可用备份。
- AVB仍为基线公开测试公钥及top flags=3；自有APK/OTA签名不改变此边界。

Error 9 在更换原装A-to-C后成功安装，本轮排障已收口；不为此重新修改签名、
SELinux或要求回到Recovery，也不推断所有C-to-C均不可用。

## 控制仓库建设进度

| 验收层 | 当前状态 |
| --- | --- |
| 本地Git初始化与工作分支 | 已完成；版本记录以`git log`为准 |
| 当前文档、公开范围、原创Apache-2.0 | 已完成；基线提交`fd506e5` |
| 历史候选锁/补丁序列 | 已完成：`20260930`锁（1262项目）保留为历史记录 |
| 当前锁 | `20261008`：Evolution-X清单`8e41c89`+本地清单，1269项目；`refresh_lock.py`生成。上一锁`20261001-upstream`（20261005版所用）因上游删除`system_memory_libdmabufheap`与ThemeIcons的`cnb`分支已无法完整同步 |
| SettingsGoogle外部输入 | 不再需要：上游已含同一修复；历史bundle描述保留 |
| 重建/同步脚本及离线回归 | `rebuild.py` init/update/prepare/build（`--kernel normal|ksu`）、`refresh_lock.py`、`crave.sh`；44项测试通过 |
| 新clone自足性 | 已通过：代码提交`3b34c18`，38项离线测试及build dry-run；见[记录](evidence/control-repository-20261001.json) |
| 从此Git提交实际重建ROM | 已构建并归档（`BUILT_AND_ARCHIVED_UNVALIDATED`）：全新init→update→prepare→build |
| KSU Next内核 | 配对boot已构建；CRC一致；未实机 |
| 本次手机/OTA验证 | 20261002版已日用、问题复核通过（维护者回报）；OTA保数据升级无记录 |

构建服务器：`~/martini/source`（SOURCE，OUT在其内的`out`与`out-ksu`），归档在
`~/martini/artifacts/run-*`。旧工作区`~/evo`已在核对密钥一致后删除。构建正迁往crave.io、产物发布到
SourceForge（CRAVE-01）；crave试编通过前保留此服务器。
控制仓库公开于<https://github.com/KennelROMs/MartiniEvoX>（2026-10-08）；ROM产物尚未公开发布；手机写入由维护者操作。
