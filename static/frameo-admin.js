(function(){
 'use strict';
 const screenOnly=new URLSearchParams(location.search).get('embed')==='screen';if(screenOnly)document.body.classList.add('screen-only');
 let embedDevice='';
 const $=id=>document.getElementById(id);let selected='',devices=[],busy=false,capturing=false,imageURL=null,backendOnline=true,initialised='',polling=false;
 const names={dashboard:'Dashboard',tibber:'Tibber',energy:'Energie',weather:'Weer',climate:'Klimaat',calendar:'Agenda',media:'Media',camera:'Camera',news:'Nieuws',tools:'Testmeldingen',manage:'Beheer'};
 const current=()=>devices.find(d=>d.id===selected);
 function message(text,error=false){$('message').textContent=text;$('message').classList.toggle('error',error)}
 function render(){
  const d=current(),online=!!d?.online&&backendOnline,s=d?.status||{},led=s.led||{};
  $('connection').textContent=online?'Fotolijst online':backendOnline?'Fotolijst offline':'Server niet bereikbaar';$('connection').classList.toggle('online',online);
  $('seen').textContent=d?'Laatste contact '+new Date(d.last_seen).toLocaleTimeString('nl-NL',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'';
  for(const button of document.querySelectorAll('[data-control]'))button.disabled=!online||busy;
  for(const id of ['test-color','save-color','restore','auto'])if(!led.connected)$(id).disabled=true;
  for(const id of ['screen-on','screen-off'])$(id).disabled=!online||busy||s.screenControl!==true;
  const sound=s.sound||{};for(const id of ['sound-save','sound-test'])$(id).disabled=!online||busy||sound.available!==true;$('sound-status').textContent=sound.message||(online?'Werk de dashboardpagina op de fotolijst bij voor geluid.':'Kies een verbonden fotolijst.');
  $('status-screen').textContent=s.screenControl?(s.screenOn===true?'Aan':s.screenOn===false?'Uit':'Onbekend'):'APK bijwerken';
  $('capture').disabled=!online||busy||capturing||s.capture!==true;$('live').disabled=!online||s.capture!==true;
  if(!online||s.capture!==true){$('live').checked=false;if(screenOnly)embedDevice=''}
  $('status-online').textContent=online?'Online':'Offline';$('status-page').textContent=s.photo?'Fotostand':names[s.page]||s.page||'—';$('status-ha').textContent=({live:'Live',polling:'Via statuscontrole',offline:'Niet verbonden',demo:'Voorbeelddata'})[s.connection]||'—';$('status-led').textContent=led.connected?(led.confirmed?'Bevestigd':'Wacht op bevestiging'):'Geen koppeling';$('status-version').textContent=d?(s.version||'Oudere APK'):'—';
  $('auto').checked=led.auto===true;$('actual-color').style.background=/^#[0-9a-f]{6}$/i.test(led.color||'')?led.color:'#344959';$('actual-label').textContent=!d?'Geen fotolijst':led.testing?'Testkleur':led.auto?'Automatische prijskleur':'Automatisch uit';$('led-message').textContent=led.message||'Nog geen LED-status';$('page-error').hidden=!s.error;$('page-error').textContent=s.error||'';
  if(d&&initialised!==d.id){initialised=d.id;if(typeof sound.enabled==='boolean')$('sound-enabled').checked=sound.enabled;if(Number.isInteger(sound.volume))$('sound-volume').value=sound.volume;updateSoundVolume();if(/^#[0-9a-f]{6}$/i.test(led.amberColor||''))$('color').value=led.amberColor;if(Number.isInteger(led.brightness))$('brightness').value=led.brightness;updateBrightness()}
  $('help').textContent=!d?'De fotolijst verschijnt hier zodra de bijgewerkte dashboardpagina in de Light Panel draait.':!s.capture?'Bediening is beschikbaar. Werk de Light Panel-APK bij voor schermbeelden.':!s.screenControl?'Werk de Light Panel-APK bij voor scherm aan/uit.':'Live meekijken haalt iedere vijf seconden een nieuw beeld op zolang deze pagina zichtbaar is.';
 }
 function updateSoundVolume(){$('sound-volume-value').textContent=$('sound-volume').value+'%'}
 function updateBrightness(){$('brightness-value').textContent=Math.round(Number($('brightness').value)/255*100)+'%'}
 async function poll(){
  if(polling)return;polling=true;const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),8000);
  try{const response=await fetch('/api/frameo/devices',{cache:'no-store',signal:controller.signal});if(!response.ok)throw Error('Status niet beschikbaar.');const data=await response.json();devices=data.devices||[];backendOnline=true;const existing=selected;if(!devices.some(d=>d.id===selected))selected=devices.find(d=>d.online)?.id||devices[0]?.id||'';
   const select=$('devices');select.replaceChildren();for(const d of devices){const option=document.createElement('option');option.value=d.id;option.textContent=d.name+(d.online?'':' · offline');select.append(option)}if(!devices.length){const option=document.createElement('option');option.value='';option.textContent='Geen fotolijst verbonden';select.append(option)}select.value=selected;if(existing!==selected)initialised='';
  }catch(error){backendOnline=false;message('Status tijdelijk niet bereikbaar.',true)}finally{clearTimeout(timer);polling=false;render();const d=current();if(screenOnly&&d?.online&&d.status?.capture===true&&embedDevice!==d.id){embedDevice=d.id;$('live').checked=true;capture()}}
 }
 async function command(action,extra={}){
  const d=current();if(!d?.online||!backendOnline||busy)throw Error('Fotolijst is niet online.');busy=true;render();message('Opdracht versturen…');const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),22000);
  try{const response=await fetch('/api/frameo/devices/'+encodeURIComponent(d.id)+'/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...extra}),signal:controller.signal});if(!response.ok){const error=await response.json();throw Error(error.detail||'Opdracht niet bevestigd.')}if(action==='capture')return await response.blob();const result=await response.json();message(result.message||'Opdracht bevestigd.');return result}
  finally{clearTimeout(timer);busy=false;render()}
 }
 async function run(action,extra){try{await command(action,extra);await poll()}catch(error){message(error.message||'Opdracht niet bevestigd.',true)}}
 async function capture(){
  if(capturing)return;capturing=true;const id=selected;
  try{const blob=await command('capture');if(id!==selected)return;if(imageURL)URL.revokeObjectURL(imageURL);imageURL=URL.createObjectURL(blob);$('screen-image').src=imageURL;$('screen-image').hidden=false;$('screen-empty').hidden=true;$('screen-time').textContent='Beeld opgehaald om '+new Date().toLocaleTimeString('nl-NL');message('Schermbeeld ontvangen.')}
  catch(error){message(error.message||'Geen schermbeeld ontvangen.',true)}finally{capturing=false;render()}
 }
 $('devices').onchange=()=>{selected=$('devices').value;initialised='';$('screen-image').hidden=true;$('screen-empty').hidden=false;if(imageURL){URL.revokeObjectURL(imageURL);imageURL=null}render()};
 $('sound-volume').oninput=updateSoundVolume;$('sound-save').onclick=()=>run('sound_settings',{enabled:$('sound-enabled').checked,volume:Number($('sound-volume').value)});$('sound-test').onclick=async()=>{try{await command('sound_settings',{enabled:$('sound-enabled').checked,volume:Number($('sound-volume').value)});await run('sound_test')}catch(error){message(error.message,true)}};
 $('brightness').oninput=updateBrightness;$('test-color').onclick=()=>run('led_test',{color:$('color').value,brightness:Number($('brightness').value)});$('save-color').onclick=()=>run('led_save',{color:$('color').value,brightness:Number($('brightness').value)});$('restore').onclick=async()=>{try{await command('auto',{enabled:true});await run('led_restore')}catch(error){message(error.message,true)}};$('auto').onchange=()=>run('auto',{enabled:$('auto').checked});$('capture').onclick=capture;
 const messageValue=()=>({title:$('full-title').value,text:$('full-text').value,icon:$('full-icon').value,camera:$('full-camera').value,camera_crop:$('full-crop').value,badge:$('full-badge').value,color:$('full-color').value,duration:Number($('full-duration').value),wake:$('full-wake').checked});
 async function loadCameraChoices(){try{const response=await fetch('/api/frameo/message/options',{cache:'no-store'});if(!response.ok)return;const data=await response.json();for(const name of data.cameras||[]){const option=document.createElement('option');option.value=name;option.textContent=name;$('full-camera').appendChild(option)}}catch{}}
 $('full-icon').onchange=()=>{if($('full-icon').value==='doorbell'&&!$('full-camera').value&&[...$('full-camera').options].some(option=>option.value==='Voordeur'))$('full-camera').value='Voordeur'};
 loadCameraChoices();
 $('full-message-form').onsubmit=event=>{event.preventDefault();run('message',messageValue())};
 $('full-preview').onclick=()=>{FrameoGaragePip.hide();FrameoMessage.show({...messageValue(),silent:true})};
 let garagePreview=false;$('garage-preview').onclick=async()=>{if(garagePreview){FrameoMessage.hide();FrameoGaragePip.hide();garagePreview=false;$('garage-preview').textContent='Voorbeeld garage & PiP';return}try{const response=await fetch('/api/frameo/message/options',{cache:'no-store'});if(!response.ok)throw Error('Camera-instellingen niet beschikbaar.');const data=await response.json(),g=data.garage||{};FrameoGaragePip.update(true,g);FrameoMessage.showGarage(g.garage_camera,0,g);garagePreview=true;$('garage-preview').textContent='Sluit garagevoorbeeld'}catch(error){message(error.message,true)}};
 let webhookLoaded=false;
 $('webhook-details').addEventListener('toggle',async()=>{if(!$('webhook-details').open||webhookLoaded)return;try{const response=await fetch('/api/frameo/webhook/settings',{cache:'no-store'});if(!response.ok)throw Error('Webhookinstellingen niet beschikbaar.');const data=await response.json();$('webhook-url').value=data.url;$('webhook-token').value=data.token;webhookLoaded=true}catch(error){message(error.message,true)}});
 $('webhook-copy').onclick=async()=>{if(!webhookLoaded)return;try{await navigator.clipboard.writeText($('webhook-token').value);message('Webhook-sleutel gekopieerd.')}catch{$('webhook-token').type='text';$('webhook-token').select();message('Selecteer en kopieer de sleutel.')}};
 for(const button of document.querySelectorAll('[data-action]'))button.onclick=()=>run(button.dataset.action);
 $('live').onchange=()=>{if($('live').checked)capture()};setInterval(()=>{if(!document.hidden){poll();if($('live').checked&&!busy)capture()}},5000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll()});poll();
})();
