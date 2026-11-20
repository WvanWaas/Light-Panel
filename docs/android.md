# Optional Android kiosk and automatic startup

**English** · [Nederlands](android.nl.md)

Start by testing the dashboard in a regular browser. `android/` contains a separate kiosk app for Android 6/API 23 and later. Hardware behaviour was developed for a particular Denver/Rockchip frame; it is not universal across Frameo devices.

## Build and install

1. Install Android Studio, Android SDK 35 and JDK 17 for the supplied Gradle setup.
2. Open `android/` as the project.
3. Change `URL` in `app/src/main/java/app/lightpanel/launcher/MainActivity.java` to your own reachable dashboard address. `http://lightpanel.local:8089` is a placeholder and does not create a DNS record.
4. Build using Android Studio or, from `android/`:

   ```sh
   ./gradlew --no-daemon :app:assembleDebug :app:lintDebug
   ```

5. Install and open the APK from the repository root:

   ```sh
   adb install -r android/app/build/outputs/apk/debug/app-debug.apk
   adb shell am start -n app.lightpanel.launcher/.MainActivity
   ```

The app ID is `app.lightpanel.launcher`. No signing key, personal APK or local SDK path is committed. Hardware screen/LED controls require supported interfaces and existing root access. A working ADB root shell does not automatically grant root to an installed app.

## Always return after power loss

1. Install version 0.2.0 or later and open the app once.
2. In Android **Settings → Home**, choose **Light Panel → Always**. Installing alone does not select a default launcher.
3. You can open that settings screen with `adb shell am start -a android.settings.HOME_SETTINGS`.
4. Test a normal Android reboot first. The panel should open and reload the dashboard automatically.
5. Then test removal/restoration of power, keeping a known way back to Android settings or another launcher.

The manifest registers Light Panel as a HOME app, so Android can use it at startup. An additional `BOOT_COMPLETED` receiver reopens the panel only when it is the chosen default HOME app. If the activity is already running when the boot event arrives, it reloads the dashboard once. Data refreshes do not trigger this boot reload. While Wi-Fi or the server is unavailable, the app displays a loading/error state and retries.

The firmware must itself boot Android when power returns. An app cannot start while the device remains powered off. Newer Android releases may impose additional background-launch restrictions; the supported legacy frame is Android 6. An app that was explicitly force-stopped may need to be opened again. Do not remove the original launcher just to configure automatic startup.

## Hardware and HA controls

See the [Frameo/Denver ADB guide](frameo-adb-root.md) for recovered setup steps, existing-root checks, hardware interfaces and recovery. How root and the vendor LED-file reader originally became available is still unknown; Light Panel does not root a device.

Use the [HA package](../home-assistant/README.md) for screen, messages and webhook control. Screen off switches the backlight and LEDs off while Android and the connection remain active. It is not an Android shutdown or reboot.

The APK build and lint checks can verify source/API issues; real startup and power-cycle behaviour still need testing on your own frame.
