"""Read the existing VRM SOC plan. Never writes ESS settings."""
import asyncio
import datetime as dt
import math
import os
import re
import time
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
import httpx
from fastapi import HTTPException

BASE='https://vrmapi.victronenergy.com/v2'

def normalize_plan(payload,start,end):
 records=payload.get('records',{})
 rows=records.get('vrm_soc_plan',[]) if isinstance(records,dict) else []
 if not isinstance(rows,list):return []
 points={}
 for row in rows:
  if not isinstance(row,list) or len(row)<2:continue
  stamp,value=row[:2]
  if isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or not math.isfinite(stamp):continue
  # VRM stats timestamps are milliseconds since the Unix epoch.
  if not start*1000<=stamp<end*1000:continue
  valid=not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and -1e-6<=value<=100+1e-6
  points[stamp]={'time':dt.datetime.fromtimestamp(stamp/1000,dt.timezone.utc).isoformat(),'soc':min(100,max(0,value)) if valid else None}
 return [points[key] for key in sorted(points)]

def normalize_solar(payload,start,end):
 records=payload.get('records',{});rows=records.get('solar_yield_forecast',[]) if isinstance(records,dict) else []
 if not isinstance(rows,list):return []
 result={}
 for row in rows:
  if not isinstance(row,list) or len(row)<2:continue
  stamp,value=row[:2]
  if isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or not math.isfinite(stamp):continue
  if not start*1000<=stamp<end*1000:continue
  valid=not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and value>=0
  # VRM solar_yield_forecast is hourly energy in Wh, independent of the SOC sample cadence.
  result[stamp]={'start':dt.datetime.fromtimestamp(stamp/1000,dt.timezone.utc).isoformat(),'end':dt.datetime.fromtimestamp(min(stamp/1000+3600,end),dt.timezone.utc).isoformat(),'kwh':value/1000 if valid else None}
 return [result[key] for key in sorted(result)]

def normalize_daily_energy(payload,start,end,zone,now=None):
 records=payload.get('records',{});records=records if isinstance(records,dict) else {};now=now or dt.datetime.now(dt.timezone.utc)
 def combine(codes):
  streams=[]
  for code in codes:
   values={};rows=records.get(code,[])
   if isinstance(rows,list):
    for row in rows:
     if not isinstance(row,list) or len(row)<2:continue
     stamp,value=row[:2]
     if isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or not math.isfinite(stamp):continue
     if not start*1000<=stamp<end*1000 or stamp/1000>now.timestamp():continue
     valid=not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and value>=0
     values[stamp]=value if valid else None
   streams.append(values)
  result=[]
  for stamp in sorted(set().union(*(set(v) for v in streams))):
   local=dt.datetime.fromtimestamp(stamp/1000,zone);next_day=dt.datetime.combine(local.date()+dt.timedelta(days=1),dt.time.min,zone);values=[v.get(stamp) for v in streams]
   result.append({'start':local.isoformat(),'end':next_day.isoformat(),'kwh':sum(values) if all(v is not None for v in values) else None,'partial':next_day.timestamp()>now.timestamp()})
  return result
 # VRM energy flow counters are already kWh. Charging (Gb/Pb) is not discharge.
 return {'solar':combine(['Pc','Pg','Pb']),'discharge':combine(['Bc','Bg'])}

class VrmPlanning:
 def __init__(self,config=lambda:{},client_factory=None,site=None,token=None):
  self.config=config;self.site=os.getenv('VRM_SITE_ID','').strip() if site is None else site;self.token=os.getenv('VRM_TOKEN','').strip() if token is None else token
  self.client_factory=client_factory or (lambda:httpx.AsyncClient(timeout=22));self.cache={};self.lock=asyncio.Lock()
 async def day(self,day):
  return await self.period(day,'day')
 async def period(self,day,kind='day'):
  if kind not in ('day','week','month'):raise HTTPException(400,'Kies dag, week of maand voor Victron.')
  try:
   if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):raise ValueError()
   selected=dt.date.fromisoformat(day)
  except (ValueError,TypeError):raise HTTPException(400,'Kies een geldige datum.') from None
  try:zone=ZoneInfo(self.config().get('timezone','Europe/Amsterdam'))
  except ZoneInfoNotFoundError:zone=ZoneInfo('Europe/Amsterdam')
  anchor=selected-dt.timedelta(days=selected.weekday()) if kind=='week' else selected.replace(day=1) if kind=='month' else selected
  stop=(anchor.replace(day=28)+dt.timedelta(days=4)).replace(day=1) if kind=='month' else anchor+dt.timedelta(days=7 if kind=='week' else 1)
  start=dt.datetime.combine(anchor,dt.time.min,zone);end=dt.datetime.combine(stop,dt.time.min,zone);key=(kind,anchor.isoformat())
  configured=bool(self.token and re.fullmatch(r'\d+',self.site))
  result={'configured':configured,'date':day,'period':kind,'start':start.isoformat(),'end':end.isoformat(),'timezone':str(zone),'points':[],'solar':[],'discharge':[],'solar_unit':'kWh','solar_interval_minutes':60,'fetched_at':None,'source':'Victron VRM','sample_minutes':15}
  if not configured:return result
  async with self.lock:
   cached=self.cache.get(key)
   if cached and time.monotonic()-cached[0]<300:return cached[1]
   try:
    async with self.client_factory() as client:
     response=await client.get(BASE+'/installations/'+self.site+'/stats',headers={'x-authorization':'Token '+self.token},params={'type':'custom' if kind=='day' else 'kwh','interval':'15mins' if kind=='day' else 'days','start':int(start.timestamp()),'end':int(end.timestamp()),'attributeCodes[]':['vrm_soc_plan','solar_yield_forecast']})
    if response.status_code in (401,403):raise HTTPException(503,'VRM weigert toegang tot de planning. Controleer het lokale token en de installatierechten.')
    response.raise_for_status();payload=response.json()
    if not isinstance(payload,dict) or payload.get('success') is not True:raise ValueError()
    
    if kind=='day':result['points']=normalize_plan(payload,start.timestamp(),end.timestamp());result['solar']=normalize_solar(payload,start.timestamp(),end.timestamp())
    else:result.update(normalize_daily_energy(payload,start.timestamp(),end.timestamp(),zone));result['solar_interval_minutes']=None
    result['fetched_at']=dt.datetime.now(dt.timezone.utc).isoformat()
   except (httpx.HTTPError,ValueError,TypeError):raise HTTPException(503,'De Victron-planning is tijdelijk niet beschikbaar.') from None
   self.cache[key]=(time.monotonic(),result)
   while len(self.cache)>14:self.cache.pop(next(iter(self.cache)))
   return result
