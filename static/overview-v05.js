function moonDrawing(moon){
 const points=[],waxing=moon.phase<=.5,k=Math.cos(2*Math.PI*moon.phase),radius=9,cx=12,cy=12;
 for(let i=0;i<=24;i++){const y=-1+i/12,s=Math.sqrt(Math.max(0,1-y*y));points.push([cx+radius*(waxing?s:-s),cy+radius*y])}
 for(let i=24;i>=0;i--){const y=-1+i/12,s=Math.sqrt(Math.max(0,1-y*y));points.push([cx+radius*(waxing?k*s:-k*s),cy+radius*y])}
 return `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="#344154"/><path d="M${points.map(p=>p.map(n=>n.toFixed(2)).join(',')).join('L')}Z" fill="#e7e5cc"/><circle cx="12" cy="12" r="9" fill="none" stroke="#b8c0cc" stroke-width=".7"/></svg>`;
}
let ambientKey='';
function renderAmbient(c){
 const moon=HubAmbient.moon((globalThis.FrameoClock?.now()??Date.now()),states[c.moon_entity]),key=moon.index+':'+moon.phase.toFixed(3);
 if(key!==ambientKey){ambientKey=key;$('moon-phase').innerHTML=moonDrawing(moon)+`<span>${esc(moon.label)}</span>`;$('moon-phase').title=moon.approximate?'Berekende maanfase bij benadering':'Maanfase uit Home Assistant'}
 document.documentElement.dataset.night=String(HomeHub.sunVisual(states,c).sky==='night');
 const model=HubAmbient.notifications(states,c,['live','polling'].includes(connection.mode)&&socket?.readyState===WebSocket.OPEN),current=boot.demo?null:model.current,element=$('house-notification');
 window.FrameoPhotoMode?.notify('home',model.live&&current&&!['unknown','stale'].includes(current.kind)?[current.kind+':'+current.detail]:[]);
 window.FrameoLED?.update(model,states,c);
 window.FrameoMessage?.updateGarage(model,c.dashboard||{});
 element.hidden=!current;
 element.onclick=()=>{if(current?.kind==='garage'&&c.dashboard?.garage_camera)FrameoMessage.showGarage(c.dashboard.garage_camera);else openPanel('home-notifications')};
 if(current){const key=JSON.stringify(current);if(element.dataset.message!==key){element.dataset.message=key;element.className='house-notification led-'+current.color;element.innerHTML=`<span class="notification-led" aria-hidden="true"></span><span><b>${esc(current.label)}</b><small>${esc(current.detail)}</small></span>`;element.setAttribute('aria-label',current.label+'. '+current.detail)}}
 if(active==='home-notifications')draw();
}
function drawHomeNotifications(){const model=HubAmbient.notifications(states,boot.config,['live','polling'].includes(connection.mode)&&socket?.readyState===WebSocket.OPEN);
 return `<section class="panel"><h2>Woningmeldingen</h2>${!model.live?'<p class="detail-error">Status niet actueel. Hieronder staan de laatst ontvangen waarden.</p>':''}${!model.garageKnown?'<p class="detail-error">Garagestatus onbekend.</p>':''}${model.items.length?model.items.map(item=>`<div class="house-message led-${item.color}"><span class="notification-led" aria-hidden="true"></span><div><b>${esc(item.label)}</b><p>${esc(item.detail)}</p></div></div>`).join(''):'<p>Geen actieve woningmeldingen.</p>'}</section>`}
function detailBack(){return `<button class="detail-back" onclick="openPanel('climate')">‹ Klimaatoverzicht</button>`}
function climateSummary(c){const overview=HomeHub.overview(states,c),thermostats=Object.entries(c.thermostats||{});
 return `${climateOverviewPanel(c)}<div class="climate-shortcuts">${thermostats.map(([label,entity],index)=>{const source=thermostatState(entity);return `<button class="compact-device" onclick="openPanel('climate-thermostat-${index}')">${icon('thermo')}<span><b>${esc(label)}</b><small data-climate-summary="${esc(entity)}">${source.target===null?'Geen instelpunt':thermostatValue(source.target,source.step)+' °C'} · ${esc(climateModes[source.state.state]||source.state.state||'Onbekend')}</small></span><span>›</span></button>`}).join('')}<button class="compact-device" onclick="openPanel('climate-ventilation')">${icon('wind')}<span><b>Ventilatie en WTW</b><small id="climate-fan-summary">${esc(overview.ventilation||'Onbekend')}</small></span><span>›</span></button></div>`;
}
function climateDetail(c){
 if(active==='climate')return climateSummary(c);
 if(active==='climate-ventilation')return detailBack()+`<section class="panel"><h2>Itho · ventilatie</h2>${ventilationButtons()}${Object.entries(c.climate||{}).slice(6).map(([k,v])=>metric(k,v)).join('')}</section>`;
 const index=Number(active.replace('climate-thermostat-','')),entry=Object.entries(c.thermostats||{})[index];
 if(!entry)return detailBack()+'<p>Dit apparaat is niet ingesteld.</p>';
 const [label,entity]=entry,isHeatPump=/thermia|warmtepomp/i.test(label+' '+entity);
 return detailBack()+thermostatCard(label,entity)+(isHeatPump?`<section class="panel"><h2>Thermia · meetwaarden</h2>${Object.entries(c.climate||{}).slice(0,6).map(([k,v])=>metric(k,v)).join('')}</section>`:'');
}
function energyOverview(c){const o=HomeHub.overview(states,c),battery=HomeHub.batteryVisual(states,c),grid=HomeHub.powerWatts(states,c.energy?.['Net nu']);
 const block=(label,value,drawing,note='')=>{const key=({Zonnepanelen:'solar',Woning:'power',Batterij:'battery'})[label];return `<article class="energy-value${key?' graph-metric':''}"${key?` role="button" tabindex="0" onclick="openMeasurement('${key}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openMeasurement('${key}')}"`:''}>${icon(drawing)}<span>${label}</span><strong>${esc(value)}</strong>${note?`<small>${esc(note)}</small>`:''}</article>`};
 return `<section class="panel"><h2>Energiestromen · nu</h2><div class="energy-values">${block('Zonnepanelen',HomeHub.formatPower(o.solar),'sun')}${block('Woning',HomeHub.formatPower(o.house),'house')}${block('Batterij',battery.soc===null?'—':Math.round(battery.soc)+'%','battery',battery.power===null?'Vermogen onbekend':(battery.charging?'Laden':Math.abs(battery.power)<=(c.battery_power_deadband??20)?'Rust':'Ontladen')+' · '+HomeHub.formatPower(Math.abs(battery.power)))}${block('Net',HomeHub.formatPower(grid),'zap',grid===null?'Geen actuele waarde':grid<0?'Teruglevering':grid>0?'Afname':'Geen uitwisseling')}</div><div class="energy-today">${c.solar_today_statistic?solarTodayMetric():metric('Zon vandaag',c.energy?.['Zon vandaag'])}</div></section>`;
}
function drawEnergy(c){return `<button class="big flow-shortcut" onclick="openPanel('power-flow')">${icon('zap')} Stroomoverzicht <span>›</span></button>`+energyOverview(c)+`<button class="big tibber-history-link" onclick="openPanel('tibber')">Tibber · kosten en opbrengsten <span>Dag · week · maand · jaar ›</span></button>`+dayPricePanel()+`<details class="panel"><summary>Alle energiewaarden</summary>${Object.entries(c.energy||{}).filter(([k])=>k!=='Zon vandaag'||!c.solar_today_statistic).map(([k,v])=>metric(k,v)).join('')}</details>`+energyDiagnostics(c)}
