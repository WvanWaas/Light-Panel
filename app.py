import os,json,asyncio,datetime,random,time,pathlib,xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
import httpx
from urllib.parse import quote
from websockets.asyncio.client import connect
from sync import StateCache
from backend_updates import BACKEND_INSTANCE, dashboard_page
from entity_filter import EntityFilter
from measurements import MeasurementHistory, media_actions
from thermostat_controls import thermostat_action
from light_controls import light_action
from fastapi import FastAPI,WebSocket,WebSocketDisconnect,HTTPException,Request
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
BASE=pathlib.Path(__file__).parent
from settings import load_config
CFG=load_config()
entity_filter=EntityFilter(CFG)
HA=os.getenv('HA_URL','').rstrip('/'); TOKEN=os.getenv('HA_TOKEN','')
DEMO=not (HA and TOKEN)
clients=set();news=[];alerts=[]
async def broadcast(msg):
 if 'ticker_history' in globals():capture_ticker()
 for ws in list(clients):
  try:await asyncio.wait_for(ws.send_json(msg),timeout=2)
  except Exception:clients.discard(ws)
cache=StateCache(broadcast)
states=cache.states
headers={'Authorization':'Bearer '+TOKEN}
ha_live=False
async def refresh_states(force=False):
 if DEMO:return
 async with cache.refresh_lock:
  before=dict(cache.versions)
  async with httpx.AsyncClient(timeout=12) as c:
   r=await c.get(HA+'/api/states',headers=headers);r.raise_for_status()
  await cache.snapshot(entity_filter.select(r.json()),before)
  await cache.connection('live' if ha_live else 'polling')
async def poll():
 last_refresh=0
 while True:
  if not DEMO and (not ha_live or time.monotonic()-last_refresh>=60):
   try:
    await refresh_states();last_refresh=time.monotonic()
   except Exception:
    if not ha_live:await cache.connection('offline')
  await asyncio.sleep(8)
async def ha_events():
 global ha_live
 delay=1
 url=('wss' if HA.startswith('https://') else 'ws')+HA[HA.index(':'):]+ '/api/websocket' if HA else ''
 while not DEMO:
  try:
   async with connect(url,open_timeout=12,ping_interval=20,ping_timeout=20,max_size=16*1024*1024) as ws:
    async def receive():return json.loads(await asyncio.wait_for(ws.recv(),timeout=15))
    if (await receive()).get('type')!='auth_required':raise RuntimeError('HA handshake')
    await ws.send(json.dumps({'type':'auth','access_token':TOKEN}))
    if (await receive()).get('type')!='auth_ok':raise RuntimeError('HA authentication')
    await ws.send(json.dumps({'id':1,'type':'subscribe_events','event_type':'state_changed'}))
    ack=await receive()
    if ack.get('id')!=1 or not ack.get('success'):raise RuntimeError('HA subscription')
    before=dict(cache.versions)
    await ws.send(json.dumps({'id':2,'type':'get_states'}))
    # Read events while the initial snapshot is in flight, preserving event versions.
    while True:
     m=await receive()
     if m.get('type')=='event':
      d=m['event']['data']
      if entity_filter.includes(d['entity_id']):await cache.event(d['entity_id'],d.get('new_state'));capture_ticker()
     elif m.get('id')==2:
      if not m.get('success'):raise RuntimeError('HA snapshot')
      await cache.snapshot(entity_filter.select(m['result']),before);break
    ha_live=True;delay=1;await cache.connection('live')
    received=0
    async for raw in ws:
     received+=1
     if received%50==0:await asyncio.sleep(0)
     m=json.loads(raw)
     if m.get('type')=='event':
      d=m['event']['data']
      if entity_filter.includes(d['entity_id']):await cache.event(d['entity_id'],d.get('new_state'));capture_ticker()
  except Exception:
   pass
  finally:
   ha_live=False
   await cache.connection('offline')
  await asyncio.sleep(delay+random.random());delay=min(delay*2,30)
async def rss():
 feeds={'Tweakers':'https://feeds.feedburner.com/tweakers/mixed','NOS':'https://feeds.nos.nl/nosnieuwsalgemeen'}
 async with httpx.AsyncClient(timeout=12,follow_redirects=True) as c:
  while True:
   result=[]
   for name,url in feeds.items():
    try:
     r=await c.get(url,headers={'User-Agent':'HomeHub/1.0'});r.raise_for_status();root=ET.fromstring(r.text)
     items=root.findall('.//item')[:3]
     result += [{'source':name,'title':(it.findtext('title') or '').strip(),'url':it.findtext('link') or ''} for it in items]
    except Exception as e:print('RSS',name,str(e)[:100])
   news[:]=result;await broadcast({'type':'news','items':news});await asyncio.sleep(900)
