# Changelog

## 2026-09-06 - Rendering resource budget and background suspension

- Default to a 30 FPS game limit, with an optional 60 FPS setting, to leave processing time for video playback and other apps.
- Stop game, character-preview and animated HUD loops when hidden or unfocused; resume without catch-up frames and remove listeners on teardown.
- Cap map canvas redraws at 15 FPS and idle preview rendering at 30 FPS.
- Make automatic resolution respect the chosen frame limit and retain a 1.5 pixel-ratio ceiling in balanced mode.
- Add scheduler tests across 60-165 Hz displays, focus/visibility transitions, disposal and settings migration.

## 2026-09-06 - Gothic citadel skyline and deeper keep

- Replaced the squat roof tower with a dominant 125-metre spire, staggered corner spires, roof pinnacles, leaded lancet windows and projecting stonework.
- Deepened the hall from 26 to 62 metres toward the courtyard. Extended roofs, galleries and collision while preserving the rear mountain doorway; moved the entrance gate, facade decorations, capture ring and staging positions to fit.
- Rebuilt and visually reviewed three keep LODs within the existing 30,000-triangle budget, retained shared PBR textures, and updated the missing-asset silhouette.
- Added scoped export/review/promotion tools and regression checks for deeper geometry, spire height, traversal and formation clearance.

## 2026-09-06 - Aegis garden wards and reviewed city population

- Add 23 varied houses, 52 linden/cypress trees and 80 rose/violet flowerbeds across the five city districts with preserved street, canal, service and siege clearances.
- Build four original planting assets with shared 2048px PBR textures, three reviewed LODs, editable masters and GM Builder support.
- Replace primitive ambient guards, service NPCs and public-building residents with reviewed Aegis models; retain named services and use bounded, safely disposed animation instances.
- Replace remaining visible city map scenery with fitted modeled props while preserving collision, IDs and harvesting; repair civilian walking skin weights in separate reviewed derivatives.
- Keep off-map interior players and cameras on the room floor instead of lifting them to the mountain heightfield.

## 2026-09-06 - Smoother frame pacing and resolution scaling

- Add automatic 70-100% 3D resolution scaling toward 60 FPS, plus fixed 75% and native-quality settings; keep HUD text at display resolution.
- Use sustained timing windows and slow recovery to avoid rapid buffer resizing; ignore background pauses and simulation-bound frames.
- Precompile material shaders during loading and report frame time/current scale in the debug overlay.
- Rebuild only affected city instance batches and stabilize LOD transitions around distance thresholds.
- Add tests for scaling limits, timing, recovery, settings compatibility, partial batch updates and LOD stability.

## 2026-09-06 - Crownwatch citadel interiors and three-stage siege

- Built the east mountain vault with a guarded entrance and royal return passage; enlarged the throne room and organized barracks, cookhouse, stores and counting rooms around the garrison hall.
- Added Courtyard, Vault and Throne Room capture objectives with ordered prerequisites, persisted progress and campaign siege requirements enforced by the local service.
- Added fourteen custom detailed PBR decoration assets with editable masters, three LODs, reviewed exports and GM Builder support.
- Added model-space collision for new asymmetric builder pieces so their doorways and walkable surfaces remain aligned when rotated.
- Kept the original courtyard battle staging and reserved the sealed Crypts connection.


## 2026-09-06 - Exaggerated Battle Prelate swings

- Enlarge the embedded-derived opening windup, sweeping attack arcs, shoulder loads, torso rotation and follow-through while retaining existing impact times.
- Bake the opening from the original embedded motion through the same hand/foot constraints; use it for basic attacks and Litany. Retain unmodified embedded fallback clips.
- Add exported hammer-travel regression coverage alongside grip, foot, timing and silhouette checks.

## 2026-09-06 - Citadel mountain redoubt

- Extended Crownwatch through a real rear keep doorway and working internal portcullis into a vaulted mountain siege hall, flanking aisles and rear command chamber.
- Added 36-player staging, cover, supply alcoves and sealed, connected Crypts/Vault approaches with stable future expansion metadata.
- Built high-resolution passage, redoubt and sealed portal assets with three LODs and GM Builder support; reshaped the mountain to clear the interior volumes.
- Expanded the capital bounds while limiting detailed terrain rendering to the city slopes, preserving one-metre movement samples.


## 2026-09-06 - Gated Crownwatch citadel and explorable keep

- Enclose the hilltop battle court with fortress walls and three functional, independently controlled entrance portcullises.
- Replace the solid keep with a hollow hall, side chambers, twin stairways and upper gallery; add a separate working main keep gate and interior furnishings.
- Preserve the large 18-versus-18 court and regenerate campaign data and GM prefab defaults.
- Rebuild and review the high-resolution keep at all three LODs; test real mesh openings, closed perimeter coverage, open approaches and interior traversal.

## 2026-09-06 - Battle Prelate swing variety revision

- Enable the preferred embedded windup as the gameplay opening/basic strike, retaining the three-strike Litany sequence.
- Separate return sweep, descending blow, low engagement strike, shoulder-coiled Sanctified Blow, overhead smash and chest-height thrust silhouettes; establish the loaded pose before accelerating.
- Clarify gameplay versus embedded-comparison controls and add exported windup/pose-distinction regression checks.


## 2026-09-06 - Battle Prelate combat animation

- Add original choreography for all ten abilities, including three cycling Litany strikes, a breathing combat guard and landing recovery; preserve Icon of Wrath's existing gameplay restriction.
- Blend locomotion beneath moving attacks, restart repeated actions, fit playback duration and synchronize hammer trails/contact effects with impact markers.
- Bake constrained hands/feet into a separate verified GLB without changing character geometry or sockets; register the existing rigid Dawn Maul for the female body.
- Add editable Blender sources, an equipped development review stage, and regression tests for exported grips, planted feet, shaft clearance, combo playback, fallbacks and 30/60 FPS timing.

## 2026-09-06 - Aegis city guards

- Added four civic guard loadouts with shared steel armor, blue/ivory heraldry, pierced helmets and distinct patrol weapons.
- Added editable sources, corrected two-handed weapon holds, three exported detail levels and validation/review tooling.
- Replaced the distorted guard head cage with a fitted natural human head/neck, preserving skin texture detail and improving the jaw transition.
- Routed Aegis guard variants through reviewed manifests while preserving non-guard and Riftbound behavior.

## 2026-09-06 - City visibility and scene traversal

- Skip zero-instance draw submissions from empty LOD batches.

- Cull individual city instances against camera and shadow frusta while retaining off-screen shadow casters and existing LOD distances.
- Detach hidden source models from scene traversal during normal play; keep collision references and restore models for GM editing and resource disposal.
- Preserve texture resolution, mesh detail, lighting and shadow settings; cover culling, nested shadow lights, camera turns and GM restoration with regression tests.

## 2026-09-06 - City frame-time tuning

