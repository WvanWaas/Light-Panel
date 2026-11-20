"""Current, local notifications only. No news or restored historical incidents."""
import datetime as dt
import hashlib
import math
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
UTC=dt.timezone.utc

def timestamp(value, zone='Europe/Amsterdam'):
    try:
        if isinstance(value,(int,float)):
            return dt.datetime.fromtimestamp(value/1000 if value>1e11 else value,UTC)
        if not isinstance(value,str) or not value:return None
        parsed=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:parsed=parsed.replace(tzinfo=ZoneInfo(zone))
        return parsed.astimezone(UTC)
    except (ValueError,TypeError,OverflowError):return None

def number(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError):return None

def fresh(when,now,seconds):return when is not None and -30<=(now-when).total_seconds()<=seconds

def flight_details(flight):
    def text(key):return str(flight.get(key) or '')[:150]
    def country(key):
        code=text(key).upper()
        return code if re.fullmatch(r'[A-Z]{2}',code) else None
    model=text('aircraft_model');icao=text('aircraft_code') or text('aircraft_icao');category=(text('aircraft_category')+' '+model).lower()
    helicopter_codes={'B06','EC35','EC45','R22','R44','R66','AS50','AS55','AS65','AS32','H125','H135','H145','S76','AW139','A139','A109','H60','H64'}
    kind='balloon' if 'balloon' in category or 'luchtballon' in category or icao.upper()=='BALL' else 'helicopter' if 'helicopter' in category or 'helicop' in category or icao.upper() in helicopter_codes else 'plane'
    altitude=number(flight.get('altitude'));speed=number(flight.get('ground_speed'))
    return {'vehicle':kind,'code':text('flight_number') or text('callsign') or text('aircraft_registration'),
            'origin':text('airport_origin_city') or text('airport_origin_code_iata'),
            'destination':text('airport_destination_city') or text('airport_destination_code_iata'),
            'origin_country':country('airport_origin_country_code'),'destination_country':country('airport_destination_country_code'),
            'airline':text('airline_name'),'model':model,'registration':text('aircraft_registration'),
            'altitude_m':round(altitude*.3048) if altitude is not None else None,
            'speed_kmh':round(speed*1.852) if speed is not None and speed>=0 else None}

def source_url(value):
    if not isinstance(value, str) or len(value)>2000:return None
    try:
        parsed=urlsplit(value)
        return value if parsed.scheme in ('https','http') and parsed.hostname and not parsed.username and not parsed.password else None
    except ValueError:return None


def emergency_service(entity, attributes, message):
    words=' '.join([entity,str(attributes.get('discipline') or ''),str(attributes.get('friendly_name') or ''),message]).lower()
    if re.search(r'\bgrip\s*[-:]?\s*\d*\b',words) or 'sensor.grip' in words:return 'grip'
    if any(word in words for word in ('ambulance','ambu','trauma','geneeskundig')):return 'ambulance'
    if any(word in words for word in ('brandweer','brandw','brw')):return 'fire'
    return 'other'


