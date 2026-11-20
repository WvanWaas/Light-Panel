# Build your own Light Panel with AI

**English** · [Nederlands](AI-START.nl.md)

Use Light Panel as a starting point in Codex, Claude Code, Cursor or another AI coding editor. Work in your own copy; access to the original installation is not needed.

## Start with your own repository

Choose **Use this template → Create a new repository** on GitHub, clone it and open the folder in your editor. Alternatively, download the source ZIP. First run the unmodified project using the [README](../README.md) so you know the Docker setup works. Without integrations, empty readings are expected.

Keep photos in `photos/`, credentials in `.env` and device mappings in `config/settings.json`. They should remain local and are ignored by Git. Consider a private repository when adding your own household information.

## Copy this prompt

```text
Help me turn this Light Panel repository into my own home dashboard.
Work directly in this project folder. First read README.md,
docs/configuratie.md, NOTICE.md and the existing code. Check for AGENTS.md.

My requirements:
- Device: [tablet/frame/browser], resolution [width x height],
  orientation [portrait/landscape], viewing distance [about ... metres].
- Style: [dark/light/calm], accent colour [...], large readable numbers.
- Home screen: [photos, energy, climate, calendar, ...].
- Notifications: [doorbell, garage, washing machine, ...].
- Controls: [lights, ventilation, thermostat, ...].
- Integrations: [Home Assistant, Tibber, Victron, none, ...].
- Things I do not have or want: [...].

Give a short proposal based on the existing capabilities. Ask only for
missing information that materially affects the result. Then build a small
working version, check it in a browser and continue in manageable steps.

Use config/settings.json for my entity mappings and .env for secrets.
Ask me to enter tokens locally; do not ask me to paste secrets into chat.
Never include tokens in logs, screenshots, examples or commits.
Do not read .env or personal photos unless the task actually requires it.
Keep config.json and config.example.json generic and suitable for sharing.
Do not reuse the original owner's personal data, photos or branding.

Preserve existing features unless I ask to remove them. Handle missing
sensors and failed integrations gracefully. Do not invent live values;
label demonstrations clearly. Do not install software on or control real
devices without my instruction.

Check relevant changes. Explain what changed, how to start it, what was
verified and what I still need to configure. Do not publish anything or
change HA automations without my instruction. Preserve GPLv3 and
third-party license notices.
```

You can request a different design too. Ask the AI to identify which existing parts it reuses and which it replaces.

## Give useful information, not secrets

Provide a short list of the entity IDs and units needed for your requested feature. The example configuration uses fictional `sensor.example_battery_soc` (%), `sensor.example_battery_power` (W), `sensor.example_house_power` (W), `sensor.example_solar_power` (W), `sensor.example_room_temperature` (°C), `sensor.example_co2` (ppm), `binary_sensor.example_garage_open` and `camera.example_frontdoor`.

Explain whether positive battery power means charging or discharging, its capacity and minimum charge. Specify price units (€/kWh or ct/kWh), garage sensor states and whether fan numbers mean minutes or speed. For notifications, define the trigger, duration and dismissal behaviour.

Do not paste a full HA state dump: it may include locations, camera information and personal URLs. Share only the subset required, and review it before sending it to an external AI service.

## Source map

| Area | Starting point |
| --- | --- |
| Startup and Docker | `README.md`, `compose.yaml`, `Dockerfile` |
| Settings | `settings.py`, `config.json`, `config.example.json`, `.env.example` |
| Backend / HA | `app.py`, `sync.py`, `entity_filter.py` |
| Main UI | `static/index.html`, `static/app.js`, `static/style.css` |
| Home energy | `static/home-energy.js`, `static/homehub.js` |
| Tibber / Victron | `tibber_data.py`, `vrm_planning.py`, `static/tibber/` |
| Messages / controls | `frameo_remote.py`, `static/frameo-message.js`, `static/frameo-admin.js` |
| Feed | `feed_events.py`, `live_ticker.py`, `static/ticker.js` |
| HA examples | `home-assistant/README.md`, `home-assistant/packages/` |
| Android / startup | `android/`, `docs/android.md` |

This is a map, not a complete specification: have the AI inspect the current code. Frameo remains in several technical paths for compatibility.

## Iterate in small steps

Useful follow-up prompts:

- “Adapt the home screen to an 800 x 1280 portrait tablet. Keep energy and climate readable from three metres.”
- “I have no home battery. Hide that area and emphasise house consumption.”
- “Notify me after five minutes above 1,500 ppm CO₂, and clear the notification below 900 ppm.”
- “Create a clearly labelled demo mode with fictional values.”
- “Review my entity mappings without controlling devices or modifying automations.”

Commit working steps and inspect the file list before each commit. Adding a file to `.gitignore` does not remove a version that was already committed.

## Verify

After source changes, run `docker compose up -d --build` and open `http://localhost:8089`. Check empty/missing-sensor states and your actual screen size. See the README for the basic, webhook and optional HA-template checks.

Screen/LED access is hardware-specific. Do not let an AI assume all tablets share the same root permissions or interfaces. For a dedicated frame, explicitly include the one-time default-HOME selection and reboot/power-cycle test.

Keep management on a trusted LAN. General management pages have no login; a webhook key only protects the webhook. Ask separately for an appropriate authenticated remote-access design if needed.

## License

The current source uses [GPLv3](../LICENSE), GPL-3.0-only. Follow source-distribution and license obligations when sharing modifications. The initial public version was MIT; see [NOTICE](../NOTICE.md). AI-assisted editing does not remove existing license conditions.
