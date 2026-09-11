const {readFileSync}=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');
let now=1000;const memory=new Map();const storage={getItem:k=>memory.get(k)??null,setItem:(k,v)=>memory.set(k,String(v)),removeItem:k=>memory.delete(k)};
const scope={localStorage:storage,Date:{now:()=>now},Math};scope.globalThis=scope;vm.createContext(scope);vm.runInContext(readFileSync(__dirname+'/../hush_journey.js','utf8'),scope);const j=scope.HushJourney;
const first=j.begin('Fox');assert.equal(j.phase(),'night');now=2000;assert.equal(j.begin('Fox').id,first.id,'resuming must not reset night start');
storage.setItem('hush.diary',JSON.stringify([{kind:'diary',text:'first night',ts:2100,sessionId:first.id},{kind:'tarot',card:'The Star',reading:'Keep going',ts:2200,sessionId:first.id}]));
storage.setItem('hush.letters',JSON.stringify([{text:'Sealed letter',ts:2300,sessionId:first.id}]));
now=3000;j.sleep();assert.equal(j.phase(),'sleeping');assert.equal(j.selected(),null,'sleep is not morning');
now=4000;j.wake();assert.equal(j.phase(),'day');assert.equal(j.records().tarot[0].card,'The Star');assert.equal(j.records().letters.length,1);assert.equal(j.active(),null);
now=5000;const second=j.begin('Fox');assert.notEqual(second.id,first.id);assert.equal(j.sessions().length,2);assert.equal(j.records().diary[0].text,'first night','new night does not erase completed archive');
now=6000;j.sleep();now=7000;j.wake();assert.equal(j.records().all.length,0,'empty second night does not borrow old entries');
j.select(first.id);assert.equal(j.records().tarot[0].reading,'Keep going','reviewing never redraws tarot');assert.equal(j.records().stay.id,first.id);
const ended=j.latest().endedAt;now=9000;j.wake();assert.equal(j.latest().endedAt,ended,'repeat wake is idempotent');
// Legacy records migrate by original time window; do not fabricate or discard content.
memory.clear();storage.setItem('hush.phase','day');storage.setItem('hush.openedAt','1000');storage.setItem('hush.closedAt','4000');storage.setItem('hush.diary',JSON.stringify([{kind:'diary',text:'legacy',ts:2000},{kind:'diary',text:'older',ts:500}]));j.migrate();assert.equal(j.records().diary.length,1);assert.equal(j.records().diary[0].text,'legacy');
console.log('PASS: resume, sleep/wake, per-night records, saved tarot, archive selection, empty stay, idempotent wake, legacy migration');
