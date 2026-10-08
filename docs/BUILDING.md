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

先提交/固定CONTROL版本。以下变量由构建者指定，不能照搬另一台机器的私有目录：

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
`manifests/locked/martini-20261001.xml`，不叠加浮动的`manifests/martini.xml`。
Evolution-X会改写`cnb`分支历史，部分固定提交已不在分支上；当前锁对其全部项目
使用`clone-depth="1"`按SHA直接获取，修订本身不变（推导见`baselines/20261001.json`）。
项目和LFS由Repo正常同步。若网络失败，保留现场，不自动清空工作区。

### 2. 应用固定补丁

```sh
python3 "$CONTROL/tools/rebuild.py" prepare --source "$SOURCE"
```

核对基线、补丁哈希和工作树，先检查再应用：EROFS/update_engine/target-files、PixelOS增强
（设备树、vendor、内核）与KSU开关/内核补丁。PixelOS内核补丁同时用于两份内核checkout；
KSU补丁只在`kernel/oneplus/sm8350-ksu`中。
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
项目，并更新profile、补丁基线和KSU版本号。提交后在SOURCE上`update`与`prepare`：补丁若
已被上游合入或冲突，按上游现状重做补丁或从序列移除，并在[PIXELOS](PIXELOS.md)记录。

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

crave（foss.crave.io）只允许公开仓库，同一账号同时只跑一个构建；不要`--clean`或删除out，
否则排队从约半小时变成数小时。`tools/crave.sh`在构建节点的工作区根目录（即SOURCE）运行：
CONTROL克隆在工作区外（默认`$HOME/MartiniEvoX`，节点home不保留时自动重新克隆），依次
`update`、`prepare`、普通ROM（`out`）与KSU boot（`out-ksu`），均用`--signing release`。

一次性准备（维护者在crave devspace中操作）：

1. 从基础项目建立工作区：`crave clone create --projectID <ID> /crave-devspaces/martini`。
   基础项目越接近Evolution X Android 17，首次`update`需下载的越少；若`repo sync`报告
   某路径的项目已更换，按上文“更新已准备的SOURCE”处理，不用`--force-sync`。
2. 放入现有签名私钥（必须沿用，否则OTA证书与APK签名不连续，无法保数据升级）：在自己的
   备份处`tar -cf keys.tar keys`，经scp传到devspace后
   `crave push keys.tar -d <工作区>/vendor/evolution-priv/`（工作区路径用`crave ssh -- pwd`
   查看），再`crave ssh -- "cd vendor/evolution-priv && tar -xf keys.tar && rm keys.tar && chmod -R go-rwx keys"`，
   删除devspace上的`keys.tar`。私钥不进入任何Git、gist或CI secret；工作区重置后重新放入。
3. SourceForge：建立项目，为上传单独生成一把SSH密钥并把公钥加入SourceForge账号；私钥用同样
   方式放到`<工作区>/.martini-secrets/sourceforge`（权限600）。主机指纹首次连接时记录在同目录。

每次发布：

```sh
crave run --no-patch -- "curl -fsSL https://raw.githubusercontent.com/KennelROMs/MartiniEvoX/main/tools/crave.sh |
  SF_USER=<用户> SF_PROJECT=<项目> bash -s -- build origin/main"
```

构建成功后脚本核对ROM与KSU boot来自同一CONTROL提交，把ZIP和`*-ksu-boot.img`上传到
SourceForge项目的`martini/`目录，并打印Updater条目（也保存为ROM归档里的`martini.json`）。
把条目提交为本仓库的`ota/martini.json`、补写`ota/changelogs/martini.txt`后设备才会看到更新。
上传失败时不必重建：`crave ssh -- "curl … | SF_USER=… SF_PROJECT=… bash -s -- upload <ROM归档> <KSU归档>"`。

每个ROM归档约11GiB（ZIP约3.7GiB、target-files约7.8GiB），确认上传后只保留最新一次；
SourceForge建议项目总量在5GiB左右，最多20–30GiB，只保留最新一到两版。

## 验收范围

- 离线测试验证脚本的实际关键行为和已有ROM补丁/配置，不以测试数量代表质量。
- `BUILT_AND_ARCHIVED_UNVALIDATED`只表示构建/归档成功，不冒充原生验签、首启或OTA通过。
- 新产物保存自己的哈希和身份，不要求ZIP等于历史a811…候选；原始META不能用旧文件替代。
- 本阶段不新增通用镜像审计框架。后续按实际需要使用源码原生工具做产物/OTA验证。
- 脚本不刷机、不格式化、不切槽、不重锁。失败先查看日志并定位，不自动弱化安全检查。