- Reuse unchanged city instance buffers and bounds instead of rebuilding and uploading them every frame.
- Cache static scenery camera bounds, skip distant mesh hierarchies, and invalidate bounds on GM root transforms; interactive objects retain live collision.
- Avoid redundant mesh raycasts against procedural heightfields while retaining imported terrain and voxel mesh collision.
- Add regression coverage for buffer reuse, LOD/suppression updates, transformed and animated collision, and terrain filtering, plus a reproducible CPU sweep fixture.

## 2026-09-06 - Runtime memory and resource cleanup

- Share decoded external GLB images per game/preview loader while preserving resolution, independent texture settings, geometry and lighting.
- Deduplicate static and animated requests for the same model.
- Release scene resources, loader caches and reflection targets on teardown, including late-loading assets after unmount.
- Size city instance buffers by actual mesh occurrences.
- Add regression tests for sharing, texture settings, retries, cleanup, skeleton independence and instance capacity.

## 2026-09-06 - GM Builder scenery coverage

- Generate the catalog from map props and runtime-ready static assets, retaining collision, walkable surfaces, interactions and city LODs; derive footprints from GLB bounds.
- Add cross-kit asset search and a placed-object list covering collision-only and removed map objects, with restore and undo.
- Fix rotated collision offsets and Aegis portcullis lift behavior on new placements; retain city and world-life fallbacks.
- Add coverage, placement, deletion/reload, restoration and undo/redo regression tests.
- Scenery only: functional NPC/enemy/resource spawning and procedural canal/heightfield authoring remain separate systems.

## 2026-09-06 - Camera range and world obstructions

- Expanded mouse and touch pitch to nearly straight up/down indoors and outdoors, with a level horizon view and preserved inversion/sensitivity controls.
- Replaced infinite-height camera checks with finite-height collision and full-path terrain sampling; camera collision no longer filters out obstacles just because they are above or below the player.
- Added geometry checks for static props, instanced city sources, GM edits, roofs, ceilings and interior furnishings, with clearance around the camera's near plane. Openings remain usable without a whole-building bounding-box obstruction.
- Preserve the requested angle and zoom while drawing the camera forward around obstructions, and hide the avatar at close camera distances to prevent it from blocking the viewport.

## 2026-09-06 - Aegis rich civic decorations

- Added ten original Blender decoration models and 30 reviewed GLBs: twin street lights, wall lanterns, four named trade signs, a ceramic canal relief, civic bench, astronomical sculpture and directory post.
- Distributed 69 street lights, 104 wall lanterns, four trade signs, 22 artworks and 15 benches/directories through all five Aegis districts, preserving storefront portal IDs and gameplay approaches.
- Reserved existing furniture footprints and level ground, aligned facade attachments with building elevations, and added appropriately sized missing-model fallbacks.
- Added an isolated civic build/validation/promotion workflow, an actual-export review sheet and regression coverage for district distribution, clearance, slopes, asset hashes, LODs and fallbacks.

## 2026-09-06 - Grand citadel battle precinct

- Replaced the serrated ridge with an original eroded mountain massif with broad shoulders and unequal peaks.
- Rebuilt the citadel as a monumental keep with bastions, open arcades, three wide entrances and a 128 by 68 metre battle court. Extended the enclosing fortress to the north.
- Authored and collision-tested two 18-person staging formations, wide approaches and flanking routes; added optional avatar-sized spacing markers to the isolated review page. This does not establish live 36-player networking or performance.
- Expanded the reviewed Blender kit to 52 assets and 156 three-LOD exports, and reduced unnecessary terrain subdivision on flat city levels.

## 2026-09-06 - Aegis mountainside

- Raised the northern capital in terraces to a citadel 42 metres above the low canal district, with a winding ascent and exposed mountain ridge beyond the north wall.
- Added deterministic baked elevation, terrain-conforming road beds, level building pads, deeper fortress foundations and a level terrace beneath the wall stairs.
- Updated movement, saved-position recovery and regression checks to use the elevated ground rather than the former flat plane.

## 2026-09-06 - Aegis density and material variety

- Added 36 infill buildings, 135 street furnishings and eight court features across all five districts.
- Expanded the high-resolution Blender kit to 47 assets and 141 GLBs with narrow rowhouses, workshops, awnings, carts, storage piles, greenery, washing lines, noticeboards and a fountain.
- Added contrasting plaster, masonry and roof finishes, irregular PBR surface detail, separate paving and flagstone textures, and world-space weathering on city surfaces.

## 2026-09-06 � Bastion of Aegis canal city

- Rebuilt Aegis with five districts, winding brick walks, canals, six bridges, 98 ordinary houses, a citadel, eight exploration courts and six public interior entrances. Preserved campaign exits and local services.
- Enclosed the city in fortress walls with towers, operable road gates, barred water gates and two stairways to the wall walk. Added canal collision, actual ground cutouts and safe recovery for obstructed saved positions.
- Added 34 original Blender architecture assets with editable sources, 2048/1024 PBR maps, 102 validated GLB exports and manifest-backed review records. Shared textures, three runtime LODs and instanced static rendering reduce repeated asset costs.
- Added city minimap geometry and district labels, four public room variants, an isolated runtime review page, and regression tests for routes, water, perimeter coverage, interiors and GM rendering transitions.

## 2026-09-06 — Keep commanders and functional abilities

- Added Git LFS coverage for the new authoring masters and large review artifacts, and preserved exact Ember Arcanist source/QC bytes for cross-platform evidence verification.
- Added 36 named keep commanders across 18 campaign zones. Clearing an unlocked keep's approach summons its commander; cone cleaves, circular pulses and a low-health last stand lead into the capture and gear reward. Approach guards stay down during the encounter, with clean resets on death or retreat.
- Implemented temporary self guards, finite shields, damage and speed boosts, cleanses, swept movement, periodic burns/bleeds and numeric mark/weakening effects. Added shared ability recovery and active-effect feedback. Summaries now describe current local effects; three unfinished persistent summons are explicitly unavailable without spending resources.
- Gave every class a working level-one damage/resource builder, including Siegewright's Crank Charge. Passive health recovery now pauses during combat while mana recovery continues. Added deterministic solo commander simulations with responsive and missed-warning policies.
- Fixed friendly capital standards hiding expedition guidance with an unavailable defense, and reserved space for active effects above the first-steps panel. Added commander, movement, utility, status, regeneration and reset regression coverage.
- Hostile enemies now engage when damaged from range. Encounter resets cancel pending area attacks so restored guards and commanders cannot be hit by an attack from the previous attempt.

## 2026-09-06 — Ember Arcanist

- Added the male Ember Arcanist reference outfit, red hair and stubble, nine armor modules and an emissive brazier staff, with editable Blender sources and three GLB LODs.
- Added local starter staff equipment and non-destructive empty-slot backfill; preserved custom weapons and female defaults.
- Retained hashed binary, material, rig and exported-motion review evidence; documented simplified likeness and current LOD-selection limits.


