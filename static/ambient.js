/* Pure notification arbitration and a display-only lunar approximation. No device writes. */
(function(root){
 const phases=['Nieuwe maan','Wassende sikkel','Eerste kwartier','Wassende maan','Volle maan','Afnemende maan','Laatste kwartier','Afnemende sikkel'];
 const keys=['new_moon','waxing_crescent','first_quarter','waxing_gibbous','full_moon','waning_gibbous','last_quarter','waning_crescent'];
 function moon(now,source){
  const known=keys.indexOf(source?.state);
  const cycle=29.530588853,days=(new Date(now).getTime()-Date.UTC(2000,0,6,18,14))/86400000;
  const phase=((days/cycle)%1+1)%1,index=known>=0?known:Math.round(phase*8)%8;
  return {index,label:phases[index],phase:known>=0?index/8:phase,approximate:known<0};
 }
 function notifications(states,c={},live=true){
  const settings=c.notifications||{},garage=settings.garage_entity||'';
  const raw=garage?states[garage]?.state:'off',open=['on','open','opening','closing'].includes(raw),known=['on','off','open','closed','opening','closing'].includes(raw);
  const trash=states[settings.trash_entity||c.trash]?.state;
  const handled=states[settings.handled_entity||'input_boolean.example_waste_handled']?.state==='on';
  const valid=!handled&&typeof trash==='string'&&!['none','geen','unknown','unavailable','','—','-'].includes(trash.trim().toLowerCase());
  const items=[];
  if(open)items.push({kind:'garage',label:'Garagedeur open',detail:'Controleer de garagedeur.',color:'red'});
  if(valid)items.push({kind:'trash',label:'Morgen buitenzetten',detail:trash,color:/gft|groen|bio/i.test(trash)?'green':/papier/i.test(trash)?'blue':'amber'});
  let current=items[0]||null;
  if(known&&!open&&settings.handled_entity&&!['on','off'].includes(states[settings.handled_entity]?.state))current={kind:'unknown',label:'Afvalstatus onbekend',detail:'De status van afval afgehandeld is niet beschikbaar.',color:'muted'};
  if(!known)current={kind:'unknown',label:'Garagestatus onbekend',detail:valid?'Afval morgen: '+trash:'Geen actuele garagestatus beschikbaar.',color:'muted'};
  if(!live)current={kind:'stale',label:'Status niet actueel',detail:items.length?'Laatste melding: '+items.map(i=>i.label+' · '+i.detail).join(' / '):'Verbinding met Home Assistant wordt hersteld.',color:'muted'};
  return {current,items,garageKnown:known,live};
 }
 const api={moon,notifications};if(typeof module!=='undefined')module.exports=api;else root.HubAmbient=api;
})(typeof window==='undefined'?globalThis:window);
