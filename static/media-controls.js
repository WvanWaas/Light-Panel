const extraMediaActions={};
let mediaBusy=false,mediaMessage='';
function mediaActionSpec(key){return boot.config?.actions?.[key]||extraMediaActions[key]}
function mediaDrawing(key){const speaker='<path d="M10 5 5 9H2v6h3l5 4Z"/>';const drawings={
 tv:'<rect x="2" y="4" width="20" height="14" rx="2"/><path d="M8 22h8m-4-4v4m0-15v5m-3-3a4 4 0 1 0 6 0"/>',
 tv_off:'<rect x="2" y="4" width="20" height="14" rx="2"/><path d="M8 22h8m-4-4v4m-3-11 6 6m0-6-6 6"/>',
 film_mode:'<path d="M3 9h18v11H3ZM3 9 2 4l18-3 1 5ZM7 3l3 4m4-5 3 4m-7 6 6 3-6 3Z"/>',
 bose_power:'<rect x="5" y="2" width="14" height="20" rx="3"/><path d="M12 5v5m-3-3a4 4 0 1 0 6 0"/><circle cx="12" cy="17" r="1.5"/>',
 input_tv:'<path d="M9 4h11a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9M8 22h10m-5-4v4M1 11h13m-4-4 4 4-4 4"/>',
 input_xbox:'<path d="M7 7h10c3 0 4 3 5 10 .3 3-2 4-4 1l-2-2H8l-2 2c-2 3-4 2-4-1 1-7 2-10 5-10ZM6 10v5m-2.5-2.5h5"/><circle cx="16" cy="11" r=".6"/><circle cx="19" cy="14" r=".6"/>',
 volume_down:speaker+'<path d="M15 12h7"/>',
 volume_up:speaker+'<path d="M18 8v8m-4-4h8"/>',
 mute:speaker+'<path d="m16 9 6 6m0-6-6 6"/>',
 bose_tv:'<rect x="2" y="3" width="15" height="12" rx="2"/><path d="M6 19h7m-3.5-4v4m10-12a4 4 0 0 1 0 6m2-9a8 8 0 0 1 0 12"/>',
 bose_music:'<path d="M9 17V5l12-3v12M9 9l12-3"/><ellipse cx="6" cy="18" rx="3" ry="3"/><ellipse cx="18" cy="15" rx="3" ry="3"/>',
 bose_bluetooth:'<path d="m7 7 10 10-5 5V2l5 5L7 17"/>'
 };return `<svg class="media-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${drawings[key]||drawings.tv}</svg>`}
function mediaButton(label,key,caption=label){if(!mediaActionSpec(key))return '';return `<button class="big media-control" data-media-key="${key}" onclick="runMediaAction('${key}')" aria-label="${esc(label)}" title="${esc(label)}">${mediaDrawing(key)}<span class="media-control-label">${esc(caption)}</span><small class="media-button-status"></small></button>`}
function drawMediaControls(){return `<section class="panel media-panel"><h2>TV en geluid</h2><div class="buttons media-power-grid">${mediaButton('TV aan','tv')}${mediaButton('TV uit','tv_off')}${mediaButton('Filmmodus','film_mode')}${mediaButton('Versterker aan/uit','bose_power')}</div></section><section class="panel media-panel"><h2>Beeldbron</h2><div class="buttons media-source-grid">${mediaButton('TV ingang','input_tv','TV')}${mediaButton('Xbox ingang','input_xbox','Xbox')}</div></section><section class="panel media-panel"><h2>Geluid</h2><div class="buttons media-sound-grid">${mediaButton('Volume −','volume_down','Zachter')}${mediaButton('Volume +','volume_up','Harder')}${mediaButton('Mute','mute','Stil')}${mediaButton('TV geluid','bose_tv')}${mediaButton('Muziek','bose_music')}${mediaButton('Bluetooth','bose_bluetooth')}</div></section><section class="panel"><h2>Fotolijst</h2><a class="notification-more" href="/beheer/fotolijst">Scherm, meldingen en bediening ›</a></section><p id="media-feedback" role="status"></p><p class="muted">Een scriptopdracht bevestigt dat Home Assistant de opdracht heeft ontvangen. Infraroodapparaten geven hun werkelijke stand niet altijd terug.</p>`}
function refreshMediaControls(){for(const button of document.querySelectorAll('[data-media-key]')){const spec=mediaActionSpec(button.dataset.mediaKey),state=states[spec?.entity_id],available=!!state&&!['unavailable','unknown'].includes(state.state);button.disabled=mediaBusy||!available;button.querySelector('small').textContent=!spec?'Niet gekoppeld':!available?'Niet beschikbaar':state.state==='on'&&spec.entity_id.startsWith('script.')?'Script actief':''}if($('media-feedback'))$('media-feedback').textContent=mediaMessage}
async function runMediaAction(key){if(mediaBusy)return;mediaBusy=true;mediaMessage='Opdracht versturen…';refreshMediaControls();try{await controlPost({key});mediaMessage='Opdracht ontvangen door Home Assistant.';await refreshStates()}catch(e){mediaMessage='Niet uitgevoerd: '+e.message}finally{mediaBusy=false;refreshMediaControls()}}