## 2026-09-06

- Added the Novitiate Field Harness: nine additional male Battle Prelate armor modules with compact shoulders, plain plate, leather guards and a short russet tabard. Refined rolled edges, hinge tabs, rivets, leather toe reinforcement, stitched welts, cloth hems and material maps. Preserved the ornate set and shared body, hammer and animations.
- Added a character-selection armor comparison and nine catalog entries without changing saved equipment, starter inventory or item stats. Included editable masters, explicit mesh records, three runtime LODs and local review evidence; no deployment.

- Added solo defense of friendly battlefield standards, with eight-second cleared-area holds, 50 XP / 35 influence rewards and persisted three-minute cooldowns. Three home defenses now unlock the existing 100-influence keep requirement.
- Required living objective defenders to be defeated before capture or defense, including guards pulled outside the ring. Added campaign guidance, hold progress, blocker explanations and victory receipts. Keep captures award tier-scaled XP, gold and universal amulets; full-bag gear is preserved per character for later collection.
- Kept quest rewards ready for turn-in when inventory space is insufficient, with an inline explanation instead of discarding the reward. Quest and campaign rewards now share capacity and stack placement rules.
- Added fixed enemy attack footprints, visible 0.9–1.2-second windups, target cast bars, movement-based dodges and interrupt cleanup. Extended objective defender recovery to 30 seconds and roaming raider/beast recovery to 15 seconds.

- Fixed metallic-material reflections by extending fallback sky capture beyond the sky sphere and adding neutral room reflections to character previews; delivered asset files and material values are unchanged.

- Replaced the male Battle Prelate with a full reference-authored character, nine modular armor slots and separate sanctified warhammer. Retained explicit mesh records, editable Blender masters, packed materials, canonical rigging and three validated LODs (98,274 / 56,628 / 29,484 triangles; 66.2 MB combined GLBs). Previous assets are archived. The result follows the accepted modeling direction and remains a stylized interpretation rather than photographic reconstruction.
- Corrected the rigid hammer's equipment metadata and prevented duplicate procedural weapon offsets when a calibrated authored socket animation owns an ability. Existing fallback and uncalibrated weapon behavior remains covered by tests.
- Added hash-bound source/archive/export validation and local promotion evidence, including per-LOD provenance and exact evaluated vertex data. Excluded Blender authoring files from Vite's watch list to avoid locked-file crashes. No site deployment was performed.

## 2026-09-05

- Added 304 scenery props, 85 ambient citizens/guards/wildlife, and 32 smoke/ember/mote emitters across both capitals and four Tier 1 routes, with markets, wash yards, gardens, supply camps, resting areas, and clear travel paths.
- Added ten local scenery builders, articulated ambient actors, waypoint walking and pauses, grazing and flight motion, cloth/fire animation, solid furniture collision, and vegetation exclusions. Bounded population/effect budgets, distance culling, deterministic authoring, and owned-resource cleanup keep the world-life layer separate from combat and quest NPCs.
- Routed both realms through their own Tier 1 starter expeditions, added local field-officer handoffs and named captain targets, scoped quest kill credit to the intended zone, and awarded a universal expedition amulet at the finale. Preserved Aegis quest IDs and migrated legacy Riftbound progress to the equivalent new chain.
- Added a shared expedition destination across the objective card, minimap and campaign atlas, with actual exit routing and reward previews. Made minimap filters and the full first-session checklist expandable.
- Introduced three starter abilities per class and gradual unlocks through level 8, with visible unlock requirements, runtime activation gates and learned-ability messages. Fixed Cleaver's Whirly Chop damage and Warped Reaver's missing usable resource builder.

## 2026-07-15

- Added a reusable dark-fantasy armor pass that applies muted class palettes over fitted MPFB silhouettes, removing bright contemporary source graphics and gold helmet materials from the Battle Prelate and Warbrute runtime sets.
- Reparented rigid equipment overlays to the canonical animated hand sockets, added Warbrute starter cleaver and shield equipment, and regenerated/promoted both characters with animation, deformation, clearance, and round-trip QC evidence.
- Corrected generated armor color encoding so dark cloth remains readable in the browser, added visible woven/normal variation, and calibrated procedural sword/shield fallbacks for guarded hand placement.

## 2026-07-14

- Preserved visible weapon attachments when an authored weapon is blocked or unavailable: the approval gate still prevents the unapproved model from loading, while the player now receives an animatable procedural fallback instead of appearing unarmed.
- Generated and directly promoted the real Equipment01 CC0 Battle Prelate Dawn Maul from the installed MPFB pack, including canonical hand sockets, round-trip QC, and five attachment review views; the runtime now prefers this authored mesh.
- Fixed the runtime handoff for directly promoted playable armor: legacy local-save item keys now resolve to the family-prefixed approved registry entries, preserving the skinned overlay path instead of mounting detached static armor.
- Refined the unified Campaign Atlas with dark-fantasy engraved relief styling, fit-to-pane defaults, shared physical scene scaling, cursor-anchored wheel zoom, drag panning, and reliable node/tier gesture handling.
- Reworked the character-generation pilot around explicit rigid, skinned, and loose wearable paths with canonical socket/body-mask/pose-pack/export resources, narrow MCP stage tools and prompts, Blender BVH/weight-transfer helpers, and three draft-only generated GLB fixtures (base body, socketed sabre, and transferred chest wearable) validated before any runtime promotion.
- Completed the first two end-to-end playable animation-stage pilots: Battle Prelate with the `battle_prelate_hammer` equipment profile and Warbrute with the canonical `unarmed` profile. Both variants per character embed the nine-clip pack and carry deterministic locomotion/melee review frames; artifacts remain draft-only and pending human approval.
- Added an explicit user-authorized direct-promotion path for roster pilots. It requires `--bypass-approval`, revalidates model/QC hashes and review previews, publishes neutral runtime GLBs plus approved manifests atomically, and records the bypass instead of silently weakening the normal review workflow. Battle Prelate and Warbrute are now runtime-resolvable.
- Built and directly promoted the first NPC/creature pilot batch: Aegis civic and Riftbound Greenskin NPC foundations with role-combination evidence, plus Barrow Wolf and Lair Spider. The bypass registers 47 live NPC/enemy profiles, preserves the nine embedded humanoid animation clips, registers both creature static keys, and records the authorization in each revision and approved manifest.
- Fixed modular armor runtime metadata so canonical-skeleton armor is rebound to the player body skeleton and covered body regions are masked. Existing approved rows also infer the skinned path from their skeleton metadata.
- Regenerated the Battle Prelate and Warbrute body/armor pilots with corrected shoulder seam anchors and slot-specific body clearance, reran bind/idle geometry audits and animation evidence, and directly promoted the verified revisions with the authorized bypass.
- Rebuilt humanoid roster generation around the installed MPFB/MakeHuman fixture packs: race-specific bodies, skin, hair, brows, lashes, fitted class silhouettes, and Equipment01-authored one-handed, dual-wield, and two-handed review weapons now replace the earlier primitive draft approach. Reapplied equipped-body material cleanup after authoring reloads to prevent face holes, removed visually corrupt closed hoods and helmets from live recipes, strengthened race/class differentiation, and rebuilt creature drafts with closed rigged body-plan meshes and stress poses.
- Reworked the staged model-review screen for phones and small tablets: landscape now reserves separate model and scrolling-control regions, portrait stacks a fixed model viewport above the review sheet, touch targets meet a 44px minimum, navigation labels compact cleanly, safe-area insets are respected, approval actions remain reachable, and reviewer entry no longer relies on a blocking browser prompt.

