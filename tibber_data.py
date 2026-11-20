"""Local read-only Tibber dashboard. Uses Python standard library only."""
import base64
import hashlib
import json
import math
import os
import sqlite3
import time
import urllib.error
import urllib.request
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
TOKEN = os.environ.get('TIBBER_TOKEN', '').strip()
CACHE_PATH = os.environ.get('TIBBER_CACHE_PATH', str(ROOT / 'data' / 'tibber.sqlite3'))
API_URL = 'https://api.tibber.com/v1-beta/gql'

class ApiError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def graphql(query, variables=None):
    if not TOKEN:
        raise ApiError('Vul TIBBER_TOKEN in het lokale .env-bestand in en herstart de container.', 503)
    req = urllib.request.Request(API_URL, json.dumps({'query': query, 'variables': variables or {}}).encode(),
        {'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json', 'User-Agent': 'LocalTibberDashboard/2'})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        messages = {401: 'Tibber weigert het token. Controleer TIBBER_TOKEN en herstart.',
                    403: 'Geen toegang tot Tibber met dit token.', 429: 'Tibber vraagt om rust. Probeer het later opnieuw.'}
        raise ApiError(messages.get(exc.code, 'Tibber is tijdelijk niet beschikbaar.'), 502) from None
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise ApiError('Geen geldig antwoord van Tibber ontvangen. Probeer het later opnieuw.') from None
    if not result.get('data'):
        raise ApiError('Tibber kon de aanvraag niet uitvoeren. Controleer je token en account.')
    return result


def cached(key, ttl, loader):
    # Namespace by account token so rotating credentials cannot reveal an old account cache.
    key = hashlib.sha256(TOKEN.encode()).hexdigest() + ':' + key
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(CACHE_PATH, timeout=10)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, saved REAL, payload TEXT)')
        row = db.execute('SELECT saved, payload FROM cache WHERE key=?', (key,)).fetchone()
        if row and time.time() - row[0] < ttl:
            return json.loads(row[1])
    value = loader()
    with closing(sqlite3.connect(CACHE_PATH, timeout=10)) as db, db:
        db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?)', (key, time.time(), json.dumps(value)))
    return value


def homes():
    def load():
        result = graphql('{ viewer { homes { id appNickname timeZone } } }')
        return [h for h in (result['data'].get('viewer') or {}).get('homes', []) if h]
    return cached('homes', 300, load)


def bounds(day, zone):
    d = date.fromisoformat(day)
    tz = ZoneInfo(zone)
    return (datetime.combine(d, datetime.min.time(), tz).astimezone(timezone.utc),
            datetime.combine(d + timedelta(days=1), datetime.min.time(), tz).astimezone(timezone.utc))


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def numeric(value):
    return value if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) else None


