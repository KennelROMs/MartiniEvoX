# MartiniEvoX

OnePlus 9RT（MT2110 / martini）的 **Evolution X Android 17 控制仓库**。
保存源码锁、适配补丁、最小构建入口及工作进度；不存整棵Android源码、out、私钥和ROM。

## 接手入口

- [当前状态](docs/STATUS.md)：当前候选、已验证范围、已知问题。
- [任务台账](docs/TASKS.md)与[路线图](docs/ROADMAP.md)：下一步做什么、完成标准。
- [构建说明](docs/BUILDING.md)：固定输入、外部材料及构建命令。
- [Agent规则](AGENTS.md)：最简设计、功能相关测试、适度核查。
- [来源与许可](docs/PROVENANCE.md)：Apache-2.0范围和第三方材料边界。

**顺序：Git仓库 → KernelSU Next → PixelOS增强 → OTA → 集中修复 → 剩余交付。**
当前主ROM默认普通内核，KSU Next后续作为匹配版本的可选配套。

## 使用

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
python3 tools/rebuild.py --help
```

重建通过一个脚本完成源码准备、补丁应用和构建，具体前提与参数见
[BUILDING](docs/BUILDING.md)。真实构建需要有足够资源的Linux机器、Repo/Git LFS、
Android主机依赖和外部签名材料，不在小型控制机上自动进行。

历史SettingsGoogle源码及原补丁未确认再分发许可，**不在Git中**；合法持有者需显式
提供其固定哈希对应的材料。详情见 [sources/README](sources/README.md)。
有构建入口不等于已完成从此Git版本的真实重建；验收状态以STATUS为准。

## 许可

新增原创控制代码、配置和文档采用 [Apache-2.0](LICENSE)。第三方原许可按
[NOTICE](NOTICE)保留；这不授权重分发Google/OPlus专有组件。
当前仅建立本地Git仓库，未自动创建远端、推送或公开发布。
