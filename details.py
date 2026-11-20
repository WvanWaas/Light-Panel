"""Read-only weather forecasts and calendar ranges from Home Assistant."""
import asyncio
import datetime as dt
import re
import time
import math
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import httpx
from fastapi import HTTPException
from weather_sources import weather_source

class DetailProvider:
    def __init__(self, config, states, connection):
        self.config, self.states, self.connection = config, states, connection
        self.weather_cache = {}
        self.solar_cache = {}
        self.price_cache = {}
        self.price_lock = asyncio.Lock()
        self.solar_lock = asyncio.Lock()
        self.weather_lock = asyncio.Lock()

    def zone(self):
        try:return ZoneInfo(self.config().get('timezone') or 'Europe/Amsterdam')
        except ZoneInfoNotFoundError:return ZoneInfo('Europe/Amsterdam')

    def client(self):
        base, token, demo = self.connection()
        return httpx.AsyncClient(base_url=base+'/',headers={'Authorization':'Bearer '+token},timeout=18)

    async def sources(self):
        _,_,demo=self.connection()
        if demo:return {'sources':[], 'selected':[], 'demo':True}
        try:
            async with self.client() as client:
                response=await client.get('api/calendars');response.raise_for_status()
                rows=response.json()
                if not isinstance(rows,list):raise ValueError()
            sources=[{'entity_id':r['entity_id'],'name':str(r.get('name') or r['entity_id'])} for r in rows
                     if isinstance(r,dict) and re.fullmatch(r'calendar\.[a-z0-9_]+',r.get('entity_id',''))]
        except (httpx.HTTPError,ValueError,TypeError):
            raise HTTPException(503,'Agenda’s konden niet worden opgehaald. Controleer de HA-verbinding.')
        allowed={r['entity_id'] for r in sources}
        configured=self.config().get('calendar_ids',[])
        selected=[entity for entity in configured if entity in allowed]
        return {'sources':sources,'selected':selected,'timezone':str(self.zone())}

    def date_range(self, start, end):
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',start) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',end):raise ValueError()
            a,b=dt.date.fromisoformat(start),dt.date.fromisoformat(end)
            if not 0<(b-a).days<=62:raise ValueError()
            return dt.datetime.combine(a,dt.time.min,self.zone()),dt.datetime.combine(b,dt.time.min,self.zone())
        except ValueError:raise HTTPException(400,'Kies een geldige periode van maximaal 62 dagen.')

    @staticmethod
    def normalize_event(item, source):
        def value(field):
            raw=item.get(field)
            return raw.get('dateTime') or raw.get('date') if isinstance(raw,dict) else raw
        start,end=value('start'),value('end')
        if not isinstance(start,str) or not isinstance(end,str):return None
        all_day=bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',start))
        try:
            a=dt.date.fromisoformat(start) if all_day else dt.datetime.fromisoformat(start.replace('Z','+00:00'))
            b=dt.date.fromisoformat(end) if all_day else dt.datetime.fromisoformat(end.replace('Z','+00:00'))
            if b<a:return None
        except (ValueError,TypeError):return None
        return {'calendar_id':source['entity_id'],'calendar_name':source['name'],
                'summary':str(item.get('summary') or 'Afspraak')[:500],
                'location':str(item.get('location') or '')[:1000],
                'description':str(item.get('description') or '')[:4000],
                'start':start,'end':end,'all_day':all_day}

    async def events(self, start, end, calendars):
        a,b=self.date_range(start,end)
        data=await self.sources()
        chosen=list(dict.fromkeys(calendars.split(','))) if calendars else data.get('selected',[])
        if len(chosen)>20:raise HTTPException(400,'Kies maximaal 20 agenda’s.')
        lookup={s['entity_id']:s for s in data['sources']}
        if any(entity not in lookup for entity in chosen):raise HTTPException(400,'Onbekende agenda geselecteerd.')
        errors=[];events=[]
        if chosen:
            async with self.client() as client:
                async def load(entity):
                    try:
                        r=await client.get('api/calendars/'+quote(entity,safe=''),params={'start':a.isoformat(),'end':b.isoformat()});r.raise_for_status()
                        if not isinstance(r.json(),list):raise ValueError()
                        result=[]
                        for item in r.json():
                            if not isinstance(item,dict):continue
                            event=self.normalize_event(item,lookup[entity])
                            if event is not None:
                                if not event['all_day']:
                                    for key in ['start','end']:
                                        parsed=dt.datetime.fromisoformat(event[key].replace('Z','+00:00'))
                                        if parsed.tzinfo is None:event[key]=parsed.replace(tzinfo=self.zone()).isoformat()
                                result.append(event)
                        return result
                    except (httpx.HTTPError,ValueError,TypeError):
                        errors.append({'calendar_id':entity,'name':lookup[entity]['name'],'message':'Agenda tijdelijk niet bereikbaar.'});return []
                groups=await asyncio.gather(*(load(entity) for entity in chosen))
                events=[event for group in groups for event in group]
        events.sort(key=lambda e:(e['start'],e['calendar_id'],e['summary']))
        return {'events':events,'errors':errors,'start':start,'end':end,'timezone':str(self.zone()),'selected':chosen,
                'no_calendars':not data['sources']}

    async def weather(self, force=False):
        config,states=self.config(),self.states()
        source=weather_source(config,states)
        if not source:raise HTTPException(503,'Geen actuele weerbron beschikbaar. Controleer Pirate Weather en de ingestelde reservebron in Home Assistant.')
        entity,current=source['entity_id'],source['current']
        _,_,demo=self.connection()
        if demo:raise HTTPException(503,'Geen weersverwachting beschikbaar zonder Home Assistant.')
        now=time.monotonic()
        async with self.weather_lock:
            old=self.weather_cache.get(entity)
            if old and not force and now-old['time']<300:
                return {**old['data'],**source}
            forecasts={};errors=[]
            async with self.client() as client:
                async def load(kind):
                    try:
                        r=await client.post('api/services/weather/get_forecasts',params={'return_response':''},json={'entity_id':entity,'type':kind});r.raise_for_status()
                        body=r.json()
                        if not isinstance(body,dict) or not isinstance(body.get('service_response'),dict):raise ValueError()
                        entity_data=body['service_response'].get(entity,{})
                        if not isinstance(entity_data,dict):raise ValueError()
                        rows=entity_data.get('forecast')
                        if not isinstance(rows,list):raise ValueError()
                        valid=[]
                        for row in rows:
                            if not isinstance(row,dict) or not isinstance(row.get('datetime'),str):continue
                            try:dt.datetime.fromisoformat(row['datetime'].replace('Z','+00:00'))
                            except ValueError:continue
                            valid.append(row)
                        forecasts[kind]=valid
                    except (httpx.HTTPError,ValueError,TypeError):
                        forecasts[kind]=[];errors.append({'type':kind,'message':'Uurverwachting niet beschikbaar.' if kind=='hourly' else 'Dagverwachting niet beschikbaar.'})
                await asyncio.gather(load('daily'),load('hourly'))
            data={**source,'daily':forecasts['daily'],'hourly':forecasts['hourly'],
                  'errors':errors,'timezone':str(self.zone()),'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat()}
            # Cache complete successes only. A failed provider gets another chance on refresh.
            if not errors:self.weather_cache[entity]={'time':now,'data':data}
            return data

    async def solar_today(self):
        entity=self.config().get('solar_today_statistic')
        if not entity:raise HTTPException(404,'Geen teller voor dagopbrengst ingesteld.')
        now=dt.datetime.now(self.zone());day=now.date().isoformat()
        key=(entity,day)
        async with self.solar_lock:
            cached=self.solar_cache.get(key)
            if cached and time.monotonic()-cached['time']<300:return cached['data']
            start=now.replace(hour=0,minute=0,second=0,microsecond=0)
            try:
                async with self.client() as client:
                    r=await client.post('api/services/recorder/get_statistics',params={'return_response':''},json={
                        'start_time':start.isoformat(),'end_time':now.isoformat(),'statistic_ids':[entity],
                        'period':'5minute','types':['change'],'units':{'energy':'kWh'}})
                    r.raise_for_status()
                rows=r.json().get('service_response',{}).get('statistics',{}).get(entity,[])
                values=[row.get('change') for row in rows]
                if not values or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
                    raise ValueError()
                amount=sum(values)
                if amount<0:raise ValueError()
            except (httpx.HTTPError,ValueError,TypeError,AttributeError):
                raise HTTPException(503,'De dagopbrengst is nog niet beschikbaar in HA-statistieken.')
            data={'date':day,'amount':amount,'unit':'kWh','source':entity,'as_of':rows[-1].get('end'),'basis':'HA-statistieken sinds lokale middernacht'}
            self.solar_cache={key:{'time':time.monotonic(),'data':data}}
            return data

    async def day_prices(self, date=''):
        now=dt.datetime.now(self.zone())
        try:
            day=dt.date.fromisoformat(date) if date else now.date()
            if abs((day-now.date()).days)>7:raise ValueError()
        except ValueError:raise HTTPException(400,'Kies een datum binnen een week van vandaag.')
        key=day.isoformat()
        async with self.price_lock:
            cached=self.price_cache.get(key)
            if cached and time.monotonic()-cached['time']<300:return cached['data']
            start=dt.datetime.combine(day,dt.time.min,self.zone());end=dt.datetime.combine(day+dt.timedelta(days=1),dt.time.min,self.zone())
            try:
                async with self.client() as client:
                    r=await client.post('api/services/tibber/get_prices',params={'return_response':''},json={'start':start.isoformat(),'end':end.isoformat()});r.raise_for_status()
                homes=r.json().get('service_response',{}).get('prices',{})
                if not isinstance(homes,dict) or not homes:raise ValueError()
                selected=self.config().get('price_home')
                if selected:
                    rows=homes.get(selected)
                    if not isinstance(rows,list):raise ValueError()
                elif len(homes)==1:rows=next(iter(homes.values()))
                else:raise HTTPException(409,'Meerdere Tibber-adressen gevonden; stel price_home in om één adres te kiezen.')
                points=[]
                for row in rows:
                    stamp=dt.datetime.fromisoformat(row['start_time'].replace('Z','+00:00'))
                    if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=self.zone())
                    price=row.get('price')
                    if stamp.astimezone(self.zone()).date()!=day or type(price) not in [int,float] or not math.isfinite(price):continue
                    points.append({'start':stamp.isoformat(),'price':price})
                points=list({p['start']:p for p in points}.values())
                points.sort(key=lambda p:dt.datetime.fromisoformat(p['start']))
                if len(points)<2:raise ValueError()
                stamps=[dt.datetime.fromisoformat(p['start']).astimezone(dt.timezone.utc) for p in points]
                steps=sorted((b-a).total_seconds() for a,b in zip(stamps,stamps[1:]) if b>a)
                cadence=steps[len(steps)//2]
                if cadence not in [900,1800,3600]:raise ValueError()
                for index,point in enumerate(points):
                    usual=stamps[index]+dt.timedelta(seconds=cadence)
                    following=stamps[index+1] if index+1<len(points) else end.astimezone(dt.timezone.utc)
                    point['end']=min(usual,following,end.astimezone(dt.timezone.utc)).isoformat()
            except HTTPException:raise
            except (httpx.HTTPError,ValueError,TypeError,KeyError,AttributeError):raise HTTPException(503,'Dagprijzen zijn momenteel niet beschikbaar bij Tibber.')
            values=[point['price'] for point in points]
            # Weight by duration so DST and mixed price intervals are handled correctly.
            durations=[(dt.datetime.fromisoformat(p['end']).astimezone(dt.timezone.utc)-dt.datetime.fromisoformat(p['start']).astimezone(dt.timezone.utc)).total_seconds() for p in points]
            total=sum(durations)
            if total<=0:raise HTTPException(503,'Tibber leverde geen geldige prijsperioden.')
            data={'date':key,'start':start.isoformat(),'end':end.isoformat(),'timezone':str(self.zone()),'unit':'EUR/kWh','points':points,'min':min(values),'max':max(values),
                  'average':sum(p['price']*duration for p,duration in zip(points,durations))/total,'source':'Tibber','complete':abs(total-(end.astimezone(dt.timezone.utc)-start.astimezone(dt.timezone.utc)).total_seconds())<1,'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat()}
            self.price_cache={key:{'time':time.monotonic(),'data':data}}
            return data
