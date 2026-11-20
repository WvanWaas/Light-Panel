[English](README.md) · **Nederlands**

# Home Assistant-webhookpakket voor Light Panel

Met dit pakket stuur je vanuit Home Assistant schermopdrachten en grote meldingen naar Light Panel. Er zijn geen persoonlijke adressen, tokens of sensoren ingevuld. Je hoeft geen ADB-integratie in HA te installeren: HA praat met de dashboardserver; de Android-app bedient de hardware.

## 1. Dashboard en fotolijst voorbereiden

1. Start Light Panel volgens de [README](../README.nl.md).
2. Maak de server bereikbaar vanaf HA en de fotolijst. De Docker-standaard bindt alleen op localhost. Voor je vertrouwde LAN stel je in `.env` `BIND_ADDRESS=0.0.0.0` in en herstart je de container.
3. Open de Android-app en daarna de dashboardpagina `/beheer/fotolijst` op dezelfde server. Er moet een hardwarefotolijst online staan. Een gewone browser krijgt deze opdrachten niet.
4. Open daar **Webhook**. Kopieer de URL en sleutel naar je eigen HA-configuratie. Deel de sleutel niet.

Je kunt ook zelf `FRAMEO_WEBHOOK_TOKEN` in de eigen `.env` instellen (minstens 32 tekens). Herstart Docker na wijzigingen. De webhook gebruikt die sleutel, niet je HA-toegangstoken. De URL is die van de **Light Panel-server**, niet de URL van Home Assistant.

## 2. Secrets instellen

Voeg de twee regels uit [secrets.example.yaml](secrets.example.yaml) toe aan je eigen `/config/secrets.yaml` en vervang beide voorbeelden. De autorisatie bevat `Bearer `, één spatie en de volledige sleutel.

Gebruik bij de URL een naam of adres dat HA echt kan bereiken. `localhost` in HA wijst naar HA zelf; `lightpanel.local` is slechts een voorbeeld en wordt niet automatisch aangemaakt. Houd in voorbeeldbestanden alleen placeholders.

## 3. Pakket plaatsen

Kopieer alleen `packages/light_panel.yaml` naar `/config/packages/light_panel.yaml`.

Activeer packages in `configuration.yaml`, zoals in [configuration.example.yaml](configuration.example.yaml):

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Heb je al een `homeassistant:`-blok of een packages-instelling, voeg dit daarin samen. Maak geen dubbele YAML-sleutels. Kopieer `secrets.example.yaml`, `configuration.example.yaml` en `dashboard-view.yaml` niet naar de packages-map.

Controleer de HA-configuratie en herstart Home Assistant. Alleen scripts herladen is bij de eerste installatie van `rest_command` niet voldoende. Dit pakket wordt niet automatisch geïnstalleerd op een bestaande HA-server.

## 4. Eerste test

Ga naar **Ontwikkelaarstools → Acties** en voer uit:

```yaml
action: script.light_panel_test
```

Alle online hardwarefotolijsten tonen nu een testmelding van 15 seconden. Het scherm wordt wakker gemaakt. Er is geen opdrachtwachtrij op de server voor uitgeschakelde of offline fotolijsten; een offline fout wordt teruggegeven aan HA. Gedeeltelijke bezorging wordt ook als fout gemeld.

Je kunt [dashboard-view.yaml](dashboard-view.yaml) als nieuwe Lovelace-weergave gebruiken voor scherm aan/uit, foto’s, dashboard, volgende foto, vernieuwen en testmeldingen.

## Beschikbare scripts

| Script | Functie |
| --- | --- |
| `script.light_panel_test` | Testmelding zonder parameters |
| `script.light_panel_screen_on` | Scherm aan; automatische LED-aansturing hervatten |
| `script.light_panel_screen_off` | Scherm én LED’s uit; dashboardverbinding blijft actief |
| `script.light_panel_photo` | Fotostand |
| `script.light_panel_dashboard` | Normaal dashboard |
| `script.light_panel_next_photo` | Volgende foto |
| `script.light_panel_reload` | Webpagina opnieuw laden, geen Android-reboot |
| `script.light_panel_message` | Instelbare volbeeldmelding |
| `script.light_panel_message_clear` | Huidige volbeeldmelding sluiten |
| `script.light_panel_command` | Een andere ondersteunde vaste webhookopdracht |

Zonder `device` gaat een opdracht naar alle **op dat moment online** hardwarefotolijsten. Voor één specifieke fotolijst kopieer je het ID uit de beheerpagina. Alle scripts behalve de parameterloze test accepteren `device`; bij `light_panel_command` is ook `command` verplicht.

### Melding met eigen duur en camera

```yaml
action: script.light_panel_message
data:
  title: Er is aangebeld
  text: Er staat iemand voor de deur.
  icon: doorbell
  color: "#338cc7"
  duration: 30
  wake: true
  camera: Voordeur
  camera_crop: full
```

