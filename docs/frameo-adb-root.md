# Frameo / Denver: ADB, existing root and installation

**English** · [Nederlands](frameo-adb-root.nl.md)

This guide records what could be reconstructed from earlier project sessions and the source code. It helps you inspect your own frame and install Light Panel. It is not a universal rooting procedure.

## What was recovered?

| Item | Evidence / status |
| --- | --- |
| Original model | Denver PFF-1081; other models may differ |
| Android | Reported as Android 6.0.1, API 23 |
| CPU | Reported as `armeabi-v7a`, 32-bit ARM |
| ADB access | Frameo Beta Program and ADB Access enabled |
| Connection | USB initially failed on macOS; ADB later worked through Windows and then over the network |
| Root | `/system/xbin/su` and `daemonsu` were noticed during inspection; `su` was subsequently used |
| Root installation | No completed exploit, Magisk installation, bootloader unlock or root-flashing procedure was recovered |
| Wireless ADB | TCP port 5555; persistent settings discussed and a connection after reboot reported |
| LED interface | The current APK writes to `/sdcard/frameo_light.txt` |
| Screen interface | The current APK controls `/sys/class/backlight/rk28_bl/brightness` |

The recovered route uses **existing root access**. Its original source—factory firmware, an earlier change or something else—is not established. Having `su` on one frame does not prove it exists on another. Enabling ADB does not grant root.

Private conversations, device addresses and logs are not distributed with this guide.

## 1. Prepare

Record your exact model, Android and firmware versions. Install [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools). Use a USB data cable and retain the frame’s normal power supply where required. Keep access to Android settings and the original launcher until your replacement works reliably.

Commands below assume one device. With several devices, use `adb -s SERIAL ...` or `adb -s FRAME_IP:5555 ...`, replacing those placeholders with your own values.

## 2. Enable ADB

