/* Date-only navigation avoids UTC/date parsing shifts and browser timezone assumptions. */
(function(root){
 const valid=key=>/^\d{4}-\d{2}-\d{2}$/.test(key)&&!Number.isNaN(new Date(key+'T12:00:00Z').getTime())&&new Date(key+'T12:00:00Z').toISOString().slice(0,10)===key;
 const fromDate=date=>date.toISOString().slice(0,10);
 const add=(key,days)=>{const d=new Date(key+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+days);return fromDate(d)};
 function today(zone='Europe/Amsterdam',now=new Date(globalThis.FrameoClock?.now()??Date.now())){const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));return `${p.year}-${p.month}-${p.day}`}
 function range(key,view){
  if(view==='day')return {start:key,end:add(key,1)};
  const d=new Date(key+'T12:00:00Z');
  if(view==='week'){const start=add(key,-((d.getUTCDay()+6)%7));return {start,end:add(start,7)}}
  const first=key.slice(0,7)+'-01',firstDate=new Date(first+'T12:00:00Z');
  const start=add(first,-((firstDate.getUTCDay()+6)%7));return {start,end:add(start,42)};
 }
 function navigate(key,view,direction){
  if(view!=='month')return add(key,direction*(view==='week'?7:1));
  const d=new Date(key+'T12:00:00Z'),day=d.getUTCDate();d.setUTCDate(1);d.setUTCMonth(d.getUTCMonth()+direction);
  const last=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,0)).getUTCDate();d.setUTCDate(Math.min(day,last));return fromDate(d);
 }
 function onDay(event,key,zone){
  if(event.all_day)return event.start<=key&&key<event.end;
  const a=new Date(event.start),b=new Date(event.end);
  if(Number.isNaN(a.getTime())||Number.isNaN(b.getTime()))return false;
  // End is exclusive: an event ending exactly at midnight is not on the next day.
  return today(zone,a)<=key&&today(zone,new Date(Math.max(a.getTime(),b.getTime()-1)))>=key;
 }
 function eventsOn(events,key,zone){return events.filter(e=>onDay(e,key,zone)).sort((a,b)=>Number(b.all_day)-Number(a.all_day)||a.start.localeCompare(b.start))}
 const api={valid,add,today,range,navigate,onDay,eventsOn};if(typeof module!=='undefined')module.exports=api;else root.HubCalendar=api;
})(typeof window!=='undefined'?window:globalThis);