def normalize(day, home, raw):
    start, end = bounds(day, home['timeZone'])
    obj = (raw.get('data', {}).get('viewer') or {}).get('home') or {}
    warnings = []
    if raw.get('errors'):
        warnings.append('Tibber gaf een gedeeltelijk antwoord; sommige gegevens ontbreken.')
    readings = {}
    for source, fields in [('consumption', {'consumption': 'consumption', 'cost': 'cost'}),
                           ('production', {'production': 'production', 'profit': 'revenue'})]:
        for row in (obj.get(source) or {}).get('nodes') or []:
            if not row:
                continue
            a, b = stamp(row['from']), stamp(row['to'])
            if not start <= a < end:
                continue
            if b - a != timedelta(hours=1):
                warnings.append('Onverwacht meetinterval overgeslagen.')
                continue
            if row.get('currency') not in (None, 'EUR') or row.get(source + 'Unit') not in (None, 'kWh'):
                warnings.append('Een meetwaarde met een andere eenheid of valuta is overgeslagen.')
                continue
            reading = readings.setdefault(a, {'start': a.isoformat(), 'end': b.isoformat(),
                'consumption': None, 'production': None, 'cost': None, 'revenue': None})
            reading.update({dest: numeric(row.get(src)) for src, dest in fields.items()})
    sub = obj.get('currentSubscription') or {}
    price_rows = (sub.get('priceInfo') or {}).get('today' if raw.get('_priceMode') == 'today' else 'tomorrow') if raw.get('_priceMode') else (sub.get('priceInfoRange') or {}).get('nodes')
    prices = {}
    for row in price_rows or []:
        if not row or not row.get('startsAt'):
            continue
        a = stamp(row['startsAt'])
        if start <= a < end and row.get('currency') == 'EUR':
            prices[a] = {'start': a.isoformat(), 'end': min(a + timedelta(minutes=15), end).isoformat(), 'price': numeric(row.get('total'))}
    if not readings:
        warnings.append('Nog geen historische metergegevens voor deze dag ontvangen.')
    expected_hours = int((end-start).total_seconds()/3600)
    complete = {k: sum(r[k] is not None for r in readings.values()) == expected_hours for k in ('cost','revenue','consumption','production')}
    if readings and not all(complete.values()):
        warnings.append('De dag is onvolledig. Totalen tellen alleen de beschikbare meetwaarden op.')
    if len(prices) < expected_hours*4:
        warnings.append('Kwartierprijzen zijn niet volledig beschikbaar voor deze dag.')
    return {'date': day, 'home': home, 'source': 'tibber', 'start': start.isoformat(), 'end': end.isoformat(),
            'measurements': [readings[k] for k in sorted(readings)], 'prices': [prices[k] for k in sorted(prices)],
            'complete': complete, 'warnings': list(dict.fromkeys(warnings)), 'fetchedAt': datetime.now(timezone.utc).isoformat()}


def day_data(day, home_id):
    selected = next((h for h in homes() if h['id'] == home_id), None)
    if not selected:
        raise ApiError('Deze woning is niet beschikbaar in jouw account.', 404)
    try:
        start, end = bounds(day, selected['timeZone'])
    except (ValueError, KeyError):
        raise ApiError('Ongeldige datum of tijdzone.', 400) from None
    today = datetime.now(ZoneInfo(selected['timeZone'])).date()
    mode = 'today' if day == today.isoformat() else 'tomorrow' if day == (today+timedelta(days=1)).isoformat() else None
    cursor = base64.b64encode((start-timedelta(seconds=1)).isoformat().encode()).decode()
    def load():
        price_query = f'priceInfo(resolution: QUARTER_HOURLY) {{ {mode} {{ startsAt total currency }} }}' if mode else 'priceInfoRange(resolution: QUARTER_HOURLY, first: 101, after: $after) { nodes { startsAt total currency } }'
        query = '''query Day($home: ID!, $after: String!) { viewer { home(id: $home) {
            consumption(resolution: HOURLY, first: 26, after: $after) { nodes { from to consumption consumptionUnit cost currency } }
            production(resolution: HOURLY, first: 26, after: $after) { nodes { from to production productionUnit profit currency } }
            currentSubscription { PRICE_QUERY }
        } } }'''.replace('PRICE_QUERY', price_query)
        raw = graphql(query, {'home': home_id, 'after': cursor})
        raw['_priceMode'] = mode
        return normalize(day, selected, raw)
    return cached('day:' + home_id + ':' + day, 300 if day >= today.isoformat() else 3600, load)


def period_bounds(day, kind, zone):
    d = date.fromisoformat(day)
    if kind == 'week':
        d -= timedelta(days=d.weekday())
        end = d + timedelta(days=7)
    elif kind == 'month':
        d = d.replace(day=1)
        end = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    elif kind == 'year':
        d = d.replace(month=1, day=1)
        end = d.replace(year=d.year + 1)
    else:
        raise ApiError('Ongeldige periode.', 400)
    return bounds(d.isoformat(), zone)[0], bounds(end.isoformat(), zone)[0]