@asynccontextmanager
async def lifespan(app):
 tasks=[asyncio.create_task(site_monitor.run()),asyncio.create_task(poll()),asyncio.create_task(ha_events()),asyncio.create_task(rss()),asyncio.create_task(cache.stream()),asyncio.create_task(feed_loop()),asyncio.create_task(feed_price_loop())]
 if DEMO:await cache.connection('demo')
 yield
 for t in tasks:t.cancel()
 await asyncio.gather(*tasks,return_exceptions=True)
from site_status import SiteMonitor
site_monitor=SiteMonitor(domains=CFG.get('websites',[]))
app=FastAPI(title='Light Panel',version='0.1.0',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
(BASE/'photos').mkdir(exist_ok=True)
app.mount('/photos',StaticFiles(directory=BASE/'photos'),name='photos')
@app.get('/')
def index():return dashboard_page(BASE/'static/index.html')
@app.get('/api/backend-version')
def backend_version():
 return Response(json.dumps({'backend_instance':BACKEND_INSTANCE}),media_type='application/json',headers={'Cache-Control':'no-store'})
@app.get('/api/time')
def server_time():
 return Response(json.dumps({'server_time_ms':int(time.time()*1000)}),media_type='application/json',headers={'Cache-Control':'no-store'})
@app.get('/api/bootstrap')
def bootstrap():
 photos=['/photos/'+quote(p.name) for p in sorted((BASE/'photos').iterdir()) if p.suffix.lower() in ('.jpg','.jpeg','.png','.webp')]
 return {'backend_instance':BACKEND_INSTANCE,'demo':DEMO,'config':CFG,'states':dict(states),'revision':cache.revision,'connection':dict(cache.status),'news':news,'photos':photos,'alerts':alerts[-15:]}
@app.get('/api/states')
async def state_refresh():
 try:await refresh_states()
 except Exception:raise HTTPException(503,'Home Assistant-status niet bereikbaar; laatste status kan verouderd zijn.')
 return cache.payload()
@app.websocket('/ws')
async def socket(ws:WebSocket):
 await ws.accept()
 try:
  await ws.send_json({'type':'backend_version','backend_instance':BACKEND_INSTANCE})
  async with cache.lock:
   clients.add(ws);await ws.send_json(cache.payload())
  while True:
   await ws.receive_text()
   await ws.send_json({'type':'pong','connection':dict(cache.status)})
 except WebSocketDisconnect:pass
 finally:clients.discard(ws)
@app.post('/api/action')
async def action(req:Request):
 data=await req.json();key=data.get('key');item=media_actions(CFG).get(key)
 if key in ['thermostat_temperature','thermostat_mode']:item=thermostat_action(data,CFG,states)
 if key=='light_set':item=light_action(data,CFG,states)
 if not item and key=='light_toggle':
  entity=data.get('entity_id','')
  if entity not in CFG.get('lights',[]):raise HTTPException(403,'Light not allowlisted')
  item={'service':'light.toggle','entity_id':entity}
 if not item:raise HTTPException(403,'Action not allowlisted')
 if not DEMO and key in media_actions(CFG) and item['entity_id'].startswith(('script.','media_player.')):
  target=states.get(item['entity_id'])
  if not target or target.get('state') in ('unknown','unavailable'):raise HTTPException(409,'Dit apparaat of script is niet beschikbaar in Home Assistant.')
 if DEMO:return {'ok':True,'demo':True,'key':key}
 domain,service=item['service'].split('.',1)
 try:
  async with httpx.AsyncClient(timeout=12) as c:
   r=await c.post(HA+f'/api/services/{domain}/{service}',headers=headers,json={'entity_id':item['entity_id'],**item.get('data',{})});r.raise_for_status()
 except httpx.TimeoutException:
  raise HTTPException(504,'Geen bevestiging van Home Assistant. Controleer de status voordat je opnieuw schakelt.')
 except httpx.HTTPError:
  raise HTTPException(502,'Home Assistant kon de actie niet uitvoeren. Controleer verbinding en token.')
 synced=True
 try:await refresh_states(force=True)
 except Exception:synced=False
 return {'ok':True,'synced':synced}
@app.get('/api/camera/{name}')
async def camera(name:str,refresh:int=0):
 entity=CFG['cameras'].get(name)
 if not entity:raise HTTPException(404)
 if DEMO:raise HTTPException(404,'No live camera in demo')
 try:
  async with httpx.AsyncClient(timeout=15) as c:
   r=await c.get(HA+'/api/camera_proxy/'+entity,headers=headers)
   if r.status_code>=500:
    await asyncio.sleep(.3)
    r=await c.get(HA+'/api/camera_proxy/'+entity,headers=headers)
   if r.status_code==404:raise HTTPException(404,'Deze camera-entiteit of snapshot is niet beschikbaar in Home Assistant.')
   r.raise_for_status()
  if not r.headers.get('content-type','').startswith('image/'):
   raise HTTPException(502,'Home Assistant leverde geen camerabeeld.')
 except httpx.TimeoutException:
  raise HTTPException(504,'De camera reageert niet op tijd. Probeer een nieuwe snapshot.')
 except httpx.HTTPError:
  raise HTTPException(502,'Het camerabeeld kon niet worden opgehaald bij Home Assistant.')
 return Response(r.content,media_type=r.headers.get('content-type','image/jpeg'),headers={'Cache-Control':'no-store'})
@app.post('/api/notify')
async def notify(req:Request):
 secret=os.getenv('NOTIFY_SECRET','')
 if not secret or req.headers.get('X-Notify-Secret')!=secret:raise HTTPException(403)
 data=await req.json();item={'title':str(data.get('title','Melding'))[:140],'message':str(data.get('message',''))[:500],'kind':str(data.get('kind','info'))[:30],'time':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 alerts.append(item);del alerts[:-30];await broadcast({'type':'alert','item':item});return {'ok':True}

# Read-only detail panels. HA tokens stay on the server.
from details import DetailProvider
from fastapi import Query
provider=DetailProvider(lambda:CFG,lambda:states,lambda:(HA,TOKEN,DEMO))
@app.get('/api/weather')
async def weather_details(refresh:bool=False):
 return Response(json.dumps(await provider.weather(force=refresh)),media_type='application/json',headers={'Cache-Control':'no-store'})
@app.get('/api/calendar/sources')
async def calendar_sources():
 return Response(json.dumps(await provider.sources()),media_type='application/json',headers={'Cache-Control':'no-store'})
@app.get('/api/calendar')
async def calendar_events(start:str,end:str,calendars:str=''):
 return Response(json.dumps(await provider.events(start,end,calendars)),media_type='application/json',headers={'Cache-Control':'no-store'})

from live_ticker import collect_ticker, TickerHistory
from notification_history import NotificationArchive,history_id
import sqlite3
notification_archive=NotificationArchive(os.getenv('NOTIFICATION_HISTORY_PATH',str(BASE/'notification-history'/'notifications.sqlite3')))
from feed_events import FeedEvents
try:feed_engine=FeedEvents(notification_archive.load_feed_state())
except (OSError,sqlite3.Error,ValueError):feed_engine=FeedEvents()
feed_prices_state={'days':[],'checked':0}
ticker_history=TickerHistory()
def capture_ticker():
 managed=feed_engine.cards();ids={item['id'] for item in managed}
 for key,item in list(ticker_history.items.items()):
  if item.get('managed_feed') and key not in ids:ticker_history.items.pop(key,None)
 ticker_history.observe(states,CFG,alerts,ha_online=DEMO or cache.status['mode'] in ['live','polling'])
 for item in managed:ticker_history.items[item['id']]=item
 ticker_history.items=dict(sorted(ticker_history.items.items(),key=lambda pair:pair[1]['time'],reverse=True)[:200])
 result=ticker_history.payload()
 try:notification_archive.remember(result['items']);result['history_available']=True
 except (OSError,sqlite3.Error):result['history_available']=False
 result['items']=[{**item,'history_id':history_id(item)} for item in result['items']]
 return result
@app.get('/api/ticker')
async def current_notifications():
 return Response(json.dumps(capture_ticker()),media_type='application/json',headers={'Cache-Control':'no-store'})
@app.get('/api/ticker/history')
def notification_history(categories:str='',before:str='',limit:int=50):
 try:return notification_archive.page(categories,before,limit)
 except ValueError:raise HTTPException(400,'Ongeldig historiefilter of paginanummer.') from None
 except (OSError,sqlite3.Error):raise HTTPException(503,'De meldingshistorie is tijdelijk niet bereikbaar.') from None

@app.get('/api/ticker/history/{card_id}')
def historical_notification(card_id:str):
 try:item=notification_archive.get(card_id)
 except (OSError,sqlite3.Error):raise HTTPException(503,'De meldingshistorie is tijdelijk niet bereikbaar.') from None
 if not item:raise HTTPException(404,'Deze melding staat niet in de historie.')
 return {'item':item}

@app.get('/api/energy/solar-today')
async def solar_daily():
 return Response(json.dumps(await provider.solar_today()),media_type='application/json',headers={'Cache-Control':'no-store'})

@app.get('/api/energy/prices')
async def electricity_day_prices(date:str=''):
 return Response(json.dumps(await provider.day_prices(date)),media_type='application/json',headers={'Cache-Control':'no-store'})

from energy_day import EnergyDayProvider
from countdowns import CountdownProvider
energy_day_provider=EnergyDayProvider(provider)
countdown_provider=CountdownProvider(provider)
@app.get('/api/energy/day')
async def p1_day(date:str='',export_mode:str='unknown',export_rate:float|None=None,refresh:bool=False):
 return Response(json.dumps(await energy_day_provider.day(date,export_mode,export_rate,refresh)),media_type='application/json',headers={'Cache-Control':'no-store'})
@app.get('/api/countdowns')
async def upcoming_moments(calendars:str|None=None,refresh:bool=False):
 return Response(json.dumps(await countdown_provider.get(calendars,refresh)),media_type='application/json',headers={'Cache-Control':'no-store'})

measurement_history=MeasurementHistory(provider)
@app.get('/api/history/measurement')
async def measurement_graph(key:str,hours:int=24):
 return Response(json.dumps(await measurement_history.get(key,hours)),media_type='application/json',headers={'Cache-Control':'no-store'})

# Tibber history is separate from Home Assistant P1 calculations.
from tibber_routes import router as tibber_router
app.include_router(tibber_router)

@app.get('/meldingen/{card_id}')
def notification_detail(card_id:str):
 return FileResponse(BASE/'static/notification-detail.html',headers={'Cache-Control':'no-store'})


@app.get('/api/sites')
async def website_status(refresh:bool=False):
 return await site_monitor.check(force=refresh)

from dashboard_tools import test_card

def check_local_request(req):
 origin=req.headers.get('origin')
 if origin and origin.rstrip('/')!=str(req.base_url).rstrip('/'):
  raise HTTPException(403,'Open deze bediening vanuit het dashboard.')

@app.post('/api/ticker/test')
async def send_test_card(req:Request):
 check_local_request(req)
 try:data=await req.json()
 except ValueError:raise HTTPException(400,'Ongeldige aanvraag.')
 if not isinstance(data,dict):raise HTTPException(400,'Ongeldige aanvraag.')
 item=test_card(data.get('kind'))
 capture_ticker()
 tests=[key for key,value in ticker_history.items.items() if value.get('is_test')]
 for key in tests[:-19]:ticker_history.items.pop(key,None)
 ticker_history.items[item['id']]=item
 notification_archive.remember([item])
 return {'ok':True,'item':item}

@app.delete('/api/ticker/test')
async def clear_test_cards(req:Request):
 check_local_request(req)
 notification_archive.clear_tests()
 for key in list(ticker_history.items):
  if ticker_history.items[key].get('is_test'):ticker_history.items.pop(key,None)
 return {'ok':True}


from device_energy import DeviceEnergy
from astronomy import Astronomy
device_energy=DeviceEnergy(provider)
astronomy=Astronomy(provider)

@app.get('/api/energy/devices-today')
async def device_day_totals():
 return await device_energy.today()

@app.get('/api/astronomy')
async def sun_moon_today():
 return await astronomy.today()

from solar_forecast import solar_forecast
@app.get('/api/energy/solar-forecast')
async def solar_production_forecast():
 return Response(json.dumps(solar_forecast(states,CFG)),media_type='application/json',headers={'Cache-Control':'no-store'})

from vrm_planning import VrmPlanning
vrm_planning=VrmPlanning(lambda:CFG)
@app.get('/api/energy/victron-planning')
async def victron_battery_planning(date:str,period:str='day'):
 return Response(json.dumps(await vrm_planning.period(date,period)),media_type='application/json',headers={'Cache-Control':'no-store'})

async def feed_price_loop():
 import tibber_data
 while True:
  if tibber_data.TOKEN:
   try:
    homes=await asyncio.to_thread(tibber_data.homes);selected=homes[0] if homes else None
    if selected:
     from zoneinfo import ZoneInfo
     today=datetime.datetime.now(ZoneInfo(selected['timeZone'])).date();fresh=[]
     for day in [today,today+datetime.timedelta(days=1)]:
      try:fresh.append(await asyncio.to_thread(tibber_data.day_data,day.isoformat(),selected['id']))
      except tibber_data.ApiError:pass
     if fresh:feed_prices_state.update(days=fresh,checked=time.monotonic())
   except Exception:pass
  await asyncio.sleep(300)

async def feed_loop():
 last_saved=''
 while True:
  try:
   now=datetime.datetime.now(datetime.timezone.utc);prices=feed_prices_state['days'] if time.monotonic()-feed_prices_state['checked']<=900 else []
   feed_engine.update(states,CFG,site_monitor.payload()['sites'],prices,now=now,ha_online=not DEMO and cache.status['mode'] in ['live','polling'])
   saved=json.dumps(feed_engine.export(),sort_keys=True)
   if saved!=last_saved:
    try:notification_archive.save_feed_state(feed_engine.export());last_saved=saved
    except (OSError,sqlite3.Error):pass
   capture_ticker()
  except Exception:pass
  await asyncio.sleep(15)

from frameo_remote import router as frameo_remote_router
app.include_router(frameo_remote_router)
