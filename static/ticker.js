let liveTicker={items:[],notes:[],index:0,loading:false,error:'',ready:false},tickerTimer=null;let notificationManagementOpen=false;let notificationView='current',notificationFilters={grip:true,fire:true,ambulance:true,flight:true,aurora:true,sites:true,energy:true,air:true,laundry:true,fault:true},notificationHistory={items:[],next:null,loading:false,error:'',request:0,ready:false};try{const saved=JSON.parse(localStorage.getItem('homehub-notification-filters')||'{}');for(const key of Object.keys(notificationFilters))if(typeof saved[key]==='boolean')notificationFilters[key]=saved[key]}catch{};let dismissedCards={};try{dismissedCards=JSON.parse(localStorage.getItem('homehub-dismissed-cards')||'{}')}catch{}
let seenNotifications={};try{const saved=JSON.parse(localStorage.getItem('homehub-seen-notifications')||'{}');if(saved&&typeof saved==='object'&&!Array.isArray(saved))seenNotifications=saved}catch{}
function notificationKnown(item){return !!seenNotifications[item.original_id||item.id]}
function quietCharge(item){return item.kind==='energy'&&(notificationKnown(item)||Date.parse(item.expires_at)<=(globalThis.FrameoClock?.now()??Date.now()))}
function notificationOrder(a,b){return Number(quietCharge(a))-Number(quietCharge(b))||Date.parse(b.time)-Date.parse(a.time)||a.id.localeCompare(b.id)}
function markNotificationSeen(id){
 if(seenNotifications[id])return;
 seenNotifications[id]=globalThis.FrameoClock?.now()??Date.now();
 seenNotifications=Object.fromEntries(Object.entries(seenNotifications).sort((a,b)=>b[1]-a[1]).slice(0,200));
 try{localStorage.setItem('homehub-seen-notifications',JSON.stringify(seenNotifications))}catch{}
 renderTicker();if(active==='notifications')draw();
}
function vehicleDrawing(kind){const shapes={plane:'<path d="M10 21v-6L3 18v-3l7-5V4a2 2 0 0 1 4 0v6l7 5v3l-7-3v6l3 2H7Z"/>',helicopter:'<path d="M3 4h15M10 4v5M5 18h13M8 15v3m7-3v3M6 9h8a4 4 0 0 1 4 4v2H8a4 4 0 0 1-4-4v-1l-2-2M18 13h3V8m-2 0h4"/>',balloon:'<path d="M6 7a6 6 0 0 1 12 0c0 5-4 9-4 9h-4S6 12 6 7Zm4 9 1 4h2l1-4M12 1c-4 4-3 9 0 15m0-15c4 4 3 9 0 15"/>'};return `<svg class="icon vehicle-icon" data-vehicle="${kind||'plane'}" viewBox="0 0 24 24" aria-hidden="true">${shapes[kind]||shapes.plane}</svg>`}
function tickerIcon(kind){const custom={laundry:'<rect x="4" y="2" width="16" height="20" rx="2"/><circle cx="12" cy="14" r="5"/><path d="M7 6h2m3 0h5"/>',fault:'<path d="m12 3 10 18H2L12 3Zm0 6v5m0 3v1"/>',aurora:'<path d="m3 17 3-11 4 7 4-9 3 9 4-4M3 21h18"/>',sites:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c-5 5-5 13 0 18m0-18c5 5 5 13 0 18"/>',energy:'<path d="m13 2-9 12h7l-1 8 10-12h-7z"/>',air:'<path d="M3 8h12a3 3 0 1 0-3-3M2 12h18a3 3 0 1 1-3 3M4 16h7a3 3 0 1 1-3 3"/>'};if(custom[kind])return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${custom[kind]}</svg>`;if(kind==='flight')return vehicleDrawing('plane');const path=kind==='weather'?'<path d="m12 3 10 18H2L12 3Zm0 6v5m0 3v1"/>':kind==='p2000'?'<path d="M8 17h8M5 21h14M7 17v-5a5 5 0 0 1 10 0v5M4 8 2 7m18 1 2-1M12 2v2"/>':'<path d="M6 17h12l-2-3V9a4 4 0 0 0-8 0v5l-2 3Zm4 3h4"/>';return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${path}</svg>`}
function countryFlag(code){return /^[A-Z]{2}$/.test(code||'')?`<img class="country-flag" alt="${esc(code)}" title="${esc(code)}" src="/static/flags/${code.toLowerCase()}.svg" onerror="this.hidden=true">`:''}
function flightRoute(flight){if(!flight.origin&&!flight.destination)return esc(flight.model||flight.registration||'Route niet beschikbaar');return `<span class="flight-place">${countryFlag(flight.origin_country)}<span>${esc(flight.origin||'Onbekend')}</span></span><span class="flight-arrow">→</span><span class="flight-place">${countryFlag(flight.destination_country)}<span>${esc(flight.destination||'Onbekend')}</span></span>`}
function flightMeta(flight){return [flight.altitude_m!==null&&flight.altitude_m!==undefined?Math.round(flight.altitude_m).toLocaleString('nl-NL')+' m':null,flight.speed_kmh!==null&&flight.speed_kmh!==undefined?Math.round(flight.speed_kmh)+' km/u':null].filter(Boolean).join(' · ')}
function flightMarkup(item){const f=item.flight||{};return `<span class="ticker-symbol">${vehicleDrawing(f.vehicle)}</span><span class="ticker-copy flight-copy"><span class="flight-route">${flightRoute(f)}</span><span class="flight-meta">${esc(flightMeta(f))}</span><span class="flight-operator">${esc([f.airline,f.code||f.registration].filter(Boolean).join(' · ')||'Maatschappij onbekend')}</span></span>`}
function notificationCategory(item){return item.kind==='flight'?'flight':item.kind==='p2000'?item.service:(item.kind in notificationFilters?item.kind:'other')}
function notificationMatches(item){return notificationFilters[notificationCategory(item)]!==false}
function tickerItems(){const now=(globalThis.FrameoClock?.now()??Date.now());return liveTicker.items.filter(item=>item.kind!=='sites'&&Date.parse(item.expires_at)>now&&!dismissedCards[item.id]&&notificationMatches(item)).sort(notificationOrder)}
function notificationClass(item){return item.kind==='p2000'?'ticker-'+(item.service||'p2000'):item.severity?'ticker-'+item.severity:'ticker-'+item.kind}
function itemIcon(item){return item.flight?vehicleDrawing(item.flight.vehicle):tickerIcon(item.kind)}
function dismissTicker(id){const item=liveTicker.items.find(i=>i.id===id);if(!item)return;dismissedCards[id]=item.expires_at;saveDismissedCards();renderTicker();if(active==='notifications')draw()}
function saveDismissedCards(){const now=(globalThis.FrameoClock?.now()??Date.now());for(const [id,expires] of Object.entries(dismissedCards))if(Date.parse(expires)<=now)delete dismissedCards[id];try{localStorage.setItem('homehub-dismissed-cards',JSON.stringify(dismissedCards))}catch{}}
function openTicker(id){const item=liveTicker.items.find(item=>item.id===id);if(item?.kind==='energy')markNotificationSeen(item.original_id||item.id);notificationView='current';openPanel('notifications')}
function flightStripMarkup(item){const f=item.flight||{},code=f.code||f.registration||f.model||item.title,route=f.origin||f.destination?[f.origin||'Onbekend',f.destination||'Onbekend'].join(' → '):item.message,altitude=f.altitude_m!==null&&f.altitude_m!==undefined?Math.round(f.altitude_m).toLocaleString('nl-NL')+' m':'';return `<span class="ticker-symbol">${vehicleDrawing(f.vehicle)}</span><span class="ticker-copy flight-strip-copy"><b>${esc(code)}</b><span class="flight-strip-route">${esc(route)}</span>${altitude?`<small>${esc(altitude)}</small>`:''}</span>`}
function renderTickerLane(id,prefix,items,compact=false){
 const element=$(id),button=$(prefix+'-open');if(!element||!button)return;
 element._items=()=>tickerItems().filter(item=>(item.kind==='flight')===compact);setupTickerSwipe(element);
 element.hidden=!items.length;
 if(!items.length){element._cancelSwipe?.();delete element._topId;button.textContent='';element._markup='';return}
 const item=items[0],changed=element._topId&&element._topId!==item.id;if(changed)element._cancelSwipe?.();element._topId=item.id;
 element.className=(compact?'flight-ticker':'live-ticker notification-banner')+' card-stack '+notificationClass(item)+(changed?' is-revealing':'');
 element.dataset.stacked=String(items.length>1);element.dataset.depth=String(Math.min(items.length-1,2));
 const peeks=$(prefix+'-peeks'),preview=items.slice(1,3).map((next,index)=>`<span class="ticker-peek ${notificationClass(next)}" style="--depth:${index+1}"><span class="ticker-symbol">${itemIcon(next)}</span></span>`).join('');if(peeks&&peeks.innerHTML!==preview)peeks.innerHTML=preview;
 const markup=compact?flightStripMarkup(item):`<span class="ticker-symbol">${itemIcon(item)}</span><span class="ticker-copy"><span class="ticker-title">${esc(item.title)}</span><span class="ticker-message">${esc(item.message)}</span></span>`;
 if(element._markup!==markup){button.innerHTML=markup;element._markup=markup}
 button.onclick=()=>openTicker(item.id);button.setAttribute('aria-label',item.title+'. '+item.message+'. Meldingenoverzicht openen');$(prefix+'-dismiss').onclick=()=>dismissTicker(item.id);$(prefix+'-count').textContent=items.length>1?String(items.length):'';
}
function renderTicker(){
 const items=tickerItems(),primary=items.filter(item=>item.kind!=='flight'),flights=items.filter(item=>item.kind==='flight');
 window.FrameoPhotoMode?.notify('ticker',items.map(item=>item.id));
 renderTickerLane('live-ticker','ticker',primary);renderTickerLane('flight-ticker','flight',flights,true);
 const wrapper=$('header-notifications');if(wrapper){wrapper.dataset.main=String(primary.length>0);wrapper.dataset.flight=String(flights.length>0)}
 syncPhotoEdge();
}
async function loadTicker(){if(liveTicker.loading)return;liveTicker.loading=true;try{const data=await readPanelJSON('/api/ticker');liveTicker.items=data.items||[];for(const item of liveTicker.items)if(dismissedCards[item.id])dismissedCards[item.id]=item.expires_at;saveDismissedCards();liveTicker.notes=data.notes||[];liveTicker.error='';liveTicker.ready=true;liveTicker.historyAvailable=data.history_available!==false;window.FrameoSound?.observe(liveTicker.items,tickerItems())}catch(error){liveTicker.error=error.message}finally{liveTicker.loading=false;renderTicker();if(active==='notifications')draw()}}
function queueTicker(){if(tickerTimer)return;tickerTimer=setTimeout(()=>{tickerTimer=null;loadTicker()},500)}
function setupTicker(){saveDismissedCards();loadTicker();setInterval(loadTicker,10000);setInterval(renderTicker,3000)}
function setupTickerSwipe(element){
 if(element._swipeBound||!element.addEventListener)return;element._swipeBound=true;
 element.addEventListener('dragstart',event=>event.preventDefault());
 let gesture=null,lastDown=null,blockClick=false;
 const reset=()=>{element.style?.setProperty('--swipe-x','0px');element.style?.setProperty('--swipe-opacity','1');delete element.dataset.dragging};
 const moved=event=>lastDown&&(Math.abs(event.clientX-lastDown.x)>12||Math.abs(event.clientY-lastDown.y)>12);
 element._cancelSwipe=()=>{if(gesture?.dragging)blockClick=true;gesture=null;reset()};
 element.addEventListener('pointerdown',event=>{
  if(event.isPrimary===false||(event.button!==undefined&&event.button!==0))return;
  blockClick=false;lastDown={x:event.clientX,y:event.clientY};
  if(event.target.closest?.('.ticker-dismiss'))return;
  const top=(element._items?.()||tickerItems())[0];if(top)gesture={x:event.clientX,y:event.clientY,id:top.id,pointer:event.pointerId,dragging:false};
 });
 element.addEventListener('pointermove',event=>{
  if(moved(event))blockClick=true;
  if(!gesture||event.pointerId!==gesture.pointer)return;
  const dx=event.clientX-gesture.x,dy=event.clientY-gesture.y;
  if(!gesture.dragging&&Math.abs(dy)>18&&Math.abs(dy)>Math.abs(dx)){gesture=null;return}
  if(Math.abs(dx)>14&&Math.abs(dx)>Math.abs(dy)*1.3){
   gesture.dragging=true;try{element.setPointerCapture(event.pointerId)}catch{}
   element.dataset.dragging='true';element.style.setProperty('--swipe-x',dx+'px');element.style.setProperty('--swipe-opacity',String(Math.max(.4,1-Math.abs(dx)/500)));event.preventDefault();
  }
 });
 element.addEventListener('pointerup',event=>{
  if(moved(event))blockClick=true;
  if(!gesture||event.pointerId!==gesture.pointer)return;
  const g=gesture,dx=event.clientX-g.x,dy=event.clientY-g.y;gesture=null;
  const horizontal=Math.abs(dx)>14&&Math.abs(dx)>Math.abs(dy)*1.3;
  const threshold=Math.max(55,Math.min(110,(element.getBoundingClientRect?.().width||350)*.18));
  reset();if(horizontal){blockClick=true;event.preventDefault();if(Math.abs(dx)>=threshold&&(element._items?.()||tickerItems())[0]?.id===g.id)dismissTicker(g.id)}
 });
 element.addEventListener('pointercancel',()=>{blockClick=true;gesture=null;reset()});
 element.addEventListener('lostpointercapture',()=>{if(gesture){if(gesture.dragging)blockClick=true;gesture=null;reset()}});
 element.addEventListener('click',event=>{
  // Keep suppression until the next deliberate pointerdown; delayed compatibility
  // clicks and a replaced top card must never turn a swipe into navigation.
  if(event.detail!==0&&(blockClick||moved(event))){event.preventDefault();event.stopImmediatePropagation()}
 },true);
}

function setNotificationView(view){notificationView=view;if(view==='history'&&!notificationHistory.ready)loadNotificationHistory(true);draw()}
function toggleNotificationFilter(key){if(!(key in notificationFilters))return;notificationFilters[key]=!notificationFilters[key];try{localStorage.setItem('homehub-notification-filters',JSON.stringify(notificationFilters))}catch{}renderTicker();if(notificationView==='history')loadNotificationHistory(true);draw()}
async function loadNotificationHistory(reset=false){if(notificationHistory.loading&&!reset)return;const request=notificationHistory.request+1,cursor=reset?null:notificationHistory.next;notificationHistory.request=request;notificationHistory.loading=true;notificationHistory.error='';if(reset){notificationHistory.items=[];notificationHistory.next=null}if(active==='notifications')draw();try{const categories=Object.keys(notificationFilters).filter(key=>notificationFilters[key]).concat('other').join(','),params=new URLSearchParams({categories,limit:'50'});if(cursor)params.set('before',cursor);const data=await readPanelJSON('/api/ticker/history?'+params);if(request!==notificationHistory.request)return;notificationHistory.items=[...new Map([...notificationHistory.items,...(data.items||[])].map(item=>[item.id,item])).values()];notificationHistory.next=data.next;notificationHistory.ready=true}catch(error){if(request===notificationHistory.request)notificationHistory.error=error.message}finally{if(request===notificationHistory.request){notificationHistory.loading=false;if(active==='notifications')draw()}}}
function refreshNotifications(){return notificationView==='history'?loadNotificationHistory(true):loadTicker()}
function notificationCard(item,historical=false,compact=false){const original=item.original_id||item.id,expired=Date.parse(item.expires_at)<=(globalThis.FrameoClock?.now()??Date.now()),status=historical?`<small class="notification-state">${expired?'Verlopen':dismissedCards[original]?'Weggeveegd':liveTicker.items.some(row=>row.id===original&&(!row.history_id||row.history_id===item.id))?'Actueel':'Opgeslagen'}</small>`:'',close=historical?'':`<button class="notification-dismiss" onclick="dismissTicker('${esc(item.id)}')" aria-label="Melding wegklikken">×</button>`;return `<section class="panel notification-card ${notificationClass(item)}${item.kind==='energy'&&notificationKnown(item)?' notification-known':''}"><div class="notification-heading">${itemIcon(item)}<h2>${esc(item.title)}</h2>${status}${item.kind==='energy'&&notificationKnown(item)?'<small class="notification-state">Bekend</small>':''}${close}</div>${item.flight?`<div class="flight-detail-route">${flightRoute(item.flight)}</div><p class="${compact?'flight-compact-meta':''}">${esc(compact?[flightMeta(item.flight),item.flight.airline].filter(Boolean).join(' · '):flightMeta(item.flight))}</p>${compact?'':`<p>${esc(item.flight.airline||'Maatschappij onbekend')}</p>`}`:`<p>${esc(item.message)}</p>`}<small class="muted">${esc(historical?new Date(item.time).toLocaleString('nl-NL',{timeZone:typeof detailZone==='function'?detailZone():'Europe/Amsterdam',day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}):timeTitle(item.time))}${item.distance_km!==undefined?' · '+detailNumber(item.distance_km,'km',1):''}</small><div class="notification-card-actions"><a class="notification-more" href="/meldingen/${encodeURIComponent(item.id)}"${item.kind==='energy'?` onclick="markNotificationSeen('${esc(original)}')"`:''}>Bekijk details ›</a>${item.kind==='energy'&&!notificationKnown(item)?`<button class="notification-ack" onclick="markNotificationSeen('${esc(original)}')">Begrepen ✓</button>`:''}</div></section>`}
function notificationColumns(items,historical){
 const main=items.filter(item=>item.kind!=='flight').sort(notificationOrder),flights=items.filter(item=>item.kind==='flight');
 const primary=`<section class="notification-primary" aria-label="Overige meldingen"><div class="notification-column-title"><h2>Meldingen</h2><span>${main.length}</span></div>${main.length?main.map(item=>notificationCard(item,historical)).join(''):'<p class="muted notification-empty">Geen overige meldingen met deze filters.</p>'}</section>`;
 const secondary=flights.length?`<aside class="notification-flights" aria-label="Vliegtuigmeldingen"><div class="notification-column-title"><h2>Vliegtuig</h2><span>${flights.length}</span></div>${flights.map(item=>notificationCard(item,historical,true)).join('')}</aside>`:'';
 return `<div class="notification-columns${flights.length?'':' no-flights'}">${primary}${secondary}</div>`;
}
function drawNotifications(){if($('title'))$('title').textContent='Meldingen';const historical=notificationView==='history',items=historical?notificationHistory.items.filter(notificationMatches):tickerItems(),error=historical?notificationHistory.error:liveTicker.error;return `<div class="detail-toolbar"><div class="notification-tabs" role="group" aria-label="Meldingenweergave"><button onclick="setNotificationView('current')" aria-pressed="${!historical}">Actueel</button><button onclick="setNotificationView('history')" aria-pressed="${historical}">Historie</button></div><button onclick="refreshNotifications()">Vernieuwen</button></div><div class="notification-filters" role="group" aria-label="Filter meldingen">${[['grip','GRIP'],['fire','Brandweer'],['ambulance','Ambulance'],['flight','Vliegtuig'],['aurora','Noorderlicht'],['sites','Websites'],['energy','Laadmoment'],['air','Luchten'],['laundry','Wasgoed'],['fault','Storingen']].map(([key,label])=>`<button class="filter-${key}" onclick="toggleNotificationFilter('${key}')" aria-pressed="${notificationFilters[key]}">${esc(label)}</button>`).join('')}</div><p class="notification-filter-note">Filters gelden ook voor de kaarten op Home.${historical?' Ook weggeveegde en verlopen kaarten blijven hier staan.':' Swipe een kaart naar links of rechts om hem weg te leggen.'}</p>${error?`<p class="detail-error">${esc(error)}</p>`:''}${liveTicker.historyAvailable===false?'<p class="detail-error">Historie opslaan lukt momenteel niet.</p>':''}${items.length?notificationColumns(items,historical):`<div class="panel">${historical&&notificationHistory.loading?'Historie ophalen…':historical?'Geen meldingen in de historie met deze filters.':'Geen actuele meldingen met deze filters.'}</div>`}${historical&&notificationHistory.next?`<button class="history-more" onclick="loadNotificationHistory()" ${notificationHistory.loading?'disabled':''}>${notificationHistory.loading?'Laden…':'Meer meldingen'}</button>`:''}<details class="panel notification-sources"><summary>Bronnen en bewaartijd</summary><p class="muted">Actuele kaarten: brandweer en ambulance 10 minuten, GRIP 30 minuten en vliegtuigen tot 5 minuten na de laatste waarneming. Daarna blijven ze in de historie. Alleen ontvangen meldingen worden bewaard.</p>${liveTicker.notes.map(note=>`<p class="muted">${esc(note.source)}: ${esc(note.status)}</p>`).join('')}</details><button class="management-link" onclick="openPanel('manage')">Beheer ›</button>`}
