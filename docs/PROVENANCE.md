# 来源、许可与公开范围

维护者于2026-10-01选择：按可公开标准整理，新增原创控制代码、配置和文档采用
Apache-2.0。尚未创建远端或公开分发；[LICENSE](../LICENSE)不替代第三方原许可。

## 保留的材料

- 五份库内ROM diff、EROFS和target-files fixture保留LineageOS、Unlegacy-Android、
  AOSP及Linux Foundation原声明，见[NOTICE](../NOTICE)。不伪造作者/DCO。
- [补丁清单](../patches/series.json)和`baselines/`下各锁的基线保存
  仓库、提交与字节哈希。完整manifest只做已记录的remote规范化。
- Android、Linux、vendor、固件和GApps仍按各自条件取得；源码URL不是分发授权。

## SettingsGoogle外部输入

2026-10-01起，上游`vendor_google_apps_SettingsGoogle`的collector文件与此前外部补丁的结果
逐字节相同，当前锁直接使用上游，不再需要下列外部输入。以下内容只适用于历史候选`20260930`。

未找到覆盖历史bundle和collector源码的明确再分发许可。维护者确认采用
**公开控制仓库＋外部输入**，不把bundle、原补丁或完整源码fixture纳入Git。
其他文件上的Apache头不能自动覆盖这些内容。

合法持有者显式提供 `--source-bundle`、`--settings-patch`，按
[恢复描述](../sources/settings-google.json)检查固定身份。该检查不产生再分发授权；
公共获取缺口仍标BLOCKED，不虚构下载地址或换用新的上游提交。

原始对象和修复等价性已在维护者环境检查，见
[验证摘要](evidence/settings-private-validation-20261001.json)。公开功能测试只使用
自有临时数据测试实际构建脚本，不复制原始源码、不为测试数量添加合成演练。

## 历史证据

原始历史报告、研究、旧方案及日志留在本机，未经审查不收入公共历史，原件未改。
公开摘要分别注明来源：

- [首启](evidence/first-boot-20261001.json)：用户提供的结果，不是本控制机直接连接。
- [候选构建](evidence/candidate-20260930.json)：历史服务器验证，不是本次Git重建。

本轮不交付通用审计框架。暂未启用的扩展验证器及依赖测试保留在本机草稿区，
不属于当前构建入口，也不计入公共功能测试结果。

## 公开签名身份

[release-info.json](../certificates/release-info.json)及两份PEM仅含公开证书/公钥，
已检查SPKI一致，subject是通用Android模板，不是维护者个人身份或Google授权。

- OTA证书DER SHA256：`d6310c4135f42e1cb4087d6a21c88d3f8d5c04f89e7db0ef1e08a2122b41f9af`
- 公钥SPKI DER SHA256：`5a34b5891d03033f4bdc30e37375c51051e41e1ced2b0eab7c8392184856966a`

这不是完整APK密钥集或AVB身份。私钥外置；self-build不承诺保数据升级既有安装。

## 提交边界

显式暂存、查看差异，检查许可、凭据、设备标识和大文件即可；不引入通用扫描框架。
原始`recovery.log`、Settings原材料、私有配置、密钥、完整ROM和target-files均被排除。
创建远端、推送和分发仍需明确授权。
