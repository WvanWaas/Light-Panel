/* Server time plus monotonic elapsed time: independent of the tablet wall clock. */
(function(root){
 'use strict';
 const monotonic=()=>root.performance?.now?root.performance.now():Date.now();
 let anchor=null,at=0,inFlight=null;
 const now=()=>anchor===null?Date.now():anchor+Math.max(0,monotonic()-at);
 async function synchronize(){
  if(inFlight)return inFlight;
  inFlight=(async()=>{
   const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),5000),sent=monotonic();
   try{
    const response=await fetch('/api/time',{cache:'no-store',signal:controller.signal});if(!response.ok)return false;
    const data=await response.json(),received=monotonic();
    if(!Number.isFinite(data.server_time_ms)||data.server_time_ms<=0)return false;
    anchor=data.server_time_ms+Math.max(0,received-sent)/2;at=received;return true;
   }catch{return false}finally{clearTimeout(timer)}
  })();
  try{return await inFlight}finally{inFlight=null}
 }
 const api={now,synchronize,get synced(){return anchor!==null}};root.FrameoClock=api;api.ready=synchronize();
 setInterval(()=>{if(!root.document?.hidden)synchronize()},60000);
 root.document?.addEventListener('visibilitychange',()=>{if(!root.document.hidden)synchronize()});
 root.addEventListener?.('pageshow',()=>synchronize());
})(globalThis);
