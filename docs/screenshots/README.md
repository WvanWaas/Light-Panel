# Example screenshots

**English** · [Nederlands](README.nl.md)

Captured from the real Light Panel interface using synthetic data only. Every image carries a DEMO label. Values are not household measurements. Still images show a moment from animated notifications; the alarm images show their final state.

The three measurement charts are cropped for detail readability.

| Washing machine finished | Dishwasher finished |
| --- | --- |
| <a href="washer-finished.jpg"><img src="washer-finished.jpg" alt="Washing machine finished" width="350"></a> | <a href="dishwasher-finished.jpg"><img src="dishwasher-finished.jpg" alt="Dishwasher finished" width="350"></a> |

| Alarm armed | Alarm disarmed |
| --- | --- |
| <a href="alarm-armed.jpg"><img src="alarm-armed.jpg" alt="Alarm armed" width="350"></a> | <a href="alarm-disarmed.jpg"><img src="alarm-disarmed.jpg" alt="Alarm disarmed" width="350"></a> |

| Weather, sun and moon | Hourly and daily forecast |
| --- | --- |
| <a href="weather.jpg"><img src="weather.jpg" alt="Weather, sun and moon" width="350"></a> | <a href="weather-forecast.jpg"><img src="weather-forecast.jpg" alt="Hourly and daily forecast" width="350"></a> |

| Heat pump hot-water temperature | Indoor temperature history |
| --- | --- |
| <a href="heatpump-hot-water.jpg"><img src="heatpump-hot-water.jpg" alt="Heat pump hot-water temperature" width="350"></a> | <a href="indoor-temperature.jpg"><img src="indoor-temperature.jpg" alt="Indoor temperature history" width="350"></a> |

| Heat pump power history | Appliance power and daily energy |
| --- | --- |
| <a href="heatpump-power.jpg"><img src="heatpump-power.jpg" alt="Heat pump power history" width="350"></a> | <a href="appliance-energy.jpg"><img src="appliance-energy.jpg" alt="Appliance power and daily energy" width="350"></a> |

## Reproduce

With the project dependencies installed, run `python tools/screenshot_demo.py` from the repository root. Open `http://127.0.0.1:8093/` and choose an example. Controls hide automatically; Escape restores them. The preview never reads `.env`, contacts HA or controls a real device. Dates and sensor values are fixed synthetic examples.

The [HTML gallery](index.html) can also be opened locally with these image files.
