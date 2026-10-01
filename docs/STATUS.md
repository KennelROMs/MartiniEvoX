# 当前状态

更新日期：2026-10-01。本文是当前状态入口；历史时间点的报告不能覆盖较新的
实机回报。状态变化同时更新 [任务台账](TASKS.md)，不得用未验证的推测填 PASS。

## 一句话定位

**手机运行首个工程候选`a8114027`。控制仓库已跟随上游刷新，PixelOS增强与KernelSU Next
补丁在真实源码上`prepare`通过；普通ROM正在构建服务器整包构建，随后构建配对的KSU boot。**
实机验证（KSU、PixelOS项、OTA、问题复核）统一放在全部工作完成之后。

## 当前手机候选

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

- 高刷新率疑似未生效：静态配置正确（peak 120、内容检测、4秒空闲回落60Hz），待实机区分
  设计行为与故障。
- 相机0.9×模糊：新构建由OplusCamera取代Aperture；原因最可能是Aperture对定焦微距镜头的
  标注，待实机确认。
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
| 当前锁 | `20261001-upstream`：Evolution-X清单`b3001cf`+本地清单，1268项目；`refresh_lock.py`生成 |
| SettingsGoogle外部输入 | 不再需要：上游已含同一修复；历史bundle描述保留 |
| 重建/同步脚本及离线回归 | `rebuild.py` init/update/prepare/build（`--kernel normal|ksu`）、`refresh_lock.py`；40项测试通过 |
| 新clone自足性 | 已通过：代码提交`3b34c18`，38项离线测试及build dry-run；见[记录](evidence/control-repository-20261001.json) |
| 从此Git提交实际重建ROM | IN_PROGRESS：全新`init`成功；`update`+`prepare`到当前锁成功；普通ROM构建中 |
| KSU Next内核 | 补丁与独立编译通过，普通/KSU导出CRC一致；配对boot待整包后构建 |
| 本次手机/OTA验证 | 未执行（按维护者安排放在最后） |

构建服务器：`~/martini/source`（SOURCE，OUT在其内的`out`与`out-ksu`），归档在
`~/martini/artifacts/run-*`。旧工作区`~/evo`待新构建成功后退役。
有GitHub私有远端，未推送或公开发布；手机写入由维护者操作。
