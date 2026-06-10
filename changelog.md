# Changelog

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
- Added Altdorf crafting stations, minimap station markers, starter crafting materials/seeds, salvage outputs, corpse gathering rolls, and craftable consumables/talismans.
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
- Added `altdorf_land.glb` exported from `blends/altdorf_land.blend` as the visible Altdorf major-city terrain.
- Added model-backed terrain loading with runtime height sampling so props, NPCs, enemies, and the player align to GLB terrain.
- Added a reproducible `export_altdorf_land.py` Blender export pass that scales the source terrain and levels a castle plateau for `altdorf_castle.glb`.
- Added rectangular biome no-scatter exclusions and applied them to Altdorf so the evergreen biome surrounds the castle grounds without filling the castle footprint.
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
- Applied Pacific Northwestern evergreen landscaping patches to Altdorf around the riverfront, outer walls, market, and west-quarter courtyard.
- Expanded Altdorf into forested castle grounds with northwest and northeast dirt trails plus a central cobblestone avenue to the north edge of the map.
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
- Wired selected Altdorf props and training dummies to generated `.glb` model names.
- Documented the Codex MCP setup and runtime asset conventions.
- Fixed Blender-to-GLB axis normalization so generated assets stand upright in Three.js.
- Added MCP runtime bounds validation for generated characters and animated dummies.
- Rebuilt `dummy.glb` as an upright dark-fantasy training dummy with `idle` and `hit_react` clips.
- Added `character_empire_warrior_priest.glb` with heavy armor, hammer, tabard, parchment, and relic-halo details.
- Updated enemy loading so GLB enemies play idle animations and trigger `hit_react` when damaged.
- Updated Warrior Priest player loading to try the generated GLB before falling back to the procedural rig.
- Fixed loaded player GLB visibility by disabling skinned-mesh frustum culling and forcing double-sided runtime materials.
- Moved the Altdorf player spawn to the Warrior Priest training dummy yard for faster asset and combat testing.
- Fixed the cached skinned-GLB clone path and made the game canvas mount deterministic so the controlled player renders on the active canvas.
- Added a player-only Warrior Priest silhouette layer over the generated GLB so the centered character clearly reads as a Warrior Priest from the default camera.
- Added a Blender-generated `altdorf_castle.glb` and replaced Altdorf's central castle placeholder with the new model.
- Enlarged the Altdorf castle into a 3-to-5-floor hard-surface structure with explicit collision boxes.
- Added reusable animated `castle_gate.glb` plus click-to-open/click-to-close runtime support and closed-gate collision.
- Fixed interactive gate input so short right-clicks open and close gates/doors while right-drag still controls camera/facing.
- Added reusable animated `castle_door.glb` and placed a grand keep entrance plus interior castle doors with closed-door collision.
- Added reusable `castle_stairs.glb` and walkable prop surfaces so castle stairs can raise the player's floor height onto landings.
- Rebuilt `altdorf_castle.glb` with physical keep door openings and split keep colliders instead of a single solid center block.
- Rebuilt the Altdorf keep interior with a connected grand entrance frame, side rooms, rear hall, stair bays, second-floor platforms, and an upper center platform.
- Fixed castle floor traversal so upper platforms only become ground after the player climbs within step range instead of teleporting by X/Z overlap.
- Fixed right-click door/gate interaction by tracking mouse clicks from pointer events and adding a forgiving ray-proximity interaction fallback.
- Fixed Altdorf castle actor placement by adding foundation/ground-floor walkable surfaces and resolving player, NPC, and enemy spawn heights against them.
- Upgraded the generated Warrior Priest GLB with denser beveled armor, bright steel/brass materials, exposed bald headband, broad layered pauldrons, relic halo, tabard/parchment details, and an oversized decorated hammer.
- Retired the temporary player-only Warrior Priest silhouette overlay so the centered character renders from the generated `.glb` asset itself.
- Rebuilt the Warrior Priest GLB at higher mesh density and fixed Blender cylinder authoring so legs, neck, arms, and hammer shafts align on the game's Y-up axis instead of lying sideways.
- Added a reusable hero procedural character framework with lofted body meshes, curved armor shells, folded cloth panels, shaped glove/boot geometry, and embedded deterministic material textures.
- Rebuilt `character_empire_warrior_priest.glb` through the hero procedural framework at 5.57 MB / 75,716 vertices while preserving the existing animation clip set.
- Added a Warrior Priest hero rig profile with lowered arms and rebuilt the GLB at 5.67 MB / 77,644 vertices so pauldrons, forearm plates, gloves, and hammer grip align in idle instead of reading as an outstretched pose.
- Rebuilt `character_empire_warrior_priest.glb` from the reference sheet with slate-blue worn plate, white tabard, brass skull-sun medallions, scripture/book belt accessories, black gauntlets, fuller beard, and a taller decorated hammer.
- Corrected the Warrior Priest reference model structure with a solid breastplate barrel, filled lower undercoat, inward shoulder sockets, thicker connected arms/gloves, closer pauldrons, and visible accessory straps to reduce holes and floating parts.