## 2026-07-13

- Combined the detailed zone map and Aegis/Riftbound campaign tracker into one three-tier Campaign Atlas. Map/M opens the current zone, the Campaign HUD action opens the full graph, left/right click moves between zone, route, and campaign tiers, wheel zoom works within each tier, and every generated campaign zone now has a static preview without fast travel.
- Added the full local roster model-stage pipeline: 24 playable class pairs (48 appearances/432 T1 modules), 12 NPC race/body foundations covering all 106 humanoid profiles, 12 rig-ready creature species, a shared one-/two-hand/dual-wield review suite, deterministic revisions, resumable generation, consolidated QC, and strict preflight gating.
- Completed the initial `full-roster-v1` geometry batch with all 48 groups in `ready_for_review`, all 432 armor modules unique, all 106 NPC combinations rendered, and every generated artifact present with its recorded SHA-256; no model was promoted into the runtime registry. That draft is superseded by the fixture-backed `full-roster-v2` review run.
- Hardened Blender 5/MPFB generation with explicit add-on activation, finalized-body armor reprojection, shape-key baking, deterministic topology cleanup and headgear remesh fallbacks, calibrated pair-specific seam clearance, traceback detection, and immediate recovery of locks whose owner process is proven dead.
- Replaced the hard-coded Battle Prelate development route with a protected Classes/NPCs/Creatures review queue supporting item/version navigation, body and weapon modes, stress evidence, required rejection notes, regeneration, hash-bound authoring approval, safe revision cleanup, and reapproval history without runtime promotion.
- Removed seven historical static creature GLBs/QC files/blueprints/registry exemptions through a manifest-driven cleanup and redistributed the canonical campaign's 60 existing beast placements across six Aegis and six Riftbound species without changing placement IDs, levels, or coordinates.
- Added a persistent, conflict-safe settings page with Gameplay and Key binds tabs, covering camera controls plus movement, targeting, mouse selection, interactions, abilities, and interface shortcuts. Added MMO-standard Tab / Shift+Tab enemy cycling, middle-mouse nearest-enemy selection, and NumLock autorun that stops on manual movement.
- Added a reusable original dark-fantasy Fortress Build Pack with crenellated curtain walls, corner towers, gatehouses, wall stairs, ember braziers, torn banners, siege barricades, and the existing animated fortress gate exposed together in GM Build mode. Rebuilt Bastion of Aegis and Riftspire Citadel with the pack, gatehouse-wrapped interactive city gates, walkable wall surfaces, and perimeter scenery.

## 2026-07-12

- Cleaned up the detailed world map with quieter icon-only rendering, connected city terrain treatment, responsive square map framing, and hover cards that reveal location names and context without overlapping the map.
- Added a SHA-256-pinned, Vite-development-only bridge that loads the exact Battle Prelate v19 assembled GLB in character preview and normal local gameplay without copying it into `public/`, changing approved registry state, stacking duplicate equipment, or affecting production/fallback resolution.
- Prevented assembled characters from double-driving embedded weapons by giving mapped authored GLB clips authority over baked weapon transforms, while retaining procedural motion for equipment overlays and no-clip fallbacks and marking only the highest imported weapon attachment root.

## 2026-07-11

- Replaced the external modular fantasy-town FBX and imported Aegis city packs with 20 original, deterministic dark-fantasy Blender generations using realistic masonry, timber framing, staggered slate, PBR surface maps, ironwork, leaded glass, grounded building proportions, and a monumental capital castle; rebuilt both capitals as dense navigable medieval cities and mapped the full pack into the GM building/editor system with MCP validation and review coverage.
- Fixed generated house and modular-roof geometry by adding closed manifold roof shells, outward-facing gable/end faces, and correctly pitched overlapping slate courses so roofs remain seamless and opaque under runtime backface culling.
- Added reusable small and large furnished house interiors for generated and GM-placed town houses, including click/E door portals, exact street-position returns, ambient residents, furniture, warm lighting, room collision, and tighter collision-aware indoor camera tracking.
- Replaced the procedural character/body/armor preset pipeline with a zero-cost local Blender + MPFB 2.0.16 workflow, original stable-topology Greenskin targets, four reproducible Human/Greenskin body recipes, canonical rig/socket metadata, and local QC/review rendering.
- Added persistent MCP model jobs, locking, cancellation, provenance schemas, strict validation, explicit human review, hash-bound atomic promotion, and deterministic approved-only runtime registry compilation.
- Removed the 48 proxy playable bodies, 432 proxy armor modules, related NPC/enemy character presets, generated outputs, and unverified external character mappings; quarantined raw authoring sources outside `public/` and retired commands that recreated proxies.
- Made runtime character and equipment resolution approval-aware and family/variant/skeleton/bind-pose compatible while preserving Three.js fallbacks for every unbuilt or blocked profile.
- Added a dev-only in-game Battle Prelate review route backed by the first local draft body, nine-slot fitted armor set, socketed hammer, and nine embedded animation clips; it remains outside the approved gameplay registry.
- Added live selection for all nine Battle Prelate animation clips, pause and auto-rotation controls, formal bare/equipped review jobs, and a hash-bound geometry-only acceptance stage that cannot be mistaken for final promotion approval.
- Added an opt-in local animation evidence profile with side/back walk and run contact phases plus front/side melee ready, windup, impact, follow-through, and recovery frames; all samples are hash-bound without breaking existing promotion evidence keys.
- Added a one-command zero-cost Battle Prelate runtime assembly, now defaulting to the v18 seam-trimmed, flowing-cloth modules while retaining earlier review history. The revised set uses a closed curved belt, shoulder-attached cape folds, a shaped/scalloped hem, waist clearance, outward-only tabard pleats, rounded shoulder shells, and bone-relative sleeve/gauntlet plus trouser/boot seam ownership; assembly still rejects missing mesh/bone/clip evidence or unstable bind-to-idle round trips.
- Rebuilt the Battle Prelate layering pass with a closed curved belt, tapered pleated tabard, swept/folded cape, outer glove and boot seams, and closed rounded pauldrons; added bind/idle BVH clearance reports so remaining hidden underlaps are measurable instead of judged from screenshots alone.

