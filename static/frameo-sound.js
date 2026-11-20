/* One gentle chime per new notification, on hardware only, 08:00–20:00 Amsterdam. */
(function(root){
 'use strict';
 const storageKey='frameo-notification-sound',seenKey='frameo-sound-seen';
 function allowed(at){
  try{const hour=Number(new Date(at).toLocaleTimeString('nl-NL',{timeZone:'Europe/Amsterdam',hour:'2-digit',hour12:false}).split(':')[0]);return hour>=8&&hour<20}catch{return false}
 }
 function valid(value){return value&&typeof value.enabled==='boolean'&&Number.isInteger(value.volume)&&value.volume>=0&&value.volume<=100}
 if(typeof module!=='undefined'&&module.exports){module.exports={allowed,valid};return}
 let settings={enabled:true,volume:35},seen={},initialised=false,lastPlayed=-Infinity,message='Nog geen meldingsgeluid afgespeeld.';
 try{const saved=JSON.parse(localStorage.getItem(storageKey)||'null');if(valid(saved))settings={enabled:saved.enabled,volume:saved.volume};const remembered=JSON.parse(localStorage.getItem(seenKey)||'{}');if(remembered&&typeof remembered==='object'&&!Array.isArray(remembered))seen=remembered}catch{}
 const now=()=>root.FrameoClock?.now?.()??Date.now();
 function saveSeen(){const at=now();seen=Object.fromEntries(Object.entries(seen).filter(([,stamp])=>Number.isFinite(stamp)&&stamp>at-172800000).sort((a,b)=>b[1]-a[1]).slice(0,400));try{localStorage.setItem(seenKey,JSON.stringify(seen))}catch{}}
 function reason(){if(!root.FrameoLED?.ready?.())return 'Geluid werkt op de fysieke fotolijst.';if(!root.FrameoClock?.synced)return 'Wachten op de juiste servertijd.';if(!allowed(now()))return 'Stille uren: geluid alleen tussen 08:00 en 20:00.';if(!settings.enabled||settings.volume===0)return 'Meldingsgeluid staat uit.';return ''}
 async function notify(key){
  const at=now();if(key&&seen[key])return 'Deze melding heeft al geklonken.';
  if(key){seen[key]=at;saveSeen()}
  const blocked=reason();if(blocked){message=blocked;return blocked}
  if(at-lastPlayed<5000)return 'Gelijktijdige meldingen gebundeld.';
  lastPlayed=at;
  try{const audio=new Audio('/static/notification-chime.wav');audio.volume=settings.volume/100;const result=audio.play();if(result?.then)await result;message='Kort meldingsgeluid afgespeeld.';return message}
  catch{message='Geluid kon niet worden afgespeeld. Gebruik Test geluid op de fotolijst.';return message}
 }
 const api={
  notify,
  observe(items,visible){
   const ids=new Set((visible||items).map(item=>'feed:'+item.id));let fresh=false;
   for(const item of items){const key='feed:'+item.id;if(!seen[key]&&initialised&&ids.has(key)&&Date.parse(item.expires_at)>now())fresh=true;seen[key]=now()}
   const wasReady=initialised;initialised=true;saveSeen();if(wasReady&&fresh)notify();
  },
  configure(value){if(!valid(value))throw Error('Kies een volume van 0 tot 100 en geluid aan of uit.');localStorage.setItem(storageKey,JSON.stringify(value));settings={enabled:value.enabled,volume:value.volume};return api.snapshot()},
  test(){return notify()},
  snapshot(){return {...settings,available:!!root.FrameoLED?.ready?.(),hours:'08:00–20:00',timeZone:'Europe/Amsterdam',message:reason()||message}}
 };root.FrameoSound=api;
})(globalThis);
