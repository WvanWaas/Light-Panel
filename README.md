# Light Panel

Een persoonlijk dashboard voor een fotolijst, tablet of browser. Foto’s staan centraal, met energie, klimaat en meldingen binnen handbereik.

Deze startversie bevat geen persoonlijke foto’s, huisplattegrond, logo, accountgegevens of geschiedenis van het oorspronkelijke project. Koppelingen zijn optioneel en starten leeg. Zonder Home Assistant zie je nog geen eigen meetwaarden; dit is een startscherm, geen gevulde demo.

## Beginnen in vijf minuten

Installeer Docker met Docker Compose. Open een terminal in deze map en voer uit:

```sh
cp .env.example .env
docker compose up -d --build
```

Open **http://localhost:8089**. Poort 8080 op de computer blijft beschikbaar voor andere toepassingen. Stoppen kan met `docker compose down`; lokale instellingen en meldingen blijven bewaard.

## Je eigen Home Assistant verbinden

1. Maak in Home Assistant via je gebruikersprofiel een langlevend toegangstoken.
2. Vul in `.env` je eigen `HA_URL` en `HA_TOKEN` in. Zowel een lokaal adres als je eigen HTTPS-adres via Nabu Casa kan werken, mits bereikbaar vanaf de Docker-container.
3. Kopieer de voorbeeldinstellingen:

   ```sh
   cp config.example.json config/settings.json
   ```

4. Vervang de `example_*` entiteiten door je eigen entiteiten uit **Ontwikkelaarstools → Statussen**. Verwijder onderdelen die je niet hebt. Het hele configuratiebestand wordt ingelezen; dit is geen gedeeltelijke aanvulling op het voorbeeld.
5. Herstart na een wijziging aan instellingen of `.env`:

   ```sh
   docker compose up -d --force-recreate
   ```

Zie [de configuratiegids](docs/configuratie.md) voor sensoren, camera’s, energie en acties. Pas voorbeeldacties aan jouw apparaten aan voordat je ze gebruikt.

## Foto’s

Plaats je eigen foto’s in `photos/` en vernieuw de pagina. Je foto’s en lokale instellingen zijn uitgesloten van Git en van de Docker-image. Ze worden via lokale mappen aan de container gekoppeld.

## Wat kan het dashboard?

- Foto’s en een fotostand op volledig scherm.
- Energiekaart met batterijpercentage, actueel verbruik, zon en stroomprijs.
- Tibber-detail met dag, week, maand en jaar, kosten en teruglevering.
- Optioneel Victron-planning en zonverwachting.
- Klimaat, CO₂, tapwater, ventilatie en thermostaten.
- Meldingen met historie, filters en animaties; camerafoto’s en garagebeeld in beeld.
- Kalender, weer, nieuws en instelbare websitecontrole.
- Fotolijstbediening, webhooks en grote meldingen. Geluid is instelbaar.
- Optionele Android-kiosk met scherm- en LED-bediening op ondersteunde hardware.

Wat zichtbaar werkt, hangt af van je eigen koppelingen en sensoren. Hardwarefuncties zijn niet beschikbaar in een gewone browser. De naam Frameo komt nog voor in technische routes en onderdelen voor compatibiliteit.

## Op een tablet of fotolijst

De standaard is alleen toegankelijk op deze computer. Voor apparaten op je eigen netwerk zet je in `.env`:

```dotenv
BIND_ADDRESS=0.0.0.0
```

Herstart en open `http://IP-VAN-JE-SERVER:8089` op je apparaat. Gebruik eerst een gewone browser. Voor de optionele kioskbroncode zie [Android](docs/android.md).

Het dashboard bevat bediening voor je huis en een beheerpagina zonder algemene aanmeldbeveiliging. Gebruik deze instelling daarom alleen op een vertrouwd lokaal netwerk; zet poort 8089 niet rechtstreeks open naar internet. De webhook heeft een eigen sleutel, maar die beveiligt niet de overige beheerfuncties. Bewaar tokens uitsluitend in je eigen `.env` en deel dat bestand niet.

## Updates en bijdragen

Na wijzigingen aan broncode: `docker compose up -d --build`. Bij een herstart van de backend kunnen geopende dashboardpagina’s automatisch vernieuwen.

Deze map is bedoeld als een zelfstandig project met een nieuwe Git-geschiedenis. Maak hiervoor een **nieuwe repository** en zet die desgewenst later om naar een GitHub-template. Maak geen publieke fork van een persoonlijke repository waarvan de oude geschiedenis gevoelige gegevens kan bevatten.

De projectlicentie is nog niet gekozen. Publiceer en verspreid het project pas nadat die keuze is vastgelegd. Zie [NOTICE](NOTICE.md) voor meegeleverde bronnen.
