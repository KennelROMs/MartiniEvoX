# 实机验证步骤

这些步骤需要维护者手持手机执行；构建任务不授权刷机、格式化、切槽或重锁。
每一步只记录看到的结果，失败时保留输出，不为通过而关闭安全检查。产物路径与哈希
以 [STATUS](STATUS.md) 和各次构建的 `result.json` 为准。

开始前：确认当前系统可正常开机、已备份重要数据；PixelOS回退包与当前候选的
`boot.img`/`vendor_boot.img` 在构建服务器 `~/evo-logs/candidate-rebuild-*/artifacts/`。

## 1. KSU：临时启动，不写入分区（KSU-02）

KSU内核与同源普通内核的模块CRC完全一致，可以在现有系统上只临时启动KSU的
`boot.img`；重启后自动回到原内核。

```sh
adb reboot bootloader
fastboot boot ksu-boot.img        # 只引导一次，不刷写
```

开机后记录：

```sh
adb shell uname -r                       # 应含 -dirty（KSU内核）
adb shell getenforce                     # 应为 Enforcing
adb shell 'lsmod | wc -l'                # 与普通内核下的数量比较
adb shell dmesg | grep -i kernelsu | head -20   # 需要可读dmesg的环境
```

安装 KernelSU Next Manager（v3.4.0，对应内核版本33304）：确认显示“工作中”及版本；
对一个Shell应用分别授权与拒绝 `su`，记录结果；音量下键安全模式可选。
重启后确认回到普通内核（`uname -r` 不含 `-dirty`）。

如果临时启动失败或卡住：长按电源+音量下进入bootloader，再 `fastboot reboot`，
原分区未被修改。

## 2. PixelOS增强构建（PIXEL-02）

刷入新的完整包后（或经第3节OTA升级后）检查：

- 显示：挖孔区域、状态栏边距、锁屏提示与指纹区距离、电源键位置提示。
- 亮度：低亮度与滑杆手感、自动亮度。
- 性能：`adb shell dumpsys android.hardware.power.IPower/default` 可见libperfmgr；
  日常操作流畅度与发热主观对照。
- 传感器：抬手/拿起亮屏、AOD、接近感应（通话时熄屏）。
- 相机：OPlus Camera各镜头拍照、录像；Aperture是否被替代。
- 音频：Dolby开关、扬声器、耳机、蓝牙、通话。

## 3. OTA升级（OTA-01）

同一发布签名（项目OTA证书SHA256 `d6310c41…f9af`）的保数据升级：

```sh
adb root                                   # userdebug；若被拒绝，先在开发者选项开启root调试
./push-update.sh EvolutionX-*.zip          # 来自 packages/apps/Updater，放入 /data/evolution_updates
```

在“系统更新”中安装，完成后重启。记录：

```sh
adb shell getprop ro.boot.slot_suffix      # 升级前后应切换
adb shell getprop ro.build.fingerprint
adb shell getprop ro.evolution.version 2>/dev/null
adb shell snapshotctl dump 2>/dev/null | head   # 合并状态（root）
```

确认应用、设置、锁屏密码和用户数据保留；再重启一次确认稳定。KSU用户升级后内核会
回到普通内核，需要再按第1节验证或刷入匹配的KSU `boot.img`。

## 4. 集中修复的诊断数据（FIX-01）

只读命令，结果整理后交给维护记录，不上传原始日志到公共仓库：

```sh
# 高刷新率
adb shell settings get system peak_refresh_rate
adb shell settings get system min_refresh_rate
adb shell dumpsys display | grep -iE 'mode|refresh|fps' | head -40
adb shell dumpsys SurfaceFlinger | grep -iE 'refresh|mode|fps' | head -40

# 0.9× 相机：先在相机App切到0.9×拍一张，再收集
adb shell dumpsys media.camera | head -200
adb logcat -d -b all | grep -iE 'camera|aperture' | tail -200
```
