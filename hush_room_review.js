/* Morning is a read-only view of a completed stay, never a new tarot draw. */
function renderMorningRoom(){
  const data=HushJourney.records(),stay=data.stay;
  const host=stay?.hostName||innName();
  const h=stay&&HushJourney.hours(stay),slept=h&&h.sleepMs!=null;
  document.getElementById('morning-host').textContent=!stay?'Your morning room.':slept?`You slept ${HushJourney.duration(h.sleepMs)}.`:host+' kept these for you.';
  document.getElementById('morning-note').textContent=!stay?'Your room is quiet. A completed night will appear here after you wake.'
    :slept?`${host} kept the inn open from ${clockTime(h.sleepingAt)} to ${clockTime(h.endedAt)}. Tap the objects to revisit your night.`
    :'Tap the objects to revisit your night.';
  document.getElementById('open-duration').textContent=h?'Open '+HushJourney.duration(h.sleepMs??h.openMs):'';
  const sb=document.querySelector('.morning-links [data-record="sleep"]');
  if(sb){sb.hidden=!h;if(h)sb.textContent=(slept?'Slept · ':'Open · ')+HushJourney.duration(h.sleepMs??h.openMs);}
  const picker=document.getElementById('stay-picker');picker.replaceChildren();
  for(const s of HushJourney.sessions().filter(s=>s.endedAt)){
    const option=document.createElement('option');option.value=s.id;option.textContent=new Date(s.startedAt).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'})+' · '+s.hostName;option.selected=s.id===stay?.id;picker.appendChild(option);
  }
  picker.hidden=picker.options.length<2;
  for(const [kind,label,items] of [['diary','Diary',data.diary],['letters','Letters',data.letters],['tarot','Tarot',data.tarot],['all','Night recap',data.all]]){
    const b=document.querySelector(`.morning-links [data-record="${kind}"]`);if(b)b.textContent=label+' · '+items.length;
  }
  dispatchEvent(new Event('hush:records'));
}
function selectMorningStay(id){HushJourney.select(id);renderMorningRoom();}
let roomRecordKind='all';
function openRoomRecord(kind){roomRecordKind=kind;go('roomrecord');renderRoomRecord();}
function renderRoomRecord(){
  const d=HushJourney.records();
  const labels={diary:'Your night diary',letters:'Letters you kept',tarot:'Your saved card',all:'What happened last night',mood:'Sounds & moods',sleep:'How long the inn stayed open'};
  document.getElementById('record-title').textContent=labels[roomRecordKind]||labels.all;
  const meta=document.getElementById('record-meta');meta.textContent=d.stay?new Date(d.stay.startedAt).toLocaleDateString(undefined,{month:'long',day:'numeric',year:'numeric'})+' · kept by '+d.stay.hostName:'No completed night yet';
  const panel=document.getElementById('roomrecord-list');panel.replaceChildren();
  if(roomRecordKind==='sleep'){renderSleepRecord(d.stay,panel);return;}
  let records=roomRecordKind==='letters'?d.letters:roomRecordKind==='all'?d.all:d[roomRecordKind]||[];
  if(!records.length){const p=document.createElement('p');p.className='empty';p.textContent={diary:'You did not keep a diary entry during this stay.',letters:'No letters were sealed during this stay.',tarot:'You did not draw a card during this stay. Nothing new is drawn here.',mood:'No sound or mood was kept during this stay.',all:'There are no saved activities from this stay. Rest was enough.'}[roomRecordKind];panel.appendChild(p);return;}
  records=[...records].sort((a,b)=>a.ts-b.ts);
  for(const item of records){
    const entry=document.createElement('article');entry.className='entry';
    const time=document.createElement('div');time.className='d';
    const kind=item.kind||'letter';const names={diary:'Diary',letter:'Letter',tarot:'Tarot',mood:'Sound & mood',conversation:item.role==='host'?(d.stay?.hostName||'Fox'):'You'};
    time.textContent=(names[kind]||kind)+' · '+(item.ts?new Date(item.ts).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}):item.date||'');entry.appendChild(time);
    if(kind==='tarot'&&item.card){const name=document.createElement('h2');name.className='saved-card-title';name.textContent=(item.glyph||'✦')+' '+item.card;entry.appendChild(name);}
    const body=document.createElement('div');body.className='tx';body.style.whiteSpace='pre-wrap';body.textContent=(kind==='tarot'&&item.reading)||item.text;entry.appendChild(body);
    if(item.reply){const reply=document.createElement('div');reply.className='tx host-kept-reply';reply.style.whiteSpace='pre-wrap';reply.textContent=(d.stay?.hostName||'Your host')+': '+item.reply;entry.appendChild(reply);}
    if(roomRecordKind==='letters'){const status=document.createElement('div');status.className='d';status.textContent=item.sent?'Previously marked as sent':'Sealed · kept from this night';entry.appendChild(status);}
    panel.appendChild(entry);
  }
}
function clockTime(t){return new Date(t).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});}
function renderSleepRecord(stay,panel){
  const h=stay&&HushJourney.hours(stay);
  if(!h){const p=document.createElement('p');p.className='empty';p.textContent='No completed night yet.';panel.appendChild(p);return;}
  const rows=[
    ['The lamps were lit',h.startedAt,'You opened the inn and stepped inside.'],
    h.sleepingAt&&['You said goodnight',h.sleepingAt,'From here, the inn kept its hours for you.'],
    ['You woke · the inn closed',h.endedAt,h.sleepingAt?`You slept ${HushJourney.duration(h.sleepMs,true)}.`:`The inn was open ${HushJourney.duration(h.openMs,true)}. Goodnight was never said, so sleep was not timed.`]
  ].filter(Boolean);
  for(const [label,t,note] of rows){
    const entry=document.createElement('article');entry.className='entry';
    const d=document.createElement('div');d.className='d';d.textContent=label+' · '+clockTime(t);
    const tx=document.createElement('div');tx.className='tx';tx.textContent=note;
    entry.append(d,tx);panel.appendChild(entry);
  }
}
function returnToNightLobby(){go('arrival');syncArrival();}
function showWakeGreeting(){
  stopAudio();stopHubVoiceLoop();stopRoomVoice();
  document.getElementById('wake-host').textContent=innName();
  const stay=HushJourney.active(),h=stay&&HushJourney.hours(stay);
  document.getElementById('wake-message').textContent=h&&h.sleepMs!=null
    ?`Good morning. You slept ${HushJourney.duration(h.sleepMs,true)}, and I kept the inn open the whole time. Everything you left is here.`
    :"Oh, you're awake. Good morning. I've kept everything you left with me.";
  go('waking');speak(document.getElementById('wake-message').textContent);window.hushDayScene?.load();
}
async function enterMorningRoom(){
  const button=document.getElementById('morning-enter');if(button.disabled)return;
  button.disabled=true;button.textContent='Opening your room…';
  try{await Promise.race([window.hushDayScene?.load()||Promise.resolve(),new Promise(r=>setTimeout(r,8000))]);HushJourney.wake();go('dayroom');}
  finally{button.disabled=false;button.textContent='Close the inn and look around';}
}
