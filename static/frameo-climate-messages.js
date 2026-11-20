/* Status feedback only: timer minutes, not fan speed. Never changes devices. */
(function(root){
 const previous=new Map(),recent=new Map();let online=false;
 const presets={timer1:10,timer2:20,timer3:30},modes={cool:'Koelen',heat:'Verwarmen',dry:'Ontvochtigen',fan_only:'Ventileren',heat_cool:'Automatisch',auto:'Automatisch'};
 const now=()=>root.FrameoClock?.now?.()??Date.now();
 function emit(notices){
  notices=notices.filter(n=>{if(now()-(recent.get(n.key)??-Infinity)<5000)return false;recent.set(n.key,now());return true});if(!notices.length)return;
  const n=notices.length===1?notices[0]:{icon:'airco',title:'Klimaat bijgewerkt',text:notices.map(n=>n.title+' · '+n.text).join('\n')};
  root.FrameoMessage?.show({...n,color:'#75bed8',duration:8});root.FrameoLED?.screen?.(true)?.catch(()=>{});
 }
 function fanNotice(key){const minutes=({fan_timer_10:10,fan_timer_20:20,fan_timer_30:30})[key];return minutes?{key:'fan:'+minutes,icon:'fan',badge:minutes+' min',title:'Ventilatietimer aan',text:minutes+' minuten ventileren.'}:{key:'fan:off',icon:'fan-off',title:'Ventilatietimer uit',text:'Ventilatie terug naar de basisstand.'}}
 function update(states,config,live){
  if(!live){previous.clear();online=false;return}const notices=[],fanId=config.ventilation_entity,row=states[fanId],valid=row&&!['unknown','unavailable'].includes(row.state);
  if(valid){const state=row.state==='off'?'off':row.attributes?.preset_mode||'on',old=previous.get(fanId);previous.set(fanId,state);
   if(online&&old!==undefined&&old!==state){if(presets[state])notices.push(fanNotice('fan_timer_'+presets[state]));else if(state==='off'||presets[old])notices.push(fanNotice('fan_off'));else notices.push({key:'fan:'+state,icon:'fan',title:'Ventilatie aan',text:({low:'Basisstand',medium:'Middenstand',high:'Hoge stand',auto:'Automatisch',autonight:'Automatische nachtstand'})[state]||'Ventilatiestand gewijzigd.'})}
  }else if(fanId)previous.delete(fanId);
  for(const [label,id] of Object.entries(config.dashboard?.airco_entities||{})){
   const row=states[id];if(!row||['unknown','unavailable'].includes(row.state)){previous.delete(id);continue}
   const value={state:row.state,temp:row.attributes?.temperature},old=previous.get(id);previous.set(id,value);
   if(!online||!old||old.state===value.state&&(value.state==='off'||old.temp===value.temp))continue;
   const off=value.state==='off',temp=typeof value.temp==='number'&&Number.isFinite(value.temp)?value.temp.toLocaleString('nl-NL')+' °C':'';
   notices.push({key:id+':'+value.state+':'+value.temp,icon:off?'airco-off':'airco',badge:off?'Uit':temp,title:label+(off?' uit':old.state==='off'?' aan':''),text:off?'Airco uitgeschakeld.':[(modes[value.state]||value.state),temp].filter(Boolean).join(' · ')});
  }
  online=true;emit(notices);
 }
 root.FrameoClimateMessages={update,ventilationCommand(key){emit([fanNotice(key)])}};
})(globalThis);
