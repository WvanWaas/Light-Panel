"""Normalize existing HA solar forecasts; production is not grid export."""
import datetime as dt
import math
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

def solar_forecast(states,config,now=None):
 try:zone=ZoneInfo(config.get('timezone','Europe/Amsterdam'))
 except ZoneInfoNotFoundError:zone=ZoneInfo('Europe/Amsterdam')
 now=now or dt.datetime.now(dt.timezone.utc);today=now.astimezone(zone).date();mapping=config.get('solar_forecast',{});values={};timestamps=[]
 for key in ['today','remaining','tomorrow','current_hour','next_hour','peak_today','peak_tomorrow']:
  row=states.get(mapping.get(key),{});attributes=row.get('attributes',{});raw=row.get('state');value=None
  stamp=row.get('last_reported') or row.get('last_updated');fresh=False
  try:
   updated=dt.datetime.fromisoformat(stamp.replace('Z','+00:00'));fresh=updated.tzinfo is not None and updated.astimezone(zone).date()==today
   if fresh:timestamps.append(updated)
  except (ValueError,TypeError,AttributeError):pass
  if fresh and key.startswith('peak_'):
   try:
    peak=dt.datetime.fromisoformat(raw.replace('Z','+00:00'));day=today+dt.timedelta(days=key=='peak_tomorrow')
    if peak.tzinfo is not None and peak.astimezone(zone).date()==day:value=peak.isoformat()
   except (ValueError,TypeError,AttributeError):pass
  elif fresh:
   try:
    number=float(raw);unit=attributes.get('unit_of_measurement');factor={'kWh':1,'Wh':.001,'MWh':1000}.get(unit)
    if factor is not None and math.isfinite(number) and number>=0:value=number*factor
   except (ValueError,TypeError):pass
  values[key]=value
 return {'date':today.isoformat(),'tomorrow_date':(today+dt.timedelta(days=1)).isoformat(),'timezone':str(zone),'values':values,'updated_at':max(timestamps).isoformat() if timestamps else None,'available':any(values[k] is not None for k in ['today','remaining','tomorrow'])}
