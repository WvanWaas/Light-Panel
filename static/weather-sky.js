/* Original, lightweight weather artwork; existing HA readings remain authoritative. */
(function(root){
 function model(condition,sun={}){
  const known=['sunny','clear-night','partlycloudy','cloudy','rainy','pouring','lightning','lightning-rainy','snowy','snowy-rainy','hail','fog','windy','windy-variant','exceptional'].includes(condition);
  const raw=sun.attributes?.elevation,elevation=raw===null||raw===undefined?NaN:Number(raw),night=condition==='clear-night'||sun.state==='below_horizon';
  const twilight=Number.isFinite(elevation)&&elevation>=-6&&elevation<4;
  const kind=!known?'unknown':condition.includes('lightning')?'storm':['rainy','pouring'].includes(condition)?'rain':condition.includes('snow')||condition==='hail'?'snow':condition==='fog'?'fog':['cloudy','partlycloudy','windy-variant'].includes(condition)?'cloud':condition==='windy'?'wind':'clear';
  return {kind,phase:twilight?'twilight':night?'night':'day',clouds:['cloud','rain','snow','fog','storm'].includes(kind)};
 }
 function sunTrack(a,now){
  const rise=Date.parse(a?.sunrise),set=Date.parse(a?.sunset);if(!Number.isFinite(rise)||!Number.isFinite(set)||set<=rise)return null;
  if(!Number.isFinite(now))return null;
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:a.timezone||'Europe/Amsterdam',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(now)),local=['year','month','day'].map(key=>parts.find(part=>part.type===key).value).join('-');
  if(a.date&&local!==a.date)return null;
  const progress=Math.max(0,Math.min(1,(now-rise)/(set-rise)));
  return {progress,above:now>=rise&&now<=set,x:24+272*progress,y:104-76*Math.sin(Math.PI*progress),dayMinutes:Math.round((set-rise)/60000),next:now<rise?'sunrise':now<set?'sunset':null};
 }
 const api={model,sunTrack};if(typeof module!=='undefined')module.exports=api;else root.WeatherSky=api;
})(globalThis);

function weatherSkyMarkup(data){
 const current=states[data.entity_id]||data.current||{},a=current.attributes||{},scene=WeatherSky.model(current.state,states[boot.config?.sun||'sun.sun']||{});
 const now=globalThis.FrameoClock?.now()??Date.now(),unit=a.temperature_unit||'°C',hourly=(data.hourly||[]).filter(row=>Number.isFinite(Date.parse(row.datetime))&&Date.parse(row.datetime)>=now-1800000).slice(0,8);
 const today=(data.daily||[]).find(row=>HubCalendar.today(detailZone(),new Date(row.datetime))===HubCalendar.today(detailZone()));
 const moon=HubAmbient.moon(now,states[boot.config?.moon_entity]);moon.phase=Math.round(moon.phase*1000)/1000;
 const celestial=scene.phase==='night'?moonDrawing(moon):'<span class="sky-sun"></span>';
 const metric=(label,value)=>`<div><small>${label}</small><b>${value}</b></div>`;
 return `<section class="weather-sky sky-${scene.kind} sky-${scene.phase}" aria-label="Actueel weer"><div class="weather-sky-art" aria-hidden="true"><div class="sky-celestial">${celestial}</div>${scene.clouds?'<span class="weather-cloud cloud-a"></span><span class="weather-cloud cloud-b"></span><span class="weather-cloud cloud-c"></span>':''}${['rain','snow','storm'].includes(scene.kind)?`<div class="sky-particles">${Array.from({length:12},(_,i)=>`<i style="--particle:${i}"></i>`).join('')}</div>`:''}<div class="sky-horizon"></div></div><div class="weather-sky-content"><div class="weather-sky-kicker"><span>Buiten · nu</span><span>${scene.phase==='night'?'Nacht':scene.phase==='twilight'?'Schemering':'Overdag'}</span></div><div class="weather-sky-main"><div class="weather-sky-reading"><strong>${detailNumber(a.temperature,unit,1)}</strong><h2>${esc(conditionLabels[current.state]||'Weer niet beschikbaar')}</h2><p>Voelt als ${detailNumber(a.apparent_temperature,unit,1)}</p>${today?`<p class="sky-highlow">↑ ${detailNumber(today.temperature,unit,0)} <span>↓ ${detailNumber(today.templow,unit,0)}</span></p>`:''}</div><div class="weather-sky-facts">${metric('Wind',detailNumber(a.wind_speed,a.wind_speed_unit,1))}${metric('Luchtvochtigheid',detailNumber(a.humidity,'%',0))}${metric('Luchtdruk',detailNumber(a.pressure,a.pressure_unit,0))}${metric('Zonsondergang',astronomyState.data?.sunset?esc(timeTitle(astronomyState.data.sunset)):'—')}</div></div>${hourly.length?`<div class="weather-sky-hours" aria-label="De komende uren">${hourly.map(row=>`<div><small>${esc(timeTitle(row.datetime))}</small>${weatherIcon(row.condition)}<b>${detailNumber(row.temperature,unit,0)}</b><span>${detailNumber(row.precipitation_probability,'%',0)}</span></div>`).join('')}</div>`:''}</div></section>`;
}
function weatherSunPath(a){
 const track=WeatherSky.sunTrack(a,globalThis.FrameoClock?.now()??Date.now());if(!track)return '';
 const time=value=>value?esc(timeTitle(value)):'—',headline=track.next==='sunrise'?'Zonsopkomst':track.next==='sunset'?'Zonsondergang':'Zon onder',headlineTime=track.next?time(a[track.next]):time(a.sunset);
 return `<div class="weather-sun-track"><div class="sun-track-top"><span>${headline}<strong>${headlineTime}</strong></span><small>${Math.floor(track.dayMinutes/60)} uur ${track.dayMinutes%60} min daglicht</small></div><svg viewBox="0 0 320 126" role="img" aria-label="Daglicht van ${time(a.sunrise)} tot ${time(a.sunset)}${track.above?', de zonmarkering toont de voortgang van de dag':''}"><path class="sun-track-base" d="M24 104H296"/><path class="sun-track-arc" d="${Array.from({length:33},(_,i)=>(i?'L':'M')+(24+272*i/32)+','+(104-76*Math.sin(Math.PI*i/32))).join('')}"/>${track.above?`<circle class="sun-track-dot" cx="${track.x}" cy="${track.y}" r="6"/>`:''}<text x="24" y="122">${time(a.sunrise)}</text><text x="296" y="122" text-anchor="end">${time(a.sunset)}</text></svg></div>`;
}
