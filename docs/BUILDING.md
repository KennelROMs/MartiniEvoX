# 构建说明

此仓库提供固定输入和最小重建脚本，不是预装好几百GB源码的环境。
先查看 [STATUS](STATUS.md)：本仓库的真实ROM重建和OTA验收仍需独立记录。

## 前提

- Linux x86-64，Git、Repo、Git LFS、Python3、GNU Make及Android构建主机依赖。
- 历史成功环境是Debian13、约64GiB内存；新工作区按至少600GB可用空间准备。
  编译使用源码自带JDK/Clang；归档需要tar和zstd，证书检查需要openssl。
- CONTROL是这个小Git仓库；SOURCE、OUT、ARTIFACTS在CONTROL之外。不要把源码同步进这里。
- 当前锁不需要外部源码输入：上游SettingsGoogle已含此前外置补丁的同一修复。历史候选
  `20260930`的bundle/补丁身份仍记录在[恢复描述](../sources/settings-google.json)。
- 自己的完整签名材料按官方模板放在 `SOURCE/vendor/evolution-priv/keys`，不入控制Git。
  模板为 `Evolution-X/vendor_evolution-priv_keys-template`，固定提交
  `fed6526d27440d6c1317b465ea399a287313ba19`。自行审查模板后生成或恢复密钥，
  不在已有密钥上重新生成。脚本不会自动生成、覆盖或打印私钥。

`release`须匹配仓库记录的项目OTA公钥；`self-build`使用自己的身份，不承诺保数据
升级现有安装。全部APK签名连续性、AVB和OTA实机兼容仍是独立事项。

## 三步重建

先提交/固定CONTROL版本，并让它位于本地分支上：`repo init -b <提交>`只在CONTROL的分支中查找该提交，
detached HEAD会报`revision ... not found`。以下变量由构建者指定，不能照搬另一台机器的私有目录：

```sh
CONTROL="$PWD"
SOURCE="$HOME/android/martini/source"
ARTIFACTS="$HOME/android/martini/artifacts"
```

### 1. 初始化并同步固定源码

```sh
python3 "$CONTROL/tools/rebuild.py" init --source "$SOURCE"
```

仅接受不存在或空的SOURCE，不覆盖已有树。使用profile指定的当前锁
（现为`manifests/locked/martini-20261008.xml`），不叠加浮动的`manifests/martini.xml`。
Evolution-X会改写`cnb`分支历史，部分固定提交已不在分支上；当前锁对其全部项目
使用`clone-depth="1"`按SHA直接获取。上游删除仓库或分支后旧锁无法再同步（2026-10-08
`20261001-upstream`即如此），需要刷新锁。
项目和LFS由Repo正常同步。若网络失败，保留现场，不自动清空工作区。

### 2. 应用固定补丁

```sh
python3 "$CONTROL/tools/rebuild.py" prepare --source "$SOURCE"
```

核对基线、补丁哈希和工作树，先检查再应用：update_engine、vendor/lineage（target-files、
内核OUT）、PixelOS的vendor与frameworks/base补丁和telephony修正。设备树martini、sm8350-common
和内核不打补丁：它们是KennelROMs fork（`kennel-17`；`kernel/oneplus/sm8350-ksu`用
`kennel-17-ksu`，即`kennel-17`加KernelSU Next hooks），改动直接提交在fork上。
未知修改或部分应用时停止，不reset/clean。准备记录仅用于后续发现输入/工作树变化，
不代替构建与实机验证。已准备的树直接进入build，不盲目重复应用补丁。

### 3. 使用已有签名材料构建并归档

```sh
python3 "$CONTROL/tools/rebuild.py" build \
  --source "$SOURCE" --artifacts "$ARTIFACTS" --signing self-build
```

