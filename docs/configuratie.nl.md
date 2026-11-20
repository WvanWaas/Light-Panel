[English](configuratie.md) · **Nederlands**

# Configuratie

Alle gegevens hieronder zijn voorbeelden. `.env.example` bevat geen werkende toegangssleutels. `config.example.json` bevat geen echte apparaten.

## Bestanden

| Bestand | Doel |
| --- | --- |
| `.env` | Lokale URL’s en geheime tokens; niet in Git |
| `config/settings.json` | Jouw sensoren, camera’s en acties; niet in Git |
| `config.json` | Lege standaard als er nog geen lokale instellingen zijn |
| `photos/` | Jouw foto’s; niet in Git |
| `notification-history/` | Lokale meldingenhistorie en eventueel gegenereerde webhook-sleutel |

## Home Assistant

`HA_URL` is het basisadres zonder `/api`, bijvoorbeeld je eigen lokale HA-adres. `HA_TOKEN` bevat het langlevende token, zonder `Bearer` ervoor. Het dashboard ontvangt statuswijzigingen via WebSocket en probeert bij verbindingsverlies opnieuw te verbinden.

Kies entiteiten uit jouw Home Assistant en vervang de voorbeelden in `config/settings.json`:

| Configuratiesleutel | Verwachte bron |
| --- | --- |
| `battery` | Batterijlading in procent |
| `battery_power` | Batterijvermogen in W; controleer het teken |
| `battery_charge_positive` | `true` als positief vermogen laden betekent |
| `power` / `dashboard.house_power` | Huisverbruik in W |
| `solar` | Huidige zonneproductie in W |
| `energy.Stroomprijs` | Sensor voor stroomprijs; controleer de eenheid |
| `weather` | Je HA-weersentiteit |
| `dashboard.indoor_temperature` | Binnentemperatuur in °C |
| `dashboard.indoor_co2` | CO₂ in ppm |
| `dashboard.hot_water_temperature` | Tapwatertemperatuur in °C |
| `dashboard.heat_pump_power` | Warmtepompvermogen in W |
| `notifications.garage_entity` | Open/dicht-sensor van je garagedeur |
| `cameras` | Namen gekoppeld aan HA-camera-entiteiten |
| `thermostats` | Namen gekoppeld aan HA-climate-entiteiten |
| `calendar_ids` | Lijst met jouw kalenderentiteiten |
| `websites` | Lijst met eigen domeinen zonder `https://` |

Laat optionele lijsten leeg en verwijder onbekende optionele entiteiten. Een niet-ingestelde garage geeft geen garagemelding. Een ingestelde maar onbereikbare sensor kan wel een onbekende status tonen.

Voor batterijruimte gebruikt `feed_notifications.battery_capacity_kwh` jouw werkelijke capaciteit. Er is geen persoonlijke batterijcapaciteit vooraf ingevuld. `feed_notifications.battery_min_soc_entities` is een lijst van jouw HA-sensoren voor de minimumlading in procent. Een ondergrens moet ook via je eigen configuratie/sensoren beschikbaar zijn; er wordt geen kWh-reserve verzonnen zonder benodigde meetwaarden.

De voorbeeldventilatie gebruikt `fan.set_preset_mode` met `timer1`, `timer2`, `timer3`. Alleen apparaten met deze standen ondersteunen dat. Vervang deze acties door passende services of je eigen HA-scripts. Er worden geen scripts in Home Assistant geïnstalleerd vanuit deze startversie.

## Tibber en Victron

Vul voor Tibber `TIBBER_TOKEN` in `.env` in. Zonder token blijven persoonlijke Tibbergegevens leeg. De detailpagina staat op `/tibber`.

Voor Victron gebruik je je eigen `VRM_SITE_ID` en `VRM_TOKEN`. Beschikbare planning en meetwaarden verschillen per installatie en VRM-configuratie. Deze koppeling is bedoeld om gegevens te lezen, niet om je ESS-instellingen te veranderen.

Zonverwachtingen onder `solar_forecast` verwijzen naar je eigen HA-sensoren. Controleer eenheden en verwachte intervallen voordat je ze vergelijkt met werkelijk opgewekte energie.

## Meldingen en bediening

Open `/beheer/fotolijst` voor aangesloten fotolijsten, scherm- en LED-bediening, geluid en de webhook. De daadwerkelijke mogelijkheden hangen af van de geïnstalleerde Android-app. Webhookopdrachten werken met de sleutel onder Webhook; deel die niet.

De beheerpagina genereert zo nodig een lokale sleutel. Je kunt ook zelf `FRAMEO_WEBHOOK_TOKEN` in `.env` instellen. In Home Assistant hoort de autorisatie als `Bearer JOUW_SLEUTEL` in een eigen secret. Je kunt meldingen met een grote afbeelding of camera gebruiken; er wordt geen HA-automation uit het privéproject meegeleverd. Gebruik het [generieke HA-webhookpakket](../home-assistant/README.nl.md) met voorbeeldscripts, een bedieningsweergave en uitgeschakelde voorbeeldautomations voor je eigen entiteiten.

## Problemen oplossen

- Geen waarden: controleer HA-adres, token en exacte entiteit-ID’s.
- `localhost` bij `HA_URL` verwijst binnen Docker naar de container zelf. Gebruik een bereikbaar HA-adres.
- Poort bezet: wijzig `PORT` in `.env` en herstart.
- Logs bekijken: `docker compose logs --tail=100 light-panel`. Deel geen geheime waarden uit je configuratie.
- Geen camera: controleer of HA zelf een camerabeeld geeft en of de naam in `cameras` klopt.
- Na configuratiewijziging: herstart de container; JSON moet geldig zijn.
