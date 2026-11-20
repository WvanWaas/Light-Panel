"""Read-only event cards for aurora, CO2, site availability and cheap power."""
import datetime as dt
import hashlib
import math
from zoneinfo import ZoneInfo
from live_ticker import timestamp
from solar_forecast import solar_forecast
from appliance_events import appliance_events
UTC=dt.timezone.utc

def numeric(value):
 if isinstance(value,bool):return None
 try:
  n=float(value);return n if math.isfinite(n) else None
 except (ValueError,TypeError):return None

def charging_context(states,config,now,ha_online=True):
 settings=config.get('feed_notifications',{});row=states.get(config.get('battery'),{});soc=numeric(row.get('state'))
 reported=timestamp(row.get('last_reported') or row.get('last_updated'));age=(now-reported).total_seconds() if reported else None
 if not ha_online or soc is None or not 0<=soc<=100 or age is None or not 0<=age<=900:return None
 if soc>=settings.get('cheap_max_soc',90):return None
 forecast=solar_forecast(states,config,now);remaining=forecast['values'].get('remaining')
 # Never substitute total daily production for sunlight that is still to come.
 solar_row=states.get(config.get('solar_forecast',{}).get('remaining'),{});solar_time=timestamp(solar_row.get('last_reported') or solar_row.get('last_updated'))
 if remaining is None or solar_time is None or not 0<=(now-solar_time).total_seconds()<=7200:return None
 capacity=numeric(settings.get('battery_capacity_kwh'));target=settings.get('cheap_max_soc',90);fraction=settings.get('cheap_solar_charge_fraction',.5)
 limit_entities=settings.get('battery_min_soc_entities',[]);limits=[numeric(states.get(entity,{}).get('state')) for entity in limit_entities];limits=[value for value in limits if value is not None and 0<=value<target]
 if limit_entities and not limits:return None
 minimum=max(limits,default=0);room=None;usable=None
 if capacity is not None and capacity>0:
  room=capacity*(target-soc)/100
  usable=capacity*max(0,soc-minimum)/100
  if room<settings.get('cheap_min_charge_kwh',1) or (soc>=minimum and remaining*fraction>=room):return None
 elif soc>=settings.get('cheap_solar_min_soc',60) and remaining>=settings.get('cheap_solar_min_kwh',3):return None
 return {'battery_soc':soc,'solar_remaining_kwh':remaining,'battery_capacity_kwh':capacity,'battery_min_soc':minimum,'battery_usable_kwh':usable,'battery_room_kwh':room}

