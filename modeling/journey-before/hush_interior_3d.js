import * as THREE from './three.module.min.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

// Blender-authored room. Entrance is behind the camera, reception ahead.
const canvas = document.getElementById('interior3d');
if (canvas) {
  const host = canvas.closest('section') || canvas.parentElement;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#33271d');
  const camera = new THREE.PerspectiveCamera(76, 1, .05, 35);
  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: true});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x33271d, 1);
  scene.add(new THREE.HemisphereLight(0xffe6c2, 0x66503b, 1.5));
  const windowLight = new THREE.DirectionalLight(0xffd59b, 2.6);
  windowLight.position.set(-3.4, 4, -.1);
  windowLight.target.position.set(.8, .2, -.8);
  windowLight.castShadow = true;
  windowLight.shadow.mapSize.set(2048, 2048);
  Object.assign(windowLight.shadow.camera, {left:-5,right:5,top:5,bottom:-5,near:.1,far:16});
  windowLight.shadow.bias = -.00025;
  windowLight.shadow.normalBias = .025;
  windowLight.shadow.radius = 3;
  scene.add(windowLight, windowLight.target);
  const fill = new THREE.DirectionalLight(0xffe6cc, 1.2);
  fill.position.set(1, 4, 4);
  scene.add(fill);
  const candle = new THREE.PointLight(0xffab52, 1.7, 3, 2);
  candle.position.set(1.98, 2.68, -2.40);
  scene.add(candle);

  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const hitVolumes = [];
  let room, active = false, frame = 0, start = 0, yaw = 0, targetYaw = 0;
  const base = new THREE.Vector3(1.15, 2.15, 3.9);
  const look = new THREE.Vector3(-.15, 1.05, -1.25);
  let resolveReady;
  window.hushInteriorReady = new Promise(resolve => { resolveReady = resolve; });
  const markReady = ok => {
    canvas.dataset.ready = ok ? 'true' : 'fallback';
    resolveReady(ok);
  };
  new GLTFLoader().load(new URL('./assets/models/hush-inn-interior.glb?v=20260907-baked' , import.meta.url).href, gltf => {
    room = gltf.scene;
    room.traverse(o => {
      if (!o.isMesh) return;
      o.castShadow = o.receiveShadow = !o.userData.bakedLighting;
      if (o.userData.bakedLighting) o.material.emissive.setRGB(1, .90, .76);
      if (o.material.map) o.material.map.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    });
    scene.add(room);
    // Whole-object hit volumes include decorative metal plates and paper edges.
    // Compare their ray distances with the room so furniture still occludes them.
    for (const [go,position,size,angle] of [
      ['book',[.68,1.34,-.43],[.81,.22,.61],.13],
      ['book',[-1.9,1.15,-.08],[.75,.13,.51],0],
      ['post',[-.73,.61,-2.2],[1.08,1.2,.80],0]
    ]) {
      const volume = new THREE.Mesh(new THREE.BoxGeometry(...size), new THREE.MeshBasicMaterial());
      volume.position.set(...position); volume.rotation.y=angle;
      volume.userData.go=go; volume.updateMatrixWorld(true);
      hitVolumes.push(volume);
    }
    if (room.getObjectByProperty('isMesh', true)?.userData.bakedLighting) renderer.shadowMap.enabled = false;
    renderer.compile(scene, camera);
    markReady(true);
    if (active) start = performance.now();
  }, undefined, error => {
    console.error('Hush interior model failed to load', error);
    canvas.style.opacity = '0';
    canvas.style.animation = 'none';
    host.dataset.modelError = 'true';
    markReady(false);
  });

  function resize() {
    const {width, height} = canvas.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    // Maintain the doorway's horizontal field of view on tall phone screens.
    camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(64)/2) / Math.min(camera.aspect, 1)));
    camera.updateProjectionMatrix();
  }
  const resizer = new ResizeObserver(resize);
  resizer.observe(canvas);
  function draw(now) {
    if (!active) return;
    const progress = reduced ? 1 : THREE.MathUtils.smoothstep((now-start)/2200, 0, 1);
    yaw += (targetYaw-yaw)*.07;
    camera.position.copy(base);
    camera.position.z += (1-progress)*.16;
    camera.position.x += yaw*.3;
    camera.lookAt(look.x+yaw, look.y, look.z);
    candle.intensity = reduced ? 1.7 : 1.7 + Math.sin(now*.0027)*.07 + Math.sin(now*.0053)*.035;
    renderer.render(scene, camera);
    frame = requestAnimationFrame(draw);
  }
  function sync() {
    const next = !document.hidden && (host.classList.contains('on') || host.dataset.preview === 'true');
    if (next === active) return;
    active = next;
    cancelAnimationFrame(frame);
    if (active) { start = performance.now(); resize(); frame = requestAnimationFrame(draw); }
  }
  new MutationObserver(sync).observe(host, {attributes:true, attributeFilter:['class','data-preview']});
  document.addEventListener('visibilitychange', sync);
  let down = null;
  canvas.addEventListener('pointerdown', e => {
    down = {x:e.clientX,y:e.clientY,yaw:targetYaw};
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointermove', e => {
    if (!down) return;
    targetYaw = THREE.MathUtils.clamp(down.yaw-(e.clientX-down.x)*.003, -.24, .24);
  });
  canvas.addEventListener('pointerup', e => {
    const tap = down && Math.hypot(e.clientX-down.x,e.clientY-down.y)<6;
    down = null;
    if (canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
    if (!tap || !room) return;
    const r=canvas.getBoundingClientRect();
    const ray=new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1),camera);
    // Raycast all geometry so hidden objects cannot be clicked through walls.
    const hit=ray.intersectObjects([room,...hitVolumes],true)[0];
    if(hit?.object.userData.go) window.go?.(hit.object.userData.go);
  });
  canvas.addEventListener('pointercancel', () => {down=null;});
  resize(); sync();
}
