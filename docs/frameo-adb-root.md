# Frameo / Denver: ADB, rootcontrole en Light Panel installeren

Deze handleiding legt vast wat uit de projectcode, documentatie en eerdere tests kon worden gereconstrueerd. Hij helpt je een eigen fotolijst onderzoeken en Light Panel installeren. Er is geen universeel rootrecept voor alle Frameo-apparaten.

## Wat is daadwerkelijk teruggevonden?

| Onderdeel | Status |
| --- | --- |
| Onderzocht model | Denver PFF-1081; andere modellen kunnen afwijken |
| Android | In de oorspronkelijke sessie uitgelezen als Android 6.0.1, API 23 |
| CPU-architectuur | In die sessie uitgelezen als `armeabi-v7a` (32-bit ARM) |
| ADB openen | Frameo Beta Program en ADB Access ingeschakeld |
| Verbinding | USB werkte aanvankelijk niet op de Mac; later werkte ADB via Windows en daarna via het netwerk |
| Root | Tijdens de verkenning werden `/system/xbin/su` en `daemonsu` opgemerkt; later werd `su` gebruikt voor opdrachten |
| Root aanbrengen | Geen uitgevoerde exploit, Magisk-installatie, bootloader-unlock of root-flash teruggevonden |
| Draadloze ADB | Poort 5555; persistente property besproken en verbinding na herstart gemeld |
| LED-interface | De huidige APK schrijft naar `/sdcard/frameo_light.txt` |
| Scherminterface | De huidige APK bedient `/sys/class/backlight/rk28_bl/brightness` |

De gevonden route gebruikt dus **bestaande roottoegang**. We kunnen niet vaststellen of die uit de fabrieksfirmware, een eerdere aanpassing of een andere herkomst kwam. De aanwezigheid van `su` op één exemplaar zegt niet dat jouw fotolijst ook geroot is. ADB inschakelen geeft op zichzelf geen rootrechten.

De historische privégesprekken en apparaatgegevens worden niet meegeleverd; alleen deze algemene reconstructie en de openbare broncode.

## 1. Voorbereiden

- Noteer het exacte model, Android-versie en firmwareversie van jouw fotolijst.
- Installeer [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) op je computer.
- Gebruik een USB-kabel die gegevens kan overdragen. Houd de normale voeding van de fotolijst aangesloten wanneer die afzonderlijk nodig is.
- Bewaar toegang tot de bestaande launcher en Android-instellingen totdat Light Panel betrouwbaar werkt.

De onderstaande voorbeelden gaan uit van één aangesloten apparaat. Gebruik bij meerdere apparaten `adb -s SERIENUMMER ...` of `adb -s FRAME_IP:5555 ...`, met jouw eigen serienummer of adres.

## 2. ADB inschakelen

