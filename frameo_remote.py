"""LAN-only dashboard control relay. No shell commands or arbitrary navigation."""
import asyncio,base64,binascii,json,re,time,uuid,os,secrets
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import APIRouter,HTTPException,Request,WebSocket,WebSocketDisconnect
from fastapi.responses import Response
from backend_updates import dashboard_page

router=APIRouter();devices={};pending={}
ACTIONS={'sound_settings','sound_test','led_test','led_restore','led_save','auto','photo','dashboard','next_photo','reload','capture','screen_on','screen_off','message','message_clear'}
def local_origin(headers,host):
 origin=headers.get('origin')
 if origin and (urlsplit(origin).netloc!=host or urlsplit(origin).scheme not in ('http','https')):raise HTTPException(403,'Open de bediening via dezelfde dashboardserver.')
from settings import load_config
MESSAGE_CAMERAS=load_config().get('cameras',{})
MESSAGE_ICONS={'fan','fan-off','airco','airco-off','garage','lock','unlock','check', 'battery', 'info', 'dishwasher', 'car', 'package', 'bell', 'warning', 'door', 'doorbell', 'thermometer', 'charging', 'trash', 'dryer', 'washing-machine'}
def command_value(data):
 if not isinstance(data,dict) or data.get('action') not in ACTIONS:raise HTTPException(400,'Onbekende opdracht.')
 action=data['action'];result={'action':action}
 if action=='sound_settings':
  if type(data.get('enabled')) is not bool or type(data.get('volume')) is not int or not 0<=data['volume']<=100:raise HTTPException(400,'Kies een volume van 0 tot 100 en geluid aan of uit.')
  result.update(enabled=data['enabled'],volume=data['volume'])
 if action in ('led_test','led_save'):
  color=data.get('color');brightness=data.get('brightness')
  if not isinstance(color,str) or not re.fullmatch('#[0-9a-fA-F]{6}',color) or type(brightness) is not int or not 0<=brightness<=255:raise HTTPException(400,'Kies een geldige kleur en helderheid.')
  result.update(color=color.lower(),brightness=brightness)
 if action=='auto':
  if type(data.get('enabled')) is not bool:raise HTTPException(400,'Kies aan of uit.')
  result['enabled']=data['enabled']
 if action=='message':
  title=data.get('title','');text=data.get('text','');color=data.get('color','#338cc7');duration=data.get('duration',30);wake=data.get('wake',True);icon=data.get('icon','bell')
  if not isinstance(title,str) or len(title)>100 or not isinstance(text,str) or len(text)>1000 or not (title.strip() or text.strip()):raise HTTPException(400,'Geef een titel of tekst op (maximaal 100 / 1000 tekens).')
  if not isinstance(color,str) or not re.fullmatch('#[0-9a-fA-F]{6}',color):raise HTTPException(400,'Ongeldige meldingskleur.')
  if type(duration) is not int or not 0<=duration<=3600 or type(wake) is not bool:raise HTTPException(400,'Duur: 0–3600 seconden. Wakker maken: aan of uit.')
  if not isinstance(icon,str) or icon not in MESSAGE_ICONS:raise HTTPException(400,'Kies een geldig meldingsicoon.')
  camera=data.get('camera','Voordeur' if icon=='doorbell' and 'Voordeur' in MESSAGE_CAMERAS else '')
  if not isinstance(camera,str) or camera and camera not in MESSAGE_CAMERAS:raise HTTPException(400,'Kies een gekoppelde camera.')
  crop=data.get('camera_crop','full')
  if crop not in ('full','left'):raise HTTPException(400,'Kies een geldig camerakader.')
  badge=data.get('badge','')
  if not isinstance(badge,str) or len(badge)>24:raise HTTPException(400,'Ongeldig bijschrift.')
  result.update(camera_crop=crop,badge=badge,camera=camera,icon=icon,title=title.strip(),text=text.strip(),color=color.lower(),duration=duration,wake=wake)
 return result

def online(device):return device.get('socket') is not None and time.monotonic()-device['seen']<45