普通目标固定为`lineage_martini-cp2a-userdebug`、`m evolution`，实际导出
`EVO_KEEP_TARGET_FILES=true`；默认OUT为SOURCE/out。OUT必须位于SOURCE内，脚本以相对SOURCE的
`OUT_DIR`导出：siso在绝对路径的配置目录下无法加载`main.star`（Soong会跳过带`.out-dir`标记的OUT）。

配对的KernelSU Next内核在同一个已准备的SOURCE上另用一个OUT构建，只构建`bootimage`：

```sh
python3 "$CONTROL/tools/rebuild.py" build --kernel ksu \
  --source "$SOURCE" --out "$SOURCE/out-ksu" --artifacts "$ARTIFACTS" --signing release
```

`--kernel ksu`导出`MARTINI_KSU=true`：设备树据此改用`kernel/oneplus/sm8350-ksu`、追加
`vendor/ksu.config`并固定KSU版本号（Repo不同步标签，版本由`refresh_lock.py`按上游Kbuild
规则算出）。归档为`<ROM版本>-ksu-boot.img`，只与同一次prepare的普通ROM配对。OUT首次使用时记录
内核变体，之后不同变体复用同一OUT会被拒绝，避免两种内核产物混合。
构建检查实际证书绑定，保留失败退出码和日志，不把tee成功当作构建成功。
成功后保存实际ZIP、原始target-files及构建记录到新的归档目录，不覆盖旧候选。

### 与上游同步

```sh
python3 "$CONTROL/tools/refresh_lock.py" --id YYYYMMDD     # 需要repo与网络
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s "$CONTROL/tests"
```

工具让Repo合并当前Evolution-X清单与`manifests/martini.xml`，用`git ls-remote`固定全部
项目，并更新profile与补丁基线。设备树fork里的KSU版本号（`BoardConfig.mk`）若与KernelSU Next
不符，工具拒绝并给出应提交到fork的值。提交后在SOURCE上`update`与`prepare`：补丁若
已被上游合入或冲突，按上游现状重做补丁或从序列移除，并在[PIXELOS](PIXELOS.md)记录。

fork只用合并同步上游：在fork中`git merge`LineageOS `lineage-24.0`到`kennel-17`，再把
`kennel-17`合并到`kennel-17-ksu`，推送后刷新锁；不rebase、不force push（旧锁固定的提交须保持可取）。

### 更新已准备的SOURCE到新的CONTROL提交

```sh
python3 "$CONTROL/tools/rebuild.py" update --source "$SOURCE"
python3 "$CONTROL/tools/rebuild.py" prepare --source "$SOURCE"
```

`update`先确认各已修改项目与准备记录逐字节一致，只撤销这些已记录的改动并归档记录到
`SOURCE/.martini-history/`，再`repo init -b`当前CONTROL提交并`repo sync`。出现记录外
的改动时停止，不reset/clean。之后重新prepare。

上游若把某路径换成不同项目（名称/远端改变），`repo sync`会拒绝覆盖。确认该checkout
无改动后，把它和`.repo/projects/<路径>.git`移出SOURCE（例如`~/martini/displaced/`），
再重跑`update`；不使用`--force-sync`。

在上述任一命令末尾加 `--dry-run` 只显示计划，不联网、建目录或运行Android代码。
控制机只适合控制仓库工作；构建服务器为16核/62GiB，源码约211GiB、每个OUT约170GiB。

## OTA更新条目

```sh
python3 "$CONTROL/tools/ota_json.py" EvolutionX-*.zip --url "<最终下载地址>" > martini.json
```

条目字段与Evolution X Updater的解析要求一致，时间戳取自包内OTA元数据（等于该构建的
`ro.build.date.utc`）。补丁`ota/0001`把设备的`updater_server_url`改为本仓库`main`分支的
`ota/martini.json`（更新日志为`ota/changelogs/martini.txt`）；此前的构建仍指向官方
`Evolution-X/OTA`（其中没有martini），只能用`push-update.sh`本地推送。

## 在crave.io构建并发布到SourceForge

