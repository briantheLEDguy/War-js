# Frontier siege and caravan package

This staging package contains eight original models at three LODs and one
animation-only pack. It does not modify maps, the public registry, game saves or
combat authority. No new body or prop uses primitive geometry constructors.

| Asset | LOD0 / LOD1 / LOD2 triangles | Construction and motion |
| --- | --- | --- |
| Supply wagon | 87,766 / 42,214 / 28,628 | Fitted panel bindings, sewn repair, eyelets and ties; adzed joinery, spoke wheels, teamster bench and footboard; `caravan_roll` |
| Battering ram | 70,560 / 33,740 / 22,442 | Bound hide mantlet, forged bull head, crew boards, animated striker and suspension slings; `siege_roll`, `ram_strike` |
| Oil cauldron | 23,584 / 5,958 / 2,766 | Hollow bowl, rolled lip, open spout, trunnions, lever and wall brackets; `oil_pour` |
| Field catapult | 75,376 / 30,692 / 20,780 | Oak arm, rawhide spoon, torsion skein, winding drum, ratchet, crank and following haul rope; `siege_roll`, `catapult_fire`, `catapult_reload` |
| Keep gate | 25,080 / 11,848 / 6,964 | Two hinged oak leaves, scroll iron, rosettes and bull reliefs; `gate_open`, `gate_close` |
| Draft horse | 118,342 / 52,512 / 16,534 | Original anatomical cages, connected skin, hooves, mane, tail and full fitted harness; `idle`, `walk`, `draft_trot` |
| Caravan reins | See measured inventory | Independent fitted leather ribbons, shaped bit and grip sockets |
| Officer kit | See measured inventory | Ledger pouch, fitted flap/fastener, stitched edging, paper signatures, quill sleeve, seal and belt loops |

`frontier_teamster_animations.glb` contains the four-second `driver_seated` pose
on the existing `humanoid_game_v2` skeleton. It adds no character geometry.
Published Battle Prelate body and novitiate equipment GLBs were reimported,
rebound and rendered for the actual seated-driver and standing-officer fits.

## Runtime contract

`source/runtime_contract.json` is the handoff contract. It includes exact model
basenames and hashes, metre-scale builder defaults, driven nodes, sockets,
operator locations, clip timing, hitch/hand/belt fits and measured LOD budgets.
The complete file inventory is `review/package_validation.json`.

Blender uses Z-up/front -Y. Exported glTF uses Y-up/front +Z. All models use metre
scale 1 and retain their authored origins. Preserve each fixed `pivot.*` parent
and its driven child. Flattening those nodes breaks axle and hinge positions.
Each moving actor needs its own AnimationMixer. No clip moves a world root.

- The horse origin is wagon-local glTF `[0,0,3.75]`; both tugs meet the literal
  wagon shaft sockets. Reins share the wagon origin.
- The canonical driver's origin is wagon-local `[0,0.6541226745,1.38]`, using
  `driver_seated` with the hand-held weapon omitted. The bench socket is butt
  contact, not the hip-joint origin. Palm grips are `[+/-0.20,1.895,1.61]`.
- Wheel timing follows distance: a wagon revolution covers `2*pi*0.79` metres
  and its clip lasts 1.6 seconds. Horse walk is authored at 1.5 m/s; draft trot
  is authored at 3.5 m/s. Stop the roll action when movement stops.
- Initialize `catapult_fire` at time zero for its cocked ready pose. Its default
  bind pose is vertical. Fire/reload, ram, oil and gate events come from server
  state. Projectiles, liquid, damage and replacement timing remain runtime work.
- The officer kit's bone-local matrix is fitted only to `civic_battle_prelate_m`
  with novitiate armor. Other bodies and races need their own measured fit.
- Sunmeadow wheat standards are regional artwork. Exported faction/color
  variants, destruction meshes, enter/exit motions and separate ram-crew poses
  are not included in this package.

## Editable sources and rebuild