def safe_report(data):
 if not isinstance(data,dict):return {}
 result={}
 for key in ('page','connection','version','error'):
  if isinstance(data.get(key),str):result[key]=data[key][:240]
 for key in ('photo','visible','capture','screenControl','screenOn'):
  if type(data.get(key)) is bool:result[key]=data[key]
 sound=data.get('sound')
 if isinstance(sound,dict):result['sound']={k:sound[k] for k in ('enabled','volume','available','message','hours','timeZone') if k in sound and isinstance(sound[k],(str,bool,int)) and (not isinstance(sound[k],str) or len(sound[k])<250)}
 led=data.get('led')
 if isinstance(led,dict):
  result['led']={k:led[k] for k in ('connected','auto','testing','confirmed','message','color','brightness','amberColor') if k in led and isinstance(led[k],(str,bool,int)) and (not isinstance(led[k],str) or len(led[k])<250)}
 return result

@router.get('/beheer/fotolijst')
def page():return dashboard_page(Path(__file__).parent/'static/frameo-admin.html')

@router.get('/api/frameo/devices')
def listing():
 return Response(json.dumps({'devices':[{'id':key,'name':d['name'],'online':online(d),'last_seen':d['wall'],'status':d.get('status',{})} for key,d in devices.items()]}),media_type='application/json',headers={'Cache-Control':'no-store'})

@router.websocket('/ws/frameo')
async def device_socket(ws:WebSocket):
 try:local_origin(ws.headers,ws.url.netloc)
 except HTTPException:await ws.close(code=1008);return
 await ws.accept();key=None;device=None
 try:
  first=await asyncio.wait_for(ws.receive_text(),15)
  if len(first)>10000:raise ValueError()
  hello=json.loads(first)
  if not isinstance(hello,dict):raise ValueError()
  key=hello.get('device')
  if hello.get('type')!='register' or not isinstance(key,str) or not re.fullmatch('[a-zA-Z0-9_-]{12,80}',key):raise ValueError()
  if key not in devices and len(devices)>=20:raise ValueError()
  previous=devices.get(key)
  if previous and previous.get('socket'):
   await previous['socket'].close(code=1000)
  device={'name':str(hello.get('name','Fotolijst'))[:60],'socket':ws,'seen':time.monotonic(),'wall':int(time.time()*1000),'status':safe_report(hello.get('status',{})),'lock':asyncio.Lock()};devices[key]=device
  await ws.send_json({'type':'registered'})
  while True:
   raw=await asyncio.wait_for(ws.receive_text(),60)
   if len(raw)>2000000:raise ValueError()
   message=json.loads(raw)
   if not isinstance(message,dict):raise ValueError()
   device['seen']=time.monotonic();device['wall']=int(time.time()*1000)
   if message.get('type')=='status':device['status']=safe_report(message.get('status'))
   elif message.get('type')=='result':
    request=pending.get(message.get('id'))
    if request and request['socket'] is ws and not request['future'].done():request['future'].set_result(message)
 except (WebSocketDisconnect,asyncio.TimeoutError,ValueError,TypeError,RuntimeError):pass
 finally:
  if device and devices.get(key) is device:device['socket']=None
  for request in list(pending.values()):
   if request['socket'] is ws and not request['future'].done():request['future'].set_result({'ok':False,'message':'Fotolijstverbinding verbroken.'})
  try:await ws.close()
  except RuntimeError:pass

@router.post('/api/frameo/devices/{key}/command')
async def control(key:str,req:Request):
 local_origin(req.headers,req.url.netloc)
 try:data=await req.json()
 except ValueError:raise HTTPException(400,'Ongeldige opdracht.')
 return await relay(key,command_value(data))

async def relay(key,value):
 device=devices.get(key)
 if not device or not online(device):raise HTTPException(409,'Fotolijst is niet online.')
 if (value['action'] in ('screen_on','screen_off') or value['action']=='message' and value['wake']) and device.get('status',{}).get('screenControl') is not True:raise HTTPException(409,'Werk de APK bij voor schermbediening.')
 if value['action']=='capture' and device.get('status',{}).get('capture') is not True:raise HTTPException(409,'Werk de APK bij voor schermbeelden.')
 if sum(1 for p in pending.values() if p['socket'] is device['socket'])>=3:raise HTTPException(429,'Wacht op de vorige opdracht.')
 identifier=uuid.uuid4().hex;future=asyncio.get_running_loop().create_future();pending[identifier]={'future':future,'socket':device['socket']}
 try:
  async with device['lock']:await device['socket'].send_json({'type':'command','id':identifier,**value})
  result=await asyncio.wait_for(future,18 if value['action']=='capture' else 12)
  if result.get('ok') is not True:raise HTTPException(502,str(result.get('message','Niet bevestigd.'))[:240])
  if value['action']=='capture':
   image=result.get('image','')
   if not isinstance(image,str) or not image.startswith('data:image/jpeg;base64,') or len(image)>1800000:raise HTTPException(502,'Ongeldig schermbeeld.')
   try:decoded=base64.b64decode(image.split(',',1)[1],validate=True)
   except (ValueError,binascii.Error):raise HTTPException(502,'Ongeldig schermbeeld.')
   if not decoded.startswith(b'\xff\xd8'):raise HTTPException(502,'Ongeldig schermbeeld.')
   return Response(decoded,media_type='image/jpeg',headers={'Cache-Control':'no-store'})
  return {'ok':True,'message':str(result.get('message','Uitgevoerd.'))[:240]}
 except asyncio.TimeoutError:raise HTTPException(504,'Geen bevestiging van de fotolijst.')
 except (RuntimeError,WebSocketDisconnect):raise HTTPException(409,'Fotolijstverbinding verbroken.')
 finally:pending.pop(identifier,None)



