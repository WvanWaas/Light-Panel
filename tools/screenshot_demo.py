"""Local documentation preview with synthetic fixtures; never reads .env or contacts HA.

Run with the project's Python dependencies: python tools/screenshot_demo.py
Open http://127.0.0.1:8093, select an example; controls hide automatically for screenshots.
This tool does not change the production app or install/control any device.
"""
import argparse
import asyncio
import datetime as dt
import json
import math
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
NOW = dt.datetime(2026, 6, 12, 12, tzinfo=dt.timezone.utc)
DAY = NOW.date().isoformat()
INSTANCE = 'light-panel-synthetic-documentation-v1'
CFG = json.loads((ROOT / 'config.example.json').read_text())
CFG['notifications'] = {}
CFG['dashboard'].pop('alarm_entity', None)
CFG['dashboard'].pop('airco_entities', None)
CFG['dashboard']['climate_mode'] = 'sensor.example_heatpump_mode'
CFG['feed_notifications'] = {'battery_capacity_kwh': 10, 'battery_min_soc_entities': ['sensor.example_reserve']}
CFG['calendar_ids'] = []
CFG['countdown_calendar_ids'] = []
CFG['cameras'] = {}
CFG['power_display']['grid'] = 'sensor.example_grid_power'
HEAVY = [('heatpump', 'Warmtepomp', 650, 3.42), ('hob', 'Kookplaat', 850, 0.84),
         ('oven', 'Oven', 0, 1.12), ('hotwater', 'Kookkraan', 0, 0.24),
         ('microwave', 'Magnetron', 0, 0.18), ('washer', 'Wasmachine', 0, 0.76),
         ('dryer', 'Droger', 0, 1.63), ('dishwasher', 'Vaatwasser', 0, 0.91)]
MINOR = [('ventilation', 'Ventilatie', 200, 0.73), ('office', 'Kantoor', 75, 0.38),
         ('meter', 'Meterkast', 40, 0.46), ('media', 'Entertainment', 75, 0.54),
         ('other', 'Overig', 10, 0.12)]
STATES = {}


def row(entity, value, unit=None, **attributes):
    if unit is not None:
        attributes['unit_of_measurement'] = unit
    STATES[entity] = {'entity_id': entity, 'state': str(value), 'attributes': attributes,
                      'last_changed': NOW.isoformat(), 'last_updated': NOW.isoformat()}


for section, devices in [('heavy', HEAVY), ('minor', MINOR)]:
    CFG['power_display'][section] = []
    for key, label, watts, _ in devices:
        entity = 'sensor.example_' + key
        if key == 'heatpump':
            entity = CFG['dashboard']['heat_pump_power']
        CFG['power_display'][section].append({'key': key, 'label': label, 'entities': entity})
        row(entity, watts, 'W', friendly_name=label)
row(CFG['battery'], 68, '%')
row(CFG['battery_power'], 1500, 'W')
row(CFG['power'], 1900, 'W')
row(CFG['solar'], 3400, 'W')
row(CFG['energy']['Net nu'], 0, 'W')
row(CFG['energy']['Stroomprijs'], 0.24, 'EUR/kWh', min_price=0.18, max_price=0.43)
row(CFG['dashboard']['indoor_temperature'], 21.2, '°C')
row(CFG['dashboard']['hot_water_temperature'], 52.4, '°C')
row(CFG['dashboard']['indoor_co2'], 784, 'ppm')
row(CFG['dashboard']['ventilation'], 'Laag')
row('sensor.example_heatpump_mode', 'heating')
row('sensor.example_reserve', 15, '%')
row('sun.sun', 'above_horizon', elevation=42, azimuth=190)
row(CFG['weather'], 'partlycloudy', temperature=19.2, apparent_temperature=18.8,
    temperature_unit='°C', wind_speed=12.4, wind_speed_unit='km/h', humidity=63,
    pressure=1018, pressure_unit='hPa', precipitation_unit='mm', friendly_name='Demo weather')
