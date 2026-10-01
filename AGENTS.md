# 接手规则

先读 `README.md`、`docs/STATUS.md`、`docs/TASKS.md`；构建前再读
`docs/BUILDING.md`。`docs/ROADMAP.md`记录已确定的后续顺序。

## 设计与执行标准

- **以满足当前需求的最简设计为准，禁止过度设计。** 不为假设中的未来需要增加框架。
- 测试只覆盖实际程序功能和关键失败路径，不为测试数量添加用例。
- 做适度的一轮核查；出现具体问题再定点修复，不自动安排多层、多轮复核。
- 复用已确认事实，不重复进行大规模盘点。任务完成后更新状态、验证结果和下一动作。

## 项目边界

这是控制仓库，不是完整Android源码树。源码、out、私钥、大产物在仓库外。
冻结输入由 `manifests/locked/`、`baselines/`、`profiles/`、`patches/series.json` 描述。
主ROM使用普通内核；KSU Next是版本匹配的可选配套，不预设只有boot.img。

顺序固定为 **Git仓库 → KernelSU Next → PixelOS增强 → OTA → 集中修复 → 剩余交付**。
不要重新把完整无Root日用验收设为KSU前置条件；但启动、数据安全和验证阻塞必须处理。

SettingsGoogle bundle与原补丁是显式外部输入，许可未确认材料不得偷偷收入公共Git。
私钥、原始设备日志和本机历史材料不入库；顶层Apache-2.0不覆盖第三方原许可。

## 常用命令

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
python3 tools/rebuild.py --help
```

首次完整ROM重建、原生验签、实机和OTA是不同验收层；未执行的明确标未验证。
不自动reset/clean/force-sync，不覆盖未知工作区或密钥，不关闭安全检查制造成功。
刷机、格式化、切槽、固件降级和重锁均不由构建任务授权。

提交前使用任务分支，显式暂存并查看差异。只在维护者授权范围内提交；不自动创建远端、
推送或发布。提交末尾使用：

```text
Co-Authored-By: Claude Code <noreply@anthropic.com>
```
