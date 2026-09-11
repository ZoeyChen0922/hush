import {mountRoom} from './hush_room_scene.js?v=journey-4';
window.hushNightScene=mountRoom(document.getElementById('interior3d'),{phase:'night',eager:true});
window.hushInteriorReady=window.hushNightScene?.load()||Promise.resolve(false);