for entity in CFG.get('thermostats', {}).values():
    row(entity, 'heat', current_temperature=21.2, temperature=21.5, hvac_action='heating',
        hvac_modes=['off', 'heat', 'auto'], min_temp=16, max_temp=26, target_temp_step=0.5)

app = FastAPI(title='Light Panel documentation fixtures')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
app.mount('/examples', StaticFiles(directory=ROOT / 'docs/screenshots', html=True), name='examples')


@app.get('/')
def page():
    html = (ROOT / 'static/index.html').read_text()
    extra = '''<style>
#docs-demo-controls{position:fixed;bottom:12px;left:12px;right:12px;z-index:2147483647;background:#071724ee;border:1px solid #5d8caa;border-radius:12px;padding:10px;display:flex;flex-wrap:wrap;gap:7px}
#docs-demo-controls[hidden]{display:none}#docs-demo-controls button{font:14px system-ui;padding:9px 12px;background:#213d50;color:white;border:1px solid #537086;border-radius:8px}
#docs-demo-label{position:fixed;top:8px;right:10px;z-index:2147483646;background:#06131ce8;color:#b7d6e5;border:1px solid #446379;border-radius:6px;padding:5px 9px;font:11px system-ui;letter-spacing:.04em;pointer-events:none}
</style><div id="docs-demo-label">DEMO · SYNTHETIC DATA</div>
<div id="docs-demo-controls" aria-label="Documentation examples">
<button onclick="docsMessage('washing-machine','Washing machine finished','Your laundry is ready.','#338cc7')">Washer finished</button>
<button onclick="docsMessage('dishwasher','Dishwasher finished','The dishes are clean.','#20a882')">Dishwasher finished</button>
<button onclick="docsMessage('lock','Alarm armed','Your home is protected.','#33bba0')">Alarm armed</button>
<button onclick="docsMessage('unlock','Alarm disarmed','Welcome home.','#6cb3e8')">Alarm disarmed</button>
<button onclick="docsPanel('weather')">Weather</button>
<button onclick="docsMeasurement('water')">Hot water temperature</button>
<button onclick="docsMeasurement('temperature')">Indoor temperature</button>
<button onclick="docsMeasurement('heatpump')">Heat pump power</button>
<button onclick="docsPanel('power-flow')">Appliance energy</button>
<button onclick="document.getElementById('docs-demo-controls').hidden=true">Hide controls</button>
</div><script>
function docsReset(){FrameoMessage.hide();window.FrameoPhotoMode?.showDashboard();}
function docsMessage(icon,title,text,color){docsReset();closePanel();document.getElementById('docs-demo-controls').hidden=true;FrameoMessage.show({icon,title,text,color,duration:0,silent:true});}
function docsPanel(name){docsReset();document.getElementById('docs-demo-controls').hidden=true;openPanel(name);}
function docsMeasurement(key){docsReset();document.getElementById('docs-demo-controls').hidden=true;openMeasurement(key);}
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('docs-demo-controls').hidden=false});
</script>'''
    return HTMLResponse(html.replace('</body>', extra + '</body>'))


@app.get('/api/time')
def clock():
    return {'server_time_ms': int(NOW.timestamp() * 1000)}


def state_payload():
    return {'backend_instance': INSTANCE, 'demo': True, 'config': CFG, 'states': STATES,
            'revision': 1, 'connection': {'mode': 'live'}, 'news': [], 'photos': [], 'alerts': []}


@app.get('/api/bootstrap')
@app.get('/api/states')
def bootstrap():
    return state_payload()


@app.get('/api/backend-version')
def version():
    return {'backend_instance': INSTANCE}


@app.websocket('/ws')
async def websocket(ws: WebSocket):
    await ws.accept()
    await ws.send_json({'type': 'states', **state_payload()})
    try:
        while True:
            await ws.receive_text()
            await ws.send_json({'type': 'pong', 'connection': {'mode': 'live'}})
    except WebSocketDisconnect:
        pass