De [officiële Frameo-instructie](https://support.frameo.com/hc/en-us/articles/6126183308434--How-to-Enable-ADB-on-Your-Frame) beschrijft deze route:

**Instellingen → Over / About → Beta Program aan → ADB Access aan.**

Sluit daarna de datakabel aan en accepteer een eventuele autorisatievraag op de fotolijst. Controleer op je computer:

```sh
adb version
adb devices -l
```

| Uitkomst | Betekenis / vervolgstap |
| --- | --- |
| `device` | ADB is verbonden |
| `unauthorized` | Controleer de autorisatievraag op de fotolijst |
| `offline` | De verbinding bestaat, maar de sessie werkt niet goed; verbind opnieuw |
| Geen apparaat | Controleer voeding, datakabel, poort, ADB-toggle en zo nodig de Windows-driver |

Op het onderzochte exemplaar werkte USB aanvankelijk niet op macOS. Later werd ADB via Windows gebruikt. Dat is een waarneming, geen bewijs dat alle PFF-1081's een Windows-computer vereisen. Bij Windows verwijst Frameo naar de [Google USB Driver](https://developer.android.com/studio/run/win-usb); welke driver jouw model nodig heeft, hangt van de hardware af.

Op macOS kun je controleren of het apparaat überhaupt op de USB-bus verschijnt:

```sh
ioreg -p IOUSB
```

Geen vermelding op de USB-bus wijst op een probleem vóór de ADB-autorisatie. Zoek dan eerst verder naar kabel, aansluiting, voeding of de firmware-instelling.

## 3. Model en bestaande root controleren

Deze opdrachten lezen gegevens; ze installeren geen root:

```sh
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell getprop ro.product.cpu.abi
adb shell id
adb shell which su
adb shell su -c id
```

Een ontbrekend `which`-commando bewijst niet dat `su` ontbreekt; de laatste opdracht is de belangrijke test. Bij werkende root verwacht je bij `su -c id` onder meer:

```text
uid=0(root)
```

Een gewone `adb shell id` kan `uid=2000(shell)` tonen terwijl `su -c id` wel root geeft. Dat zijn verschillende toegangsrechten.

**Geen `su`, geweigerde toegang of geen `uid=0`?** Dan is bestaande root niet bevestigd. De browserweergave heeft geen root nodig; de APK gebruikt root voor hardwarebediening en systeemklokcorrectie. Zoek voor aanvullende roottoegang een aantoonbaar passende methode voor jouw exacte model en firmware. Deze handleiding bevat geen gegokte flash- of bootloaderstappen.

`adb root` is ook geen algemene rootinstallatie. Het herstart op geschikte debug-builds de ADB-daemon met hogere rechten; normale productie-builds kunnen dit weigeren. Zie de [AOSP-uitleg](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/dev/root.md).

## 4. Optioneel: ADB via het netwerk

Dit is voor installatie en diagnose. De normale Light Panel-werking heeft geen blijvende ADB-verbinding nodig.

Begin met een werkende USB-verbinding en gebruik een vertrouwd netwerk. Vervang `FRAME_IP` door het adres van jouw fotolijst:

```sh
adb tcpip 5555
adb connect FRAME_IP:5555
adb devices -l
```

Controleer de eigenschappen op de fotolijst:

```sh
adb shell getprop service.adb.tcp.port
adb shell getprop persist.adb.tcp.port
adb shell getprop init.svc.adbd
```

`service.adb.tcp.port` betreft de lopende instelling. De persistente property is bedoeld om een herstart te overleven, maar de firmware moet die wel gebruiken. Alleen een reboot-test bevestigt dat.

Als bestaande root werkt en je bewust draadloze ADB na een herstart wilt, was dit de gebruikte configuratieroute:

```sh
adb shell su -c 'setprop persist.adb.tcp.port 5555'
adb shell getprop persist.adb.tcp.port
```

Houd USB als terugvalmogelijkheid. Herstart op een geschikt moment en probeer daarna zonder opnieuw `adb tcpip` via USB uit te voeren:

```sh
adb reboot
# Wacht tot de fotolijst volledig is opgestart.
adb connect FRAME_IP:5555
adb devices -l
```

Android 6 gebruikt niet de moderne draadloze ADB-pairing van Android 11+. Beperk bereikbaarheid van poort 5555 tot je eigen beheercomputer en stel die poort niet beschikbaar aan internet of een gedeeld gastnetwerk. Een lokale `adb disconnect` schakelt de luisterende ADB-poort op de fotolijst niet uit. Voor tijdelijk netwerk-ADB kun je terug naar USB met `adb usb`; een ingestelde persistente poort moet afzonderlijk ongedaan worden gemaakt als je die niet meer wilt.

Bij een vastgelopen sessie kun je opnieuw verbinden:

```sh
adb disconnect FRAME_IP:5555
adb connect FRAME_IP:5555
```

Een gastnetwerk kan verbindingen tussen apparaten blokkeren. In de historische tests liepen daarnaast HA-ADB-opdrachten soms gelijktijdig of dubbel. Test bij problemen met één beheerclient en zonder concurrerende ADB-automatiseringen voordat je concludeert dat het apparaat maar één client ondersteunt.

## 5. Light Panel-APK bouwen en installeren

Volg eerst [de Android-instructies](android.md) om de bron te bouwen en het dashboardadres in te stellen. De eigen server moet vanaf de fotolijst bereikbaar zijn. Het voorbeeldadres `lightpanel.local` maakt zelf geen DNS-naam aan.

Voer vanaf de projecthoofdmap uit, nadat de debug-APK is gebouwd:

```sh
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n app.lightpanel.launcher/.MainActivity
```

Test laden, bediening en herstel na een tijdelijke verbindingsfout voordat je de app als standaardlauncher kiest. Kies daarna via Android **Home / Startscherm** de app **Light Panel** en **Altijd**. Het instelscherm kun je zo openen:

```sh
adb shell am start -a android.settings.HOME_SETTINGS
```

De APK is geregistreerd als Android HOME-app. Het app-ID is `app.lightpanel.launcher`; de persoonlijke launcher uit het oorspronkelijke project gebruikt een ander app-ID.

Krijg je een fout over een andere handtekening? Verwijder de bestaande app dan niet automatisch: controleer eerst of je dezelfde app en ondertekensleutel gebruikt. Verwijderen wist de appinstellingen.

## 6. Root in ADB is niet hetzelfde als root voor de app

De app opent zelf `su -c /system/bin/sh`. Een succesvolle `adb shell su -c id` bewijst niet dat de geïnstalleerde app dezelfde toestemming krijgt. Geef Light Panel, als jouw rootbeheer daarom vraagt, toegang en test daarna via de fotolijstbediening.

De website gebruikt een beperkte WebMessagePort naar de APK voor vaste opdrachten. Alleen de ingestelde dashboard-origin krijgt die koppeling. Andere websites krijgen geen algemene shelltoegang via de launcher.

## 7. LED's, scherm, klok en schermbeelden

| Functie | Huidige implementatie |
| --- | --- |
| LED-kleur | Root schrijft `<helderheid,rood,groen,blauw>` naar `/sdcard/frameo_light.txt`; ieder getal is 0–255 |
| LED uit | Frame `<0,0,0,0>` |
| Rood ademen | De APK berekent de animatie lokaal; ongeveer iedere 100 ms een update, cyclus van 3,2 seconden |
| Scherm uit | Achtergrondverlichting op het onderzochte pad naar 0; Android en de netwerkverbinding blijven actief |
| Scherm aan | Opgeslagen helderheid herstellen; een tik op het donkere scherm kan het weer aanzetten |
| LED en scherm samen | De LED-controller onderdrukt de LED wanneer het scherm uit staat en bewaart de gewenste stand |
| Klok | Referentietijd uit de dashboard-API, met terugval op NTP; root stelt de systeemklok in UTC in |
| Schermbeeld | De app maakt op verzoek een afbeelding van de dashboard-WebView, geen opname van alle Android-apps |

Het LED-bestand is een interface die op de oorspronkelijke fotolijst werd gebruikt. De bijbehorende firmware- of achtergrondlezer zit **niet** in Light Panel. Alleen dat bestand aanmaken levert op een willekeurige Android-tablet geen werkende LED's op. De herkomst en installatie van die lezer konden niet worden gereconstrueerd.

Voor het scherm kun je eerst alleen controleren of het bekende pad bestaat:

```sh
adb shell ls -l /sys/class/backlight/rk28_bl/brightness
adb shell cat /sys/class/backlight/rk28_bl/brightness
```

Als het pad ontbreekt, geldt deze hardwarebediening niet voor jouw model. Gebruik de appbediening om aan/uit te testen; de app bewaart en herstelt daarbij de helderheid.

Het oude shellscript `frameo_breathe.sh` is niet nodig voor de huidige animatie. Laat oude HA-ADB-scripts en de nieuwe APK niet tegelijk dezelfde LED aansturen.

## 8. WebView en herstel

Bij het oorspronkelijke apparaat speelden fouten met de systeem-WebView en ARM32-bibliotheken. Een oude chat noemt uiteindelijk een geladen WebView 106. Dat is historische informatie, geen advies om die oude browserengine nu opnieuw te installeren.

Controleer je eigen actieve provider met:

```sh
adb shell dumpsys webviewupdate
```

Bij een crash kun je recente foutinformatie ophalen:

```sh
adb logcat -d -b crash -v time
```

Controleer logs voordat je ze deelt: URL's en andere apparaatgegevens kunnen persoonlijk zijn. Deze handleiding overschrijft geen systeem-WebView, wijzigt geen `/system`-bestanden en bevat geen firmware-image.

Kom je niet meer bij de Android-instellingen, probeer via een werkende ADB-verbinding:

```sh
adb shell am start -a android.settings.SETTINGS
adb shell input keyevent 3
```

De tweede opdracht gaat naar HOME. Welke app daar opent, hangt af van de ingestelde standaardlauncher. Bewaar een werkende alternatieve launcher totdat Light Panel stabiel draait.

## Wat ontbreekt nog?

- De oorspronkelijke herkomst of installatie van `su` en `daemonsu`.
- Een bevestigde rootprocedure voor een niet-geroot exemplaar van dezelfde firmware.
- De herkomst van de LED-bestandslezer op de fotolijst.
- Een volledige, gecontroleerde firmware-back-up en herstelprocedure voor elk ondersteund model.

MaskROM, testpunten en het vervangen van systeemonderdelen kwamen als mogelijkheden langs, maar zijn niet als uitgevoerde succesvolle rootmethode teruggevonden. Daarom staan ze hier niet als installatie-instructie.