The [official Frameo instructions](https://support.frameo.com/hc/en-us/articles/6126183308434--How-to-Enable-ADB-on-Your-Frame) describe:

**Settings → About → Beta Program on → ADB Access on.**

Connect the data cable, approve any debugging prompt on the frame, then check:

```sh
adb version
adb devices -l
```

| Result | Next step |
| --- | --- |
| `device` | Connected |
| `unauthorized` | Approve the authorization prompt on the frame |
| `offline` | Reconnect and check the ADB session |
| No device | Check power, data cable, port, ADB toggle and, on Windows, drivers |

The original frame initially did not enumerate over USB on macOS; Windows was used later. This is an observation, not a requirement for every PFF-1081. Frameo points Windows users to the [Google USB Driver](https://developer.android.com/studio/run/win-usb), but the correct driver depends on the device.

On macOS, check whether USB detects it at all:

```sh
ioreg -p IOUSB
```

If the device is absent from the USB bus, solve that before diagnosing ADB authorization.

## 3. Inspect the model and existing root

These commands read information; they do not install root:

```sh
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell getprop ro.product.cpu.abi
adb shell id
adb shell which su
adb shell su -c id
```

A missing `which` command alone does not prove `su` is absent. Successful `su -c id` should include `uid=0(root)`. A normal ADB shell can report `uid=2000(shell)` while `su` still provides root.

If `su` is missing, access is denied or no root UID appears, existing root has not been confirmed. The browser dashboard does not need root; native hardware controls and system clock correction do. Find a verified method for your exact device/firmware rather than guessing flash steps.

`adb root` is not a root installer. It restarts a suitable debug-build ADB daemon with elevated rights; production builds may refuse it. See [AOSP’s explanation](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/dev/root.md).

## 4. Optional wireless ADB

ADB is for installation/diagnostics; normal Light Panel operation does not require an ongoing ADB connection.

Start with working USB on a trusted network. Replace `FRAME_IP` with your frame’s address:

```sh
adb tcpip 5555
adb connect FRAME_IP:5555
adb devices -l
```

Read the relevant properties:

```sh
adb shell getprop service.adb.tcp.port
adb shell getprop persist.adb.tcp.port
adb shell getprop init.svc.adbd
```

The service property describes the current setting. The persistent property is intended to survive reboot, but firmware must honour it. Only a reboot test confirms it.

If existing root works and you deliberately want wireless ADB after reboot, the recovered configuration route was:

```sh
adb shell su -c 'setprop persist.adb.tcp.port 5555'
adb shell getprop persist.adb.tcp.port
```

Keep USB as a fallback. Reboot at a suitable time and reconnect without first running `adb tcpip` over USB again:

```sh
adb reboot
# Wait for Android to finish starting.
adb connect FRAME_IP:5555
adb devices -l
```

Android 6 does not use modern Android 11+ wireless-debugging pairing. Restrict port 5555 to your own administration computer; do not expose it to the internet or a shared guest network. `adb disconnect` only disconnects your client; it does not disable the listener. `adb usb` returns a temporary TCP session to USB, but any configured persistent property must be reverted separately if you no longer want it.

To reconnect a stuck session:

```sh
adb disconnect FRAME_IP:5555
adb connect FRAME_IP:5555
```

Guest-network isolation can block device-to-device traffic. Earlier HA-ADB tests also showed concurrent/duplicated commands. Test with one management client and without competing automations before assuming the device supports only one connection.

## 5. Install the launcher

Follow [the Android build guide](android.md), set your own reachable dashboard URL and build the APK. The sample hostname does not create a DNS entry.

From the repository root:

```sh
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n app.lightpanel.launcher/.MainActivity
```

Test loading, controls and recovery from a temporary network failure. Then choose **Light Panel → Always** in Android’s Home settings:

```sh
adb shell am start -a android.settings.HOME_SETTINGS
```

This one-time default-HOME choice is necessary for automatic startup. Version 0.2.0 adds a boot fallback; see [automatic startup](android.md#always-return-after-power-loss). Keep another working launcher available. A signing mismatch during an update is a reason to check the package/key, not to uninstall automatically and lose settings.

## 6. ADB root and app root are different

The app opens `su -c /system/bin/sh` itself. A successful ADB root test does not prove that the installed app has the same permission. Approve Light Panel in your existing root manager if prompted, then test from the frame controls.

The website passes fixed commands through a WebMessagePort restricted to the configured dashboard origin. Other websites do not get a general-purpose shell interface.

## 7. Hardware, clock and screenshots

| Feature | Current implementation |
| --- | --- |
| LED colour | Root writes `<brightness,red,green,blue>` to `/sdcard/frameo_light.txt`; channels 0–255 |
| LED off | `<0,0,0,0>` |
| Red breathing | Generated locally in the app, roughly every 100 ms over a 3.2-second cycle |
| Screen off | Set the supported backlight to zero; Android/network stay active |
| Screen on | Restore saved brightness; touching the dark screen can wake it |
| Screen/LED relationship | Screen-off suppresses LEDs while keeping the desired LED setting |
| Clock | Reference time from the dashboard API, falling back to NTP; root sets UTC system time |
| Screenshots | Requested image of the dashboard WebView, not the full Android screen or other apps |

The LED file is an interface used by the original frame. Its firmware/background reader is **not included** in Light Panel, and its installation could not be reconstructed. Creating that file on another Android tablet will not create working LEDs.

Read-only backlight checks:

```sh
adb shell ls -l /sys/class/backlight/rk28_bl/brightness
adb shell cat /sys/class/backlight/rk28_bl/brightness
```

If that path is missing, this controller does not match your model. Use the app’s controls for on/off tests because it saves/restores brightness. The old `frameo_breathe.sh` is not needed by the current app. Do not run old HA-ADB LED automations and the app as competing controllers.

## 8. WebView and recovery

The original device had WebView/ARM32 library problems. An old session eventually reported WebView 106; that is historical evidence, not advice to install an old browser engine today.

```sh
adb shell dumpsys webviewupdate
adb logcat -d -b crash -v time
```

Review logs for personal URLs/data before sharing them. This guide does not replace a system WebView, modify `/system`, or include a firmware image.

To return to Android settings or HOME through working ADB:

```sh
adb shell am start -a android.settings.SETTINGS
adb shell input keyevent 3
```

The HOME key opens whichever launcher is currently the default.

## Still unknown

The original installation/source of `su` and `daemonsu`, a verified root procedure for an unrooted matching frame, the vendor LED reader’s origin and a complete model-specific firmware recovery procedure are still unconfirmed. MaskROM/testpoints and system replacement were discussed as possibilities, but not recovered as a successfully executed rooting method, so they are not installation steps here.
