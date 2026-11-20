# Home Assistant webhook package

**English** · [Nederlands](README.nl.md)

Control Light Panel screens and full-screen messages from Home Assistant. All addresses, keys and entities are placeholders. HA does not need an ADB integration: it contacts the dashboard server, and the Android app handles supported hardware.

## 1. Prepare the server and frame

Start Light Panel using the [main README](../README.md). Make the server reachable from HA and the frame: the Docker default is localhost-only, so use `BIND_ADDRESS=0.0.0.0` in your own `.env` for a trusted LAN and restart the container.

Open the native Android app, then visit `/beheer/fotolijst` on the same dashboard server. A hardware frame must appear online. Ordinary browser instances do not receive these webhook commands.

Open **Webhook** in that page and copy its URL/key to your own HA configuration. Alternatively, set your own `FRAMEO_WEBHOOK_TOKEN` in `.env` (at least 32 characters) and restart Docker. This key is separate from the HA access token. The webhook URL belongs to **Light Panel**, not Home Assistant.

## 2. Add secrets

Copy the two entries from [secrets.example.yaml](secrets.example.yaml) into your own `/config/secrets.yaml` and replace both examples. Authorization is `Bearer ` followed by one space and the complete key.

Use a server address reachable from HA. `localhost` inside HA points to HA itself; `lightpanel.local` is only a placeholder and does not create a DNS record. Do not put real keys in shared example files.

## 3. Install the package

Copy `packages/light_panel.yaml` to `/config/packages/light_panel.yaml`. Enable packages in `configuration.yaml` as shown in [configuration.example.yaml](configuration.example.yaml):

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Merge this into an existing `homeassistant:`/packages configuration; do not duplicate YAML keys. Do not copy the secrets, configuration example or dashboard view into the packages directory.

Validate the HA configuration, then restart HA. Reloading scripts alone is insufficient when first adding `rest_command`. This repository does not install anything automatically on a live HA server.

## 4. Test

In **Developer tools → Actions**, run:

```yaml
action: script.light_panel_test
```

Every currently online hardware frame should wake and show a 15-second test message. Offline frames are not queued for later delivery; an offline or partially delivered command is reported as an error.

Use [dashboard-view.yaml](dashboard-view.yaml) as a new Lovelace view for screen on/off, photo mode, dashboard mode, next photo, refresh and test messages.

## Scripts

| Script | Purpose |
| --- | --- |
| `script.light_panel_test` | Test message, no parameters |
| `script.light_panel_screen_on` | Screen on and resume the desired LED state |
| `script.light_panel_screen_off` | Backlight and LEDs off; connection stays active |
| `script.light_panel_photo` | Photo mode |
| `script.light_panel_dashboard` | Normal dashboard |
| `script.light_panel_next_photo` | Next photo |
| `script.light_panel_reload` | Reload the page, not an Android reboot |
| `script.light_panel_message` | Custom full-screen message |
| `script.light_panel_message_clear` | Close the current full-screen message |
| `script.light_panel_command` | Another supported fixed command |

Without `device`, commands target all currently online hardware frames. To select one, copy its ID from the management page. All scripts except the parameterless test accept `device`; `light_panel_command` also requires a `command` object.

### Message with camera and duration

```yaml
action: script.light_panel_message
data:
  title: Someone is at the door
  text: The doorbell has been pressed.
  icon: doorbell
  color: "#338cc7"
  duration: 30
  wake: true
  camera: Voordeur
  camera_crop: full
```

`camera` is the alias in your Light Panel `cameras` configuration, not an HA `camera.*` entity or external URL. `Voordeur` is an alias used in the supplied example; map it to your own camera, or consistently use your own name. Omit the camera for an icon-only message. `left` crops to the left half. Images refresh during the message; this is not a video stream.

Duration is 0–3600 seconds. `0` remains until dismissed or replaced by another message. `wake: false` does not wake a dark screen; `wake: true` can deliberately interrupt your night schedule. Sound still follows its configured volume and allowed hours.

### One frame

```yaml
action: script.light_panel_screen_off
data:
  device: REPLACE_WITH_ID_FROM_MANAGEMENT_PAGE
```

### LED test

```yaml
action: script.light_panel_command
data:
  command:
    action: led_test
    color: "#ff7800"
    brightness: 80
```

Other fixed commands include `sound_test`, `sound_settings` with `enabled`/`volume` (0–100), `auto` with `enabled`, and `led_restore`. The server validates actions and values; arbitrary shell commands are not supported.

## Optional automations

Copy `packages/light_panel_examples.yaml` into the HA packages directory only if you want the examples:

- Doorbell with camera.
- Garage open with camera.
- Washer finished, two minutes after its running sensor turns off.
- Dishwasher finished using the same pattern.
- Alarm armed/disarmed with lock animation.
- Screen and LEDs off at 22:00.
- Screen on at 08:00.

**Every example is disabled** with `initial_state: false`. Replace all `example_*` entity IDs, check their real states and adjust camera names/times. Enable only the ones you want. To keep one enabled across HA restarts, remove its `initial_state: false` line; otherwise HA disables it again on startup.

The schedules are simple examples, not household-specific presence/TV rules. Use a reliable running/finished sensor: a power drop alone does not necessarily mean a cycle ended. Garage picture-in-picture additionally requires garage mappings in Light Panel. Avoid duplicate alerts if another automation or the dashboard already handles the same event.

## Startup after power returns

HA does not boot Android. Select **Light Panel → Always** as the frame’s default Home app once. The launcher and additional boot receiver return to Light Panel after an Android reboot only when it is the chosen HOME app. The page reloads once and retries while Wi-Fi/the server is unavailable.

See [Android setup and startup](../docs/android.md). Whether Android powers on when electricity returns is controlled by the device firmware/hardware. A webhook screen-off command is not an Android shutdown/reboot.

## Troubleshooting

| Result | Check |
| --- | --- |
| HTTP 401 | Key or `Bearer ` prefix incorrect |
| HTTP 409 | No hardware frame online or wrong device ID |
| HTTP 400 | Invalid action, camera, colour or duration |
| HTTP 502 / 504 | Missing/partial confirmation; check app, root and network |
| Connection refused / timeout | Server address, port, LAN binding or firewall |
| Missing camera | Alias must exactly match Light Panel configuration |

The key protects the webhook, not the other management pages. Use a trusted network and do not expose this service directly to the internet.

Sources: [packages](https://www.home-assistant.io/docs/configuration/packages/), [RESTful Command](https://www.home-assistant.io/integrations/rest_command/), [scripts](https://www.home-assistant.io/integrations/script/).
