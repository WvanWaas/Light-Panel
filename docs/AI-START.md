# Maak jouw eigen Light Panel met AI

Je kunt Light Panel als uitgangspunt gebruiken in bijvoorbeeld Codex, Claude Code, Cursor of een andere AI-code-editor. Laat de AI in jouw eigen kopie van het project werken. Je hebt geen toegang tot de oorspronkelijke installatie nodig.

## 1. Begin met je eigen project

Klik op GitHub op **Use this template → Create a new repository** en kies je eigen naam. Kloon jouw nieuwe repository en open die map in je AI-editor. Je kunt ook de broncode als zip downloaden.

Start eerst de ongewijzigde versie volgens de [README](../README.md). Zo weet je of Docker en de basis werken voordat je het uiterlijk of koppelingen verandert. Zonder koppelingen zijn de meetwaarden leeg; dat is normaal.

Gebruik voor eigen foto's `photos/`, voor koppelingen `.env` en voor je apparaten `config/settings.json`. Die bestanden horen lokaal te blijven en zijn uitgesloten van Git. Een privé-repository is verstandig wanneer je later eigen huisgegevens aan je project toevoegt.

## 2. Vertel de AI wat jij wilt

Kopieer deze prompt naar je AI-editor en vul de stukken tussen vierkante haken in:

```text
Ik wil met deze Light Panel-repository mijn eigen thuisdashboard maken.
Werk direct in deze projectmap. Lees eerst README.md, docs/configuratie.md,
NOTICE.md en de bestaande code. Controleer eventuele AGENTS.md-instructies.

Mijn wensen:
- Scherm: [tablet/fotolijst/browser], resolutie [breedte × hoogte],
  oriëntatie [staand/liggend], kijkafstand [ongeveer ... meter].
- Stijl: [rustig/donker/licht], accentkleur [kleur], grote leesbare cijfers.
- Hoofdscherm: [foto, energie, klimaat, agenda, ...].
- Meldingen: [deurbel, garage, wasmachine, ...].
- Bediening: [lampen, ventilatie, thermostaat, ...].
- Koppelingen: [Home Assistant, Tibber, Victron, geen, ...].
- Wat ik niet heb of niet wil: [...].

Maak eerst een kort voorstel op basis van de bestaande mogelijkheden.
Vraag alleen om ontbrekende informatie die een wezenlijk verschil maakt.
Maak daarna een kleine werkende eerste versie en controleer die in de browser.
Werk vervolgens stapsgewijs verder.

Gebruik config/settings.json voor mijn entiteiten en .env voor geheime waarden.
Vraag mij om tokens zelf lokaal in te vullen; laat mij ze niet in de chat plakken.
Toon geen tokenwaarden in logs, screenshots, voorbeeldcode of commits.
Lees geen .env of persoonlijke foto's als dat voor de wijziging niet nodig is.
Houd config.json en config.example.json geschikt als lege/generieke start.
Gebruik geen persoonlijke gegevens, afbeeldingen of logo's van de maker.

Laat bestaande functies werken, tenzij ik vraag ze te verwijderen.
Behandel gegevens die ontbreken of een koppeling die uitvalt als een normale
situatie. Verzin geen live waarden en presenteer voorbeelddata duidelijk als
voorbeeld. Installeer of bedien geen echte apparaten zonder mijn opdracht.

Controleer de relevante wijzigingen. Rapporteer wat is aangepast, hoe ik het
start, wat getest is en welke instellingen ik nog zelf moet invullen.
Publiceer niets en wijzig geen Home Assistant-automations zonder mijn opdracht.
Behoud GPLv3 en de licentievermeldingen van derden.
```

Je kunt ditzelfde uitgangspunt ook gebruiken om een ander ontwerp te laten maken. Laat de AI dan expliciet aangeven welke onderdelen uit Light Panel worden hergebruikt en welke opnieuw worden gemaakt.

## 3. Geef bruikbare informatie, zonder geheimen

Een AI kan veel gerichter werken met een korte lijst van je entiteiten en hun eenheden. Bijvoorbeeld:

