# 实机验证步骤

全部工作完成后由维护者手持手机执行；构建任务不授权刷机、格式化、切槽或重锁。
每一步只记录看到的结果，失败时保留输出，不为通过而关闭安全检查。产物名称与哈希以
[STATUS](STATUS.md) 与各次构建归档的 `result.json` 为准。

开始前：确认当前系统（候选 `a8114027`）可正常开机并备份重要数据。PixelOS回退包及候选的
`boot.img`/`vendor_boot.img` 在构建服务器 `~/evo-logs/candidate-rebuild-*/artifacts/`。

## 1. OTA升级到新ROM（OTA-01）

新ROM与 `a8114027` 使用同一项目OTA证书（SHA256 `d6310c41…f9af`），按保数据升级安装：

```sh
adb root                                   # userdebug；若被拒绝，先在开发者选项开启root调试
./push-update.sh EvolutionX-*.zip          # packages/apps/Updater 中的脚本
```

在“系统更新”中安装并重启。记录升级前后：

```sh
adb shell getprop ro.boot.slot_suffix      # 应切换槽位
adb shell getprop ro.build.date.utc
adb shell getprop ro.evolution.build.version 2>/dev/null
adb shell getenforce                       # Enforcing
```

确认应用、设置、锁屏密码与用户数据保留；稍后再重启一次，确认稳定并完成snapshot合并
（`adb shell su 0 snapshotctl dump` 或 `dumpsys` 中无未合并状态）。

## 2. PixelOS增强（PIXEL-02）

- 显示：挖孔区域、状态栏边距、锁屏提示与指纹区距离、电源键位置提示。
- 亮度：低亮度与滑杆手感、自动亮度。
- 性能：`adb shell pidof android.hardware.power-service.lineage-libperfmgr` 有进程号；
  `adb shell su -c 'dumpsys android.hardware.power.IPower/default'` 可见libperfmgr节点状态
  （普通shell执行会得到`FAILED_TRANSACTION`：系统策略只允许dumpstate/root把输出fd交给
  电源HAL，并非HAL故障）。日常流畅度、发热、续航主观对照。
- 传感器：拿起/抬手亮屏、AOD、通话接近熄屏、熄屏指纹。
- 相机：OPlus Camera各镜头（含超广角）拍照、录像。
- 音频：Dolby开关与效果、扬声器、耳机、蓝牙、通话。

## 3. 已知问题复核（FIX-01）

```sh
# 高刷新率：区分“空闲4秒/60fps内容回落60Hz”的设计行为与真正故障
adb shell settings get system peak_refresh_rate
adb shell settings get system min_refresh_rate
adb shell dumpsys display | grep -iE 'mode|refresh|fps' | head -40
adb shell dumpsys SurfaceFlinger | grep -iE 'refresh|mode|fps' | head -40
```

0.9×相机：在OPlus Camera中切换各镜头确认清晰；若仍异常，收集
`adb shell dumpsys media.camera | head -200` 与对应时段日志。原始日志不进公共仓库。

## 4. 配对的KernelSU Next内核（KSU-02）

KSU `boot.img` 只与同一次构建的普通ROM配对（文件名前缀即ROM版本）。先临时启动，
不写入分区，重启即回到普通内核：

```sh
adb reboot bootloader
fastboot boot EvolutionX-…-ksu-boot.img
```

开机后记录：`adb shell uname -r`（应含 `-dirty`）、`getenforce`（Enforcing）、
`lsmod | wc -l`（与普通内核下相同）。安装 KernelSU Next Manager（v3.4.0），确认显示
“工作中”与版本号；对Shell应用分别授权与拒绝 `su`。

临时启动正常后，如需常驻：`fastboot flash boot_a`/`boot_b`（写入当前槽位）。
每次OTA后内核回到普通版，需刷入新版本对应的KSU boot。卡住时长按电源+音量下进入
bootloader，`fastboot reboot` 回到原内核。
