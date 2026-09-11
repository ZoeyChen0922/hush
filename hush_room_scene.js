import * as THREE from './three.module.min.js';
import {GLTFLoader} from './vendor/GLTFLoader.js';

export function mountRoom(canvas,{phase='night',eager=false}={}) {
  if(!canvas)return null;
  const host=canvas.closest('section'),day=phase==='day',reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  canvas.dataset.phase=phase;
  let renderer;
  try { renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true}); }
  catch(error){canvas.style.display='none';canvas.dataset.ready='fallback';return {load:()=>Promise.resolve(false)};}
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.75));
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.AgXToneMapping;renderer.toneMappingExposure=day?1:1.1;
  const scene=new THREE.Scene();scene.background=new THREE.Color(day?'#ad9777':'#100f1c');
  const camera=new THREE.PerspectiveCamera(75,1,.05,35);
  // Both versions occupy exactly the same space and use the same doorway camera.
  const base=new THREE.Vector3(1.15,2.15,3.9),look=new THREE.Vector3(-.15,1.05,-1.25);
  // Day room only: the model ends right behind the doorway (z≈3.95), so the view turns in place
  // within these limits and walks along one doorway→counter path instead of roaming freely.
  const inner=new THREE.Vector3(.55,1.85,1.45),innerLook=new THREE.Vector3(0,1.3,-1.6);
  const stands={diary:[-1.2,1.95,1.35],letters:[-.55,1.8,.3],tarot:[1,2.4,-.3],all:[.55,2.05,1.05],sleep:[1.35,2.05,.95]};
  const YAW=THREE.MathUtils.degToRad(35),PITCH=THREE.MathUtils.degToRad(12),clamp=THREE.MathUtils.clamp;
  scene.add(new THREE.HemisphereLight(day?0xffecd1:0xffbe75,0x26334c,day?2:.7));
  const objects=new THREE.Group();scene.add(objects);
  let room,loading,active=false,frame=0,start=0,yaw=0,targetYaw=0,down=null,dragged=false;
  let pitch=0,targetPitch=0,walk=0,targetWalk=0,tween=null,focused=null,pinch=0;
  const pointers=new Map(),cur={pos:base.clone(),target:look.clone()},up=new THREE.Vector3(0,1,0);
  const volumes=[],anchors=[];
  const locations=[
    ['diary',[-1.90,1.24,-.08],[.80,.24,.58],0,'Night diary'],
    ['letters',[-.73,.85,-2.2],[1.10,1.30,.82],0,'Letters'],
    ['tarot',[1.03,2.59,-2.49],[.38,.60,.15],0,'Tarot reading'],
    ['all',[.68,1.34,-.43],[.82,.23,.63],.13,'Last night'],
    ['sleep',[1.62,1.45,-.55],[.34,.34,.34],0,'Hours open']
  ];
  if(day && host.querySelector('.room-hotspots')) for(const [kind,position,size,angle,label] of locations){
    const volume=new THREE.Mesh(new THREE.BoxGeometry(...size),new THREE.MeshBasicMaterial());volume.position.set(...position);volume.rotation.y=angle;volume.userData.review=kind;volume.updateMatrixWorld();volumes.push(volume);
    const b=document.createElement('button');b.className='room-hotspot';b.hidden=true;b.dataset.review=kind;b.type='button';b.setAttribute('aria-label',label);b.onclick=()=>focusOn(kind);host.querySelector('.room-hotspots').appendChild(b);
    anchors.push({kind,position:new THREE.Vector3(...position),button:b,label});
  }
  function texture(draw){const c=document.createElement('canvas');c.width=512;c.height=512;draw(c.getContext('2d'));const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;}
  function addBox(size,position,color){const m=new THREE.Mesh(new THREE.BoxGeometry(...size),new THREE.MeshStandardMaterial({color,roughness:.82}));m.position.set(...position);objects.add(m);return m;}
  function clearObjects(){objects.traverse(o=>{if(o.isMesh){o.geometry.dispose();o.material.map?.dispose();o.material.dispose();}});objects.clear();}
  function refresh(){
    if(!day)return;
    clearObjects();
    const data=window.HushJourney?.records()||{diary:[],letters:[],tarot:[],conversation:[],mood:[],all:[]};
    const counts={diary:data.diary.length,letters:data.letters.length,tarot:data.tarot.length,mood:data.mood.length,all:data.all.length};
    const hrs=window.HushJourney?.hours?.();
    for(const a of anchors){
      if(a.kind==='sleep'){
        a.button.textContent=hrs?(hrs.sleepMs!=null?'Slept · ':'Inn open · ')+HushJourney.duration(hrs.sleepMs??hrs.openMs):a.label;
        a.button.dataset.empty=String(!hrs);a.button.setAttribute('aria-label',a.button.textContent);continue;
      }
      a.button.textContent=a.label+(counts[a.kind]?' · '+counts[a.kind]:'');a.button.dataset.empty=String(!counts[a.kind]);a.button.setAttribute('aria-label',`${a.label}, ${counts[a.kind]} saved ${counts[a.kind]===1?'record':'records'}`);}
    // A saved diary adds pages on the desk; envelopes only appear when written.
    for(let i=0;i<Math.min(data.diary.length,5);i++)addBox([.29,.012,.37],[-1.42,1.119+i*.014,-.55],0xdbc69b).rotation.y=-.15;
    for(let i=0;i<Math.min(data.letters.length,4);i++){
      const envelope=addBox([.35,.016,.24],[1.26,1.279+i*.022,-.85],0xe3cda6);envelope.rotation.y=.12;
      const seal=new THREE.Mesh(new THREE.CylinderGeometry(.03,.03,.009,20),new THREE.MeshStandardMaterial({color:0x983e2e,roughness:.6}));seal.position.set(1.26,1.292+i*.022,-.85);objects.add(seal);
    }
    const card=data.tarot[0],name=card?.card||card?.text?.split(' — ')[0];
    const map=texture(ctx=>{ctx.fillStyle=card?'#293f49':'#64584a';ctx.fillRect(0,0,512,512);ctx.strokeStyle='#d6b271';ctx.lineWidth=9;ctx.strokeRect(22,22,468,468);ctx.fillStyle='#ecd7a5';ctx.textAlign='center';ctx.font='150px Georgia';ctx.fillText(card?.glyph||'✦',256,245);ctx.font='30px Georgia';const words=(name||'No card drawn').split(' ');let line='',y=335;for(const word of words){if((line+' '+word).length>17){ctx.fillText(line,256,y);line=word;y+=42;}else line+=(line?' ':'')+word;}ctx.fillText(line,256,y);});
    const face=new THREE.Mesh(new THREE.PlaneGeometry(.29,.50),new THREE.MeshBasicMaterial({map}));face.position.set(1.03,2.59,-2.474);objects.add(face);
    canvas.dataset.records=JSON.stringify(counts);
  }
  function freePose(y,p,w){
    const pos=base.clone().lerp(inner,w),dir=look.clone().lerp(innerLook,w).sub(pos).normalize().applyAxisAngle(up,-y);
    dir.applyAxisAngle(new THREE.Vector3().crossVectors(dir,up).normalize(),p);
    return {pos,target:pos.clone().add(dir)};
  }
  function walkTo(to,done){tween={from:{pos:cur.pos.clone(),target:cur.target.clone()},to,t0:performance.now(),dur:950,done};}
  // Tapping an object walks up to it first; the record opens on arrival.
  function focusOn(kind){
    const a=anchors.find(x=>x.kind===kind);
    if(tween)return;
    if(!a||!room||reduced){window.openRoomRecord?.(kind);return;}
    focused=kind;walkTo({pos:new THREE.Vector3(...stands[kind]),target:a.position.clone()},()=>window.openRoomRecord?.(kind));
  }
  function load(){
    if(loading)return loading;
    canvas.dataset.ready='loading';
    loading=new Promise(resolve=>new GLTFLoader().load(new URL(`./assets/models/hush-inn-${phase}.glb?v=journey-2`,import.meta.url).href,gltf=>{
      room=gltf.scene;room.traverse(o=>{if(!o.isMesh)return;o.castShadow=o.receiveShadow=false;for(const m of [o.material].flat()){if(m.emissiveMap)m.emissiveMap.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());}});scene.add(room);refresh();canvas.dataset.ready='true';resolve(true);if(active)start=performance.now();
    },undefined,error=>{console.error(`Hush ${phase} room`,error);canvas.dataset.ready='fallback';canvas.style.opacity='0';canvas.style.animation='none';resolve(false);}));
    return loading;
  }
  function resize(){const {width,height}=canvas.getBoundingClientRect();if(!width||!height)return;renderer.setSize(width,height,false);camera.aspect=width/height;camera.fov=THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(THREE.MathUtils.degToRad(64)/2)/Math.min(camera.aspect,1)));camera.updateProjectionMatrix();}
  function draw(now){
    if(!active)return;
    if(day){
      if(tween){
        const k=Math.min(1,(now-tween.t0)/tween.dur),e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
        cur.pos.lerpVectors(tween.from.pos,tween.to.pos,e);cur.target.lerpVectors(tween.from.target,tween.to.target,e);
        if(k>=1){const done=tween.done;tween=null;done?.();}
      }else{
        yaw+=(targetYaw-yaw)*.12;pitch+=(targetPitch-pitch)*.12;walk+=(targetWalk-walk)*.1;
        const p=freePose(yaw,pitch,walk);cur.pos.copy(p.pos);cur.target.copy(p.target);
      }
      camera.position.copy(cur.pos);camera.lookAt(cur.target);
    }else{
      const progress=reduced?1:THREE.MathUtils.smoothstep((now-start)/2200,0,1);
      yaw+=(targetYaw-yaw)*.07;camera.position.copy(base);camera.position.z+=(1-progress)*.16;camera.position.x+=yaw*.3;camera.lookAt(look.x+yaw,look.y,look.z);
    }
    camera.updateMatrixWorld();
    for(const a of anchors){const p=a.position.clone().project(camera);a.button.style.left=(p.x*.5+.5)*100+'%';a.button.style.top=(-p.y*.5+.5)*100+'%';a.button.hidden=!room||!!tween||p.z>1||Math.abs(p.x)>1||Math.abs(p.y)>1;}
    renderer.render(scene,camera);frame=requestAnimationFrame(draw);
  }
  function sync(){const next=!document.hidden&&(host.classList.contains('on')||host.dataset.preview==='true');if(next===active)return;active=next;cancelAnimationFrame(frame);if(active){load();refresh();start=performance.now();resize();walkOut();frame=requestAnimationFrame(draw);}}
  // Coming back from a record walks the guest back out to the doorway.
  function walkOut(){
    if(!day||!focused)return;
    const a=anchors.find(x=>x.kind===focused);focused=null;
    yaw=targetYaw=pitch=targetPitch=walk=targetWalk=0;
    if(!a||reduced){const p=freePose(0,0,0);cur.pos.copy(p.pos);cur.target.copy(p.target);return;}
    cur.pos.set(...stands[a.kind]);cur.target.copy(a.position);walkTo(freePose(0,0,0));
  }
  new ResizeObserver(resize).observe(canvas);new MutationObserver(sync).observe(host,{attributes:true,attributeFilter:['class','data-preview']});document.addEventListener('visibilitychange',sync);
  window.addEventListener('hush:records',refresh);window.addEventListener('storage',refresh);
  const spread=()=>{const [a,b]=[...pointers.values()];return Math.hypot(a.x-b.x,a.y-b.y);};
  const release=e=>{pointers.delete(e.pointerId);if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);};
  canvas.addEventListener('pointerdown',e=>{
    pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});canvas.setPointerCapture(e.pointerId);
    if(pointers.size===1){down={x:e.clientX,y:e.clientY,yaw:targetYaw,pitch:targetPitch};dragged=false;}
    else{down=null;dragged=true;pinch=spread();}
  });
  canvas.addEventListener('pointermove',e=>{
    if(!pointers.has(e.pointerId))return;pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(pointers.size>=2){if(day&&!tween){const s=spread();targetWalk=clamp(targetWalk+(s-pinch)*.004,0,1);pinch=s;}return;}
    if(!down||tween)return;
    if(Math.hypot(e.clientX-down.x,e.clientY-down.y)>6)dragged=true;
    if(day){targetYaw=clamp(down.yaw-(e.clientX-down.x)*.004,-YAW,YAW);targetPitch=clamp(down.pitch+(e.clientY-down.y)*.004,-PITCH,PITCH);}
    else targetYaw=clamp(down.yaw-(e.clientX-down.x)*.003,-.25,.25);
  });
  canvas.addEventListener('pointerup',e=>{
    const tap=down&&!dragged&&pointers.size===1;release(e);down=null;
    if(!tap||!day||!room||tween)return;
    const r=canvas.getBoundingClientRect(),ray=new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1),camera);
    const kind=ray.intersectObjects(volumes,false)[0]?.object.userData.review;if(kind)focusOn(kind);
  });
  canvas.addEventListener('pointercancel',e=>{release(e);down=null;});
  if(day){
    canvas.addEventListener('wheel',e=>{e.preventDefault();if(!tween)targetWalk=clamp(targetWalk-e.deltaY*.0015,0,1);},{passive:false});
    canvas.tabIndex=0;
    canvas.addEventListener('keydown',e=>{
      if(tween)return;const k=e.key.toLowerCase();
      if(k==='arrowleft'||k==='a')targetYaw=clamp(targetYaw-.1,-YAW,YAW);
      else if(k==='arrowright'||k==='d')targetYaw=clamp(targetYaw+.1,-YAW,YAW);
      else if(k==='arrowup'||k==='w')targetWalk=clamp(targetWalk+.12,0,1);
      else if(k==='arrowdown'||k==='s')targetWalk=clamp(targetWalk-.12,0,1);
      else return;
      e.preventDefault();
    });
  }
  resize();sync();if(eager)load();return{load,refresh};
}