| Functie | Voorbeeld van een entiteit | Eenheid / betekenis |
| --- | --- | --- |
| Batterijlading | `sensor.example_battery_soc` | % |
| Batterijvermogen | `sensor.example_battery_power` | W; positief betekent laden of ontladen? |
| Huisverbruik | `sensor.example_house_power` | W |
| Zonnepanelen | `sensor.example_solar_power` | W |
| Stroomprijs | `sensor.example_electricity_price` | €/kWh of ct/kWh? |
| Temperatuur | `sensor.example_room_temperature` | °C |
| CO₂ | `sensor.example_co2` | ppm |
| Garage | `binary_sensor.example_garage_open` | on = open? |
| Camera | `camera.example_frontdoor` | Camerafoto beschikbaar in HA? |

Dit zijn fictieve voorbeelden. Kopieer geen volledig HA-statusoverzicht: dat kan locaties, camerabeelden, URL's en andere persoonlijke gegevens bevatten. Deel alleen wat voor je gekozen functie nodig is. Controleer de gegevens ook voordat je ze naar een externe AI-dienst stuurt.

Vertel bij een batterij ook de capaciteit, minimumlading en het teken van het vermogen. Geef bij ventilatie aan of getallen minuten of snelheden zijn. Geef voor meldingen aan wanneer ze beginnen, hoe lang ze blijven en hoe je ze wegklikt.

## 4. Waar vindt de AI de onderdelen?

| Onderdeel | Begin hier |
| --- | --- |
| Starten en Docker | `README.md`, `compose.yaml`, `Dockerfile` |
| Instellingen en voorbeelden | `settings.py`, `config.json`, `config.example.json`, `.env.example` |
| Backend en HA-verbinding | `app.py`, `sync.py`, `entity_filter.py` |
| Hoofdscherm en opmaak | `static/index.html`, `static/app.js`, `static/style.css` |
| Energie op het hoofdscherm | `static/home-energy.js`, `static/homehub.js` |
| Tibber en Victron | `tibber_data.py`, `vrm_planning.py`, `static/tibber/` |
| Meldingen en fotolijstbediening | `frameo_remote.py`, `static/frameo-message.js`, `static/frameo-admin.js` |
| Meldingenfeed | `feed_events.py`, `live_ticker.py`, `static/ticker.js` |
| Android-app | `android/`, `docs/android.md` |

Laat de AI voor een wijziging eerst de actuele code lezen; deze tabel is een wegwijzer, geen volledige technische specificatie. De naam Frameo blijft in een aantal routes en bestandsnamen staan voor compatibiliteit.

## 5. Werk in kleine stappen

Goede vervolgopdrachten zijn bijvoorbeeld:

- “Maak het hoofdscherm geschikt voor een staande tablet van 800 × 1280. Laat energie en klimaat leesbaar op drie meter afstand.”
- “Ik heb geen thuisbatterij. Verberg de batterijweergave en geef huisverbruik meer ruimte.”
- “Voeg een melding toe wanneer mijn CO₂-sensor vijf minuten boven 1.500 ppm staat. Wis de melding onder 900 ppm.”
- “Maak een rustige voorbeeldstand met fictieve waarden, duidelijk als demo gemarkeerd.”
- “Controleer de entiteiten die ik heb ingesteld. Verander geen HA-apparaten of automations.”

Bewaar elke werkende stap in Git. Controleer vóór een commit welke bestanden meegaan. Een uitgesloten bestand dat ooit al in Git is gezet, verdwijnt niet automatisch door `.gitignore`.

## 6. Controleren en starten

Na broncodewijzigingen:

```sh
docker compose up -d --build
```

Open `http://localhost:8089`. Test ook de lege toestand, een ontbrekende sensor en het schermformaat van jouw apparaat. De meegeleverde startcontroles kun je draaien met:

```sh
docker compose run --rm light-panel python -m unittest discover -s tests -v
```

Scherm- en LED-bediening in de Android-app zijn hardwareafhankelijk. Laat een AI niet aannemen dat iedere Android-tablet dezelfde LED-interface of toegangsrechten heeft. Begin met de browserweergave.

Gebruik het dashboard op een vertrouwd lokaal netwerk. De gewone beheerpagina's hebben geen algemene aanmeldbeveiliging; een webhook-sleutel beschermt alleen de webhook. Vraag apart om een passende veilige toegangsoplossing als je het van buiten je netwerk wilt gebruiken.

## Licentie

De huidige versie valt onder [GNU GPLv3](../LICENSE) (GPL-3.0-only). Houd bij verspreiding van wijzigingen rekening met de verplichtingen voor bijbehorende broncode en licentieteksten. De eerste openbare versie was MIT; zie [NOTICE](../NOTICE.md). AI gebruiken om de code aan te passen verandert de bestaande licentievoorwaarden niet.