@app.get('/api/weather')
def weather():
    hourly = [{'datetime': (NOW + dt.timedelta(hours=i)).isoformat(),
               'temperature': round(18 + 4 * math.sin(i / 4), 1),
               'precipitation': round(max(0, math.sin((i - 4) / 2)) * 1.3, 1),
               'precipitation_probability': 70 if 5 <= i <= 10 else 15,
               'condition': 'rainy' if 5 <= i <= 10 else 'partlycloudy'} for i in range(24)]
    daily = [{'datetime': (NOW + dt.timedelta(days=i)).isoformat(), 'temperature': 22 + i % 3,
              'templow': 13 + i % 2, 'precipitation': 1.2 if i % 2 else 0.1,
              'precipitation_probability': 65 if i % 2 else 15,
              'condition': 'rainy' if i % 2 else 'partlycloudy'} for i in range(5)]
    return {'entity_id': CFG['weather'], 'current': STATES[CFG['weather']],
            'timezone': CFG['timezone'], 'hourly': hourly, 'daily': daily, 'errors': []}


@app.get('/api/astronomy')
def astronomy():
    def at(hour, minute=0):
        return NOW.replace(hour=hour, minute=minute).isoformat()
    return {'date': DAY, 'timezone': CFG['timezone'], 'phase': 0.25,
            'phase_label': 'Eerste kwartier', 'sunrise': at(3, 20), 'sunset': at(20, 5),
            'moonrise': at(10, 15), 'moonset': at(23, 30)}


@app.get('/api/history/measurement')
def measurement(key: str = 'water', hours: int = 24):
    start = NOW - dt.timedelta(hours=hours)
    points = []
    for i in range(145):
        f = i / 144
        if key == 'water':
            value = 48.4 + 5.3 * max(0, math.sin(f * math.pi * 3)) - 1.1 * math.sin(f * 22)
        elif key == 'temperature':
            value = 20.2 + 1.2 * f + 0.3 * math.sin(f * 8)
        elif key == 'battery':
            value = 35 + 33 * f + 6 * math.sin(f * 4)
        elif key == 'solar':
            value = max(0, math.sin(f * math.pi * 2 - 1.5)) * 3600
        elif key == 'heatpump':
            value = 80 + 650 * max(0, math.sin(f * math.pi * 7))
        else:
            value = 150 + 50 * math.sin(f * 12)
        if i == 144 and key in {'water', 'temperature', 'battery', 'solar', 'heatpump'}:
            value = {'water': 52.4, 'temperature': 21.2, 'battery': 68, 'solar': 3400, 'heatpump': 650}[key]
        points.append({'time': (start + dt.timedelta(hours=hours * f)).isoformat(), 'value': round(value, 2)})
    label, unit = {'water': ('Tapwater warmtepomp', '°C'), 'temperature': ('Temperatuur woning', '°C'),
                   'battery': ('Batterijlading', '%'), 'solar': ('Zonnepanelen', 'W'),
                   'heatpump': ('Warmtepompvermogen', 'W')}.get(key, ('Verbruik', 'W'))
    return {'key': key, 'label': label, 'unit': unit, 'hours': hours, 'timezone': CFG['timezone'],
            'start': start.isoformat(), 'end': NOW.isoformat(), 'points': points}


@app.get('/api/energy/devices-today')
def device_totals():
    return {'date': DAY, 'devices': {key: {'kwh': kwh, 'complete': True, 'estimated': False,
            'as_of': NOW.isoformat()} for key, _, _, kwh in HEAVY + MINOR}}


@app.get('/api/{path:path}')
def empty(path: str):
    return {'items': [], 'sources': [], 'selected': [], 'moments': [], 'prices': [],
            'sites': [], 'devices': [], 'errors': [], 'backend_instance': INSTANCE}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8093)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