## 2026-06-15

- Regenerated the Battle Prelate, Brother Steffan Battle Prelate trainer, Sunfire Templar, and reliquary hammer GLBs after reference review, then migrated local Battle Prelate saves away from legacy blackened armor/sword/shield gear so the class loads with manifest Battle Prelate armor and the two-handed reliquary hammer.
- Fixed character animation routing so player characters prefer manifest-backed playable GLBs with authored `idle`, `walk`, `run`, `jump`, attack, ranged, and cast clips instead of static external overrides.
- Added enemy locomotion animation switching between idle, walk, and run loops, with attack/cast/hit clips played as one-shot actions during combat.
- Expanded the static/procedural fallback animator so primitive or imported characters without complete clips still move limb mesh groups during walking and body actions.

## 2026-06-12

- Added imported Swordsman and medieval character sample runtime GLBs, preserving their skins and animation clips, and mixed them into Aegis guard NPC/enemy visuals through a weighted deterministic variant picker.
- Added the imported Strong Knight GLB as the default Aegis player model, preserving its rigged `idle1` clip and layering fallback locomotion/action motion over its named humanoid bones.
- Added the imported `evil-guy` GLB as the default external player model for all Riftbound races while keeping the Strong Knight override for Aegis races.
- Fixed Bastion of Aegis imported-city placement by using the medieval city GLB as terrain, preserving collision through a hidden proxy, and spreading services/resources onto accessible streets and courtyards.
- Added `models:import-external`, an external GLB/FBX import manifest, Blender importer, generated blueprints, QC sidecars, and asset-index entries for the medieval knight player, animated Warrior guard, modular fantasy town kit, and imported Aegis capital city.
- Replaced Bastion of Aegis generation with the imported medieval city visual, explicit city-wall/house/landmark colliders, relocated services/objectives/travel triggers, resource nodes, crafting stations, and additional Aegis guards spread through the town.
- Routed the player to the imported Warrior rig because the supplied medieval knight GLBs are static, while keeping static root animation as a fallback for unrigged player overrides and suppressing incompatible skinned gear overlays.
- Fixed imported Warrior visibility by forcing character-import materials to opaque output and defensively clearing zero-alpha character materials at runtime.
- Relinked the imported Warrior FBX texture directory during export so `chr_external_warrior_guard.glb` embeds its albedo texture instead of rendering as plain white.
- Layered fallback root locomotion, imported humanoid bone stride motion, and action recoil over imported player GLBs that lack explicit walk/run/attack clips, restoring visible movement while preserving the authored idle clip.
- Routed Aegis guard NPCs and Aegis guard enemies to the imported animated Warrior profile while leaving Riftbound guards and non-guard NPCs on the normal generated profile pipeline.
- Added the modular fantasy house kit to the GM build prefab catalog with asset-index previews, footprints, default colliders, snapping, wheel rotation, drag-chain placement, save, and reload support.
- Added a GM Build Kit selector so the modular fantasy house pieces appear under `Modular Town Kit` instead of being buried in the full prefab list.
- Reworked generated capital cities into dense navigable street grids with hard-colliding houses, 6-level walkable citadels, vertical-bounded upper-floor colliders, and Riftspire-only destruction props exposed in GM build mode.
- Made in-game HUD windows draggable from their headers/title bars, including inventory, character, quest, crafting, campaign, map, guide, settings, GM, chat, tracker, minimap, debug, and death/quest dialogs.
- Added manifest-backed unique static NPC and enemy model assignments across map JSON, including deterministic `characterProfileKey` profiles for humanoids and indexed creature/dummy `assetKey` visuals for non-humanoid enemies.
- Added `models:sync-npcs`, generated NPC/enemy character blueprints, generated creature static prop blueprints, NPC roster style data, runtime asset-index entries, and tests that verify every map visual assignment resolves through the index.
- Extended the Blender generators with NPC role adornments and static creature presets for hounds, wolves, boars, stags, and lair spiders.
- Expanded generated capital cities with GM-editable outer walls, district buildings, realm-specific landmarks, and inner citadels with animated front, side, rear, and keep gates.
- Added procedural weapon animation gestures for equipped and fallback weapons, including sword swings, staff/ranged aiming, heavy-weapon slams, dagger/spear thrusts, and shield bracing driven by ability motion metadata.
- Moved generated fortress default spawns outside the contested yard and made death respawns use the zone's safe spawn instead of the character's last saved entry position.
- Regenerated campaign battlefield, fortress, and capital gate structures from GM-editable modular keep pieces with animated front gates, rear exits, inner doors, and closed-only gate collision.
- Replaced the visible procedural sky dome with a screen-space sky gradient background, fixing circular viewport artifacts while keeping the sky visible at long view distances.
- Added a persisted Settings slider for world view distance and raised the default fog range so players can see much farther across keeps and battlefield zones.
- Added GM movement controls for walking/flying speed multiplier and flying mode with `Q` descend and `E` ascend controls.
- Added a GM tools menu opened with `/gm` or `/gm menu`, including campaign zone teleporting, character-name goto, coordinate copy, zone-spawn return, restore, cooldown reset, and build-mode toggle actions.
- Made `Esc` close the active UI window across Settings, Guide, Map, Campaign, inventory, character, quest, crafting, debug, GM tools, and character creation surfaces.
- Added enemy archetype AI for campaign camps, including chase/leash behavior, caster stand-off movement, cooldown abilities, player slows/roots/staggers/debuffs, and cast cancellation from control effects.
- Reworked generated RvR battlefield and fortress zones to include three battlefield objectives plus Aegis and Riftbound keeps with matching props, defenders, static hashes, and Supabase seed data.
- Added local per-zone realm influence: BO captures grant 75 XP and 25 influence, three-BO sweeps add the final keep-unlock influence, and enemy keeps require 100 influence before capture can flip zone control.
- Fixed campaign portals so zone transitions preserve the destination `targetSpawn` instead of reloading at the zone default spawn.
- Prevented intentional portal transfers from racing against old-position persistence during game disposal.
- Spread generated same-side portal triggers apart and added tests to catch overlapping portal volumes or unsafe target spawns.

## 2026-06-11

