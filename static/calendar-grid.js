/* Wall-clock geometry in HA's timezone. Events retain their original UTC offsets. */
(function(root){
 const calendar=typeof module!=='undefined'?require('./calendar.js'):root.HubCalendar;
 const formatters=new Map();
 function minute(date,zone){if(!formatters.has(zone))formatters.set(zone,new Intl.DateTimeFormat('en-GB',{timeZone:zone,hour:'2-digit',minute:'2-digit',hourCycle:'h23'}));const p=Object.fromEntries(formatters.get(zone).formatToParts(new Date(date)).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));return Number(p.hour)*60+Number(p.minute)}
 function segments(events,key,zone){const result=[];events.forEach((event,index)=>{
  if(event.all_day||!calendar.onDay(event,key,zone))return;
  const a=new Date(event.start),b=new Date(event.end);if(!Number.isFinite(a.getTime())||!Number.isFinite(b.getTime())||b<=a)return;
  const startKey=calendar.today(zone,a),endKey=calendar.today(zone,b);
  const start=startKey<key?0:minute(a,zone);let end=endKey>key?1440:minute(b,zone),dstAdjusted=false;
  // In the repeated autumn hour, local end may precede local start. Keep the block visible.
  if(end<=start){end=Math.min(1440,start+(b-a)/60000);dstAdjusted=true}
  if(end>start)result.push({event,index,start,end,dstAdjusted,continuesBefore:startKey<key,continuesAfter:endKey>calendar.add(key,1)||endKey===calendar.add(key,1)&&minute(b,zone)>0});
 });return result.sort((a,b)=>a.start-b.start||b.end-a.end||a.index-b.index)}
 function place(items,minimumMinutes=0){
  const result=[],clusters=[];let cluster=[],edge=-Infinity;
  for(const item of items){const p={...item,displayEnd:Math.max(item.end,item.start+minimumMinutes)};if(cluster.length&&p.start>=edge){clusters.push(cluster);cluster=[];edge=-Infinity}cluster.push(p);edge=Math.max(edge,p.displayEnd)}if(cluster.length)clusters.push(cluster);
  for(const group of clusters){const ends=[];for(const p of group){let lane=ends.findIndex(end=>end<=p.start);if(lane<0)lane=ends.length;ends[lane]=p.displayEnd;p.lane=lane}for(const p of group)result.push({...p,lanes:ends.length})}
  return result;
 }
 function layout(events,keys,zone='Europe/Amsterdam',availableHeight=600){
  const days=keys.map(key=>({key,allDay:calendar.eventsOn(events,key,zone).filter(e=>e.all_day),segments:segments(events,key,zone)}));
  const all=days.flatMap(day=>day.segments),start=Math.max(0,Math.min(7*60,...all.map(p=>Math.floor(p.start/60)*60))),end=Math.min(1440,Math.max(22*60,...all.map(p=>Math.ceil(p.end/60)*60)));
  const hourHeight=Math.max(32,Math.min(52,Math.floor(availableHeight/((end-start)/60)))),height=(end-start)/60*hourHeight;
  for(const day of days)day.placed=place(day.segments,14/hourHeight*60).map(p=>({...p,top:(p.start-start)/60*hourHeight,height:Math.min(height-(p.start-start)/60*hourHeight,Math.max(14,(p.end-p.start)/60*hourHeight)),left:p.lane/p.lanes*100,width:100/p.lanes}));
  return {days,start,end,hourHeight,height};
 }
 function columns(width){return width>=900?7:width>=620?4:width>=460?3:width>=310?2:1}
 function identity(event){return JSON.stringify([event.calendar_id,event.start,event.end,event.summary])}
 const api={minute,segments,place,layout,columns,identity};if(typeof module!=='undefined')module.exports=api;else root.CalendarGrid=api;
})(typeof window==='undefined'?globalThis:window);
