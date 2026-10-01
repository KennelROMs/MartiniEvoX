# 任务与问题台账

更新：2026-10-01。状态为 `TODO`、`IN_PROGRESS`、`PENDING_VALIDATION`、`BLOCKED`、
`DONE`；DONE必须有相应范围的验证记录。未分配未来任务的执行者不作推断。
提交记录可由 `git log --oneline --all` 查看；提交说明使用任务ID。

**下一项：KSU-02。** KSU-01已完成补丁与独立内核编译；REPO-05与KSU-02在构建服务器
同一棵新SOURCE上进行（普通与KSU各一个OUT）。未执行事项不写成通过。

## 控制仓库

| ID | 状态 | 交付/验收 | 阻塞与下一动作 |
| --- | --- | --- | --- |
| REPO-01 | DONE | 公开边界、原创许可、唯一接手入口与本地Git | 基线提交`fd506e5`；原始私密材料和草稿不入Git |
| REPO-02 | DONE | 1262项目便携锁、六步补丁清单、普通profile、外部恢复描述 | 数据合同9/9通过；独立公共恢复缺口仍见SRC-01 |
| REPO-03 | DONE | 一个最小重建脚本及关键功能测试 | `tools/rebuild.py`实现init/prepare/build；无通用审计/镜像验证框架，真实构建仍见REPO-05 |
| REPO-04 | DONE | 本地提交与一次干净clone功能验证 | `3b34c18`：38项测试通过、dry-run无写入；见evidence/control-repository-20261001.json |
| REPO-05 | IN_PROGRESS | 从控制提交实际同步/重建/归档/验收ROM | 构建服务器已确认。按`0e2348e`的init因Evolution-X改写分支、10个固定提交不在分支上而同步失败；新锁`martini-20261001`对Evolution-X项目按SHA浅获取，用`update`继续 |
| SRC-01 | BLOCKED | SettingsGoogle旧基线的合法、公开可获取恢复材料 | bundle对象已验证，整份分发许可不足；不入Git，记录外部受控输入 |
| LIC-01 | DONE | 确定本次公开范围与第三方边界 | Settings原材料外置，其他保留原声明；见PROVENANCE，未声称上游许可缺口已解决 |

## 后续功能与交付

| ID | 状态 | 交付/验收 | 下一动作 |
| --- | --- | --- | --- |
| KSU-01 | DONE | 固定legacy源码、手动hooks映射、兼容改动清单 | legacy `cd739c78`；8处手动hook+path_umount回移植；独立内核编译通过，86模块与14611个导出CRC同普通内核一致；见evidence/ksu-kernel-compile-20261001.json |
| KSU-02 | TODO | 可选内核、模块/镜像一致性与最小实机验收 | 完整KSU构建、dtb/dtbo/vendor_boot/vendor_dlkm对比；实机刷写由维护者操作 |
| PIXEL-01 | DONE | 完整差异/来源/许可/依赖台账 | 见[PIXELOS](PIXELOS.md)：每项给出集成/已有等效/无收益/不适用结论；维护者确认OnePlus公开blob可取用 |
| PIXEL-02 | IN_PROGRESS | 可行有价值项逐项集成及范围内验证 | 锁`martini-20261001-pixel`与9个补丁已在干净基线逐仓库检查通过；待完整构建与实机 |
| OTA-01 | TODO | 普通/KSU、同签名保数据升级与snapshot验证 | 依赖配套产物，专门设计升级/恢复场景 |
| FIX-01 | TODO | 集中修复开放问题并回归 | OTA阶段后集中收敛；阻塞/数据安全问题提前处理 |
| DELIVERY-01 | TODO | 剩余发布、可选CI、分发与长期维护 | 不在本阶段创建远端或公开发布 |

## 已知非阻塞问题

| ID | 状态 | 已有现象/证据 | 未确定的内容与验证需求 |
| --- | --- | --- | --- |
| ISSUE-DISPLAY-01 | TODO | 用户报告高刷疑似未生效 | 支持模式、系统限制、活动模式和App帧率；不直接判驱动缺失 |
| ISSUE-CAMERA-01 | TODO | 用户报告0.9×模糊 | App、Camera ID、镜头与焦距；微距解释未证实 |

重启、加密解锁、完整硬件矩阵、长期稳定性是**未验收项**，不是已确认缺陷。
AVB测试身份、未演练回退是**已知边界**，不能通过修改标签变成已解决问题。

## 每项任务的交接记录

完成或阻塞时补充：输入baseline/控制commit、修改路径、验证命令与退出状态、
证据位置、已知局限、下一项任务。原始设备日志不写进台账；公开摘要注明是用户回报
或维护者记录，不伪装为本机直接测量。