- Expanded generated Aegis/Riftbound campaign maps with deterministic NPCs, enemy camps, keep/fortress defenders, crafting stations, biome pockets, and interactive resource nodes across all 32 zones.
- Added in-world resource node gathering with minimap markers, contextual prompts, loot rewards, crafting XP, local cooldown persistence, and validation/tests for visual prop references.
- Added proximity capture for campaign objectives: standing inside an enemy or contested objective radius claims it for the character's Aegis/Riftbound realm through the existing campaign service.
- Replaced the stacked in-world text controls for logout, settings, guide, map, and campaign with a compact horizontal HUD icon bar.
- Added a detailed world map HUD panel opened with `M` or the Map icon, drawing terrain, roads, camps/objectives, landmarks, exits, NPCs, crafting stations, enemies, and the live player position from active zone data.
- Added the original static Aegis Accord vs Riftbound Host campaign graph, generated 32 committed zone maps with static hashes, bidirectional portals, objectives, keeps, fortresses, capitals, and boss/lair branches.
- Added the deterministic campaign generator, generated Supabase campaign seed SQL, and a Supabase migration for campaign static data, live control state, and world-edit tables.
- Replaced the HUD Warfront panel with a Campaign panel backed by `services.campaign`, local campaign control persistence, and Aegis/Riftbound fortress and city-siege readiness rules.
- Updated character starting zones to Bastion of Aegis and Riftspire Citadel and refreshed docs, guide copy, validation, and tests for the IP-neutral campaign map.
- Added baseline health and mana regeneration for living players, scaling each resource pool to refill from empty in about 30 seconds across all classes.
- Added a dismiss button for contextual HUD prompts so beginner interaction hints can be closed until the prompt context changes.
- Reworked generated path props as terrain-following visual ribbons without separate walkable shelves, preventing players from floating above the terrain while walking downhill on paths.
- Added terrain-height collision resolution to the follow camera so it moves forward when hills or terrain surfaces would occlude the viewport.

## 2026-06-10

- Added an objective tracker and enhanced minimap with quest, NPC, crafting station, enemy, exit, edge-distance, and marker-toggle support.
- Added inventory search, item type/slot/material filters, sort modes, capacity status, equipped-item comparison, and safer preview-before-salvage affordances.
- Added crafting recipe filters, craftable counts, missing ingredient summaries, rank-gated visibility, and cultivation-ready/soil counts.
- Added contextual interaction prompts for quest givers, crafting stations, harvestable corpses, gates, and targetable enemies.
- Added ability failure feedback for blocked UI, defeated player state, cooldowns, missing targets, range, mana, and class-resource requirements.
- Added optional first-session HUD goals for movement, camera control, interaction, combat, harvesting, gear equip, guide use, and crafting, with localStorage progress.
- Added a compact local RvR / warfront status panel with Order vs Destruction placeholder control, WAR-accurate campaign zone IDs, city-siege readiness rules, and reserved scenario hook IDs.
- Added focused helper tests for objective HUD data, inventory/crafting filters, ability failure mapping, first-session task progress, and warfront status rules.

## 2026-06-09

- Switched unit tests to Vitest and added ability catalog/runtime coverage for kit integrity, legacy aliases, resource rules, activation gating, cooldowns, animation calls, and VFX handoff.
- Added `npm run test` with unit coverage for generated wiki/data catalog consistency across races, classes, ability kits, crafting, quests, and referenced items.
- Added an in-game Guide/wiki panel backed by a reusable `src/wiki` content layer generated from race/class, ability, crafting, quest, and item catalogs, with planned roadmap pages clearly marked.
- Updated README, AGENTS, and asset-pipeline docs to reflect the current manifest model pipeline, generated playable assets, GM world editor, crafting, quests, character preview, and Supabase stub status.
- Removed the unused Supabase client helper and dependency while keeping the service stubs and backend contract intact for future implementation.
- Cleaned generated local artifacts from the workspace, including ignored Blender preview screenshots, temporary smoke-test HTML, build output, scratch Blender backups, and unlocked Vite logs.
- Added class/race-specific ability color palettes that drive hotbar icon frames, symbols, accents, glows, cast flourishes, projectiles, beams, and impact effects.
- Expanded ability visuals with class-family flair metadata, caster-side flourishes, arcing projectile motion, beam pulse rings, area spokes, aura markers, and class-styled contact fragments.
- Added per-ability visual profiles that drive thematic SVG hotbar icons, cast windups, shaped projectiles, trails, and target-contact impact animations.
- Added a character-select 3D preview stage that loads the selected character through the runtime player model/equipment path and updates live from unsaved race/class/body choices during character creation.
- Added race-themed character-select preview environments, including generated neutral Destruction foliage and stone props for twisted trees, blighted shrubs, jagged stones, and dreary reeds.
- Added manifest-backed `destruction_preview` static prop generation and asset-index entries for the new preview environment GLBs.
- Added body variants (`m`/`f`) to character summaries, local character creation, saved-character migration, character display, and game remount keys.
- Added a deterministic playable roster sync tool that expands 6 races, 24 classes, and 2 body variants into 48 neutral character manifests, 432 starter armor manifests, asset-index entries, and a generated starter item catalog.
- Extended the Blender manifest generators with profile-driven playable race/class/body variants, themed silhouettes, body-region metadata, skinned modular armor slots, and smoke/full playable generation sets.
- Updated runtime player loading to resolve all playable profiles by race/class/body variant, equip character-aware starter armor, rebind compatible skinned armor overlays to the player skeleton, and hide only covered body regions.
- Generated and validated the full playable model set: 48 character GLBs and 432 skinned starter armor GLBs, plus the Ember Arcanist/Warbrute browser smoke path.
- Removed visible Chrome scrollbar tracks from the app shell and cleaned up the character-select panel with structured header, list, create-form, and action layouts.
- Fixed local character creation and chat message IDs on browsers that expose `crypto` without `crypto.randomUUID`, such as non-localhost HTTP dev URLs.

## 2026-06-08