def hardware(device):
 status=device.get('status',{})
 return status.get('led',{}).get('connected') is True or status.get('screenControl') is True or status.get('capture') is True

async def relay_frames(value):
 keys=[key for key,device in list(devices.items()) if hardware(device) and online(device)]
 if not keys:raise HTTPException(409,'Geen hardwarefotolijst online.')
 if value['action']=='capture':
  if len(keys)!=1:raise HTTPException(400,'Kies voor een schermbeeld één fotolijst met device.')
  return await relay(keys[0],value)
 async def send(key):
  try:
   result=await relay(key,value)
   return {'device':key,'ok':True,'message':result['message']}
  except HTTPException as error:return {'device':key,'ok':False,'status':error.status_code,'message':str(error.detail)}
 results=await asyncio.gather(*(send(key) for key in keys))
 confirmed=sum(result['ok'] for result in results)
 result={'ok':confirmed==len(keys),'message':f'Bevestigd op {confirmed} van {len(keys)} fotolijsten.','results':results}
 if confirmed!=len(keys):return Response(json.dumps(result),status_code=502,media_type='application/json')
 return result


def webhook_token():
 configured=os.getenv('FRAMEO_WEBHOOK_TOKEN','')
 if configured:
  if len(configured)<32:raise HTTPException(503,'Webhook-sleutel moet minstens 32 tekens bevatten.')
  return configured
 path=Path(os.getenv('NOTIFICATION_HISTORY_PATH',str(Path(__file__).parent/'notification-history/notifications.sqlite3'))).parent/'frameo-webhook.key'
 try:
  path.parent.mkdir(parents=True,exist_ok=True)
  try:
   with open(path,'x',opener=lambda name,flags:os.open(name,flags,0o600)) as output:output.write(secrets.token_urlsafe(32))
  except FileExistsError:pass
  token=path.read_text().strip()
  if len(token)<32:raise OSError('Invalid key')
  return token
 except OSError:raise HTTPException(503,'Webhook-sleutel kan niet worden gelezen of bewaard.')

@router.get('/api/frameo/message/options')
def message_options():
 return {'cameras':list(MESSAGE_CAMERAS),'garage':{k:v for k,v in load_config().get('dashboard',{}).items() if k in ('garage_camera','garage_camera_crop','garage_pip_camera')}}

@router.get('/api/frameo/webhook/settings')
def webhook_settings(req:Request):
 local_origin(req.headers,req.url.netloc)
 return Response(json.dumps({'url':str(req.base_url)+'api/frameo/webhook','token':webhook_token()}),media_type='application/json',headers={'Cache-Control':'no-store'})

@router.post('/api/frameo/webhook')
async def webhook(req:Request):
 local_origin(req.headers,req.url.netloc)
 supplied=req.headers.get('authorization','')
 if not secrets.compare_digest(supplied.encode(),('Bearer '+webhook_token()).encode()):raise HTTPException(401,'Ongeldige webhook-sleutel.')
 raw=await req.body()
 if len(raw)>8000:raise HTTPException(413,'Melding is te groot.')
 try:data=json.loads(raw)
 except ValueError:raise HTTPException(400,'Ongeldige JSON.')
 value=command_value(data);key=data.get('device')
 if key is None:return await relay_frames(value)
 if not isinstance(key,str):raise HTTPException(400,'Ongeldige fotolijst.')
 return await relay(key,value)
