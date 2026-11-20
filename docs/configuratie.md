# Configuration

**English** · [Nederlands](configuratie.nl.md)

The examples contain fictional entities and no working credentials. Copy `config.example.json` to `config/settings.json` and replace the values with your own. The local file completely replaces the empty `config.json` starter configuration.

## Files

| File | Purpose |
| --- | --- |
| `.env` | Local URLs and secret tokens; excluded from Git |
| `config/settings.json` | Your entities, cameras and actions; excluded from Git |
| `config.json` | Empty fallback configuration |
| `photos/` | Your photos; excluded from Git |
| `notification-history/` | Local notification history and, if generated, webhook key |

## Home Assistant

`HA_URL` is the reachable base URL without `/api`. `HA_TOKEN` is the long-lived token without a `Bearer` prefix. The backend receives changes through a WebSocket and reconnects after a failure. `localhost` inside Docker is the container itself, not your HA server.

| Setting | Source |
| --- | --- |
| `battery` | Battery state of charge (%) |
| `battery_power` | Battery power (W); verify the sign |
| `battery_charge_positive` | `true` if positive power means charging |
| `power` / `dashboard.house_power` | House consumption (W) |
| `solar` | Current solar production (W) |
| `energy.Stroomprijs` | Electricity price; verify €/kWh versus ct/kWh |
| `weather` | Your HA weather entity |
| `dashboard.indoor_temperature` | Indoor temperature (°C) |
| `dashboard.indoor_co2` | CO₂ (ppm) |
| `dashboard.hot_water_temperature` | Hot water (°C) |
| `dashboard.heat_pump_power` | Heat pump power (W) |
| `notifications.garage_entity` | Garage door open/closed sensor |
| `cameras` | Display names mapped to HA camera entities |
| `thermostats` | Display names mapped to HA climate entities |
| `calendar_ids` | Your HA calendar entity IDs |
| `websites` | Your domains without `https://` |

Keep unused lists empty and remove optional entities you do not have. An unconfigured garage does not produce a garage warning; a configured but unavailable sensor can show an unknown state.

Set `feed_notifications.battery_capacity_kwh` to your own real battery capacity. `feed_notifications.battery_min_soc_entities` is a list of sensors reporting the minimum allowed charge in percent. Available energy above the reserve is not invented without the required values.

The fan examples use `fan.set_preset_mode` with `timer1`, `timer2` and `timer3`. These are device-specific examples, not standard presets for every fan. Replace them with your own supported services or scripts.

## Tibber, Victron and solar forecasts

Set `TIBBER_TOKEN` in `.env` for personal Tibber data. The detail page is `/tibber`. Without a token, personal data remains empty.

For Victron use your own `VRM_SITE_ID` and `VRM_TOKEN`. Available planning and readings depend on your installation and VRM configuration. This integration reads data; it is not intended to change your ESS configuration.

The `solar_forecast` fields refer to your own HA sensors. Check their units and periods before comparing forecasts with measurements.

## Notifications, webhooks and devices

Open `/beheer/fotolijst` for online frames, native screen/LED controls, sound and the webhook URL/key. Capabilities depend on the Android app and hardware.

The server generates a local webhook key if none was configured. Alternatively, set `FRAMEO_WEBHOOK_TOKEN` in `.env` (at least 32 characters). HA uses `Bearer YOUR_KEY` in its own `secrets.yaml`; this is a separate key from `HA_TOKEN`.

Use the [generic HA package](../home-assistant/README.md) for scripts, a control view and disabled example automations. No private automation is copied or installed automatically.

Camera names in webhook messages are configuration aliases, not `camera.*` entity IDs. For example, the supplied configuration uses `Voordeur`; map that alias to your own camera, or choose your own alias and use it consistently.

## Troubleshooting

- Missing readings: check URL, token and exact entity IDs.
- Port already in use: change `PORT` in `.env` and restart.
- After editing configuration: check JSON syntax and restart the container.
- Camera missing: first check the camera in HA, then the alias mapping.
- Logs: `docker compose logs --tail=100 light-panel`. Check for personal values before sharing logs.
- Restart after environment/settings changes: `docker compose up -d --force-recreate`.
