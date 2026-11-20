(function(root){
 const channels=new Map();let enabled=false;
 function setPhotoMode(value){enabled=!!value;const photoButton=document.getElementById('photo-wake');photoButton?.setAttribute?.('aria-label',enabled?'Dashboard openen':'Foto op volledig scherm');document.body.classList.toggle('photo-mode',enabled);try{localStorage.setItem('homehub-photo-view',enabled?'photo':'dashboard')}catch{}if(typeof syncPhotoEdge==='function')syncPhotoEdge()}
 function showDashboard(){if(enabled)setPhotoMode(false)}
 function enter(){if(typeof active!=='undefined'&&active&&typeof closePanel==='function')closePanel();setPhotoMode(true)}
 function notify(channel,keys){const previous=channels.get(channel)||new Set(),current=new Set(keys.map(String));channels.set(channel,current);if([...current].some(key=>!previous.has(key)))showDashboard()}
 root.FrameoPhotoMode={enter,showDashboard,notify,isPhotoMode:()=>enabled};
 document.getElementById('enter-photo-mode')?.addEventListener('click',enter);
 document.getElementById('photo-wake')?.addEventListener('click',()=>enabled?showDashboard():enter());
 document.getElementById('photo-show-dashboard')?.addEventListener('click',showDashboard);
 document.getElementById('photo-next-full')?.addEventListener('click',()=>{if(typeof photo==='function')photo()});
 document.addEventListener('keydown',event=>{if(enabled&&event.key==='Escape')showDashboard()});
 let saved=null;try{saved=localStorage.getItem('homehub-photo-view')}catch{}
 setPhotoMode(saved!=='dashboard');
})(window);
