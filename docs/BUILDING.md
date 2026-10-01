# 构建说明

此仓库提供固定输入和最小重建脚本，不是预装好几百GB源码的环境。
先查看 [STATUS](STATUS.md)：本仓库的真实ROM重建和OTA验收仍需独立记录。

## 前提

- Linux x86-64，Git、Repo、Git LFS、Python3、GNU Make及Android构建主机依赖。
- 历史成功环境是Debian13、约64GiB内存；新工作区按至少600GB可用空间准备。
  编译使用源码自带JDK/Clang；归档需要tar和zstd，证书检查需要openssl。
- CONTROL是这个小Git仓库；SOURCE、OUT、ARTIFACTS在CONTROL之外。不要把源码同步进这里。
- 合法持有者提供SettingsGoogle旧源码bundle和原始补丁。固定身份见
  [恢复描述](../sources/settings-google.json)，脚本不替你取得再分发许可。
- 自己的完整签名材料按官方模板放在 `SOURCE/vendor/evolution-priv/keys`，不入控制Git。
  模板为 `Evolution-X/vendor_evolution-priv_keys-template`，固定提交
  `fed6526d27440d6c1317b465ea399a287313ba19`。自行审查模板后生成或恢复密钥，
  不在已有密钥上重新生成。脚本不会自动生成、覆盖或打印私钥。

`release`须匹配仓库记录的项目OTA公钥；`self-build`使用自己的身份，不承诺保数据
升级现有安装。全部APK签名连续性、AVB和OTA实机兼容仍是独立事项。

## 三步重建

先提交/固定CONTROL版本。以下变量由构建者指定，不能照搬另一台机器的私有目录：

```sh
CONTROL="$PWD"
SOURCE="$HOME/android/martini/source"
ARTIFACTS="$HOME/android/martini/artifacts"
# SETTINGS_BUNDLE、SETTINGS_PATCH 指向你合法持有的外部材料。
```

### 1. 初始化并同步固定源码

```sh
python3 "$CONTROL/tools/rebuild.py" init \
  --source "$SOURCE" --source-bundle "$SETTINGS_BUNDLE"
```

仅接受不存在或空的SOURCE，不覆盖已有树。使用
`manifests/locked/martini-20260930.xml`，不叠加浮动的`manifests/martini.xml`。
Settings恢复材料在checkout前以受限本地镜像接入，提交身份不变；其余项目和LFS
由Repo正常同步。若网络失败，保留现场，不自动清空工作区。

### 2. 应用固定补丁

```sh
python3 "$CONTROL/tools/rebuild.py" prepare \
  --source "$SOURCE" --settings-patch "$SETTINGS_PATCH"
```

核对基线、补丁哈希和工作树，先检查再应用：五份库内diff加一份外部Settings diff。
未知修改或部分应用时停止，不reset/clean。准备记录仅用于后续发现输入/工作树变化，
不代替构建与实机验证。已准备的树直接进入build，不盲目重复应用补丁。

### 3. 使用已有签名材料构建并归档

```sh
python3 "$CONTROL/tools/rebuild.py" build \
  --source "$SOURCE" --settings-patch "$SETTINGS_PATCH" \
  --artifacts "$ARTIFACTS" --signing self-build
```

普通目标固定为`lineage_martini-cp2a-userdebug`、`m evolution`，实际导出
`EVO_KEEP_TARGET_FILES=true`；默认OUT为SOURCE/out，显式更改时始终使用同一路径。
构建检查实际证书绑定，保留失败退出码和日志，不把tee成功当作构建成功。
成功后保存实际ZIP、原始target-files及构建记录到新的归档目录，不覆盖旧候选。

在上述任一命令末尾加 `--dry-run` 只显示计划，不联网、建目录或运行Android代码。
本机约27GiB可用，仅适合控制仓库工作；首次真实构建需另行确认服务器资源与窗口。

## 验收范围

- 离线测试验证脚本的实际关键行为和已有ROM补丁/配置，不以测试数量代表质量。
- `BUILT_AND_ARCHIVED_UNVALIDATED`只表示构建/归档成功，不冒充原生验签、首启或OTA通过。
- 新产物保存自己的哈希和身份，不要求ZIP等于历史a811…候选；原始META不能用旧文件替代。
- 本阶段不新增通用镜像审计框架。后续按实际需要使用源码原生工具做产物/OTA验证。
- 脚本不刷机、不格式化、不切槽、不重锁。失败先查看日志并定位，不自动弱化安全检查。