crave（foss.crave.io）规则：只用公开仓库；同一账号同时只跑一个构建、一次一台设备；不要
`--clean`或删除out（排队会从约半小时变成数小时）；不在devspace里直接编译。

crave上没有Evolution X项目，使用`LOS 23.2`（projectID 99）。其工作区`/tmp/src/android`是
浅克隆快照（503G盘，16核/62G），本地CLI以一个该项目清单的克隆作为工作区标识：

```sh
git clone --branch lineage-23.2 https://github.com/accupara/los23.2 ~/crave/martini
cd ~/crave/martini        # 以下crave命令都在此目录执行，加 -c ~/.crave/crave.conf
```

`tools/crave.sh`在构建节点的工作区根目录（即SOURCE）运行，CONTROL克隆在`$HOME/MartiniEvoX`：

- `sync REF`：工作区还没有准备记录时先`rebuild.py adopt`——把锁里换成其他项目的路径
  （LOS 23.2约67个，均无改动）连同`.repo/projects/<路径>.git`移到`.martini-displaced/`，
  代替`--force-sync`；然后`update --clone-depth 1`（否则Repo会把浅克隆全部补成完整历史）
  与`prepare`。
- `build REF`：`sync`后构建普通ROM（`out`）与KSU boot（`out-ksu`），均用`--signing release`；
  设置`SF_USER`/`SF_PROJECT`时接着`upload`。
- `upload ROM归档 KSU归档`：核对两者来自同一CONTROL提交，rsync到SourceForge项目的
  `martini/`目录，打印Updater条目并存为ROM归档里的`martini.json`。

一次性放入的机密（不进入任何Git、gist或CI secret；工作区重置后重新放入）：

- 现有签名私钥（必须沿用，否则OTA证书与APK签名不连续，无法保数据升级）：
  `crave push keys.tar -d /tmp/src/android/vendor/evolution-priv`，再
  `crave ssh -- "cd vendor/evolution-priv && tar -xf keys.tar && rm keys.tar"`。
  `build --signing release`会核对证书指纹等于`certificates/release-info.json`。
- SourceForge上传私钥与已核对的主机指纹（frs的ED25519为
  `SHA256:209BDmH3jsRyO9UeGPPgLWPSegKmYCBIya0nR/AWWCY`，见SourceForge文档）：
  打包为`.martini-secrets/{sourceforge,known_hosts}`后同样push到工作区根目录并解开。

每次发布（REF用提交SHA，raw.githubusercontent对分支名有缓存）：

```sh
crave run --projectID 99 --no-patch --detached -- \
  "curl -fsSL https://raw.githubusercontent.com/KennelROMs/MartiniEvoX/<SHA>/tools/crave.sh |
   SF_USER=liki4 SF_PROJECT=kennelroms bash -s -- build <SHA>"
crave getlog --projectID 99 --jobID <JOB>
```

把打印的条目提交为本仓库的`ota/martini.json`、补写`ota/changelogs/martini.txt`后设备才会
看到更新。上传失败不必重建：`crave ssh -- "curl … | SF_USER=… SF_PROJECT=… bash -s -- upload …"`。

每个ROM归档约11GiB（ZIP约3.7GiB、target-files约7.8GiB），确认上传后只保留最新一次；
SourceForge建议项目总量在5GiB左右，最多20–30GiB，只保留最新一到两版。

## 验收范围

- 离线测试验证脚本的实际关键行为和已有ROM补丁/配置，不以测试数量代表质量。
- `BUILT_AND_ARCHIVED_UNVALIDATED`只表示构建/归档成功，不冒充原生验签、首启或OTA通过。
- 新产物保存自己的哈希和身份，不要求ZIP等于历史a811…候选；原始META不能用旧文件替代。
- 本阶段不新增通用镜像审计框架。后续按实际需要使用源码原生工具做产物/OTA验证。
- 脚本不刷机、不格式化、不切槽、不重锁。失败先查看日志并定位，不自动弱化安全检查。
