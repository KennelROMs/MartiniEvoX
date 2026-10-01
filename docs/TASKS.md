# 任务与问题台账

更新：2026-10-01。状态为 `TODO`、`IN_PROGRESS`、`PENDING_VALIDATION`、`BLOCKED`、
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
| REPO-05 | IN_PROGRESS | 从控制提交实际同步/重建/归档ROM | 构建服务器全新`init`成功（`e24b1f8`锁）；`update`到上游刷新锁后`prepare`通过，普通ROM构建中 |
| SYNC-01 | DONE | 跟随上游的锁刷新 | `tools/refresh_lock.py`；首个刷新锁`20261001-upstream`（1268项目），全部补丁在真实源码上`prepare`通过 |
| SRC-01 | DONE | SettingsGoogle外部输入 | 上游SettingsGoogle已含同一修复（文件SHA256一致），当前锁无外部输入；历史bundle描述保留 |
| LIC-01 | DONE | 公开范围与第三方边界 | 见PROVENANCE；PixelOS所用OnePlus公开blob经维护者确认可取用 |

## 功能

| ID | 状态 | 交付/验收 | 记录与下一动作 |
| --- | --- | --- | --- |
| PIXEL-01 | DONE | 完整差异/来源/依赖台账 | [PIXELOS](PIXELOS.md)，逐项结论 |
| PIXEL-02 | IN_PROGRESS | 可行项整合及范围内验证 | 补丁与锁已进入当前序列；整包构建中；实机检查待最终阶段 |
| KSU-01 | DONE | legacy源码、手动hooks、兼容回移植 | legacy `cd739c78`；独立编译通过；evidence/ksu-kernel-compile-20261001.json |
| KSU-02 | IN_PROGRESS | 与普通ROM配对的KSU `boot.img` | `--kernel ksu`只构建bootimage；加入PixelOS内核补丁后普通/KSU 14610个导出CRC仍一致；整包后构建 |
| OTA-01 | TODO | OTA包与升级验证 | 普通ROM构建后离线核对整包/payload签名与元数据；实机`a8114027`→新构建保数据升级待最终阶段 |
| FIX-01 | IN_PROGRESS | 集中修复开放问题并回归 | 见下方问题表 |
| DELIVERY-01 | TODO | 发布前同步上游、最终构建、发布说明 | Git推送与公开发布需另行授权 |

## 问题

| ID | 状态 | 已知事实 | 下一动作 |
| --- | --- | --- | --- |
| ISSUE-DISPLAY-01 | PENDING_VALIDATION | 配置正确：peak 120、默认0、内容检测+4秒空闲计时器，空闲/60fps内容时回落60Hz属设计行为；Evo设置可把最低刷新率设为120 | 实机`dumpsys display/SurfaceFlinger`区分设计行为与故障 |
| ISSUE-CAMERA-01 | PENDING_VALIDATION | 整合的OplusCamera覆盖Aperture/Camera2；原0.9×最可能是Aperture把定焦微距镜头按焦距标为辅助镜头 | 实机确认OPlus Camera各镜头；若仍有问题再收集`dumpsys media.camera` |

重启、加密解锁、完整硬件矩阵、长期稳定性是**未验收项**，不是已确认缺陷。
AVB测试身份、未演练回退是**已知边界**。

## 每项任务的交接记录

完成或阻塞时补充：控制提交、修改路径、验证命令与退出状态、证据位置、已知局限、
下一项任务。原始设备日志不写进台账。