def period_data(day, kind, home_id):
    home = next((h for h in homes() if h['id'] == home_id), None)
    if not home:
        raise ApiError('Deze woning is niet beschikbaar.', 404)
    start, end = period_bounds(day, kind, home['timeZone'])
    tz = ZoneInfo(home['timeZone'])
    today = datetime.now(tz).date()

    def load():
        readings, prices, warnings = {}, {}, []
        cursor_day = start.astimezone(tz).date()
        end_day = end.astimezone(tz).date()
        while cursor_day < end_day and cursor_day <= today + timedelta(days=1):
            chunk_end = min(cursor_day + timedelta(days=31), end_day)
            a = bounds(cursor_day.isoformat(), home['timeZone'])[0]
            cursor = base64.b64encode((a-timedelta(seconds=1)).isoformat().encode()).decode()
            count = (chunk_end-cursor_day).days
            query = '''query Period($home: ID!, $after: String!, $count: Int!) { viewer { home(id: $home) {
                consumption(resolution: DAILY, first: $count, after: $after) { nodes { from to consumption consumptionUnit cost currency } }
                production(resolution: DAILY, first: $count, after: $after) { nodes { from to production productionUnit profit currency } }
                currentSubscription { priceInfoRange(resolution: DAILY, first: $count, after: $after) { nodes { startsAt total currency } } }
            } } }'''
            # Cache each chunk as well, so revisiting the year does not repeat historical calls.
            raw = cached('period-chunk:'+home_id+':'+cursor_day.isoformat()+':'+str(count),
                         300 if chunk_end > today else 3600,
                         lambda: graphql(query, {'home': home_id, 'after': cursor, 'count': count}))
            if raw.get('errors'):
                warnings.append('Sommige gegevens zijn niet beschikbaar.')
            obj = ((raw.get('data') or {}).get('viewer') or {}).get('home') or {}
            for source, fields in [('consumption', {'consumption': 'consumption', 'cost': 'cost'}),
                                   ('production', {'production': 'production', 'profit': 'revenue'})]:
                for row in (obj.get(source) or {}).get('nodes') or []:
                    if not row:
                        continue
                    a, b = stamp(row['from']), stamp(row['to'])
                    if not start <= a < end or not cursor_day <= a.astimezone(tz).date() < chunk_end:
                        continue
                    if row.get('currency') not in (None, 'EUR') or row.get(source+'Unit') not in (None, 'kWh'):
                        continue
                    reading = readings.setdefault(a, {'start': a.isoformat(), 'end': b.isoformat(),
                        'consumption': None, 'production': None, 'cost': None, 'revenue': None})
                    reading.update({dest: numeric(row.get(src)) for src, dest in fields.items()})
            for row in ((obj.get('currentSubscription') or {}).get('priceInfoRange') or {}).get('nodes') or []:
                if not row or not row.get('startsAt') or row.get('currency') != 'EUR':
                    continue
                a = stamp(row['startsAt'])
                local = a.astimezone(tz).date()
                if start <= a < end and cursor_day <= local < chunk_end:
                    b = bounds((local+timedelta(days=1)).isoformat(), home['timeZone'])[0]
                    prices[a] = {'start': a.isoformat(), 'end': b.isoformat(), 'price': numeric(row.get('total'))}
            cursor_day = chunk_end
        expected = (end_day-start.astimezone(tz).date()).days
        complete = {k: sum(r[k] is not None for r in readings.values()) == expected
                    for k in ('cost', 'revenue', 'consumption', 'production')}
        return {'home': home, 'start': start.isoformat(), 'end': end.isoformat(),
                'measurements': [readings[k] for k in sorted(readings)],
                'prices': [prices[k] for k in sorted(prices)], 'complete': complete,
                'warnings': list(dict.fromkeys(warnings)), 'fetchedAt': datetime.now(timezone.utc).isoformat()}
    return cached('period:'+home_id+':'+kind+':'+start.isoformat(),
                  300 if end.astimezone(tz).date() > today else 3600, load)