- Added a data-driven gathering and crafting system with Scavenging, Butchering, Salvaging, Cultivation, Apothecary, and Talisman Making.
- Added `services.crafting` with localStorage persistence, Supabase stubs, profession progress, cultivation plots, crafting recipes, and station-aware HUD actions.
- Fixed inventory insertion capacity so runtime item grants use the same 24 slots as the inventory UI and local inventory backfill.
- Renamed player-facing classes to the `ability-system.md` roster, centralized the class list in `src/data/careers.ts`, and added legacy WAR-career alias normalization for existing local saves and ability-kit lookup.
- Added a data-driven class ability system with ten-slot hotbars for all 24 playable classes, including class-family metadata, cooldowns, mana costs, class resources, targeting shapes, tags, effects, and animation notify windows.
- Added runtime ability activation with resource validation, delayed impact resolution, projectile travel timing, generic projectile/beam/melee/area/self VFX, enemy hit reactions, healing text, and tracked status effects for roots, slows, staggers, marks, burns, bleeds, debuffs, and silences.
- Fixed ability visuals so transparent pulses, arcs, projectiles, and beams render as additive overlays without writing depth; GLB action clips now sanitize root/scale tracks before playback.
- Fixed ability activation black screens by preventing mana, health, and class-resource updates from remounting the Three.js game runtime; the world now remounts only when the selected character or zone changes.
- Updated the HUD with class-aware hotbar buttons, career-resource display, target status chips, and `1`-through-`0` keyboard activation.
- Added a guarded in-game GM build mode activated with `/gm build`, backed by `VITE_GM_ENABLED` and `VITE_GM_EMAILS`.
- Added the `services.worldEdits` contract plus local IndexedDB persistence for world-edit drafts, published versions, authored objects, and sparse voxel chunks.
- Added Supabase-ready world-edit stubs and documented the future `world_edit_versions`, `world_edit_objects`, `world_edit_chunks`, and `gm_user_roles` schema.
- Added a Three.js GM editor runtime with smoothed voxel sculpting, material painting, prefab stamping, transform controls, standalone colliders, walkable surfaces, undo/redo, autosave, and draft publishing.
- Improved GM prefab brushing with a green unplaced preview, left-click placement, drag-to-chain end-to-end placement, automatic Brush mode when choosing a prefab, and wheel-based X/Y/Z brush rotation.
- Reworked GM build UX so `Tab` cycles Add/Subtract/Erase/Scale with a top-center mode indicator, movement keys remain available after interacting with build controls, and material buttons enter Paint with a live brush preview.
- Fixed GM editor terrain and brush issues by removing hollow voxel side skirts, keeping the previous draft mesh visible until remeshing finishes, making brush drag chains update immediately, and replacing stamp selection boxes with a footprint-based preview.
- Fixed material swatches in the GM editor so selecting grass, dirt, cobble, stone, wood, or water enters Add mode and creates visible voxel terrain; explicit Paint now seeds a shallow patch when used on static terrain with no existing voxel column.
- Added Select-mode object deletion in the GM editor through a Delete Object button plus `Delete`/`Backspace` keyboard handling.
- Added a GM editor `Reset to Live` recovery action that discards the current draft and reloads the latest published world, or the static zone JSON baseline when no published overlay exists.
- Fixed GM editor undo history so it keeps the full active-session stack and can unwind a draft back to the Live baseline instead of stopping after the first loaded snapshot or the old 50-step cap.
- Added GM selection and transform support for static zone props and terrain, with draft overrides, hidden static-object markers, terrain height refreshes, and collision filtering for edited prebuilt objects.
- Reduced the GM editor transform-control gizmo size so selected objects remain easier to see while moving, rotating, or scaling.
- Added a GM editor HUD panel for tool selection, brush/material/prefab settings, snapping, save draft, publish, and selected-object status.
- Added `npm run world:validate` to validate static zone JSON compatibility with authored props, colliders, walkable surfaces, and safe model filenames.
- Implemented the manifest-first model pipeline from `deep-research-report.md`, including asset blueprints, local schema/style policy, neutral generated asset IDs, AI provenance fields, Node validation/generation scripts, and a manifest-driven Blender entrypoint.
- Replaced the Blender MCP surface with manifest tools: `list_asset_blueprints`, `generate_asset`, `generate_asset_set`, `validate_asset`, and `list_generated_assets`.
- Added `public/assets/models/asset-index.json` and updated runtime character, equipment, body override, weapon/jewel, and training-dummy loading to resolve neutral indexed GLBs before primitive fallbacks.
- Replaced the public character builder with `generate_manifest_character.py`, producing cohesive skinned character GLBs, required locomotion/action clips, neutral GLTF extras, QC sidecars, and front/side/back/isometric preview renders.
- Added `generate_manifest_accessory.py` plus weapon and jewel blueprint families with neutral anchors, collider policies, PBR channel declarations, provenance, and generated QC reports.
- Added `mesh_primitives.py` as the neutral Blender helper module, removed the old character/spec builders, removed the legacy extraction placeholder, and deleted obsolete generated preview clutter.
- Tightened validation so existing generated GLBs must have `.qc.json` sidecars with `qcPassed: true`; preview-required characters must record previews, and blocked runtime index entries must include `reviewStatus`.
- Marked unskinned same-origin armor modules and unsocketed accessory outputs as `runtimeReady: false` so the browser skips them instead of mounting broken bind-pose overlays.
- Updated runtime model caching with a new asset version token so regenerated neutral outputs are fetched instead of stale browser-cached files.
- Updated the model-pipeline style policy to treat clean blocky proxy output, floating modules, and fake-looking material breakup as review failures rather than runtime-ready art.

## 2026-05-27

- Re-exported `guard_male.glb` from the supplied guard blend with only the primary skinned mesh, opaque front-sided materials, removed export-only pose constraints, and an upright at-attention idle.
- Added guard-specific NPC runtime prep so the generic skinned-mesh double-sided material safety pass does not reintroduce guard armor shimmer.
- Rebuilt `character_empire_warrior_priest.glb` from `blends/male_base.blend` with the base-male body and fitted armor only, removing the old procedural face, beard, emblem, pouch, and weapon overlay meshes.
- Tightened base-male tabard and cape placement to torso-region depth so cloth panels fit the body instead of floating from whole-body bounds.
- Cleaned up the playable Warrior Priest export further by omitting the floating front tabard and separate arming underlayer meshes, then masking the base body as black arming cloth below the head/neck so shoulders and torso stay covered without extra overlap.
- Updated generated path strips to use visible thickness, short terrain-following chunks, and generated walkable top surfaces so actors stand on paths instead of clipping through them.
- Bumped the runtime asset version token so regenerated GLBs and path strip fallbacks are refetched by the browser.

## 2026-05-26

