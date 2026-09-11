# Hush — entrance interior

Main project: `/Users/ruohanchen/Desktop/Hush` (the running server on port 8000).

- `Hush_Inn_Interior.blend`: editable Blender 4.5 master, individual furniture, image-based wood materials, soft area lights, portrait entry camera.
- `Hush_Inn_Interior_Mobile.blend`: optimized mesh with a shared baked lighting atlas and semantic book/post hit targets.
- `../assets/models/hush-inn-interior.glb`: the real 3D model loaded by the app, including lighting texture.
- `../interior_preview.html`: persistent interactive preview without the automatic night transition.
- `hush_interior_3d.original.js` / `hush_app.original.html`: original files before this change.

## Rebuild

Run `Blender --background --python build_interior.py`, then `Blender --background --python bake_interior.py`. Blender 4.5.0 ARM64 was used. The app vendors the official Three.js r180 GLTFLoader and BufferGeometryUtils to match its existing Three.js r180 runtime; no CDN is required for the room.

## Layout and interpretation

The reference's open diorama is adapted to a doorway point of view. The entrance is behind the camera; the reception is ahead/right, journal desk and window left, correspondence cabinet and curved postal chest on the rear wall, with the sun card, rain jar, candle, key and foliage retained. A closed ceiling is added because the camera is inside the room. This is a modeled interpretation of the reference, not an exact reconstruction of its unseen reverse angle.

`hush_interior_3d.js` loads the GLB, keeps its horizontal field of view consistent in portrait, gives a gentle entry movement and limited drag-to-look, and preserves book/post routes. It pauses rendering when hidden and respects reduced motion. `hush_app.html` waits for the model (up to 8 seconds) before starting its 3.2-second interior transition, with a Blender-rendered fallback. An old transition cannot interrupt a user who has navigated away.

The light atlas intentionally bakes the furniture and room shadows; geometry remains fully three-dimensional. Re-bake after changing furniture or lighting. The editable master retains the original PBR materials.

## Night → morning journey (corrected)

The original daytime-only reveal is replaced with two Blender lighting variants of the same room:

- `Hush_Inn_Interior_Night.blend` and `Hush_Inn_Interior_Night_Mobile.blend`: cool dark window, warm indoor lamps. `build_night.py` creates this from the editable master; `HUSH_PHASE=night Blender --background --python bake_interior.py` bakes it.
- `Hush_Inn_Interior.blend` is the daytime master. `hush-inn-day.glb` is its existing baked export. `HUSH_PHASE=day` rebuilds the daylight mobile asset.
- `hush_room_scene.js` shares the geometry-view behavior; separate GLBs carry the actual night/day baked illumination. Day loads on demand. Night reveals do not open morning archives.

The journey is: existing host → door → nighttime room → Fox check-in and activities → rest (still night) → “I’m awake” → Fox's morning greeting → daylight room. Wake is an explicit user action; the app does not infer sleep/wake from a clock or sensor. No requirement forces users to finish every activity.

`hush_journey.js` stores each stay with its own ID. A resumed stay keeps its original start; a completed stay remains available in the morning selector. Existing records are preserved and old timestamped records are associated with the legacy stay where possible. Saved tarot retains its original card, glyph and reading. Morning review never calls the tarot generator.

Morning object mapping:
- Window desk/journal → diary entries (including saved host reply when available).
- Curved postal chest → full letters from that stay.
- Shelf tarot card → original card and explanation, with its real title/glyph on the 3D card face.
- Guest ledger → timeline including check-in conversation, diary, letters, tarot, sounds and moods.

Pages and sealed envelopes appear according to the selected stay's records. Explicit empty states appear when an activity wasn't used. The page offers equivalent text controls for accessibility. This data currently persists in this browser's local storage, following the existing app architecture.

Verification: `node tests/journey.test.cjs`; open `/tests/journey-browser.html` and run the isolated end-to-end fixture. It uses in-memory storage, blocks backend calls and does not create real user records. Tests exercise return visits, night/day loading, diary/letter/tarot saves, wake greeting, object review, no tarot redraw, refresh recovery and archive retention. API/voice quality is outside this fixture.
