/* Pure calculations shared by the dashboard and regression tests. */
(function(root){
  const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
  const number=value=>value===null||value===undefined||String(value).trim()===''?null:
    Number.isFinite(Number(value))?Number(value):null;
  function weatherSource(states,c={}) {
    const primary=c.weather,fallbacks=Array.isArray(c.weather_fallbacks)?c.weather_fallbacks:[];
    const candidates=primary?[primary,...fallbacks]:Object.keys(states).filter(k=>k.startsWith('weather.')).sort();
    for(const entity of [...new Set(candidates)]){if(typeof entity!=='string'||!/^weather\.[a-z0-9_]+$/.test(entity))continue;const current=states[entity];if(current?.state&&!['unknown','unavailable'].includes(current.state))return {entity_id:entity,current,is_fallback:!!primary&&entity!==primary,primary_entity_id:primary}}
    return null;
  }
  function sunVisual(states,c={}) {
    const sun=states[c.sun||'sun.sun'];
    const az=number(sun?.attributes?.azimuth),el=number(sun?.attributes?.elevation);
    const weather=weatherSource(states,c)?.current;
    const condition=weather?.state||'unknown';
    const night=sun?.state==='below_horizon'||(el!==null&&el<0);
    const rainy=['rainy','pouring','lightning-rainy','snowy-rainy'].includes(condition);
    const cloudy=['cloudy','fog','snowy','hail','exceptional','lightning'].includes(condition);
    const clear=['sunny','clear-night','partlycloudy'].includes(condition);
    let strength=rainy?.12:cloudy?.22:condition==='partlycloudy'?.6:clear?1:.35;
    const clouds=number(weather?.attributes?.cloud_coverage);
    if(clouds!==null)strength*=1-clamp(clouds,0,100)/150;
    const valid=az!==null&&el!==null&&!['unknown','unavailable'].includes(sun?.state);
    const angle=((az||0)-(number(c.sun_screen_rotation)||0))*Math.PI/180;
    return {x:50-44*Math.sin(angle),y:85-80*clamp(el||0,0,90)/90,
      opacity:valid&&!night?strength*(.3+.7*clamp(el,0,30)/30):0,
      color:el!==null&&el<12?'255, 161, 78':'255, 225, 157',
      sky:night?'night':rainy?'rain':cloudy?'cloud':clear?'clear':'neutral',condition};
  }
  function batteryReserve(states,c={}) {
    const settings=c.feed_notifications||{},capacity=number(settings.battery_capacity_kwh),soc=number(states[c.battery]?.state);
    const limits=(settings.battery_min_soc_entities||[]).map(id=>number(states[id]?.state)).filter(n=>n!==null&&n>=0&&n<=100);
    const minimum=limits.length?Math.max(...limits):null;
    const available=capacity!==null&&capacity>0&&soc!==null&&soc>=0&&soc<=100&&minimum!==null?capacity*Math.max(0,soc-minimum)/100:null;
    return {capacity,soc,minimum,available};
  }
  function cardColors(states,c={},date=new Date(globalThis.FrameoClock?.now()??Date.now())) {
    const neutral='#1c2b36',blue='#214d73',green='#285842',orange='#68411f',red='#692e35';
    const blend=(a,b,t)=>{t=clamp(t,0,1);const rgb=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));return '#'+rgb(a).map((n,i)=>Math.round(n+(rgb(b)[i]-n)*t).toString(16).padStart(2,'0')).join('')};
    const ramp=(value,low,high,colors)=>{if(value===null||!Number.isFinite(value))return neutral;const t=clamp((value-low)/(high-low),0,1)*(colors.length-1),i=Math.min(colors.length-2,Math.floor(t));return blend(colors[i],colors[i+1],t-i)};
    const reserve=batteryReserve(states,c),soc=reserve.soc!==null&&reserve.soc>=0&&reserve.soc<=100?reserve.soc:null;
    const floor=reserve.minimum??15,full=Math.min(100,Math.max(60,floor+1));
    const month=Number(new Intl.DateTimeFormat('en-US',{timeZone:c.timezone||'Europe/Amsterdam',month:'numeric'}).format(date))-1;
    const summer=[0,0,.25,.5,.75,1,1,1,2/3,1/3,0,0][month],roomCold=19+2*summer,roomWarm=22+summer;
    const temperature=id=>{const row=states[id],value=number(row?.state),unit=row?.attributes?.unit_of_measurement;return value===null?null:unit==='°C'?value:unit==='°F'?(value-32)*5/9:null};
    const price=priceSignal(states,c);
    return {battery:ramp(soc,floor,full,[red,orange,green]),price:price.color,
      room:ramp(temperature(c.dashboard?.indoor_temperature),roomCold,roomWarm,[blue,green,orange,red]),
      water:ramp(temperature(c.dashboard?.hot_water_temperature||c.climate?.Tapwater),45,60,['#0878c9','#a94d00','#bd2538']),roomCold,roomWarm};
  }
  function batteryVisual(states,c={}) {
    const soc=number(states[c.battery]?.state);
    const entity=states[c.battery_power||c.energy?.Batterijvermogen];
    let power=number(entity?.state);
    if(power!==null&&entity?.attributes?.unit_of_measurement==='kW')power*=1000;
    const deadband=number(c.battery_power_deadband)??20;
    const charging=power!==null&&(c.battery_charge_positive===false?-power:power)>deadband;
    return {soc:soc===null?null:clamp(soc,0,100),power,charging,
      fills:Array.from({length:5},(_,i)=>soc===null?0:clamp((soc-i*20)/20,0,1))};
  }
  function layerStyle(layer,states) {
    let opacity=number(layer.opacity)??1;
    if(layer.dynamicOpacity==='brightness') {
      const brightness=number(states[layer.entity]?.attributes?.brightness);
      opacity*=brightness===null?1:clamp(brightness,0,255)/255;
    }
    if(layer.dynamicOpacity==='daylight') {
      const daylight=number(states['sensor.example_daylight_percentage']?.state);
      opacity*=daylight===null?(states['sun.sun']?.state==='above_horizon'?1:0):clamp(daylight,0,100)/100;
    }
    const percent=(v,fallback)=>typeof v==='string'&&/^\d+(\.\d+)?%$/.test(v)?v:fallback;
    const blend=['normal','lighten','darken','screen','multiply','overlay','soft-light','hard-light','color-dodge','color-burn','difference','exclusion','hue','saturation','color','luminosity'].includes(layer.blend)?layer.blend:'normal';
    return `position:absolute;left:${percent(layer.left,'50%')};top:${percent(layer.top,'50%')};width:${percent(layer.width,'100%')};height:${percent(layer.height,'100%')};transform:translate(-50%,-50%);opacity:${clamp(opacity,0,1)};mix-blend-mode:${blend};object-fit:fill;pointer-events:none`;
  }
  function powerWatts(states, entities) {
    const ids=typeof entities==='string'?[entities]:Array.isArray(entities)?[...new Set(entities)]:[];
    if(!ids.length)return null;
    let sum=0;
    for(const id of ids){const entity=states[id],n=number(entity?.state),unit=entity?.attributes?.unit_of_measurement;
      if(n===null||!['W','kW'].includes(unit))return null;
      sum+=n*(unit==='kW'?1000:1);
    }
    return sum;
  }
  function overview(states,c={}) {
    const d=c.dashboard||{},temp=states[d.indoor_temperature],co2=states[d.indoor_co2];
    const tempValue=number(temp?.state),co2Value=number(co2?.state);
    const mode=states[d.ventilation||c.climate?.Ventilatiestand]?.state;
    const validMode=mode&&!['unknown','unavailable','—'].includes(mode)?mode:null;
    const modeLabels={low:'Laag',medium:'Midden',mid:'Midden',high:'Hoog',auto:'Auto',automatic:'Auto',off:'Uit',on:'Aan',away:'Afwezig',boost:'Boost'};
    return {house:powerWatts(states,d.house_power??c.power),solar:powerWatts(states,c.solar),
      heatPump:powerWatts(states,d.heat_pump_power),
      temperature:tempValue!==null&&['°C','°F'].includes(temp?.attributes?.unit_of_measurement)?tempValue:null,
      temperatureUnit:temp?.attributes?.unit_of_measurement||'°C',
      co2:co2Value!==null&&co2?.attributes?.unit_of_measurement==='ppm'?co2Value:null,
      ventilation:validMode?(modeLabels[validMode.toLowerCase()]||validMode):null};
  }
  function compactPower(value){return value===null?'—':Math.abs(value)>=1000?(value/1000).toLocaleString('nl-NL',{maximumFractionDigits:1})+' kW':Math.round(value).toLocaleString('nl-NL')+' W'}
  function compactClimate(states,c={}){
    const d=c.dashboard||{},room=states[d.indoor_temperature],weather=weatherSource(states,c)?.current,water=states[d.hot_water_temperature||c.climate?.Tapwater];
    const celsius=(value,unit)=>{const n=number(value);return n===null?null:unit==='°C'?n:unit==='°F'?(n-32)*5/9:null};
    const indoor=celsius(room?.state,room?.attributes?.unit_of_measurement),outdoor=celsius(weather?.attributes?.temperature,weather?.attributes?.temperature_unit),hotWater=celsius(water?.state,water?.attributes?.unit_of_measurement);
    const heating=states[d.heating_active]?.state==='on',cooling=states[d.passive_cooling_active]?.state==='on';
    return {mode:heating&&!cooling?'heating':cooling&&!heating?'passive-cooling':'idle',indoor,outdoor,water:hotWater,outdoorTone:indoor===null||outdoor===null?'unknown':outdoor<indoor?'colder':outdoor>indoor?'warmer':'equal',waterColor:hotWater===null?'#365568':hotWater<=45?'#267eae':hotWater>=60?'#c74749':'#d8943b'};
  }
  function formatPower(value){return value===null?'—':Math.abs(value)>=1000?(value/1000).toLocaleString('nl-NL',{maximumFractionDigits:2})+' kW':Math.round(value).toLocaleString('nl-NL')+' W'}
  function electricityPrice(states,c={}) {
    const id=c.home_price||c.energy?.Stroomprijs,entity=states[id],value=number(entity?.state);
    const unit=String(entity?.attributes?.unit_of_measurement||'').toLowerCase().replace(/\s/g,'');
    const multiplier=['eur/kwh','€/kwh'].includes(unit)?100:['ct/kwh','c/kwh','cent/kwh','cents/kwh'].includes(unit)?1:null;
    return value===null||multiplier===null?null:value*multiplier;
  }
  function priceSignal(states,c={}) {
    const value=electricityPrice(states,c),neutral='#1c2b36';
    if(value===null)return {key:'unknown',label:'Geen prijs',color:neutral,position:null,basis:'unknown'};
    const a=states[c.home_price||c.energy?.Stroomprijs]?.attributes||{};
    let position=number(a.intraday_price_ranking),basis='day';
    if(position===null||position<0||position>1){
      const minimum=number(a.min_price),maximum=number(a.max_price),raw=number(states[c.home_price||c.energy?.Stroomprijs]?.state);
      if(minimum!==null&&maximum!==null&&maximum>=minimum&&raw!==null){position=maximum===minimum?.5:clamp((raw-minimum)/(maximum-minimum),0,1);basis='range'}
      else{const fallback=priceBand(value,c.price_thresholds_ct);position=({very_cheap:.05,cheap:.25,normal:.5,expensive:.75,very_expensive:.95})[fallback.key];basis='absolute'}
    }
    const index=position<=.15?0:position<=.35?1:position<=.65?2:position<=.85?3:4;
    const keys=['very_cheap','cheap','normal','expensive','very_expensive'],labels=basis==='absolute'?['Heel laag','Laag','Normaal','Hoog','Heel hoog']:['Goedkoop vandaag','Goedkoop vandaag','Middel vandaag','Duur vandaag','Duur vandaag'];
    const green='#087d36',orange='#a94d00',red='#bd2538',mix=(a,b,t)=>{t=clamp(t,0,1);return '#'+[1,3,5].map(i=>Math.round(parseInt(a.slice(i,i+2),16)+(parseInt(b.slice(i,i+2),16)-parseInt(a.slice(i,i+2),16))*t).toString(16).padStart(2,'0')).join('')};
    const color=position<=.3?green:position<.5?mix(green,orange,(position-.3)/.2):position<.8?mix(orange,red,(position-.5)/.3):red;
    return {key:keys[index],label:labels[index],color,position,basis};
  }
  function priceBand(value,limits){
    const fallback=[10,20,35,45];if(!Array.isArray(limits)||limits.length!==4||limits.some((n,i)=>!Number.isFinite(n)||(i>0&&n<=limits[i-1])))limits=fallback;
    if(value===null||!Number.isFinite(value))return {key:'unknown',label:'Geen prijs'};
    const index=limits.findIndex(limit=>value<=limit),keys=['very_cheap','cheap','normal','expensive','very_expensive'],labels=['Heel laag','Laag','Normaal','Hoog','Heel hoog'];
    return {key:keys[index<0?4:index],label:labels[index<0?4:index]};
  }
  const api={weatherSource,number,sunVisual,batteryVisual,batteryReserve,cardColors,layerStyle,powerWatts,overview,formatPower,compactPower,compactClimate,electricityPrice,priceBand,priceSignal};
  if(typeof module!=='undefined')module.exports=api;else root.HomeHub=api;
})(typeof window!=='undefined'?window:globalThis);