- Added an in-game settings panel with `Esc`/HUD access, independent X/Y camera inversion, mouse look sensitivity, touch look sensitivity, and zoom speed settings persisted in local storage.
- Added camera obstruction handling so third-person view snaps outside active walls and large solid props instead of staying inside them.
- Added model-backed terrain loading with runtime height sampling so props, NPCs, enemies, and the player align to GLB terrain.
- Added a guard blend export path that produces `guard_male.glb` with preserved skinning and a subtle looping idle animation.
- Replaced guard-role NPCs with the generated guard model by default and updated NPC spawning so GLB idle clips are mixed in the game loop.
- Expanded equipment slots to support modular armor pieces for shoulders, hands, waist, legs, feet, back, and tabard in addition to head, chest, main hand, and off hand.
- Added a `base_male_body.glb` runtime body override for generated `base_male_*` armor items so the interchangeable modules preview on their matching body in-game.
- Added base-male modular armor item definitions and default local inventory entries for the generated chest, shoulder, bracer, belt, leg, boot, tabard, and cape equipment GLBs.
- Expanded the inventory grid to 24 slots and backfilled default local saves with missing starter equipment so existing browser saves can test the modular armor items.
- Converted inventory slots to accessible buttons and allowed click or right-click gear equipping while keeping double-click consumable use.
- Updated the base male armor generator to export `base_male_body.glb` plus same-origin `equipment_base_male_*.glb` modules, with bracers included in the regenerated forearm module.
- Added `generate_base_male_armor_showcase.py`, producing a fitted dark-fantasy armor pass over `blends/male_base.blend`, with combined and armor-only GLBs plus a Blender scene, render, and fit report.
- Added `generate_armor_ready_mannequin.py`, producing an unclothed adult male A-pose armor-fitting mannequin GLB, editable Blender scene, white-background isometric render, and automated armor-fit report.
- Added modular equipment state snapshots so equipped gear preserves item name, slot, icon, and rolled affixes.
- Added right-click inventory equipping for armor and weapons, backed by a shared item catalog.
- Added player armor overlay visuals for equipped head, chest, and offhand gear with procedural fallbacks for missing `equipment_<item_key>.glb` assets.
- Added a `C` key character sheet showing stats and equipped gear.
- Added a deterministic `biomeKits` zone JSON layer for reusable data-driven landscaping.
- Added the first `evergreen_pnw` biome kit with Douglas fir, western red cedar, hemlock, sword fern, mossy boulder, and fallen log primitive props.
- Added path-aware biome corridor exclusions, season-ready biome placement fields, and summer/default evergreen scatter selection.
- Added grass, wildflower, low shrub, path-edge stone, dirt path strip, and cobblestone path strip primitive fallbacks.
- Rebuilt `character_empire_warrior_priest.glb` with continuous wrapped breastplate, gorget, lower coat, belt, shoulder, upper-arm, forearm, and greave shell geometry so the visible armor conforms around body volumes instead of reading as flat plates.
- Added `generate_armored_inquisitor_showcase.py`, producing the original dark-fantasy `original_armored_inquisitor.glb`, organized `.blend` scene, and 1600x1600 white-background isometric render.
- Reworked the armored inquisitor generator around a more realistic humanoid mannequin with a smaller head, longer visible limbs, narrower torso and waist, fitted armor shells, flatter pauldrons, subtler facial marks, and a modeled hand grip on the weapon.
- Added `generate_modular_humanoid_body.py`, producing a reusable `human_base_body.glb`, separate blackened armor overlay GLBs for chest, arms, legs, cloth, and full set, plus 1600x1600 isometric screenshots for each module and the combined fit.
- Restored the missing `PathKit` world helper so `ZoneLoader` can compile and optional zone path definitions expand into non-blocking visual path props.
- Added defensive prop fallback handling and model URL versioning so regenerated public `.glb` files are fetched by the browser instead of reusing stale cached models.

## 2026-05-25

- Fixed mouse-look movement so camera-relative WASD follows right-drag direction instead of mirroring left/right.
- Added left-drag camera orbit, right-drag facing alignment, and both-mouse-button forward movement.
- Improved mouse-look responsiveness so fast mouse drags drive camera and character facing without turn-rate lag.
- Added Codex/Blender asset pipeline support for original generated `.glb` assets.
- Added static Blender asset generation for `dummy`, `gate`, `banner_post`, and `vendor_stall`.
- Extended the Blender MCP server with static asset, vertical-slice, and asset-listing tools.
- Added GLB animation switching for generated player characters.
- Documented the Codex MCP setup and runtime asset conventions.
- Fixed Blender-to-GLB axis normalization so generated assets stand upright in Three.js.
- Added MCP runtime bounds validation for generated characters and animated dummies.
- Rebuilt `dummy.glb` as an upright dark-fantasy training dummy with `idle` and `hit_react` clips.
- Added `character_empire_warrior_priest.glb` with heavy armor, hammer, tabard, parchment, and relic-halo details.
- Updated enemy loading so GLB enemies play idle animations and trigger `hit_react` when damaged.
- Updated Warrior Priest player loading to try the generated GLB before falling back to the procedural rig.
- Fixed loaded player GLB visibility by disabling skinned-mesh frustum culling and forcing double-sided runtime materials.
- Fixed the cached skinned-GLB clone path and made the game canvas mount deterministic so the controlled player renders on the active canvas.
- Added a player-only Warrior Priest silhouette layer over the generated GLB so the centered character clearly reads as a Warrior Priest from the default camera.
- Added reusable animated `castle_gate.glb` plus click-to-open/click-to-close runtime support and closed-gate collision.
- Fixed interactive gate input so short right-clicks open and close gates/doors while right-drag still controls camera/facing.
- Added reusable animated `castle_door.glb` and placed a grand keep entrance plus interior castle doors with closed-door collision.
- Added reusable `castle_stairs.glb` and walkable prop surfaces so castle stairs can raise the player's floor height onto landings.
- Fixed castle floor traversal so upper platforms only become ground after the player climbs within step range instead of teleporting by X/Z overlap.
- Fixed right-click door/gate interaction by tracking mouse clicks from pointer events and adding a forgiving ray-proximity interaction fallback.
- Upgraded the generated Warrior Priest GLB with denser beveled armor, bright steel/brass materials, exposed bald headband, broad layered pauldrons, relic halo, tabard/parchment details, and an oversized decorated hammer.
- Retired the temporary player-only Warrior Priest silhouette overlay so the centered character renders from the generated `.glb` asset itself.
- Rebuilt the Warrior Priest GLB at higher mesh density and fixed Blender cylinder authoring so legs, neck, arms, and hammer shafts align on the game's Y-up axis instead of lying sideways.
- Added a reusable hero procedural character framework with lofted body meshes, curved armor shells, folded cloth panels, shaped glove/boot geometry, and embedded deterministic material textures.
- Rebuilt `character_empire_warrior_priest.glb` through the hero procedural framework at 5.57 MB / 75,716 vertices while preserving the existing animation clip set.
- Added a Warrior Priest hero rig profile with lowered arms and rebuilt the GLB at 5.67 MB / 77,644 vertices so pauldrons, forearm plates, gloves, and hammer grip align in idle instead of reading as an outstretched pose.
- Rebuilt `character_empire_warrior_priest.glb` from the reference sheet with slate-blue worn plate, white tabard, brass skull-sun medallions, scripture/book belt accessories, black gauntlets, fuller beard, and a taller decorated hammer.
- Corrected the Warrior Priest reference model structure with a solid breastplate barrel, filled lower undercoat, inward shoulder sockets, thicker connected arms/gloves, closer pauldrons, and visible accessory straps to reduce holes and floating parts.

### Aegis people city integration

Seven reviewed civic profiles now populate 15 stationary NPC placements: Gateward Market, Cinderbank, Lantern Quays, Bellfound Cloister, Crownwatch Garden and Great Hall. Children remain beside adults. The campaign generator checks clear ground against canal and prop footprints; existing services and patrols are retained. City NPCs use the reviewed middle LOD and custom idle-only civic rig. Rebuild with `npm run campaign:generate` and `npm run models:registry`; verify with `npx vitest run tests/aegisPeople.test.ts` and `npm run world:validate`.

Civilian leather garments now have a contoured waist/chest, belt tension folds, curved hip panels, and laces fitted to the garment edge.
