/* Today's price, solar power and battery SOC share time, never units. */
(function(root){
 'use strict';
 const finite=value=>typeof value==='number'&&Number.isFinite(value);
 const stamp=value=>Date.parse(value);
 const clamp=(value,a,b)=>Math.max(a,Math.min(b,value));
 function dayBounds(day,zone='Europe/Amsterdam'){
  const next=new Date(day+'T12:00:00Z');next.setUTCDate(next.getUTCDate()+1);
  const midnight=key=>{const target=Date.parse(key+'T00:00:00Z');let guess=target;for(let i=0;i<3;i++){const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:zone,year:'numeric',month:'numeric',day:'numeric',hour:'numeric',minute:'numeric',second:'numeric',hourCycle:'h23'}).formatToParts(new Date(guess)).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));const represented=Date.UTC(+p.year,+p.month-1,+p.day,+p.hour,+p.minute,+p.second);guess+=target-represented}return guess};
  return {start:midnight(day),end:midnight(next.toISOString().slice(0,10))};
 }
 function priceColor(value,low,high){
  const colors=['#5cce80','#d6d65c','#eda94d','#ef6662'];
  const position=high>low?clamp((value-low)/(high-low),0,1):.5;
  const scaled=position*3,i=Math.min(2,Math.floor(scaled)),fraction=scaled-i;
  return '#'+[1,3,5].map(k=>Math.round(parseInt(colors[i].slice(k,k+2),16)*(1-fraction)+parseInt(colors[i+1].slice(k,k+2),16)*fraction).toString(16).padStart(2,'0')).join('');
 }
 function history(data,start,now,unit){
  if(!data||data.unit!==unit)return [];
  const end=Math.min(now,stamp(data.end));if(!finite(end)||end<start)return [];
  const rows=(data.points||[]).map(p=>({t:stamp(p.time),v:finite(p.value)?p.value:null})).filter(p=>finite(p.t)&&p.t<=end).sort((a,b)=>a.t-b.t);
  let prior=null;const result=[];
  for(const p of rows){if(p.t<=start)prior=p;else result.push(p)}
  result.unshift({t:start,v:prior?.v??null});
  if(result[result.length-1].t<end)result.push({t:end,v:result[result.length-1].v});
  return result.map(p=>({...p,v:p.v===null?null:unit==='%'?(p.v>=0&&p.v<=100?p.v:null):p.v>=0?p.v/1000:null}));
 }
 function futurePlan(plan,now,end){
  const rows=(plan?.points||[]).map(p=>({t:stamp(p.time),v:finite(p.soc)&&p.soc>=0&&p.soc<=100?p.soc:null})).filter(p=>finite(p.t)&&p.t<end).sort((a,b)=>a.t-b.t);
  const result=rows.filter(p=>p.t>=now);
  for(let i=1;i<rows.length;i++){const a=rows[i-1],b=rows[i];if(a.t<now&&now<b.t&&b.t-a.t<=15*60000*1.01&&a.v!==null&&b.v!==null){result.unshift({t:now,v:a.v+(b.v-a.v)*(now-a.t)/(b.t-a.t)});break}}
  return result;
 }
 function hourlyPrices(points,start,end){
  const result=[];
  for(let a=start;a<end;a+=3600000){const b=Math.min(end,a+3600000);let weighted=0,covered=0;for(const p of points){const duration=Math.max(0,Math.min(b,p.b)-Math.max(a,p.a));if(duration){weighted+=p.v*duration;covered+=duration}}if(covered)result.push({a,b,v:weighted/covered,coverage:Math.min(1,covered/(b-a))})}
  return result;
 }
 function model(data,{day,zone='Europe/Amsterdam',now=Date.now(),soc=null,solar=null,live=false,reserve=null}={}){
  const bounds=dayBounds(day,zone),{start,end}=bounds,cutoff=Math.min(now,end),prices=data.prices?.date===day?data.prices:null,plan=data.plan?.date===day?data.plan:null;
  const quarters=(prices?.points||[]).map(p=>({a:stamp(p.start),b:stamp(p.end),v:finite(p.price)?p.price*100:null})).filter(p=>p.v!==null&&finite(p.a)&&finite(p.b)&&p.b>p.a&&p.a<end&&p.b>start).map(p=>({...p,a:Math.max(start,p.a),b:Math.min(end,p.b)}));
  const bars=hourlyPrices(quarters,start,end);
  const values=bars.map(p=>p.v),low=values.length?Math.min(...values):null,high=values.length?Math.max(...values):null;
  const measuredSoc=history(data.battery,start,cutoff,'%'),measuredSolar=history(data.solar,start,cutoff,'W');
  function latest(rows,value,max){if(live&&finite(value)&&value>=0&&value<=max&&now>=start&&now<end){const tail=rows[rows.length-1];if(tail&&tail.v!==null&&now-tail.t<=5*60000)rows.push({t:now,v:tail.v});rows.push({t:now,v:value})}}
  latest(measuredSoc,soc,100);latest(measuredSolar,finite(solar)?solar/1000:null,Infinity);
  const expectedSoc=futurePlan(plan,Math.max(now,start),end);
  const expectedSolar=(plan?.solar||[]).map(p=>({a:Math.max(start,now,stamp(p.start)),b:Math.min(end,stamp(p.end)),v:finite(p.kwh)?p.kwh/((stamp(p.end)-stamp(p.start))/3600000):null})).filter(p=>finite(p.a)&&finite(p.b)&&p.b>p.a&&p.v!==null&&finite(p.v)&&p.v>=0);
  const gaps=[];
  if(!measuredSolar.length)gaps.push({a:start,b:Math.min(now,end)});
  for(let i=0;i<measuredSolar.length-1;i++)if(measuredSolar[i].v===null)gaps.push({a:measuredSolar[i].t,b:measuredSolar[i+1].t});
  const solarFallback=[];
  for(const row of plan?.solar||[]){const a=Math.max(start,stamp(row.start)),b=Math.min(now,end,stamp(row.end)),duration=(stamp(row.end)-stamp(row.start))/3600000;if(!finite(a)||!finite(b)||b<=a||!finite(row.kwh)||row.kwh<0||duration<=0)continue;for(const gap of gaps){const left=Math.max(a,gap.a),right=Math.min(b,gap.b);if(right>left)solarFallback.push({a:left,b:right,v:row.kwh/duration})}}
  const solarMax=Math.max(1,Math.ceil(Math.max(0,...measuredSolar.map(p=>p.v||0),...expectedSolar.map(p=>p.v),...solarFallback.map(p=>p.v))/.5)*.5);
  const priceMin=Math.min(0,Math.floor((low??0)/10)*10),priceMax=Math.max(10,Math.ceil((high??0)/10)*10);
  const current=quarters.find(p=>p.a<=now&&now<p.b)?.v??null;
  return {start,end,now:now>=start&&now<end?now:null,bars,low,high,current,measuredSoc,measuredSolar,expectedSoc,expectedSolar,solarFallback,solarMax,priceMin,priceMax,reserve:finite(reserve)&&reserve>=0&&reserve<=100?reserve:null};
 }
 const n=value=>Number(value.toFixed(2));
 function chart(m,{width=600,height=170}={}){
  const top=18,bottom=height,plot=bottom-top,x=t=>n(clamp((t-m.start)/(m.end-m.start),0,1)*width),ySoc=value=>n(bottom-clamp(value,0,100)/100*plot),ySun=value=>n(bottom-clamp(value,0,m.solarMax)/m.solarMax*plot),yPrice=value=>n(bottom-(value-m.priceMin)/(m.priceMax-m.priceMin)*plot),zero=yPrice(0);
  const step=(rows,y,maxGap=Infinity)=>{let path='',last=null;for(const p of rows){if(p.v===null||!finite(p.v)){last=null;continue}const connects=last&&p.t-last.t<=maxGap;path+=(connects?'H'+x(p.t)+'V':'M'+x(p.t)+',')+y(p.v);last=p}return path};
  const linear=(rows,y,maxGap)=>{let path='',last=null;for(const p of rows){if(p.v===null||!finite(p.v)){last=null;continue}path+=(last&&p.t-last.t<=maxGap?'L':'M')+x(p.t)+','+y(p.v);last=p}return path};
  let svg=`<svg class="home-energy-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Stroomprijs in cent per kWh, zonnevermogen in kW en acculading in procent. Uurgemiddelden als balken. Gemeten doorgetrokken; verwacht en gepland gestippeld."><title>Vandaag · prijs ${m.priceMin}–${m.priceMax} ct/kWh · zon 0–${m.solarMax} kW · accu 0–100%</title>`;

  for(const p of m.bars){const a=x(p.a),b=x(p.b),y=yPrice(p.v);svg+=`<rect class="home-energy-price-bar${m.now!==null&&p.b<=m.now?' is-past':''}" x="${a}" y="${Math.min(y,zero)}" width="${Math.max(.3,b-a-3)}" height="${Math.max(.7,Math.abs(zero-y))}" fill="${priceColor(p.v,m.low,m.high)}"><title>${new Date(p.a).toISOString()} · uurgemiddelde ${n(p.v)} ct/kWh${p.coverage<.999?" · gedeeltelijke prijzen":""}</title></rect>`}
  svg+=`<path class="home-energy-sun is-planned is-fallback" d="${(m.solarFallback||[]).map(p=>'M'+x(p.a)+','+ySun(p.v)+'H'+x(p.b)).join('')}"/><path class="home-energy-sun" d="${step(m.measuredSolar,ySun)}"/><path class="home-energy-sun is-planned" d="${m.expectedSolar.map(p=>'M'+x(p.a)+','+ySun(p.v)+'H'+x(p.b)).join('')}"/>`;
  if(m.reserve!==null)svg+=`<line class="home-energy-reserve" x1="0" x2="${width}" y1="${ySoc(m.reserve)}" y2="${ySoc(m.reserve)}"><title>Accu-ondergrens ${m.reserve}%</title></line>`;
  svg+=`<path class="home-energy-soc" d="${step(m.measuredSoc,ySoc)}"/><path class="home-energy-soc is-planned" d="${linear(m.expectedSoc,ySoc,15*60000*1.01)}"/>`;
  const last=m.measuredSoc[m.measuredSoc.length-1];if(last?.v!==null&&last&&m.now!==null&&Math.abs(last.t-m.now)<5*60000)svg+=`<circle class="home-energy-soc-dot" cx="${x(last.t)}" cy="${ySoc(last.v)}" r="3"/>`;
  if(m.now!==null){const anchor=x(m.now)>width-20?'end':x(m.now)<20?'start':'middle';svg+=`<line class="home-energy-now" x1="${x(m.now)}" x2="${x(m.now)}" y1="20" y2="${bottom}"/><text class="home-energy-now-text" x="${x(m.now)}" y="14" text-anchor="${anchor}">NU</text>`}
  return svg+'</svg>';
 }
 const api={dayBounds,priceColor,history,futurePlan,hourlyPrices,model,chart};
 if(typeof module!=='undefined'){module.exports=api;return}
 root.HomeEnergy=api;
 const box=document.getElementById('home-energy-chart');if(!box)return;
 const status=document.getElementById('home-energy-status'),range=document.getElementById('home-energy-range');
 let current=null,date='',lastLoad=0,busy=false,request=0,lastDraw='',data={},errors={};
 const clock=()=>root.FrameoClock?.now()??Date.now();
 const today=(zone,now)=>root.HubCalendar.today(zone,new Date(now));
 function draw(force=false){
  if(!current)return;
  const {states,config,connection}=current,now=clock(),day=today(config.timezone,now);
  if(day!==date){date=day;data={};errors={};lastLoad=0;request++;busy=false;lastDraw=''}
  const battery=root.HomeHub.batteryReserve(states,config),overview=root.HomeHub.overview(states,config),live=['live','polling'].includes(connection?.mode),key=Math.floor(now/60000)+':'+date;
  if(!force&&lastDraw===key)return;lastDraw=key;
  const m=model(data,{day,zone:config.timezone,now,soc:battery.soc,solar:overview.solar,live,reserve:battery.minimum});
  const present=m.bars.length||[...m.measuredSoc,...m.measuredSolar,...m.expectedSoc].some(p=>p.v!==null)||m.expectedSolar.length||m.solarFallback.length;
  box.innerHTML=present?chart(m,{width:Math.max(180,box.clientWidth||600),height:Math.max(54,box.clientHeight||84)}):'<span class="home-energy-empty">'+(busy?'Grafiek ophalen…':'Geen grafiekgegevens')+'</span>';
  const fmt=value=>value===null?'—':value.toLocaleString('nl-NL',{minimumFractionDigits:1,maximumFractionDigits:1});
  if(range)range.textContent=m.low===null?'':'Laagste '+fmt(m.low)+' · Hoogste '+fmt(m.high)+' ct/kWh';
  if(range)range.title='Gemiddelde stroomprijs per uur. De grote actuele prijs blijft de geldende kwartierprijs.';
  const issue=Object.keys(errors);status.hidden=!issue.length;status.textContent=issue.length?'!':'';status.title=issue.map(k=>({prices:'Dagprijzen',solar:'Zonmetingen',battery:'Accumetingen',plan:'Victron-planning'}[k])+': '+errors[k]).join('\n');
  box.title='Geel: zon, 0–'+m.solarMax+' kW. Blauw: accu, 0–100%. Balken: prijs, '+m.priceMin+'–'+m.priceMax+' ct/kWh. Gestippeld: verwachting/planning, ook als gemeten zon ontbreekt. Tik voor Tibber.';
 }
 async function load(){
  if(!current||busy)return;draw();busy=true;lastLoad=clock();const id=++request,day=date;
  const paths={prices:'/api/energy/prices?date='+day,solar:'/api/history/measurement?key=solar&hours=24',battery:'/api/history/measurement?key=battery&hours=24',plan:'/api/energy/victron-planning?date='+day};
  await Promise.allSettled(Object.entries(paths).map(async([key,path])=>{
   const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),28000);
   try{const response=await fetch(path,{cache:'no-store',signal:controller.signal});if(!response.ok)throw Error('Tijdelijk niet beschikbaar');const value=await response.json();if(id!==request||day!==date)return;data[key]=value;delete errors[key]}
   catch(error){if(id===request&&day===date)errors[key]=error.name==='AbortError'?'Geen antwoord':error.message}
   finally{clearTimeout(timeout);if(id===request)draw(true)}
  }));
  if(id===request){busy=false;draw(true)}
 }
 if(typeof ResizeObserver!=='undefined')new ResizeObserver(()=>draw(true)).observe(box);
 root.FrameoEnergy={update(states,config,connection){current={states,config,connection};draw();if(clock()-lastLoad>=120000&&!document.hidden)load()},refresh:load};
 setInterval(()=>{if(!document.hidden&&current){draw();if(clock()-lastLoad>=120000)load()}},30000);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden&&current){draw(true);if(clock()-lastLoad>=120000)load()}});
})(typeof globalThis!=='undefined'?globalThis:this);
