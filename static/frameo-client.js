/* Fixed actions only, registered only while the native app bridge is available. */
(function(root){
 if(root.top!==root)return;
 let socket=null,retry=null,heartbeat=null,connecting=false,report={},lastError='';
 let device='';try{device=localStorage.getItem('frameo-device-id')||'';if(!/^[a-zA-Z0-9_-]{12,80}$/.test(device)){device='frame-'+(root.crypto?.randomUUID?.()||Math.random().toString(36).slice(2)+Date.now().toString(36));localStorage.setItem('frameo-device-id',device)}}catch{device='frame-'+Math.random().toString(36).slice(2)+Date.now().toString(36)}
 function status(){const led=root.FrameoLED?.snapshot?.()||{};return {...report,led,sound:root.FrameoSound?.snapshot?.()||{},capture:led.capture===true,screenControl:led.screenControl===true,screenOn:led.screenOn,version:led.version||'',photo:root.FrameoPhotoMode?.isPhotoMode?.()===true,visible:!document.hidden,error:lastError}}
 function send(value){if(socket?.readyState===WebSocket.OPEN)socket.send(JSON.stringify(value))}
 async function command(message){
  let result={type:'result',id:message.id,ok:true,message:'Uitgevoerd.'};
  try{
   switch(message.action){
    case 'sound_settings':root.FrameoSound.configure({enabled:message.enabled,volume:message.volume});result.message='Meldingsgeluid bewaard op de fotolijst.';break;
    case 'sound_test':result.message=await root.FrameoSound.test();break;
    case 'led_test':if(!root.FrameoLED.preview(message.color,message.brightness))throw Error('LED-koppeling niet beschikbaar.');result.message='Testopdracht ontvangen; controleer de LED-bevestiging.';break;
    case 'led_save':if(!root.FrameoLED.configure({amberColor:message.color,brightness:message.brightness}))throw Error('Instelling niet bewaard.');result.message='Instelling bewaard op de fotolijst.';break;
    case 'led_restore':root.FrameoLED.restore();break;
    case 'auto':root.FrameoLED.setAutomatic(message.enabled);break;
    case 'photo':root.FrameoPhotoMode.enter();break;
    case 'dashboard':root.FrameoPhotoMode.showDashboard();if(typeof closePanel==='function')closePanel();break;
    case 'next_photo':if(typeof photo==='function')photo();else throw Error('Fotowissel niet beschikbaar.');break;
    case 'reload':send(result);setTimeout(()=>location.reload(),300);return;
    case 'screen_on':case 'screen_off':await root.FrameoLED.screen(message.action==='screen_on');result.message=message.action==='screen_on'?'Scherm aan.':'Scherm uit.';break;
    case 'message':if(message.wake)await root.FrameoLED.screen(true);root.FrameoMessage.show(message);result.message='Volbeeldmelding getoond.';break;
    case 'message_clear':root.FrameoMessage.hide();result.message='Volbeeldmelding gesloten.';break;
    case 'capture':result.image=await root.FrameoLED.capture();break;
    default:throw Error('Onbekende opdracht.');
   }
  }catch(error){result.ok=false;result.message=String(error.message||error).slice(0,240)}
  send(result);send({type:'status',status:status()});
 }
 function connect(){
  if(connecting||socket?.readyState===WebSocket.OPEN||!root.FrameoLED?.ready?.())return;
  connecting=true;clearTimeout(retry);
  const ws=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws/frameo');socket=ws;
  ws.onopen=()=>{connecting=false;send({type:'register',device,name:'Fotolijst',status:status()});clearInterval(heartbeat);heartbeat=setInterval(()=>send({type:'status',status:status()}),10000)};
  ws.onmessage=event=>{try{const data=JSON.parse(event.data);if(data.type==='command')command(data)}catch{}};
  ws.onerror=()=>ws.close();ws.onclose=()=>{connecting=false;clearInterval(heartbeat);retry=setTimeout(connect,4000)};
 }
 root.FrameoRemote={update(value){report=value},status};
 root.addEventListener('error',event=>{lastError=String(event.message||'Paginafout').slice(0,200)});
 root.addEventListener('unhandledrejection',event=>{lastError=String(event.reason?.message||'Onbevestigde aanvraag').slice(0,200)});
 document.addEventListener('visibilitychange',()=>{send({type:'status',status:status()});if(!document.hidden)connect()});
 setInterval(connect,3000);connect();
})(globalThis);