`camera` is de **naam uit `cameras` in jouw Light Panel `config/settings.json`**, bijvoorbeeld `Voordeur`; het is geen `camera.*`-entiteit of externe URL. Koppel die naam zelf aan je eigen HA-camera. Zonder camera laat je het veld weg. Voor `left` wordt alleen de linkerhelft getoond. Camerafoto’s worden tijdens de melding periodiek vernieuwd; het is geen videostream.

De duur is 0–3600 seconden. `0` blijft staan tot iemand de melding sluit of een volgende melding deze vervangt. `wake: false` laat het scherm uit als het uit stond. Een melding met `wake: true` kan je nachtregeling dus bewust onderbreken. Volume en de ingestelde geluidsuren blijven gelden.

### Eén fotolijst kiezen

```yaml
action: script.light_panel_screen_off
data:
  device: VUL_HIER_HET_ID_UIT_DE_BEHEERPAGINA_IN
```

### LED of geluid testen

```yaml
action: script.light_panel_command
data:
  command:
    action: led_test
    color: "#ff7800"
    brightness: 80
```

Andere vaste opdrachten zijn bijvoorbeeld `sound_test`, `sound_settings` met `enabled` en `volume` (0–100), `auto` met `enabled`, en `led_restore`. De server controleert acties en waarden. Er is geen webhook voor willekeurige shellcommando’s.

## Voorbeeldautomations

Kopieer desgewenst `packages/light_panel_examples.yaml` naar dezelfde HA-packages-map. Dit bevat zeven voorbeelden:

- Deurbel met camerafoto.
- Garage open met camerafoto.
- Wasmachine klaar, twee minuten na de overgang van bezig naar niet bezig.
- Vaatwasser klaar op dezelfde manier.
- Alarm aan/uit met slotanimatie.
- Scherm en LED’s uit om 22:00.
- Scherm weer aan om 08:00.

**Alle voorbeelden staan uit** via `initial_state: false`. Vervang alle `example_*` entiteiten door je eigen sensoren en controleer hun werkelijke toestanden. Pas tijden en cameranaam aan. Schakel alleen het gewenste voorbeeld in. Voor blijvend inschakelen over HA-herstarts heen verwijder je uit dat voorbeeld de regel `initial_state: false`; anders zet HA het bij de volgende start weer uit.

De klokvoorbeelden zijn eenvoudige schema’s, geen persoonlijke aanwezigheid- of tv-logica. Een apparaat moet een betrouwbare draait/klaar-status leveren; willekeurig vermogensverlies betekent niet vanzelf dat de was klaar is. De garagecamera-in-beeld-functie vereist daarnaast je eigen garageconfiguratie in Light Panel. Vermijd dubbele deurbel-/garagemeldingen wanneer dezelfde gebeurtenis al door een andere automation of door het dashboard wordt gemeld.

## Stroom terug? De app hoort terug te komen

Dit HA-pakket is niet verantwoordelijk voor het starten van Android. Kies **Light Panel één keer als standaard HOME/startscherm → Altijd** op de fotolijst. De Android-app is een launcher en heeft een aanvullende bootontvanger die na een echte Android-herstart teruggaat naar Light Panel, alleen wanneer Light Panel de gekozen standaardlauncher is. De website wordt dan opnieuw geladen; bij ontbrekende wifi of server volgt automatisch opnieuw proberen.

Zie [Android installeren en automatisch starten](../docs/android.nl.md). Of een uitgeschakeld apparaat vanzelf boot zodra het voeding krijgt, wordt door de hardware/firmware bepaald; de app kan niet starten zolang Android zelf niet opstart. Alleen het scherm uitzetten via de webhook is geen Android-reboot.

## Problemen oplossen

| Resultaat | Controle |
| --- | --- |
| HTTP 401 | Verkeerde sleutel of ontbrekend `Bearer ` |
| HTTP 409 | Geen online hardwarefotolijst of verkeerde device-ID |
| HTTP 400 | Ongeldige opdracht, camera, kleur of duur |
| HTTP 502 / 504 | Niet alle opdrachten bevestigd; controleer app, root en verbinding |
| Verbinding geweigerd / timeout | HA bereikt de dashboardserver niet; controleer adres, poort, LAN-binding en firewall |
| Camera werkt niet | Cameranaam moet exact overeenkomen met de Light Panel-configuratie |

De sleutel beschermt de webhook. De overige beheerpagina’s hebben geen algemene aanmeldbeveiliging; gebruik een vertrouwd netwerk en publiceer deze poort niet rechtstreeks op internet.

Bronnen: [HA-packages](https://www.home-assistant.io/docs/configuration/packages/), [RESTful Command](https://www.home-assistant.io/integrations/rest_command/), [scripts](https://www.home-assistant.io/integrations/script/).
