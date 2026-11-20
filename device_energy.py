"""Today's device energy from HA recorder counters; hob from measured 5-minute power."""
import asyncio,datetime as dt,math,time
from fastapi import HTTPException
import httpx
UTC=dt.timezone.utc

def number(value):return value if type(value) in (int,float) and math.isfinite(value) else None

def timestamp(value):
    try:
        if isinstance(value,(int,float)):return dt.datetime.fromtimestamp(value/1000 if value>1e11 else value,UTC)
        parsed=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed.astimezone(UTC) if parsed.tzinfo else None
    except (ValueError,AttributeError,TypeError,OverflowError):return None

def samples(rows,start,end,field):
    result={}
    for row in rows if isinstance(rows,list) else []:
        if not isinstance(row,dict):continue
        a,b=timestamp(row.get('start')),timestamp(row.get('end'));v=number(row.get(field))
        if not a or not b or a<start or b>end or (b-a).total_seconds()!=300 or v is None:continue
        if field=='change' and v<0:continue
        result[a]=(b,v)
    return result

def analyze(statistics,config,start,end):
    settings=config.get('power_display',{});items=settings.get('heavy',[])+settings.get('minor',[]);expected=max(0,(end-start).total_seconds());results={}
    for item in items:
        ids=item.get('energy_entities',[]);ids=[ids] if isinstance(ids,str) else ids
        streams=[samples(statistics.get(entity),start,end,'change') for entity in ids]
        times=set.intersection(*(set(s) for s in streams)) if streams else set()
        values={a:sum(s[a][1] for s in streams) for a in times}
        if item.get('estimated'):
            h=settings.get('hob',{});keys=['phase','fallback_phase','ac_in','ac_out'];sources={k:samples(statistics.get(h.get(k)),start,end,'mean') for k in keys}
            sources['battery']=samples(statistics.get(config.get('battery_power')),start,end,'mean')
            others=[samples(statistics.get(entity),start,end,'mean') for entity in h.get('subtract',[])]
            candidates=set(sources['phase'])|set(sources['fallback_phase']);values={}
            for a in candidates:
                phase=(sources['phase'].get(a) or sources['fallback_phase'].get(a))[1]
                if not all(a in sources[k] for k in ['ac_in','ac_out','battery']) or not others or not all(a in s for s in others):continue
                ac_in,ac_out,battery=(sources[k][a][1] for k in ['ac_in','ac_out','battery'])
                balance=ac_out+battery;signed=(math.copysign(abs(ac_in),balance) if abs(balance)>100 else ac_in)
                watts=max(0,phase-signed-sum(s[a][1] for s in others))
                values[a]=watts*300/3600000
        measured=len(values)*300
        results[item['key']]={'kwh':sum(values.values()) if values else None,'coverage':measured/expected if expected else 0,'complete':bool(expected) and measured==expected,'estimated':bool(item.get('estimated')),'as_of':(max(values)+dt.timedelta(minutes=5)).isoformat() if values else None}
    return results

class DeviceEnergy:
    def __init__(self,provider):self.provider=provider;self.cache={};self.lock=asyncio.Lock()
    async def today(self,now=None):
        p=self.provider;now=now or dt.datetime.now(p.zone());start=now.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(UTC);end=dt.datetime.fromtimestamp(math.floor(now.timestamp()/300)*300,UTC);day=now.date().isoformat()
        async with self.lock:
            cached=self.cache.get(day)
            if cached and time.monotonic()-cached[0]<300:return cached[1]
            if p.connection()[2]:raise HTTPException(503,'Geen dagtotalen zonder Home Assistant.')
            c=p.config();settings=c.get('power_display',{});ids=set()
            for item in settings.get('heavy',[])+settings.get('minor',[]):
                entities=item.get('energy_entities',[]);ids.update([entities] if isinstance(entities,str) else entities)
            h=settings.get('hob',{});ids.update(h.get(k) for k in ['phase','fallback_phase','ac_in','ac_out']);ids.update(h.get('subtract',[]));ids.add(c.get('battery_power'));ids.discard(None)
            stats={}
            if end>start:
                try:
                    async with p.client() as client:
                        response=await client.post('api/services/recorder/get_statistics',params={'return_response':''},json={'start_time':start.isoformat(),'end_time':end.isoformat(),'statistic_ids':sorted(ids),'period':'5minute','types':['change','mean'],'units':{'energy':'kWh','power':'W'}});response.raise_for_status()
                        stats=response.json().get('service_response',{}).get('statistics',{})
                    if not isinstance(stats,dict):raise ValueError()
                except (httpx.HTTPError,ValueError,TypeError,AttributeError):raise HTTPException(503,'Dagtotalen zijn tijdelijk niet bereikbaar.')
            result={'date':day,'devices':analyze(stats,c,start,end),'start':start.isoformat(),'end':end.isoformat(),'timezone':str(p.zone())};self.cache={day:(time.monotonic(),result)};return result
