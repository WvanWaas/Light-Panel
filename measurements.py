"""Read-only recorder history for the explicitly configured dashboard measurements."""
import asyncio
import datetime as dt
import math
import time
from urllib.parse import quote
import httpx
from fastapi import HTTPException


def measurements(config):
    d, e = config.get('dashboard', {}), config.get('energy', {})
    b = config.get('battery_details', {})
    def spec(label, ids, unit):
        return {'label': label, 'entities': [ids] if isinstance(ids, str) else ids or [], 'unit': unit}
    return {
        **{'device_'+item['key']: spec(item['label'],item['entities'],'W') for item in config.get('power_display',{}).get('heavy',[])+config.get('power_display',{}).get('minor',[]) if item.get('entities')},
        'co2': spec('CO₂', d.get('indoor_co2'), 'ppm'),
        'temperature': spec('Temperatuur woning', d.get('indoor_temperature'), '°C'),
        'battery': spec('Batterijlading', config.get('battery') or e.get('Batterij'), '%'),
        'battery_power': spec('Batterijvermogen', config.get('battery_power'), 'W'),
        'battery_voltage': spec('Batterijspanning', b.get('voltage'), 'V'),
        'battery_current': spec('Batterijstroom', b.get('current'), 'A'),
        'battery_temperature': spec('Batterijtemperatuur', b.get('temperature'), '°C'),
        'battery_charge_energy': spec('Laadenergie', b.get('charge_energy'), 'kWh'),
        'battery_discharge_energy': spec('Ontlaadenergie', b.get('discharge_energy'), 'kWh'),
        'power': spec('Woningverbruik', d.get('house_power', config.get('power')), 'W'),
        'water': spec('Tapwater warmtepomp', d.get('hot_water_temperature') or config.get('climate', {}).get('Tapwater'), '°C'),
        'solar': spec('Zonnepanelen', config.get('solar') or e.get('Zon nu'), 'W'),
        'heatpump': spec('Warmtepompvermogen', d.get('heat_pump_power'), 'W'),
    }


def numeric(row, unit, fallback_unit):
    try:
        n = float(row.get('state'))
        source = row.get('attributes', {}).get('unit_of_measurement', fallback_unit)
        if not math.isfinite(n): return None
        if unit == 'W' and source == 'kW': return n * 1000
        if unit == '°C' and source == '°F': return (n - 32) * 5 / 9
        return n if source == unit else None
    except (ValueError, TypeError): return None


def history_points(groups, spec, start, end, current):
    """Merge phase changes at their actual timestamps; a missing phase breaks the sum."""
    ids = spec['entities']
    changes = []
    for group in groups:
        if not isinstance(group, list): continue
        entity = next((r.get('entity_id') for r in group if isinstance(r, dict) and r.get('entity_id')), None)
        if entity not in ids: continue
        unit = current.get(entity, {}).get('attributes', {}).get('unit_of_measurement')
        for row in group:
            if not isinstance(row, dict): continue
            try:
                stamp = dt.datetime.fromisoformat((row.get('last_changed') or row.get('last_updated')).replace('Z', '+00:00'))
                if stamp.tzinfo is None: continue
                stamp = max(start, stamp)
                unit = row.get('attributes', {}).get('unit_of_measurement', unit)
                if stamp <= end: changes.append((stamp, entity, numeric(row, spec['unit'], unit)))
            except (ValueError, TypeError, AttributeError): continue
    values = {entity: None for entity in ids}
    # Group simultaneous changes to avoid spurious spikes in the phase total.
    by_time = {}
    for stamp, entity, value in sorted(changes, key=lambda x: x[0]):
        by_time.setdefault(stamp, {})[entity] = value
    points = [{'time': start.isoformat(), 'value': None}]
    for stamp, changed in sorted(by_time.items()):
        values.update(changed)
        total = sum(values.values()) if values and all(v is not None for v in values.values()) else None
        point = {'time': stamp.isoformat(), 'value': total}
        if points[-1]['time'] == point['time']: points[-1] = point
        else: points.append(point)
    if points[-1]['time'] != end.isoformat(): points.append({'time': end.isoformat(), 'value': points[-1]['value']})
    return compact(points, start, end)


def compact(points, start, end):
    """Keep first/last, extrema and unknown spans in each time bucket."""
    buckets = {}
    width = max(1, (end - start).total_seconds() / 180)
    for i, p in enumerate(points):
        bucket = int((dt.datetime.fromisoformat(p['time']) - start).total_seconds() / width)
        buckets.setdefault(bucket, []).append(i)
    keep = set()
    for indices in buckets.values():
        keep.update([indices[0], indices[-1]])
        valid = [i for i in indices if points[i]['value'] is not None]
        if valid:
            keep.add(min(valid, key=lambda i: points[i]['value']))
            keep.add(max(valid, key=lambda i: points[i]['value']))
        # Keep both sides of every availability transition, even during a busy bucket.
        for i in indices:
            if i and (points[i]['value'] is None) != (points[i-1]['value'] is None): keep.update([i-1, i])
    return [points[i] for i in sorted(keep)]


class MeasurementHistory:
    def __init__(self, provider):
        self.provider, self.cache, self.lock = provider, {}, asyncio.Lock()

    async def get(self, key, hours=24):
        spec = measurements(self.provider.config()).get(key)
        if not spec or not spec['entities']: raise HTTPException(404, 'Deze meetwaarde is niet ingesteld.')
        if hours not in (1, 6, 24): raise HTTPException(400, 'Kies 1, 6 of 24 uur.')
        if self.provider.connection()[2]: raise HTTPException(503, 'Geen meetgeschiedenis zonder Home Assistant.')
        cache_key = (key, hours)
        async with self.lock:
            old = self.cache.get(cache_key)
            if old and time.monotonic() - old[0] < 60: return old[1]
            end = dt.datetime.now(dt.timezone.utc)
            start = end - dt.timedelta(hours=hours)
            try:
                async with self.provider.client() as client:
                    r = await client.get('api/history/period/' + quote(start.isoformat(), safe=''), params={
                        'end_time': end.isoformat(), 'filter_entity_id': ','.join(spec['entities']),
                        'minimal_response': 'true', 'significant_changes_only': '0'})
                    r.raise_for_status()
                    groups = r.json()
                    if not isinstance(groups, list): raise ValueError()
                points = history_points(groups, spec, start, end, self.provider.states())
            except (httpx.HTTPError, ValueError, TypeError):
                raise HTTPException(503, 'Meetgeschiedenis niet bereikbaar. Controleer de HA-verbinding en Recorder.')
            result = {**spec, 'key': key, 'hours': hours, 'start': start.isoformat(), 'end': end.isoformat(),
                      'timezone': str(self.provider.zone()), 'points': points,
                      'empty': not any(p['value'] is not None for p in points)}
            self.cache[cache_key] = (time.monotonic(), result)
            return result


EXTRA_MEDIA = {}


def media_actions(config):
    actions = dict(config.get('actions', {}))
    for key, (_, entity) in EXTRA_MEDIA.items():
        actions.setdefault(key, {'service': 'script.turn_on', 'entity_id': entity})
    return actions
