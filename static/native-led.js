/* Fixed LED requests over an origin-scoped channel supplied by the Android APK. */
(function(root){
 const colors={green:[0,255,0],blue:[0,0,255],amber:[255,120,0]},defaultHex='#ff7800',storageKey='homehub-native-led-calibration';
 const hub=root.HomeHub||(typeof module!=='undefined'?require('./homehub.js'):null);
 const validBrightness=value=>typeof value==='number'&&Number.isInteger(value)&&value>=0&&value<=255;
 function rgb(hex){return typeof hex==='string'&&/^#[0-9a-f]{6}$/i.test(hex)?[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)):null}
 function calibration(value){const color=rgb(value?.amberColor)?value.amberColor:rgb(value?.pbdColor)?value.pbdColor:defaultHex;return {amberColor:color.toLowerCase(),brightness:validBrightness(value?.brightness)?value.brightness:160}}

 function priceCommand(states,c={},prefs={}){
  const signal=hub?.priceSignal(states,c);
  if(!signal||signal.key==='unknown')return {mode:'off'};
  const selected=calibration(prefs),channels=['very_cheap','cheap'].includes(signal.key)?colors.green:['expensive','very_expensive'].includes(signal.key)?[255,0,0]:rgb(selected.amberColor);
  return {mode:'color',brightness:selected.brightness,red:channels[0],green:channels[1],blue:channels[2]};
 }
 function desired(states,c={},live=true,prefs={}){
  if(!live)return null;
  const settings=c.notifications||{},garage=settings.garage_entity?states[settings.garage_entity]?.state:'off';
  if(['on','open','opening','closing'].includes(garage))return {mode:'breathe',brightness:160};
  if(!['off','closed'].includes(garage))return null;
  return priceCommand(states,c,prefs);
 }
 if(typeof module!=='undefined'){module.exports={desired,rgb,calibration,priceCommand};return}
 if(root.top!==root)return;
 let port=null,latest=null,last='',sequence=0,testTimer=null,adjustTimer=null,testing=false,customTesting=false,beforeTest=null,enabled=true,message='Open dit menu op de fotolijst om de LED’s te testen.',failed=false,context=null,prefs=calibration({});
 try{enabled=localStorage.getItem('homehub-native-led-auto')!=='off';prefs=calibration(JSON.parse(localStorage.getItem(storageKey)||'{}'))}catch{}
 let screenControlAvailable=false,screenOn=null;const screenRequests=new Map();
 let draft={...prefs},captureAvailable=false,appVersion='',lastSent=null,lastApplied=null,lastSetId=0;const sentCommands=new Map(),captures=new Map();
 function syncPicker(){
  const channels=rgb(draft.amberColor),picker=document.getElementById('native-led-picker');if(picker&&picker.value!==draft.amberColor)picker.value=draft.amberColor;
  const swatch=document.getElementById('native-led-swatch');if(swatch)swatch.style.background=draft.amberColor;
  const code=document.getElementById('native-led-hex');if(code)code.textContent=draft.amberColor.toUpperCase();
  for(const [i,key] of ['red','green','blue'].entries()){const input=document.getElementById('native-led-'+key),output=document.getElementById('native-led-'+key+'-value');if(input&&Number(input.value)!==channels[i])input.value=channels[i];if(output)output.textContent=channels[i]}
  const light=document.getElementById('native-led-brightness'),output=document.getElementById('native-led-brightness-value');if(light&&Number(light.value)!==draft.brightness)light.value=draft.brightness;if(output)output.textContent=Math.round(draft.brightness/255*100)+'%';
 }
 function screenGlow(){
  if(!document.body||!document.createElement)return;
  let edge=document.getElementById('screen-led-glow');
  if(!edge){edge=document.createElement('div');edge.id='screen-led-glow';edge.setAttribute('aria-hidden','true');document.body.appendChild(edge)}
  const command=port?(lastApplied?.command||lastSent):(enabled?latest:null);
  const on=screenOn!==false&&command&&command.mode!=='off'&&(command.brightness??160)>0;
  const channels=command?.mode==='breathe'?[255,0,0]:[command?.red||0,command?.green||0,command?.blue||0];
  edge.style.setProperty('--edge-led',channels.join(','));
  edge.style.setProperty('--edge-strength',on?String(.18+.22*(command.brightness??160)/255):'0');
  edge.classList.toggle('is-breathing',!!on&&command.mode==='breathe');
 }
 function refresh(){
  screenGlow();
  const status=document.getElementById('native-led-status');if(status){status.textContent=message;status.classList.toggle('detail-error',failed)}
  document.querySelectorAll('[data-native-led-test]').forEach(button=>button.disabled=!port);
  const button=document.getElementById('native-led-auto');if(button){button.textContent='Automatisch: '+(enabled?'aan':'uit');button.setAttribute('aria-pressed',String(enabled));}
 }
 function send(command){
  if(!port||!command)return false;
  try{const id=++sequence;lastSetId=id;lastSent={...command};sentCommands.set(id,lastSent);if(sentCommands.size>40)sentCommands.delete(sentCommands.keys().next().value);port.postMessage(JSON.stringify({type:'set',id,...command}));message='LED-opdracht versturen…';failed=false;refresh();return true}
  catch{message='LED-koppeling verbroken. Herlaad het dashboard in de app.';failed=true;port=null;refresh();return false}
 }
 function apply(){if(port&&enabled&&!testing&&latest){const key=JSON.stringify(latest);if(last!==key){last=key;send(latest)}}}
 function restore(){clearTimeout(testTimer);clearTimeout(adjustTimer);testing=false;customTesting=false;const target=enabled?(latest||beforeTest||{mode:'off'}):{mode:'off'};last=JSON.stringify(target);send(target);beforeTest=null}
 function testCommand(command,duration,custom=false){
  if(!port||!command)return false;
  if(!testing)beforeTest=last?JSON.parse(last):null;
  clearTimeout(testTimer);clearTimeout(adjustTimer);testing=true;customTesting=custom;
  send(command);testTimer=setTimeout(restore,duration);return true;
 }
 function custom(){const channels=rgb(draft.amberColor);return testCommand({mode:'color',brightness:draft.brightness,red:channels[0],green:channels[1],blue:channels[2]},30000,true)}
 const api={
  ready(){return !!port},
  snapshot(){const applied=screenOn===false?{mode:'off',brightness:0}:lastApplied?.command||lastSent,color=applied?.mode==='color'?'#'+[applied.red,applied.green,applied.blue].map(v=>v.toString(16).padStart(2,'0')).join(''):applied?.mode==='breathe'?'#ff0000':'#000000';return {connected:!!port,auto:enabled,testing,confirmed:lastApplied?.id===lastSetId&&lastSetId>0,color,brightness:applied?.brightness??0,amberColor:prefs.amberColor,message,capture:captureAvailable&&!!port,screenControl:screenControlAvailable&&!!port,screenOn,version:appVersion}},
  preview(color,brightness){if(!rgb(color)||!validBrightness(brightness)||!port)return false;draft={...draft,amberColor:color.toLowerCase(),brightness};syncPicker();return custom()},
  configure(value){if(!port)return false;draft=calibration(value);syncPicker();return api.save()},
  setAutomatic(value){if(typeof value==='boolean'&&value!==enabled)api.toggle()},
  screen(on){return new Promise((resolve,reject)=>{if(!port||!screenControlAvailable||typeof on!=='boolean'){reject(Error('Werk de APK bij voor schermbediening.'));return}const id=++sequence,timer=setTimeout(()=>{screenRequests.delete(id);reject(Error('Geen schermbevestiging ontvangen.'))},10000);screenRequests.set(id,{resolve,reject,timer});try{port.postMessage(JSON.stringify({type:'screen',id,on}))}catch(error){clearTimeout(timer);screenRequests.delete(id);reject(error)}})},
  capture(){return new Promise((resolve,reject)=>{if(!port||!captureAvailable){reject(Error('Werk de APK bij voor schermbeelden.'));return}const id=++sequence,timer=setTimeout(()=>{captures.delete(id);reject(Error('Geen schermbeeld ontvangen.'))},12000);captures.set(id,{resolve,reject,timer});try{port.postMessage(JSON.stringify({type:'capture',id}))}catch(error){clearTimeout(timer);captures.delete(id);reject(error)}})},
  update(model,states,c){context={model,states,c};latest=desired(states,c,model.live,prefs);if(testing&&latest?.mode==='breathe'){restore();return}apply()},
  test(kind){const command=kind==='breathe'?{mode:'breathe',brightness:160}:kind==='off'?{mode:'off'}:colors[kind]?{mode:'color',brightness:160,red:colors[kind][0],green:colors[kind][1],blue:colors[kind][2]}:null;return testCommand(command,10000)},
  custom,
  pick(key,value){
   if(key==='color'){if(!rgb(value))return;draft.amberColor=value.toLowerCase()}
   else{const n=Number(value);if(!validBrightness(n))return;if(key==='brightness')draft.brightness=n;else{const i=['red','green','blue'].indexOf(key);if(i<0)return;const channels=rgb(draft.amberColor);channels[i]=n;draft.amberColor='#'+channels.map(v=>v.toString(16).padStart(2,'0')).join('')}}
   syncPicker();if(testing&&customTesting){clearTimeout(adjustTimer);adjustTimer=setTimeout(custom,100)}
  },
  save(){
   if(!port)return false;
   const selected=calibration(draft);
   try{localStorage.setItem(storageKey,JSON.stringify(selected))}catch{message='Kleur kon niet worden bewaard. Je kunt wel blijven testen.';failed=true;refresh();return false}
   prefs=selected;if(context)latest=desired(context.states,context.c,context.model.live,prefs);restore();message='Energiekleur bewaard op deze fotolijst.';failed=false;refresh();return true;
  },
  resetDraft(){draft=calibration({});syncPicker();if(testing&&customTesting)custom()},restore,
  toggle(){enabled=!enabled;try{localStorage.setItem('homehub-native-led-auto',enabled?'on':'off')}catch{}clearTimeout(testTimer);clearTimeout(adjustTimer);testing=false;customTesting=false;last='';if(enabled)apply();else send({mode:'off'});refresh()},
  markup(){
   const channels=rgb(draft.amberColor);
   return `<details class="panel"><summary>LED op de fotolijst</summary><p id="native-led-status" class="control-feedback" role="status">${message}</p><div class="test-actions"><button id="native-led-auto" onclick="FrameoLED.toggle()" aria-pressed="${enabled}">Automatisch: ${enabled?'aan':'uit'}</button></div><fieldset class="led-calibration"><legend>Energie-LED afstellen</legend><p class="muted">Groen: goedkoop · oranje: middel · rood: duur. Stel hieronder de middenkleur en helderheid af.</p><div class="led-color-row"><input type="color" id="native-led-picker" value="${draft.amberColor}" aria-label="LED-kleur kiezen" oninput="FrameoLED.pick('color',this.value)"><span class="led-color-swatch" id="native-led-swatch" style="background:${draft.amberColor}" aria-hidden="true"></span><output id="native-led-hex">${draft.amberColor.toUpperCase()}</output></div>${[['red','Rood'],['green','Groen'],['blue','Blauw']].map(([key,label],i)=>`<label class="led-channel" for="native-led-${key}"><span>${label}</span><input type="range" id="native-led-${key}" min="0" max="255" step="1" value="${channels[i]}" oninput="FrameoLED.pick('${key}',this.value)"><output id="native-led-${key}-value" for="native-led-${key}">${channels[i]}</output></label>`).join('')}<label class="led-channel" for="native-led-brightness"><span>Helderheid</span><input type="range" id="native-led-brightness" min="0" max="255" step="1" value="${draft.brightness}" oninput="FrameoLED.pick('brightness',this.value)"><output id="native-led-brightness-value" for="native-led-brightness">${Math.round(draft.brightness/255*100)}%</output></label><div class="test-actions led-picker-actions"><button class="big" data-native-led-test onclick="FrameoLED.custom()" ${port?'':'disabled'}>Test kleur · 30 sec</button><button class="big" data-native-led-test onclick="FrameoLED.save()" ${port?'':'disabled'}>Bewaar energiekleur</button><button onclick="FrameoLED.resetDraft()">Standaard oranje</button></div><p class="muted">Na ‘Test kleur’ reageren de LED’s op de schuiven. De test stopt 30 seconden na je laatste wijziging. Bewaren geldt voor deze fotolijst.</p></fieldset><div class="test-buttons">${[['breathe','Rood ademen'],['green','Groen'],['blue','Blauw'],['amber','Oranje'],['off','Uit']].map(([kind,label])=>`<button class="big" data-native-led-test onclick="FrameoLED.test('${kind}')" ${port?'':'disabled'}>${label}</button>`).join('')}</div><button class="detail-refresh" data-native-led-test onclick="FrameoLED.restore()" ${port?'':'disabled'}>Terug naar actuele melding</button><p class="muted">Automatisch: stroomprijs. Een open garage gaat voor met rood ademen. Afvalmeldingen staan alleen op het scherm. Zonder stroomprijs gaan de LED’s uit.</p></details>`;
  },refresh
 };
 root.FrameoLED=api;
 root.addEventListener('message',event=>{
  if(event.data!=='frameo-led-port:v1'||!event.ports?.length)return;
  if(port)port.close();for(const pending of screenRequests.values()){clearTimeout(pending.timer);pending.reject(Error('Schermkoppeling opnieuw verbonden.'))}screenRequests.clear();screenControlAvailable=false;screenOn=null;for(const pending of captures.values()){clearTimeout(pending.timer);pending.reject(Error('LED-koppeling opnieuw verbonden.'))}captures.clear();sentCommands.clear();captureAvailable=false;lastApplied=null;port=event.ports[0];last='';failed=false;message='Lokale LED-koppeling beschikbaar.';
  port.onmessage=event=>{
   try{const reply=JSON.parse(event.data);
    if(reply.type==='ready'){captureAvailable=reply.capture===true;screenControlAvailable=reply.screenControl===true;screenOn=typeof reply.screenOn==='boolean'?reply.screenOn:null;appVersion=String(reply.appVersion||'');refresh()}
    if(reply.type==='screen'){if(typeof reply.on==='boolean')screenOn=reply.on;const pending=screenRequests.get(reply.id);if(pending){clearTimeout(pending.timer);screenRequests.delete(reply.id);if(reply.ok===true)pending.resolve(reply.on);else pending.reject(Error(reply.message||'Schermbediening mislukt.'))}return}
    if(reply.type==='capture'){const pending=captures.get(reply.id);if(pending){clearTimeout(pending.timer);captures.delete(reply.id);if(reply.ok===true&&typeof reply.image==='string')pending.resolve(reply.image);else pending.reject(Error(reply.message||'Schermbeeld mislukt.'))}return}
    if(reply.type==='result'){const command=sentCommands.get(reply.id);if(command){if(reply.ok)lastApplied={id:reply.id,command};sentCommands.delete(reply.id)}failed=!reply.ok;message=reply.message||'Geen LED-status ontvangen.';refresh()}
   }catch{}

  };
  port.start();refresh();apply();
 });
 setInterval(()=>{if(context){latest=desired(context.states,context.c,context.model.live,prefs);apply()}refresh()},1000);
})(globalThis);
