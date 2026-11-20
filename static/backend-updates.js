/* A new backend lifetime reloads the page; network outages do not. */
(function(root){
 'use strict';
 let instance=document.querySelector('meta[name="backend-instance"]')?.content||null;
 let reloading=false,busy=false;
 function observe(next){
  if(reloading||typeof next!=='string'||!next)return false;
  if(instance===null){instance=next;return false}
  if(next===instance)return false;
  reloading=true;
  root.location.reload();
  return true;
 }
 async function check(){
  if(busy||reloading)return false;
  busy=true;
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),8000);
  try{
   const response=await fetch('/api/backend-version',{cache:'no-store',signal:controller.signal});
   if(!response.ok)return false;
   const message=await response.json();
   return observe(message.backend_instance);
  }catch(error){return false}
  finally{clearTimeout(timer);busy=false}
 }
 root.FrameoUpdates={observe,check};
 setInterval(check,30000);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)return check()});
 root.addEventListener('pageshow',check);
 check();
})(globalThis);
