/* Full-screen remote messages: plain text only; previous page remains underneath. */
(function(root){
 const icons={"bell": "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4", "info": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20M12 11v6M12 7v.1", "warning": "M12 3 2 21h20L12 3ZM12 9v5M12 17v.1", "check": "M22 11v1a10 10 0 1 1-6-9M9 11l3 3L22 4", "door": "M4 22h16M6 22V3h12v19M14 12h.1", "doorbell": "M8 2h8v20H8ZM12 6v.1M12 17a2 2 0 1 0 0-4 2 2 0 0 0 0 4M3 8a7 7 0 0 0 0 8M21 8a7 7 0 0 1 0 8", "package": "M3 7 12 2l9 5v10l-9 5-9-5V7ZM3 7l9 5 9-5M12 12v10M7.5 4.5l9 5V14", "washing-machine": "M4 2h16v20H4ZM4 6h16M7 4h.1M10 4h.1M12 19a5 5 0 1 0 0-10 5 5 0 0 0 0 10M7 14c2-3 4 3 6 0s3-1 4 0", "dryer": "M4 2h16v20H4ZM4 6h16M7 4h.1M10 4h.1M12 19a5 5 0 1 0 0-10 5 5 0 0 0 0 10M10 12l4 4M14 12l-4 4", "dishwasher": "M3 2h18v20H3ZM3 6h18M7 4h.1M16 4h2M7 17a5 5 0 0 0 10 0M7 17h10M8 10v3M12 10v3M16 10v3", "trash": "M3 6h18M9 6V3h6v3M5 6l1 16h12l1-16M10 10v8M14 10v8", "battery": "M2 6h18v12H2ZM23 10v4M6 10v4M10 10v4M14 10v4", "charging": "M2 6h5M17 6h3v12h-5M7 18H2V6M23 10v4M13 2l-6 11h5l-1 9 6-12h-5l1-8Z", "car": "M3 12l2-7h14l2 7v7H3v-7ZM3 12h18M6 19v3M18 19v3M7 16h.1M17 16h.1", "thermometer": "M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0ZM12 8v10"};
 icons.garage='M2 10 12 2l10 8M4 9v13h16V9M7 22V11h10v11';
 icons.lock='M5 11h14v11H5ZM7 11V7a5 5 0 0 1 10 0v4';icons.unlock=icons.lock;
 let fitCamera=null;
 let alarmState=null;
 let layer=null,timer=null,cameraTimer=null,source=null,garageWasOpen=false;
 function hide(){fitCamera=null;clearTimeout(timer);clearTimeout(cameraTimer);if(layer){layer.remove();layer=null}source=null;root.FrameoGaragePip?.position()}
 function show(value){
  hide();const previous=document.activeElement;
  layer=document.createElement('button');layer.type='button';layer.className='frameo-full-message'+(['washing-machine','dishwasher'].includes(value.icon)?' is-appliance':'')+(['lock','unlock'].includes(value.icon)?' is-alarm':'');layer.setAttribute('aria-label',[value.title,value.text,'Tik om te sluiten'].filter(Boolean).join('. '));layer.style.setProperty('--message-color',value.color);
  const mark=document.createElement('span');mark.className='frameo-message-mark';mark.setAttribute('aria-hidden','true');
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  for(const [key,v] of Object.entries({viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'1.6','stroke-linecap':'round','stroke-linejoin':'round',focusable:'false'}))svg.setAttribute(key,v);
  if(['fan','fan-off','airco','airco-off'].includes(value.icon)){
   layer.className+=' is-climate-message';
   const body=document.createElementNS('http://www.w3.org/2000/svg','path');
   if(value.icon.startsWith('fan')){body.setAttribute('class','frameo-fan-blades'+(value.icon==='fan-off'?' is-stopping':''));body.setAttribute('d','M12 10C6 1 2 8 10 12m4 0c10-5 2-11-2-2m0 4c-2 10 8 7 2-2m-4 0C0 14 7 22 12 14');const hub=document.createElementNS('http://www.w3.org/2000/svg','circle');hub.setAttribute('cx','12');hub.setAttribute('cy','12');hub.setAttribute('r','2');svg.append(body,hub)}
   else{body.setAttribute('d','M3 4h18v8H3ZM3 9h18M7 12v3m5-3v3m5-3v3');svg.append(body);if(value.icon==='airco'){const wind=document.createElementNS('http://www.w3.org/2000/svg','path');wind.setAttribute('class','frameo-airco-wind');wind.setAttribute('d','M5 17c-2 3 2 3 0 5m7-5c-2 3 2 3 0 5m7-5c-2 3 2 3 0 5');svg.append(wind)}}
  }else if(value.icon==='lock'||value.icon==='unlock'){
   svg.setAttribute('class','frameo-lock-icon '+(value.icon==='lock'?'is-locked':'is-unlocked'));
   const body=document.createElementNS('http://www.w3.org/2000/svg','path');body.setAttribute('d','M5 11h14v11H5ZM12 15v3');
   const shackle=document.createElementNS('http://www.w3.org/2000/svg','path');shackle.setAttribute('class','frameo-lock-shackle');shackle.setAttribute('d','M7 11V7a5 5 0 0 1 10 0v4');svg.append(body,shackle);
  }else if(value.icon==='doorbell'||value.icon==='bell'){
   const bell=document.createElementNS('http://www.w3.org/2000/svg','path');bell.setAttribute('class','frameo-bell-swing');bell.setAttribute('d','M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4');
   const waves=document.createElementNS('http://www.w3.org/2000/svg','path');waves.setAttribute('class','frameo-bell-waves');waves.setAttribute('d','M2 5a8 8 0 0 0 0 7M22 5a8 8 0 0 1 0 7');waves.setAttribute('stroke-width','1.2');svg.append(bell,waves);
  }else if(value.icon==='garage'){
   const frame=document.createElementNS('http://www.w3.org/2000/svg','path');frame.setAttribute('d','M2 10 12 2l10 8M4 9v13h16V9M7 22V11h10v11');svg.append(frame);
   const defs=document.createElementNS('http://www.w3.org/2000/svg','defs'),clip=document.createElementNS('http://www.w3.org/2000/svg','clipPath'),area=document.createElementNS('http://www.w3.org/2000/svg','rect');clip.setAttribute('id','frameo-message-garage-clip');
   for(const [key,v] of Object.entries({x:'6.5',y:'10.5',width:'11',height:'11.5'}))area.setAttribute(key,v);clip.append(area);defs.append(clip);svg.append(defs);
   const opening=document.createElementNS('http://www.w3.org/2000/svg','rect');for(const [key,v] of Object.entries({x:'7',y:'11',width:'10',height:'11',fill:'currentColor',stroke:'none',opacity:'.08'}))opening.setAttribute(key,v);svg.append(opening);
   const inside=document.createElementNS('http://www.w3.org/2000/svg','g');inside.setAttribute('clip-path','url(#frameo-message-garage-clip)');
   const shutter=document.createElementNS('http://www.w3.org/2000/svg','path');shutter.setAttribute('class','frameo-garage-shutter');shutter.setAttribute('d','M7 11h10v11H7ZM7 14h10M7 17h10M7 20h10');inside.append(shutter);svg.append(inside);
  }else if(value.icon==='washing-machine'){
   const body=document.createElementNS('http://www.w3.org/2000/svg','path');body.setAttribute('d','M4 2h16v20H4ZM4 6h16M7 4h.1M10 4h.1M12 19a5 5 0 1 0 0-10 5 5 0 0 0 0 10');
   const drum=document.createElementNS('http://www.w3.org/2000/svg','path');drum.setAttribute('class','frameo-washer-drum');drum.setAttribute('d','M7 14c2-3 4 3 6 0s3-1 4 0');svg.append(body,drum);
  }else if(value.icon==='dishwasher'){
   const body=document.createElementNS('http://www.w3.org/2000/svg','path');body.setAttribute('d',icons.dishwasher);svg.append(body);
   const defs=document.createElementNS('http://www.w3.org/2000/svg','defs'),clip=document.createElementNS('http://www.w3.org/2000/svg','clipPath'),area=document.createElementNS('http://www.w3.org/2000/svg','rect');clip.setAttribute('id','frameo-message-dishwasher-clip');
   for(const [key,v] of Object.entries({x:'4',y:'7',width:'16',height:'14',rx:'1'}))area.setAttribute(key,v);clip.append(area);defs.append(clip);svg.append(defs);
   const shineGroup=document.createElementNS('http://www.w3.org/2000/svg','g');shineGroup.setAttribute('clip-path','url(#frameo-message-dishwasher-clip)');
   const shine=document.createElementNS('http://www.w3.org/2000/svg','path');shine.setAttribute('class','frameo-dishwasher-shine');shine.setAttribute('d','M-8 23 10 5');shine.setAttribute('stroke','#fff');shine.setAttribute('stroke-width','2.8');shineGroup.append(shine);svg.append(shineGroup);
   for(const [className,d] of [['frameo-dishwasher-sparkle','M17 6.7l.65 1.65L19.3 9l-1.65.65L17 11.3l-.65-1.65L14.7 9l1.65-.65Z'],['frameo-dishwasher-sparkle is-small','M7 14.5l.45 1.05L8.5 16l-1.05.45L7 17.5l-.45-1.05L5.5 16l1.05-.45Z']]){
    const sparkle=document.createElementNS('http://www.w3.org/2000/svg','path');sparkle.setAttribute('class',className);sparkle.setAttribute('d',d);sparkle.setAttribute('fill','currentColor');sparkle.setAttribute('stroke-width','.6');svg.append(sparkle);
   }
  }else{const path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',Object.prototype.hasOwnProperty.call(icons,value.icon)?icons[value.icon]:icons.bell);svg.append(path)}mark.append(svg);if(value.badge){const badge=document.createElement('span');badge.className='frameo-message-badge';badge.textContent=String(value.badge);mark.append(badge)}
  const title=document.createElement('strong');title.textContent=value.title;
  const text=document.createElement('span');text.className='frameo-message-text';text.textContent=value.text;
  const hint=document.createElement('small');hint.textContent='Tik om te sluiten';
  if(value.camera){
   layer.className+=' has-camera';
   const frame=document.createElement('span');frame.className='frameo-camera-view';
   const heading=document.createElement('span');heading.className='frameo-camera-heading';heading.append(mark,title,text);
   const status=document.createElement('small');status.className='frameo-camera-status';status.textContent='Camerabeeld ophalen…';
   layer.append(frame,heading,status,hint);
   const owner=layer,camera=String(value.camera);const cropLeft=value.camera_crop==='left';
   function snapshot(){
    if(layer!==owner)return;
    const started=root.performance?.now?.()??Date.now();
    const image=document.createElement('img');image.alt='Camera '+camera;
    image.onload=()=>{if(layer!==owner)return;if(cropLeft){const crop=document.createElement('span');crop.className='frameo-camera-left';crop.append(image);frame.replaceChildren(crop);fitCamera=()=>{if(layer!==owner)return;const ratio=(image.naturalWidth||1280)/2/(image.naturalHeight||720),width=Math.min(frame.clientWidth||root.innerWidth||800,(frame.clientHeight||root.innerHeight||1280)*ratio);crop.style.setProperty('width',width+'px');crop.style.setProperty('height',width/ratio+'px')};fitCamera()}else frame.replaceChildren(image);const now=root.FrameoClock?.now()??Date.now();status.textContent='Snapshot · '+new Date(now).toLocaleTimeString('nl-NL',{hour:'2-digit',minute:'2-digit',second:'2-digit'});cameraTimer=setTimeout(snapshot,Math.max(0,2500-((root.performance?.now?.()??Date.now())-started)))};
    image.onerror=()=>{if(layer!==owner)return;status.textContent=frame.children.length?'Laatste camerabeeld · verversen lukt tijdelijk niet':'Camerabeeld tijdelijk niet beschikbaar';cameraTimer=setTimeout(snapshot,2500)};
    image.src='/api/camera/'+encodeURIComponent(camera)+'?refresh='+Math.floor(root.FrameoClock?.now()??Date.now());
   }
   snapshot();
  }else layer.append(mark,title,text,hint);
  layer.onclick=()=>{hide();if(previous?.isConnected)previous.focus()};document.body.appendChild(layer);root.FrameoGaragePip?.position();layer.focus({preventScroll:true});
  if(!value.silent)root.FrameoSound?.notify(value.id?'message:'+value.id:undefined);
  if(value.duration>0)timer=setTimeout(hide,value.duration*1000);
 }
 function showGarage(camera,duration=0,config=garageSettings){
  if(!camera)return;
  show({icon:'garage',title:'Garagedeur open',text:'Controleer de garagedeur.',color:'#ee655c',duration,camera,camera_crop:config.garage_camera_crop||'left'});source='garage';
  root.FrameoLED?.screen?.(true)?.catch(()=>{});
 }
 let garageSettings={};
 function updateGarage(model,settings={}){
  garageSettings=settings;
  if(!model.live||!model.garageKnown)return;
  const open=model.items.some(item=>item.kind==='garage');
  root.FrameoGaragePip?.update(open,settings);
  if(!open){garageWasOpen=false;if(source==='garage')hide();return}
  if(garageWasOpen)return;
  garageWasOpen=true;
  if(settings.garage_camera)showGarage(settings.garage_camera,Number.isInteger(settings.garage_message_duration)?settings.garage_message_duration:30,settings);
 }
 function updateAlarm(states,settings={},live=false){
  const row=states[settings.alarm_entity],state=row?.state;
  if(!live||!state||['unknown','unavailable'].includes(state)){alarmState=null;return}
  const previous=alarmState;alarmState=state;
  if(previous===null||previous===state)return;
  const modes={armed_home:'Thuisbeveiliging actief.',armed_away:'Afwezigheidsbeveiliging actief.',armed_night:'Nachtbeveiliging actief.',armed_vacation:'Vakantiebeveiliging actief.',armed_custom_bypass:'Beveiliging actief.'};
  let notice;
  if(Object.prototype.hasOwnProperty.call(modes,state))notice={icon:'lock',title:'Alarm ingeschakeld',text:modes[state],color:'#33bba0'};
  else if(state==='off'||state==='disarmed')notice={icon:'unlock',title:'Alarm uitgeschakeld',text:'De beveiliging is uitgeschakeld.',color:'#6cb3e8'};
  else if(state==='arming')notice={icon:'lock',title:'Alarm wordt ingeschakeld',text:'Bezig met inschakelen…',color:'#e5a64c'};
  else if(state==='disarming')notice={icon:'unlock',title:'Alarm wordt uitgeschakeld',text:'Bezig met uitschakelen…',color:'#e5a64c'};
  if(!notice)return;
  show({...notice,id:'alarm:'+state+':'+(row.last_changed||root.FrameoClock?.now()||Date.now()),duration:10});source='alarm';
  root.FrameoLED?.screen?.(true)?.catch(()=>{});
 }
 root.addEventListener('resize',()=>fitCamera?.());
 root.FrameoMessage={show,hide,showGarage,updateGarage,updateAlarm};root.addEventListener('keydown',event=>{if(event.key==='Escape'&&layer){event.preventDefault();hide()}});
})(globalThis);
