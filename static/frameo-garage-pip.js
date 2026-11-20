/* Door camera remains visible until the garage closes, independent of a dismissed message. */
(function(root){
 let box=null,timer=null,camera='',settings={},observer=null;
 function hide(){observer?.disconnect();observer=null;clearTimeout(timer);timer=null;if(box)box.remove();box=null;camera=''}
 function position(){
  if(!box)return;
  const anchor=document.querySelector?.('.frameo-full-message.has-camera .frameo-camera-view')||document.querySelector?.('.photo-frame');
  const bounds=anchor?.getBoundingClientRect?.()||{left:0,top:0,right:root.innerWidth||800,bottom:root.innerHeight||1280,width:root.innerWidth||800,height:root.innerHeight||1280};
  const margin=14,width=Math.max(0,Math.min(250,Math.max(120,bounds.width*.28),bounds.width-margin*2));
  box.style.setProperty('width',width+'px');
  const height=box.getBoundingClientRect?.().height||width*9/16+32;
  box.style.setProperty('left',Math.max(bounds.left+margin,bounds.right-margin-width)+'px');
  box.style.setProperty('top',Math.max(bounds.top+margin,bounds.bottom-margin-height)+'px');
  box.style.setProperty('right','auto');box.style.setProperty('bottom','auto');
  box.hidden=bounds.width<=0||bounds.bottom<=0||bounds.top>=(root.innerHeight||1280);
 }
 function update(open,config={}){
  if(!open||!config.garage_pip_camera){hide();return}settings=config;
  if(box&&camera===config.garage_pip_camera){position();return;}hide();camera=config.garage_pip_camera;
  box=document.createElement('button');box.className='frameo-garage-pip';box.type='button';box.setAttribute('aria-label','Garagedeur open. Open camerabeeld');
  const view=document.createElement('span');view.className='frameo-garage-pip-view';const label=document.createElement('span');label.className='frameo-garage-pip-label';label.textContent='Garage · deur open';box.append(view,label);box.onclick=()=>root.FrameoMessage?.showGarage(settings.garage_camera,0,settings);document.body.appendChild(box);position();const photo=document.querySelector?.('.photo-frame');if(root.ResizeObserver&&photo){observer=new root.ResizeObserver(position);observer.observe(photo)}
  const owner=box,source=camera;
  function refresh(){if(box!==owner)return;position();if(document.hidden){timer=setTimeout(refresh,2500);return}const start=root.performance?.now?.()??Date.now(),img=document.createElement('img');img.alt='Garagedeur';
   img.onload=()=>{if(box!==owner)return;view.replaceChildren(img);label.textContent='Garage · deur open';position();timer=setTimeout(refresh,Math.max(0,2500-((root.performance?.now?.()??Date.now())-start)))};
   img.onerror=()=>{if(box!==owner)return;label.textContent=view.children.length?'Garage · laatste beeld':'Garage · camera niet bereikbaar';position();timer=setTimeout(refresh,2500)};
   img.src='/api/camera/'+encodeURIComponent(source)+'?refresh='+Math.floor(root.FrameoClock?.now()??Date.now());
  }refresh();
 }
 root.addEventListener?.('resize',position);root.addEventListener?.('scroll',position,{passive:true});
 root.FrameoGaragePip={update,hide,position};
})(globalThis);