class FeedEvents:
 def __init__(self,saved=None):
  saved=saved if isinstance(saved,dict) else {};self.active=saved.get('active',{});self.transient=saved.get('transient',{});self.sites=saved.get('sites',{});self.sent=saved.get('sent',{});self.co2_since=None;self.appliances=saved.get('appliances',{});self.fault_since={}
 def export(self):return {'active':self.active,'transient':self.transient,'sites':self.sites,'sent':self.sent,'appliances':self.appliances}
 def make(self,key,kind,title,message,now,expires=None,**extra):
  at=now.isoformat();return {'id':hashlib.sha256((key+'|'+at).encode()).hexdigest()[:20],'kind':kind,'title':title,'message':message,'time':at,'expires_at':(expires or now+dt.timedelta(minutes=10)).isoformat(),'priority':60,'managed_feed':True,**extra}
 def ongoing(self,key,kind,title,message,now,**extra):
  item=self.active.get(key)
  if not item:item=self.make(key,kind,title,message,now,**extra);self.active[key]=item
  item.update(message=message,expires_at=(now+dt.timedelta(minutes=10)).isoformat())
 def update(self,states,config,sites=(),prices=(),now=None,ha_online=True):
  now=now or dt.datetime.now(UTC);self.active={key:item for key,item in self.active.items() if timestamp(item['expires_at'])>now};settings=config.get('feed_notifications',{});zone=ZoneInfo(config.get('timezone') or 'Europe/Amsterdam')
  appliance_events(self,states,settings,now,ha_online)
  aurora=states.get(settings.get('aurora_entity'),{}).get('state')
  if ha_online and aurora=='on':self.ongoing('aurora','aurora','Kans op noorderlicht','Je noorderlichtsensor meldt zichtkans. Kijk of het donker en helder is; zicht is niet gegarandeerd.',now)
  elif ha_online and aurora=='off':self.active.pop('aurora',None)
  value=numeric(states.get(settings.get('co2_entity'),{}).get('state')) if ha_online else None
  threshold=settings.get('co2_threshold',1500);clear=settings.get('co2_clear_below',900);delay=settings.get('co2_delay_seconds',300)
  if value is None or value<0:self.co2_since=None
  elif 'air' in self.active:
   if value<clear:self.active.pop('air',None);self.co2_since=None
   else:self.ongoing('air','air','Tijd om te luchten',f'CO₂ is {value:.0f} ppm. De melding verdwijnt onder {clear} ppm.',now)
  elif value>=threshold:
   if self.co2_since is None:self.co2_since=now
   if (now-self.co2_since).total_seconds()>=delay:self.ongoing('air','air','Tijd om te luchten',f'CO₂ is {value:.0f} ppm en is minstens {delay//60} minuten boven {threshold} ppm.',now)
  else:self.co2_since=None
  for site in sites:
   domain=site.get('domain');checked=timestamp(site.get('checked_at'));status=site.get('status')
   if not domain or checked is None or (now-checked).total_seconds()>180 or status not in ('online','protected','error','offline'):continue
   state=self.sites.setdefault(domain,{'checked':None,'failures':0,'outage':False});key='site:'+domain
   if state['checked']==site['checked_at']:
    if state['outage']:self.ongoing(key,'sites','Website niet bereikbaar',domain+' · '+('HTTP '+str(site['http_status']) if site.get('http_status') else site.get('reason') or 'Verbindingsfout'),now,source_url=site.get('url'))
    continue
   if state['checked'] and (checked-timestamp(state['checked'])).total_seconds()>180 and not state['outage']:state['failures']=0
   state['checked']=site['checked_at'];reachable=status in ('online','protected')
   if not reachable:
    state['failures']+=1
    if state['failures']>=settings.get('website_confirmations',2):
     state['outage']=True;self.ongoing(key,'sites','Website niet bereikbaar',domain+' · '+('HTTP '+str(site['http_status']) if site.get('http_status') else site.get('reason') or 'Verbindingsfout'),now,source_url=site.get('url'))
   else:
    if state['outage']:
     self.active.pop(key,None);item=self.make('recovery:'+domain,'sites','Website weer bereikbaar',domain+' is hersteld.',now,source_url=site.get('url'));self.transient[item['id']]=item
    state.update(failures=0,outage=False)
  charge=charging_context(states,config,now,ha_online)
  if charge is None:self.transient={key:item for key,item in self.transient.items() if item.get('kind')!='energy'}
  for day in prices if charge is not None else ():
   rows=day.get('prices',[]);start=timestamp(day.get('start'));end=timestamp(day.get('end'))
   if not start or not end or not rows:continue
   valid=[]
   for row in rows:
    a,b=timestamp(row.get('start')),timestamp(row.get('end'));price=numeric(row.get('price'))
    if a and b and b>a and price is not None:valid.append((a,b,price))
   valid.sort(key=lambda row:row[0])
   if not valid or valid[0][0]!=start or valid[-1][1]!=end or any(a[1]!=b[0] for a,b in zip(valid,valid[1:])):continue
   duration=sum((b-a).total_seconds() for a,b,_ in valid);average=sum((b-a).total_seconds()*p for a,b,p in valid)/duration;window=settings.get('cheap_window_minutes',60)*60;options=[]
   for i,(a,_,_) in enumerate(valid):
    until=a+dt.timedelta(seconds=window);total=0;covered=0
    for aa,bb,p in valid[i:]:
     seconds=(min(bb,until)-aa).total_seconds()
     if seconds<=0:break
     total+=seconds*p;covered+=seconds
     if bb>=until:break
    if covered==window:options.append((total/window,a,until))
   if not options:continue
   price,a,b=min(options,key=lambda row:(row[0],row[1]));key='cheap:'+a.isoformat()
   if price>=average-.005 or key in self.sent or not a-dt.timedelta(minutes=settings.get('cheap_lead_minutes',30))<=now<b:continue
   label='Vandaag' if a.astimezone(zone).date()==now.astimezone(zone).date() else 'Morgen';clock=lambda t:t.astimezone(zone).strftime('%H:%M');amount=f'{price*100:.2f}'.replace('.',',');message=f'{label} {clock(a)}–{clock(b)} · gemiddeld {amount} ct/kWh. Het voordeligste uur van deze dag. Accu {charge["battery_soc"]:.0f}% · nog {charge["solar_remaining_kwh"]:.1f} kWh zon verwacht vandaag (productie, geen gegarandeerd laadoverschot).'
   if charge['battery_room_kwh'] is not None:message+=f' Laadruimte {charge["battery_room_kwh"]:.1f} kWh · beschikbaar boven {charge["battery_min_soc"]:.0f}% reserve: {charge["battery_usable_kwh"]:.1f} kWh.'
   item=self.make(key,'energy','Goedkoop laadmoment',message,now,expires=b,source_url=None,window_start=a.isoformat(),window_end=b.isoformat(),price=price,**charge);self.transient[item['id']]=item;self.sent[key]=now.isoformat()
  self.transient={key:item for key,item in self.transient.items() if timestamp(item['expires_at'])>now};self.sent={key:value for key,value in self.sent.items() if (now-timestamp(value)).days<7}
  return self.cards(now)
 def cards(self,now=None):
  now=now or dt.datetime.now(UTC);return sorted([item for item in [*self.active.values(),*self.transient.values()] if timestamp(item['expires_at'])>now],key=lambda item:item['time'],reverse=True)
