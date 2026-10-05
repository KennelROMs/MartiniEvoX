# PixelOS 借鉴台账（PIXEL-01）

对照对象：PixelOS `seventeen` 分支（2026-10-01取样）。设备树
`PixelOS-Devices/android_device_oneplus_martini` a86283a、`…_sm8350-common` c2beeae；
`PixelOS-AOSP/android_hardware_oplus` 8ead74c；`PixelOS-Devices/android_kernel_oneplus_sm8350`；
NoPrincessHere GitLab vendor仓库。维护者已确认PixelOS使用的OnePlus公开blob可取用。

结论只有五类：**集成**、**已有等效**、**无收益**、**不适用**、**阻塞**。“集成”表示补丁已进入
`patches/series.json`或锁，验证状态单独记录；未构建/未实机的一律写未验证。

## 设备树 sm8350-common（补丁 `patches/pixelos/common-*.patch`）

| 项 | PixelOS提交 | 结论 | 说明 |
| --- | --- | --- | --- |
| libperfmgr电源HAL | 7bd76f5、dee54b6、b69d62b、19391a6 | 集成（common-1） | 替换QTI power/perf HAL，powerhint开机完成后解析 |
| 移除QTI perfd/IO prefetcher | a678d3d、d452a57 | 集成（common-1，冲突按PixelOS终态解决） | 同时需vendor补丁与内核MSM_PERFORMANCE关闭 |
| powerhint调优（lahaina/yupik） | 0391146…27992cf共16个、2ef2744 | 集成（common-1） | DisplayWakeup节点依赖内核early_wakeup |
| 传感器多HAL/拾起/AOD亮度 | cd09cda、4fab505、9d0a101 | 集成（common-2） | 依赖hardware/oplus seventeen的multihal |
| 关闭sensors HAL事件日志 | b8742f7 | 集成（common-2） | vendor.prop一行 |
| Dolby | 9bc01a1 | 集成（common-3，audio_policy行按Lineage现状解决） | audio_effects改用本地含DAP/VQE版本 |
| OPlus Camera | 6e039d0 | 集成（common-4） | 仅取common.mk；custom.dependencies不适用 |
| PixelOS品牌化 | 59b31f5、8e5da21 | 不适用 | custom_*重命名与roomservice依赖，Evo不用 |
| 音量面板左置 | b5249f8 | 不适用 | Evo frameworks无对应配置键 |
| oplus接口去blob | f160485 | 无收益 | 只改提取清单；所用vendor仓库未变，不影响构建 |
| 音频策略位置、fastbootd、PowerOffAlarm、UFFD等 | f5b6b30、f8307d6、ecd25a8、27ccc1a、37021bc | 已有等效 | 已在锁定的LineageOS提交中 |

## 设备树 martini（`patches/pixelos/martini-*.patch`）

| 项 | PixelOS提交 | 结论 | 说明 |
| --- | --- | --- | --- |
| 亮度gamma转换关闭 | 688acbb | 集成（martini-1） | Evo frameworks支持该属性 |
| 挖孔/状态栏/UDFPS锁屏间距/电源键位置/热点SSID | 60c876f、5cea0c1、58f0843、e0510cb、5a5c867 | 集成（martini-2）；挖孔圆心y由`fixes/0002`实机标定下移3 px | 需实机查看 |
| 亮度配置迁移displayconfig | 66537e9、e09695c | 无收益 | PixelOS已自行回退 |
| 三段键提示位置 | b2bd6c8 | 已有等效 | Lineage KeyHandler RRO已设19.2% |
| PixelOS品牌化 | a86283a | 不适用 | 同上 |

## frameworks/base（`patches/pixelos/frameworks-base-1-oplus-camera-compat.patch`）

OPlus Camera在设备上因`com.oplus.util.OplusTypeCastingHelper`缺失而启动即崩溃（2026-10-02实机日志）。
PixelOS把这类OPlus兼容桩放在自己的frameworks/base，而非设备树或hardware/oplus，前一轮对照未覆盖。

| 项 | PixelOS提交 | 结论 |
| --- | --- | --- |
| OplusTypeCastingHelper、OplusThemeUtil桩 | 5d1265df | 集成（修复启动崩溃） |
| camera2向后兼容方法（CameraMetadataNative） | 158cc507 | 集成 |
| StreamConfigurationMap兼容构造函数 | 3ae9a8ce | 已有等效：Evo已在别处定义同签名构造函数（叠加会重复定义，编译失败） |
| CaptureResultExtras构造函数、mLogicalCameraSettings可访问 | f5ac784a、f2c4fd77 | 已有等效（Evo已含） |
| 辅助摄像头暴露、特权应用跳过HFR/流尺寸检查 | 61a3e755、d8945be4、99e555d2 | 已有等效（Evo以`vendor.camera.aux.packagelist`与`persist.vendor.camera.privapp.list`实现） |

## 其他仓库

| 仓库 | 结论 | 说明 |
| --- | --- | --- |
| hardware/oplus | 集成（锁改为PixelOS-AOSP 8ead74c） | 锁定提交的快进+20：传感器multihal、Doze覆盖、powerhal/walt sepolicy、oplus-fwk相机类、richtap、KeyHandler |
| vendor/oneplus/sm8350-common | 集成（vendor-common-1） | 相对TheMuppets 445ead0仅删除perfd相关模块 |
| vendor/oplus/camera、vendor/oneplus/dolby、packages/apps/DolbyAtmos | 集成（新增锁项目） | NoPrincessHere/PixelOS-AOSP seventeen |
| vendor/oneplus/martini | 无收益 | 仅删除.lfsconfig |
| richtap Awinic | 不适用 | martini未启用相关soong配置 |

## 内核（`patches/pixelos/kernel-1-pixelos-picks.patch`，普通与KSU内核相同，基于LineageOS 187d13c）

| 项 | PixelOS提交 | 结论 |
| --- | --- | --- |
| SDE early_wakeup sysfs | 09e1ce8 | 集成（powerhint需要）；节点为root只写，`fixes/0001`在boot时改为system可写（PixelOS同样缺失，实机见DAC拒绝） |
| KCAL | 04075d1 | 集成 |
| 关闭MSM_PERFORMANCE | 42c6751 | 集成（上下文不同，手工移植） |
| 移除PASR mem-offline（DTS+配置） | a94c059、711ce68 | 已有等效：LineageOS内核187d13c已合入 |
| AoD低亮度默认 | e456ff4 | 集成（CRLF文件，手工移植） |
| securityfs/functionfs genfscon | e4690bd、15df180 | 已有等效：LineageOS内核187d13c已合入 |
| OTG开关默认开启/可写 | 6f28a73、1b53fd0 | 不适用：Lineage内核本就可写；默认开启依赖PixelOS OEM导入中的充电实现 |
| 整树替换PixelOS内核 | — | 不适用：另一OEM导入（2145文件），不作为可审查补丁 |

## 已知问题对照

PixelOS未改动高刷新率相关配置，也未改动martini的Aperture/相机传感器设置；
高刷与0.9×问题不能靠本台账解决，留在FIX阶段用实机数据定位。

## 验证状态

补丁组合已在干净基线上按序列逐仓库`git apply --check`通过；内核补丁的普通/KSU独立编译
结果见STATUS。完整ROM构建、性能/温度/功耗对照、相机/音频/传感器实机检查均未执行。