def collect_ticker(states, config, webhooks=(), now=None, ha_online=True):
    now=now or dt.datetime.now(UTC);zone=config.get('timezone') or 'Europe/Amsterdam';settings=config.get('ticker',{})
    items=[];notes=[]
    def add(kind,title,message,at,expires,priority,**extra):
        identifier=hashlib.sha256((kind+title+message+at.isoformat()).encode()).hexdigest()[:20]
        items.append({'id':identifier,'kind':kind,'title':title[:150],'message':message[:1000],
                      'time':at.isoformat(),'expires_at':expires.isoformat(),'priority':priority,**extra})
    if ha_online:
        p_ttl=settings.get('p2000_max_age_seconds',600);radius=settings.get('p2000_radius_km',15)
        for entity in settings.get('p2000_entities',[]):
            source=states.get(entity)
            if not source:notes.append({'source':entity,'status':'Bron niet beschikbaar.'});continue
            a=source.get('attributes',{});at=timestamp(a.get('time'),zone)
            text=str(source.get('state',''))
            service=emergency_service(entity,a,text)
            ttl=settings.get('grip_max_age_seconds',1800) if service=='grip' else p_ttl
            if not fresh(at,now,ttl):continue
            lat,lon,metres=number(a.get('latitude')),number(a.get('longitude')),number(a.get('distance'))
            # This P2000 integration reports metres and uses 0/0 for missing geocoding.
            if not lat or not lon or metres is None:
                notes.append({'source':entity,'status':'Recente melding zonder bruikbare locatie; niet als lokaal getoond.'});continue
            km=metres/1000
            if km<0 or km>radius:continue
            text=str(source.get('state',''))
            if text in ['unknown','unavailable','']:continue
            title={'grip':'GRIP','fire':'Brandweer','ambulance':'Ambulance'}.get(service,'P2000')
            add('p2000',title,text,at,at+dt.timedelta(seconds=ttl),80,distance_km=round(km,1),service=service,source_url=source_url(a.get('url') or a.get('link')))
        entity=settings.get('weather_warning_entity');source=states.get(entity,{})
        if source:
            a=source.get('attributes',{});code=str(a.get('code') or '').strip().lower()
            colours={'oranje':'orange','orange':'orange','rood':'red','red':'red'}
            reported=timestamp(source.get('last_reported') or source.get('last_updated'),zone)
            max_age=settings.get('weather_source_max_age_seconds',7200)
            if source.get('state')=='on' and code in colours and fresh(reported,now,max_age):
                at=timestamp(a.get('timestamp'),zone) or reported
                if at>now+dt.timedelta(seconds=30):at=reported
                title='Code '+('rood' if colours[code]=='red' else 'oranje')
                text=str(a.get('description') or a.get('title') or 'Actuele KNMI-waarschuwing voor jouw omgeving.')
                add('weather',title,text,at,reported+dt.timedelta(seconds=max_age),100 if colours[code]=='red' else 90,severity=colours[code])
        entity=settings.get('flight_entity') or config.get('flight');source=states.get(entity,{})
        reported=timestamp(source.get('last_reported') or source.get('last_updated'),zone)
        ttl=settings.get('flight_max_age_seconds',120)
        if source and fresh(reported,now,ttl):
            for flight in source.get('attributes',{}).get('flights',[]):
                if not isinstance(flight,dict) or flight.get('tracked_type','live')!='live':continue
                if flight.get('on_ground') in [True,1,'1'] or (number(flight.get('altitude')) or 0)<=0:continue
                distance=number(flight.get('distance'))
                if distance is None or distance<0 or distance>settings.get('flight_radius_km',5):continue
                info=flight_details(flight)
                code=str(flight.get('flight_number') or flight.get('callsign') or flight.get('aircraft_registration') or 'Vliegtuig')
                origin=flight.get('airport_origin_city') or flight.get('airport_origin_code_iata')
                destination=flight.get('airport_destination_city') or flight.get('airport_destination_code_iata')
                route=(str(origin or '?')+' → '+str(destination or '?')) if origin or destination else str(flight.get('aircraft_model') or 'Nu in de buurt')
                label={'plane':'Vliegtuig','helicopter':'Helikopter','balloon':'Luchtballon'}[info['vehicle']]
                add('flight',label+' · '+code,route,reported,reported+dt.timedelta(seconds=ttl),30,distance_km=round(distance,1),flight=info,source_url=source_url(flight.get('url') or flight.get('link')))
    else:notes.append({'source':'HA','status':'HA niet bereikbaar; actuele meldingen worden verborgen.'})
    for item in webhooks:
        at=timestamp(item.get('time'),zone);ttl=settings.get('webhook_max_age_seconds',600)
        if fresh(at,now,ttl):add('notification',str(item.get('title') or 'Melding'),str(item.get('message') or ''),at,at+dt.timedelta(seconds=ttl),60)
    # Same incident may be present in multiple P2000 sensors.
    unique={}
    for item in sorted(items,key=lambda i:-dt.datetime.fromisoformat(i['time']).timestamp()):
        key=(item['kind'],item['message'],item['time'],item.get('flight',{}).get('code') if item['kind']=='flight' else None)
        unique.setdefault(key,item)
    result=list(unique.values())[:20]
    return {'items':result,'notes':notes,'generated_at':now.isoformat()}


class TickerHistory:
    """Retain observed cards until expiry, even after their HA sensor changes."""
    def __init__(self):
        self.items={}
        self.notes=[]

    def observe(self, states, config, webhooks=(), now=None, ha_online=True):
        now=now or dt.datetime.now(UTC)
        snapshot=collect_ticker(states,config,webhooks,now,ha_online)
        self.notes=snapshot['notes']
        self.items={key:item for key,item in self.items.items() if timestamp(item['expires_at'])>now}
        for item in snapshot['items']:
            if item['kind']=='flight':
                flight=item.get('flight',{})
                # Report timestamps change on every radar update; a flight is one card.
                identity=flight.get('registration') or flight.get('code') or item['title']
                key=hashlib.sha256(('flight:'+identity).encode()).hexdigest()[:20]
                previous=self.items.get(key)
                seen=timestamp(item['time'])
                item={**item,'id':key,'time':previous['time'] if previous else item['time'],
                      'last_seen':seen.isoformat(),'expires_at':(seen+dt.timedelta(seconds=300)).isoformat()}
            else:key=item['id']
            if timestamp(item['expires_at'])>now:self.items[key]=item
        # Do not rotate or prioritize older incidents above newer cards.
        self.items=dict(sorted(self.items.items(),key=lambda pair:timestamp(pair[1]['time']),reverse=True)[:200])
        return self.payload(now)

    def payload(self, now=None):
        now=now or dt.datetime.now(UTC)
        self.items={key:item for key,item in self.items.items() if timestamp(item['expires_at'])>now}
        return {'items':list(self.items.values()),'notes':self.notes,'generated_at':now.isoformat()}
