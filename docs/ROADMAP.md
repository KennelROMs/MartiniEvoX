# 生效路线图

决策日期：2026-10-01（同日两次调整）。本文件替代历史规划中的“先完整无Root日用验收、
再增强”的优先级，以及先单独交付KSU的顺序。

执行标准：最简充分设计，只做实际功能相关测试，适度检查；不新增通用框架或反复复核。

## 最终交付

1. **一个普通版ROM**：Evolution X Android 17，整合PixelOS已有的martini增强，
   OTA升级经验证，集中修复已知问题。
2. **一个配对的KernelSU Next内核**：与该ROM同一提交、同一内核源码构建的`boot.img`。
   普通/KSU内核模块CRC一致，KSU用户只替换boot，vendor_boot/vendor_dlkm沿用ROM。

## 与上游保持同步

Evolution-X、LineageOS、TheMuppets、PixelOS与KernelSU Next均跟随上游分支。
`tools/refresh_lock.py`把当前上游固定为新锁；随后`rebuild.py update/prepare`在真实源码上
确认补丁仍可应用。上游已合入的补丁转为“已有等效”并从序列移除；冲突的补丁按上游现状重做。
PixelOS有新提交时，按[PIXELOS台账](PIXELOS.md)逐项补充结论。发布前做最后一次同步。

## 顺序

1. **PIXEL**：PixelOS增强按[台账](PIXELOS.md)整合（设备树、hardware/oplus、vendor、内核）。
2. **KSU**：KernelSU Next legacy手动hooks补丁始终叠加在最终内核之上，`--kernel ksu`只构建
   `bootimage`。按上游原生行为接入（维护者决定），不刻意移除selinux_hide、adb_root、
   avc_spoof；不额外加入SUSFS等第三方补丁。保持CFI、SELinux、MODVERSIONS。
3. **OTA**：离线核对OTA包、payload签名与证书；实机验证`a8114027`→新构建的同签名保数据
   升级（A/B、virtual A/B snapshot）。KSU用户OTA后内核回到普通版，需刷入新版本配对boot。
4. **FIX**：高刷新率、0.9×相机及新发现问题；先用源码/日志定位，最小修复并回归。
5. **交付**：发布前同步上游、最终构建（ROM+配对KSU boot）、发布说明与许可/隐私复核。
   Git推送、公开发布与付费服务分别授权。

**实机验证统一放在全部工作完成之后**（维护者决定），步骤见
[DEVICE-VALIDATION](DEVICE-VALIDATION.md)。构建任务不授权刷机、格式化、切槽或重锁。

## 所有阶段共有的底线

原始私钥、设备日志和大产物不入Git。未执行的验证明确写未验证，不把“构建成功”写成实机
通过。失败保留证据，不关闭安全检查以制造成功；无法启动、数据安全或阻塞后续验证的问题
优先处理。