`source/frontier_collection.json` retains 67 named authored control cages and
finite placements for the five mechanisms. `author_source.py` followed by
`finish_source.py` regenerates it. `paint_materials.py` retains the original
painted grain, weave, forging and material channels. `build_collection.py`
applies finishing and uses the existing Battle Prelate atlas baking utility.
`mechanical_animation.py` authors in-place motion and static pivot parents.

`refine_mechanism_lod2.py` is the current distance finishing pass. It preserves
curved tires, recomputes normals after reduction and retains clips/sockets.
The older `refine_wagon_lod2.py`, `refine_distance_normals.py`, and
`normalize_clip_times.py` are diagnostic history; do not run them over the
current animated exports. `repair_degenerate_tangents.py` repairs only zero
exported tangent vectors using adjacent surface derivatives and records exact
input/output hashes.

The horse source is in `author_draft_horse.py`, `rig_draft_horse.py` and
`export_draft_horse.py`. Separate anatomy, rigged and LOD masters retain its
construction. Exactly four or fewer normalized bone weights drive its connected
skin. Rejected rig trials remain diagnostic files and are not runtime sources.
The shared `quadruped_rig.py` provides export plumbing; anatomy and gait remain
species-authored.

`author_officer_kit.py`, `author_caravan_reins.py` and `author_driver_pose.py`
retain the accessory and fitted operator construction. The driver preserves
canonical rest matrices and reuses the existing finger-closure helper.
Every final source/master is saved under `masters/`; PBR channels remain in
`textures/baked/` and are embedded in the GLBs.

Run the mechanism rebuild in this order, with a bounded Blender thread count:

```powershell
python authoring/blender/orvr-frontier/tools/author_source.py
python authoring/blender/orvr-frontier/tools/finish_source.py
python authoring/blender/orvr-frontier/tools/paint_materials.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/orvr-frontier/tools/build_collection.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/orvr-frontier/tools/refine_mechanism_lod2.py
python authoring/blender/orvr-frontier/tools/repair_degenerate_tangents.py
node authoring/blender/orvr-frontier/tools/validate_collection.mjs
node authoring/blender/orvr-frontier/tools/validate_package.mjs
npx vitest run tests/orvrAssetSource.test.ts tests/orvrMechanicalExport.test.ts tests/orvrHorseExport.test.ts tests/orvrCaravanExport.test.ts
```

Horse/accessory rebuilds are separate Blender scripts listed above. Run tangent
repair for their explicit asset keys after exporting. Rebuilds invalidate visual
receipts; reimport and inspect the changed files before promotion. The old
`write_blueprints.mjs` is not part of this handoff and must not publish stale
metadata into the registry.

## Actual-export review

`reimport_review.py` renders all three literal GLBs per model in a clean scene.
`review_motion_batch.py` samples actual clips, including fractional frames.
`review_horse_details.py`, `review_caravan_assembly.py` and `review_officer_fit.py`
inspect close anatomy, harness, equipment and contact points. The final contact
sheet and inventory bind all 24 model/render hashes. Observations are recorded
separately from technical validation.

With Vite running, open `review.html` for individual LODs, materials and clips,
or `caravan-review.html` for the actual equipped assembly. Both have broad
sky/ground PBR reflections. The caravan page verifies input hashes and plays
independent horse, driver and wheel mixers; it does not move a game actor.

Current binary checks: 25 files, zero glTF errors. The three horse LODs each
have two `NODE_SKINNED_MESH_NON_ROOT` warnings from the retained identity parent;
other assets have no warnings. Tests verify literal bone/clip data, normalized
weights, shafts, grip sockets, published boot soles and belt attachment matrices.
The horse's planted forefoot differs by under 1 mm at authored keys and a measured
6.12 mm at the worst sampled quaternion-interpolated midpoint (1 cm budget).

The horse intentionally has a stylized, smooth short coat. Close facial, shoulder,
hip and harness views are retained; there is no claim of photorealistic fur.
Technical validation cannot certify the Battle Prelate benchmark or 60 FPS in a
populated zone. This package remains unpublished until the main task records its
integration/visual acceptance and promotes the exact reviewed hashes.
