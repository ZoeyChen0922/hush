/* One saved stay per night. Local records keep their existing schema and gain a sessionId. */
(function (root) {
  const read = (key, fallback) => { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } };
  const save = (key, value) => localStorage.setItem(key, JSON.stringify(value));
  const sessions = () => read('hush.sessions', []);
  const phase = () => localStorage.getItem('hush.phase') || 'arrival';
  const active = () => sessions().find(s => s.id === localStorage.getItem('hush.activeSession') && !s.endedAt) || null;
  function begin(hostName) {
    const current=active();
    if(current && ['night','sleeping'].includes(phase())) { localStorage.setItem('hush.phase','night');return current; }
    const startedAt=Date.now(),stay={id:'night-'+startedAt+'-'+Math.random().toString(36).slice(2,8),startedAt,hostName,endedAt:null,checkinComplete:false};
    save('hush.sessions',[stay,...sessions()]);localStorage.setItem('hush.activeSession',stay.id);
    localStorage.setItem('hush.openedAt',String(startedAt));localStorage.removeItem('hush.closedAt');localStorage.setItem('hush.phase','night');return stay;
  }
  function update(id, patch) { const all=sessions(),stay=all.find(s=>s.id===id);if(stay){Object.assign(stay,patch);save('hush.sessions',all);}return stay; }
  function sleep(){const stay=active();if(stay){update(stay.id,{sleepingAt:Date.now()});localStorage.setItem('hush.phase','sleeping');}return stay;}
  function wake(){
    let stay=active();
    if(!stay) return latest();
    const endedAt=Date.now();stay=update(stay.id,{endedAt});
    localStorage.setItem('hush.closedAt',String(endedAt));localStorage.setItem('hush.phase','day');localStorage.setItem('hush.reviewSession',stay.id);return stay;
  }
  // The inn's open hours are the guest's sleep: goodnight (sleepingAt) → waking (endedAt).
  function hours(stay=selected()){
    if(!stay)return null;
    const end=stay.endedAt||Date.now();
    return {startedAt:stay.startedAt,sleepingAt:stay.sleepingAt||null,endedAt:stay.endedAt||null,
      openMs:end-stay.startedAt,sleepMs:stay.sleepingAt?end-stay.sleepingAt:null};
  }
  function duration(ms,spoken){
    const m=Math.max(0,Math.round(ms/60000)),h=Math.floor(m/60),r=m%60;
    if(spoken){
      if(m<1)return 'less than a minute';
      const hs=h?`${h} hour${h===1?'':'s'}`:'',ms_=r?`${r} minute${r===1?'':'s'}`:'';
      return [hs,ms_].filter(Boolean).join(' and ');
    }
    if(m<1)return '<1m';
    return h?`${h}h ${r}m`:`${r}m`;
  }
  function latest(){return sessions().find(s=>s.endedAt)||null;}
  function selected(){const all=sessions().filter(s=>s.endedAt);return all.find(s=>s.id===localStorage.getItem('hush.reviewSession'))||all[0]||null;}
  function select(id){if(sessions().some(s=>s.id===id&&s.endedAt))localStorage.setItem('hush.reviewSession',id);return selected();}
  function belongs(record,stay){if(!stay)return false;if(record.sessionId)return record.sessionId===stay.id;return Number(record.ts)>=stay.startedAt&&Number(record.ts)<=stay.endedAt;}
  function records(stay=selected()){
    const diary=read('hush.diary',[]).filter(e=>belongs(e,stay));
    const letters=read('hush.letters',[]).map((e,index)=>({...e,sourceIndex:index})).filter(e=>belongs(e,stay));
    return {stay,diary:diary.filter(e=>e.kind==='diary'),tarot:diary.filter(e=>e.kind==='tarot'),conversation:diary.filter(e=>e.kind==='conversation'),mood:diary.filter(e=>e.kind==='mood'),letters,all:diary};
  }
  function migrate(){
    if(sessions().length)return;
    const startedAt=Number(localStorage.getItem('hush.openedAt'));
    if(!startedAt)return;
    const endedAt=phase()==='day'?(Number(localStorage.getItem('hush.closedAt'))||Date.now()):null;
    const stay={id:'legacy-'+startedAt,startedAt,endedAt,hostName:localStorage.getItem('hush.innname')||'Fox',checkinComplete:false};
    save('hush.sessions',[stay]);localStorage.setItem('hush.activeSession',stay.id);if(endedAt)localStorage.setItem('hush.reviewSession',stay.id);
  }
  root.HushJourney={sessions,phase,active,begin,update,sleep,wake,latest,selected,select,records,migrate,hours,duration};
})(typeof window==='undefined'?globalThis:window);
