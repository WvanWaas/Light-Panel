# Optionele Android-kiosk

Start met het dashboard in een gewone browser. De broncode in `android/` is een aparte kiosk-app voor oudere Android-apparaten (minimaal Android 6). Er is geen persoonlijke APK of ondertekensleutel meegeleverd.

1. Installeer Android Studio, Android SDK 35 en een passende JDK voor de Android Gradle-plugin.
2. Open de map `android` als project.
3. Pas de constante `URL` in `app/src/main/java/app/lightpanel/launcher/MainActivity.java` aan naar het adres van je eigen dashboard. `http://lightpanel.local:8089` is een voorbeeld en maakt geen lokale DNS-naam aan.
4. Bouw een debug-APK met Android Studio of `./gradlew assembleDebug` vanuit die map.
5. Installeer de APK alleen op je eigen apparaat en test eerst de normale weergave.

Scherm-, screenshot- en LED-functies gebruiken apparaatspecifieke ondersteuning. De LED-code is gemaakt voor bepaalde Denver/Rockchip-fotolijsten met bestaande toegang tot de hardware. Een willekeurige Frameo-tablet biedt die toegang niet automatisch. Deze startversie root geen apparaat en installeert niets via ADB.

Het app-ID is `app.lightpanel.launcher`, zodat dit een eigen app is. De bron is beschikbaar; een werkende build en hardwaregedrag moeten per eigen apparaat worden geverifieerd.
