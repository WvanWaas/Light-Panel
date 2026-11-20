"""Read countdowns from dedicated HA calendars. Calendar recurrence stays in HA."""
import asyncio,datetime as dt,hashlib,re,time
from urllib.parse import quote
from fastapi import HTTPException
import httpx

def moment(event,zone,now):
    try:
        all_day=event['all_day']
        if all_day:
            a=dt.datetime.combine(dt.date.fromisoformat(event['start']),dt.time.min,zone);b=dt.datetime.combine(dt.date.fromisoformat(event['end']),dt.time.min,zone)
        else:
            a=dt.datetime.fromisoformat(event['start'].replace('Z','+00:00'));b=dt.datetime.fromisoformat(event['end'].replace('Z','+00:00'))
            if a.tzinfo is None:a=a.replace(tzinfo=zone)
            if b.tzinfo is None:b=b.replace(tzinfo=zone)
        if b<=now or b<a:return None
        day=a.astimezone(zone).date();days=max(0,(day-now.astimezone(zone).date()).days)
        status='ongoing' if a<now and (not all_day or day<now.astimezone(zone).date()) else 'today' if days==0 else 'upcoming'
        text=(event['calendar_name']+' '+event['summary']).lower()
        kind='birthday' if re.search(r'verjaardag|birthday|jarig',text) else 'vacation' if re.search(r'vakantie|holiday|reis|camping|trip',text) else 'celebration' if re.search(r'sinterklaas|pakjes|kerst|christmas',text) else 'event'
        identity=hashlib.sha256(repr((event['calendar_id'],event['start'],event['end'],event['summary'])).encode()).hexdigest()[:20]
        return {**event,'id':identity,'days_remaining':days,'status':status,'kind':kind,'date':day.isoformat(),'starts_at':a.isoformat(),'ends_at':b.isoformat()}
    except (ValueError,TypeError,KeyError):return None

class CountdownProvider:
    def __init__(self,provider):self.provider=provider;self.cache={};self.lock=asyncio.Lock()
    async def get(self,calendars=None,refresh=False,now=None):
        p=self.provider;zone=p.zone();now=now or dt.datetime.now(zone);now=now.astimezone(zone)
        sources=(await p.sources())['sources'];lookup={s['entity_id']:s for s in sources}
        if calendars is None:
            configured=p.config().get('countdown_calendar_ids')
            selected=[entity for entity in configured if entity in lookup] if isinstance(configured,list) else [s['entity_id'] for s in sources if re.search(r'aftel|countdown|verjaardag|birthday|vakantie',s['name']+' '+s['entity_id'],re.I)]
        else:
            selected=list(dict.fromkeys(filter(None,calendars.split(','))))
            if any(entity not in lookup for entity in selected):raise HTTPException(400,'Onbekende aftelagenda geselecteerd.')
        if len(selected)>8:raise HTTPException(400,'Kies maximaal acht aftelagenda’s.')
        today=now.date();horizon=today+dt.timedelta(days=400);key=(today.isoformat(),tuple(selected))
        async with self.lock:
            cached=self.cache.get(key)
            if not refresh and cached and time.monotonic()-cached['time']<600:
                events,errors=cached['data']
            else:
                events=[];errors=[];semaphore=asyncio.Semaphore(4);finished=set()
                async with p.client() as client:
                    async def load(entity):
                        cursor=today
                        while cursor<horizon:
                            end=min(cursor+dt.timedelta(days=62),horizon)
                            try:
                                async with semaphore:
                                    response=await client.get('api/calendars/'+quote(entity,safe=''),params={'start':dt.datetime.combine(cursor,dt.time.min,zone).isoformat(),'end':dt.datetime.combine(end,dt.time.min,zone).isoformat()});response.raise_for_status()
                                rows=response.json()
                                if not isinstance(rows,list):raise ValueError()
                                for row in rows:
                                    if isinstance(row,dict):
                                        event=p.normalize_event(row,lookup[entity])
                                        if event:events.append(event)
                            except (httpx.HTTPError,ValueError,TypeError):
                                errors.append({'calendar_id':entity,'name':lookup[entity]['name'],'message':'Aftelagenda tijdelijk niet bereikbaar; mogelijk ontbreken momenten.'});finished.add(entity);return
                            cursor=end
                        finished.add(entity)
                    try:await asyncio.wait_for(asyncio.gather(*(load(entity) for entity in selected)),timeout=30)
                    except asyncio.TimeoutError:
                        for entity in selected:
                            if entity not in finished:errors.append({'calendar_id':entity,'name':lookup[entity]['name'],'message':'Aftelagenda reageert te langzaam; mogelijk ontbreken momenten.'})
                unique={(e['calendar_id'],e['start'],e['end'],e['summary']):e for e in events};events=list(unique.values())
                # Failed reads should be retryable rather than cached for ten minutes.
                if not errors:self.cache={key:{'time':time.monotonic(),'data':(events,errors)}}
        moments=[m for event in events if (m:=moment(event,zone,now)) is not None and dt.date.fromisoformat(m['date'])<horizon]
        moments.sort(key=lambda m:(m['days_remaining'],dt.datetime.fromisoformat(m['starts_at']).timestamp(),m['calendar_name'],m['summary']))
        return {'sources':sources,'selected':selected,'moments':moments[:50],'errors':errors,'needs_setup':not selected,'timezone':str(zone),'today':today.isoformat(),'horizon':horizon.isoformat(),'generated_at':now.isoformat()}
