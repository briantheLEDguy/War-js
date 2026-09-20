# Sunmeadow / Cinderfen presentation audit

Read-only audit completed 2026-09-20, snapshot at 18:35 UTC. This report is the only authored file. Published packages, maps, registry and runtime were not changed. Root owns fixes and publication.

## Findings that affect the next work

- The allegedly missing `chr_aegis_city_guard_standard.glb` is present, approved, hash-correct and served correctly. Do not rebuild or substitute that guard to clear the inspector count.
- Both maps request absent `sky.hdr`. The inspector labels the aggregate asset fallback count as “unavailable legacy assets”; that includes HDRI failure. This explains one fallback from the current source and server state, without proving that every historical guard warning was the same failure.
- Local Game currently presents **3 service NPCs as direct primitives**, **14 humanoid enemies as training-dummy GLBs**, and **14 ambient humanoids as direct primitives** across these two zones. These paths can escape the loader fallback counter.
- Shared campaign presentation is different: it resolves a reviewed race-based city cast for combat actors/services, omits unsupported service races, and does not spawn the maps' ambient-life cast. Do not describe the local placeholder count as a freshly observed shared-campaign count.
- Cinderfen has **27 direct procedural town props**. They render as primitives in local Game and are skipped by shared scenery loading. The three `gate` entries are travel portal markers, not the authored ORvR keep gates.
- All **49 distinct explicitly indexed static prop keys**, their primary model/QC hashes and **135 QC-listed LOD files** checked successfully. Existing keep, village and universal furnishings are not missing files.
- Corren Vale's old generated Dwarf assignment conflicts with the actively authored Empire field-captain presentation. Correct the service integration metadata when that package publishes; preserve Corren's identity and the active model.

## Evidence and limits

Inspected current map JSON, registry entries, QC sidecars, GLB JSON/animation contents, source routing and local HTTP responses. No new visual-quality verdict is assigned to older approved city models merely because they are older. “Legacy” below means a pre-regional asset, not a newly proven failed mesh. No fresh browser render or console capture was possible: CUA reported `Browser is not available: iab` and an empty available-browser list. Grounding is current bytes and deterministic routing, not a claimed fresh gameplay walkthrough.

Snapshot includes the newly integrated command tables: Sunmeadow 1,726 props / 6 NPCs / 15 enemies; Cinderfen 1,529 props / 7 NPCs / 15 enemies. Each map has 12 ambient actors (7 humanoids, 5 animals). Field captain and quartermaster profiles were still unpublished at this snapshot.

| File | SHA-256 |
|---|---|
| `public/assets/maps/sunmeadow_march.json` | `1e8ea47c7c29654547e5ce6ee720bbdf1c25eaf5d5bb4f8fd6245a4e49d26d4c` |
| `public/assets/maps/cinderfen_outskirts.json` | `caa323d2aa7e32cd270ce510c16f6c584bf10c9da324e8e32a4c11c07f3dc3b8` |
| `public/assets/models/asset-index.json` | `49b9ab41d0dedbe22227687258645f242f59544948d94a9f4075436a0ea2b633` |

## Guard request and the misleading fallback count

`Enemy.build` (`src/game/Enemy.ts:60`) calls `aegisEnemyGuardVariantFor` from `src/data/modelOverrides.ts` before the ordinary profile resolver. The stable spawn-ID variant selection requests the standard guard for `sunmeadow_march_west_guard_1` and `cinderfen_outskirts_aegis_keep_guard_1`. Thus the filename is a real runtime request even though it is absent from those map records.

`npc_aegis_city_guard_standard` has all approval flags and runtimeReady, primary file size **6,803,172 bytes**, SHA-256 **`2d58fa15806af271a24a512ae779b80fd98ccd7e8c92b921a59586df3ce901fb`**, matching its current registry hash. GLB header is valid, eight images are embedded, no external image references, nine named runtime clips. Halberd, crossbow and captain variants also exist and match their registry hashes. All four returned HTTP **200 / model/gltf-binary** with matching content lengths from `127.0.0.1:5173`.

The actual absent reference is `assets/hdri/sky.hdr`: no corresponding public HDRI directory/file; HEAD returns **200 / text/html** because Vite serves its HTML fallback. `AssetLoader.canLoadAsset` rejects that type (`src/game/AssetLoader.ts:550`), and `loadHDRI` increments `assetFallbacks` and warns (`:741`). `Game.ts:369` calls `setupSky` for the maps' skybox. `Skybox.ts` already supports a procedural environment when no HDR succeeds.

`authoring/blender/frontier-population/runtime-npc-review.html:61` prints the global `assetFallbacks` value as “unavailable legacy assets”. It neither names the failing resource nor limits the counter to characters. `scripts/campaign/generate-static-campaign.mjs:247` supplies `skybox: 'sky.hdr'`. Smallest appropriate fix: make procedural sky intentional for these maps in the generator, or supply a real reviewed HDR if it is wanted. No replacement character asset is necessary. A diagnostic that separates failed models, textures and HDRI would prevent this confusion. A transient or cached failed model request remains possible in an older session; it is not proven current by these checks.

## Service NPCs: exact local versus shared routes

`NpcSpawner.ts:50` sends `npc_frontier_` profiles through the reviewed regional loader. The nonregional branch applies Aegis guard/civilian overrides first (`:63`), then profile/direct model. If neither resolves, `:79` directly constructs the role fallback, without a model HTTP failure or asset-fallback increment.

### Sunmeadow

| Identity / ID suffix | Current local presentation | Shared service behavior / remaining work |
|---|---|---|
| Elira Dawnmarch / `quartermaster` | Override `npc_aegis_people_civilian_female` → `chr_aegis_people_civilian_female_lod1.glb` | Reviewed city civilian; distinct farmland quartermaster still planned |
| Corren Vale / `marshal` | Missing named legacy profile is masked by override `npc_aegis_city_guard_halberd` | **Omitted** because generated race is Dwarf and shared resolver has no matching published regional guard; correction below |
| Mira Stonewake / `scout` | Published `npc_frontier_sunmeadow_high_elf_scout` | Preserved regional profile |
| Alden Voss / `craft_mentor` | Published `npc_frontier_sunmeadow_dwarf_artisan` | Preserved regional profile |
| Serra Brightfield / `forager` | Published `npc_frontier_sunmeadow_empire_herbalist` | Preserved regional profile |
| Edric Hayward / `inhabitant_homefield_farmer` | Published `npc_frontier_sunmeadow_empire_farmer` | Preserved regional profile |

Corren remains **`sunmeadow_march_marshal`**, **Corren Vale**, **Tier 1 Campaign Marshal**, role **guard**, position **x=-419, z=-239, rotY=0**. Map profile is `npc_aegis_corren_vale_tier_1_campaign_marshal` (not indexed). `orvrLayout.populationAssignments` calls him `dwarf`, desired `frontier_temperate_farmland_dwarf_guard`, `planned`. This arises from generic NPC-index round-robin assignment (`scripts/campaign/orvr-zone-layouts.mjs:289-292`), not a bespoke current character contract.

The active `sunmeadow-field-captain/character-contract.json` explicitly targets this same service identity as **Empire male**, profile **`npc_frontier_sunmeadow_empire_field_captain`**. Preserve that agreed build. Add it to Sunmeadow's `REGIONAL_SERVICE_PRESENTATIONS` in `regional-inhabitants.mjs`; the existing integrator changes both the NPC profile and assignment `race/desiredProfileKey/status` while preserving identity, role, position and service access. Add the profile-to-Empire mapping to shared `regionalInhabitants`. Do not revise the model into a Dwarf or change every round-robin assignment. The separate **`sunmeadow_march_field_captain` enemy** is a different entity; publishing Corren will not automatically fix its dummy.

### Cinderfen

| Identity / ID suffix | Current local presentation | Shared service route / next action |
|---|---|---|
| Vask Rauth / `quartermaster` | **Primitive vendor**; missing `npc_riftbound_vask_rauth_riftbound_quartermaster` | `npc_riftspire_greenskin`; original Greenskin quartermaster actively being authored |
| Nyra Vex / `marshal` | Published `npc_frontier_cinderfen_dark_elf_supply_officer` | Preserved regional profile |
| Dren Voss / `dispatch` | **Primitive questgiver**; missing `npc_riftbound_dren_voss_cinderfen_field_officer` | `npc_riftspire_chaos`; original Chaos field officer still needed |
| Gorvak Mirehand / `scout` | Existing `chr_npc_greenskin_m_guard_m.glb` | Reviewed `npc_riftspire_greenskin`; original marsh guard/scout still needed |
| Selk Dreadspire / `craft_mentor` | **Primitive trainer**; missing `npc_riftbound_selk_dreadspire_field_crafting_mentor` | `npc_riftspire_dark_elf`; original Dark Elf craft mentor still needed |
| Kara Ashvein / `forager` | Existing `chr_npc_greenskin_m_ambient_m.glb`, although assignment says Chaos | `npc_riftspire_chaos`; reconcile role/race with an authored regional outfit |
| Barrek Reedhauler / `inhabitant_peat_worker` | Published `npc_frontier_cinderfen_greenskin_peat_worker` | Preserved regional profile |

All shared service behavior above follows `SharedCampaignRenderer.ts:355-365` and `CampaignCharacterPresentation.ts:153+`, and is distance-limited to 260m. Reusing those already approved city profiles locally is a small interim routing repair. It does not satisfy the original regional-outfit production requirement. The Dark Elf city primary has only **idle**; appropriate for the currently stationary service, not an assumed complete combat/locomotion set.

## Local combat placeholders

`Enemy.ts:77-97` falls from a nonexistent character profile to `prop_training_dummy_t1.glb` / indexed `dummy`. The dummy exists, so this is a successful placeholder GLB load, not necessarily an assetFallback increment.

IDs below omit their zone prefix. These **8 absent profile keys** produce **14 humanoid dummy placements**:

| Missing profile | Sunmeadow entity suffixes | Cinderfen entity suffixes |
|---|---|---|
| `enemy_aegis_battlefield_hexer_caster` | `central_caster_1` | — |
| `enemy_aegis_aegis_keep_sage_caster` | `aegis_keep_caster_1` | `aegis_keep_caster_1` |
| `enemy_riftbound_riftbound_keep_guard_guard` | `riftbound_keep_guard_1` | `riftbound_keep_guard_1` |
| `enemy_riftbound_riftbound_keep_magister_caster` | `riftbound_keep_caster_1` | `riftbound_keep_caster_1` |
| `enemy_aegis_keep_captain_captain` | `field_captain` | — |
| `enemy_riftbound_campaign_raider_raider` | — | `west_raider_1`, `central_raider_1`, `east_raider_1` |
| `enemy_riftbound_objective_guard_guard` | — | `west_guard_1`, `east_guard_1` |
| `enemy_riftbound_battlefield_hexer_caster` | — | `central_caster_1` |

The other 12 humanoid enemies use existing guard/captain/raider character files: Sunmeadow has three Empire raiders, three reviewed city guards, one Empire commander and one Greenskin commander; Cinderfen has one reviewed city guard, two Greenskin captains and one Empire commander. The two Riftbound keep commanders are assigned Chaos but use legacy Greenskin captain art locally. These are legacy/race-presentation gaps, not missing downloads.

Shared combat actors come from authority snapshot NPCs and use `campaignNpcProfile` by race/realm (`SharedCampaignRenderer.ts:346-353`); they do **not** execute local `Enemy.build`. A common reviewed resolver policy can remove local/shared divergence. Approved `npc_riftspire_greenskin` and `npc_riftspire_chaos` primary hashes match and contain all nine runtime clips. They are suitable existing race-correct interim bodies, with role-specific regional armor/weapons still outstanding. Do not silently use a farmer as a combat caster merely because both have a `cast` clip.

## Ambient cast: best minimal approved reuse

Both maps lack `cityLayoutVersion`. `Game.ts:459-464` only supplies WorldLife an AssetLoader when that flag exists. Consequently all seven humanoids in each zone take `WorldLife.ts:79` / `:124` directly to `buildWorldLifeActor`, whose builder uses box/cylinder/sphere parts (`WorldLifeAssets.ts:77-92`). In addition, `worldLifeModels.ts:11` rejects every Riftbound actor **before** considering an explicit profile. Passing the loader alone fixes neither reviewed routing nor Cinderfen.

Keep existing actor IDs, routes and separation from services/combat. Add explicit approved profiles and handle them before the realm-default selection; do not make a region pretend to be a city. Suggested minimal assignments (suffixes are `_life_...`):

| Actor | Sunmeadow approved reuse | Cinderfen approved reuse |
|---|---|---|
| `kitchen_worker` | Empire farmer as a working civilian | Greenskin peat worker as a working civilian |
| `supply_worker` | Dwarf artisan | Dark Elf supply officer |
| `caravan_traveler` | Empire farmer or reviewed Aegis walking civilian | Greenskin peat worker |
| `gatherer` | Empire herbalist | Greenskin peat worker |
| `camp_guard` | Reviewed Aegis city guard | Reviewed Riftspire Greenskin |
| `trail_patrol` | Regional High Elf scout | Reviewed Riftspire Greenskin |
| `camp_resting_guard` | Reviewed Aegis city guard | Reviewed Riftspire Greenskin |

This reuses coherent published complete outfits instead of creating new placeholders. Worker reuse is an interim visible cast, not a claim that a specialized cook/traveler outfit exists. All six regional primaries used here were checked against registry hashes and have nine embedded clips, including walk/idle. The Riftspire Greenskin also has nine clips. Avoid the city Dark Elf for moving ambient cast unless its missing walk is explicitly addressed; use the complete regional supply officer instead.

WorldLife currently loads only the primary model, not its approved LOD siblings. Regional LOD0s are roughly 132k–168k triangles; merely enabling seven permanent high-detail bodies per zone leaves a real budget issue. Carry over reviewed LOD selection/culling and actual route/ground-contact checks rather than counting the map assignments alone as done. Current speed handling assumes 2.4m/s for non-civic rigs; inspect foot sliding at the authored route speeds (0.85/1.25m/s) and existing actor scale variation. SharedCampaignRenderer currently has no WorldLife/ambientLife population path, so separate shared integration is necessary if the cast should appear there.

## Town, resource and siege items

Cinderfen's direct procedural town entries have neither assetKey nor model. Local Props uses `pickFallback`; shared loading skips them (`SharedCampaignRenderer.ts:204`).

| Kind | Count | Smallest sensible reuse / remaining original work |
|---|---:|---|
| `banner_post` | 9 | Approved Riftspire banner/war standard for appropriate Riftbound positions; preserve Aegis and neutral/BFO identity. Four keep banners, two camp banners, three BFO banners |
| `life_lantern` | 7 | Approved `riftspire_lantern`, with measured support/collision refit |
| `life_signpost` | 3 | Regional marsh waymarker; existing Aegis waymarker is approved but culturally specific |
| `life_campfire` | 1 | Approved `riftspire_communal_hearth` or `riftspire_war_brazier` if the actual footprint fits |
| `life_bench` | 4 | Original marsh seating; approved Aegis civic bench is a possible interim interior reuse, not a thematic outdoor replacement |
| `gate` | 3 | Travel markers at Bleakroot Causeway, Cindermaw Pit and Riftspire Capital exits; build a regional entrance treatment preserving trigger clearance |

The three portal `gate` colliders are 9m by 2m at scale 0.85. They are not the closed/breached keep leaves. Do not substitute a keep gate and accidentally close travel approaches. Existing general `banner_post`, `gate`, `castle_gate` registry entries are not automatically approved just because their files exist.

All current explicitly indexed prop primaries/QCs passed hashes, approval/runtimeReady checks, and the union's 135 QC-listed LOD models exist with matching recorded hashes. This covers the published modular architecture and nature already in these maps; it is not a new visual/collision acceptance pass.

Sunmeadow still uses 54 approved older city furnishings: waymarkers 15, streetlights 7, planters 7, benches 4, barrels 4, crates 6, handcarts 3, hearths 2, chain winches 2, bridge/washing line/tapestry/war standard one each. Cinderfen uses **21** Aegis city furnishings: handcarts 3, crates 6, barrel clusters 5, planters 6, washing line 1. Universal logistics items are permitted by the user; prioritize Cinderfen's culturally specific planters/outdoor dressing after the actual primitives, rather than replacing every useful crate purely for its old filename.

The two maps also retain **24 direct procedural resource-node visuals** (12 per zone), including herb/wood/soil/water nodes. Sunmeadow's 12 are its only direct procedural props; its two war-scrap nodes display generic `rock`. Cinderfen has 32 direct procedural nature/resource props in addition to the 27 town props. Shared scenery skips these too: gathering coordinates can exist without their visual cue. A small original salvage/scrap cluster has more equipment/gameplay relevance than optional animal polish; keep the remaining vegetation/ecology in the recorded later queue.

Each zone now has three repair benches, three ammunition cradles, three apothecary tables, two supply chests, two arms racks and two command tables. These are present approved universal furnishings, not pending approvals. Shared caravans resolve `frontier_supply_wagon`; ram/oil/catapult use reviewed `SIEGE_ASSET_KEYS` and the published keep gate exists. Across the four keeps the configuration exposes four oil slots, eight catapult slots and four ram spawn points; those are availability slots, not a claim all machines are simultaneously deployed. The production board still calls for full shared escort/siege playthrough and additional compatible crew bodies. No new evidence here says the published siege machine meshes are missing. Regional NPC baked outfits do not imply modular player armor/crew compatibility; keep those technical contracts separate.

## Recommended next order

1. **Finish the active quartermaster and Empire field-captain packages**, preserving Vask and Corren's services; complete command-table runtime verification. Do not create duplicate characters. Correct Corren's metadata with his publication.
2. **Fix approved presentation routing first:** the fourteen ambient humanoids, three Cinderfen service fallbacks and fourteen local enemy dummies have reusable reviewed paths. Apply hash/QC, actual clips, LOD and route checks; maintain a separate list of regional art still to build. Fix the nonexistent HDR reference independently.
3. **Original Cinderfen Greenskin patrol/raider kit with fitted equipment.** Direct scope: Gorvak plus three raiders and two objective guards (six map entities); up to three ambient guard routes provide further appropriate reuse. This has the largest focused new-character coverage. Keep class/weapon fit and full limbs explicit, not palette swaps.
4. **Original regional caster/guard outfits.** Three Empire caster instances, two Chaos magisters and one Greenskin hexer currently appear as six local dummies; two Chaos keep guards are additional dummies and two Chaos commanders have legacy Greenskin art. Build coherent race/role outfits with supported weapons rather than one shared generic caster. These sit on the main BFO/keep loop.
5. **Cinderfen services: Dark Elf craft mentor and Chaos dispatch/forager.** Selk and Dren are the two remaining primitive services after Vask; Kara also needs the intended race/outfit. Their work tools give strong close-view equipment coverage. Sunmeadow's Elira quartermaster is the next distinct civilian profession; her current city model already loads.
6. **Cinderfen town identity kit:** first route the approved lantern/standard/hearth candidates where they fit, then original seating, signposts and travel entrances. Twenty-seven direct procedural placements provide concrete coverage. After that, thematic older outdoor furnishings and the small salvage/resource cue gap.
7. **Remaining siege crew fits and full campaign acceptance**, following the production board: current Battle Prelate ram seat evidence does not cover every body or an advance/counterpush. Shared scene performance matters once regional ambient LODs are active.

Animals stay last: each map has three procedural deer and two procedural birds, plus two older enemy fauna; Cinderfen's lair-spider presentation differs from the planned cinder-wolf requirement. The accepted buck needs no rear-anatomy revision. This audit does not reopen it or claim either zone art-complete.

## Paused runtime follow-up checkpoint

After this report, root assigned the ambient routing repair. The user then requested finishing the current part and committing to change focus. **Stopped before any runtime or test edits.** Only this report was created. The audit findings remain current behavior, not completed fixes.

The inspected minimal implementation boundary is `src/world/WorldLife.ts`, the existing narrow resolver `src/world/worldLifeModels.ts`, the WorldLife loader-handoff line in `src/game/Game.ts`, and a new focused `tests/worldLifeRegional.test.ts`. Existing `tests/worldLifeReviewed.test.ts` and `tests/worldLife.test.ts` provide city/legacy lifecycle regression coverage. Do not edit maps, registry, published packages or shared renderer in that bounded task.

Resume with these concrete decisions:

- Supply the loader for the two known regional zone IDs as well as existing cities; retain the existing city path. Resolve the seven known humanoid actor suffixes per zone through the approved reuse table above, preserving spawn data and routes. Check realm/race before accepting explicit regional profiles. Unknown or rejected profiles remain explicitly unavailable, not silently claimed delivered.
- Regional assets should use `resolveApprovedAssetModels(profile, 'characterProfiles')` followed by `loadModelFull` with an empty loader fallback. This registers/verifies QC and model hashes; merely calling `resolveCharacterAsset` on a non-city profile does not provide the same complete evidence path.
- Retain each LOD's own rig and embedded valid idle/walk clips; reject unusable levels with an explicit actor/profile/model failure record. Distance-select one visible rig, sample it on the common absolute timeline, retain culling/concurrency limits, and expose the actual loaded levels. Do not use the static `loadRegionalNpc` helper unchanged: it plays only idle.
- Preserve shared geometry/material ownership. Dispose cloned skeletons and mixer bindings once, including partially completed and post-disposal asynchronous loads. Never dispose AssetLoader-cached surfaces through the ambient fallback-resource collector.
- Existing WorldLife assumes 2.4m/s for non-civic walk. The regional tailored animation sources specify a 0.16m foot excursion and a 30-frame walk cycle; inspect actual exported duration and stance travel when choosing playback rate. Do not report a foot-slide/contact check from source constants alone.
- Test all fourteen current map identities, cross-realm rejection, unchanged source routes, hash-approved resolver use, actual idle/walk clips per level, near/mid/far selection, culling and re-entry phase, failed/partial assets, load concurrency, pending-load cancellation and shared-resource-safe disposal. Then perform actual Game route/ground/LOD inspection; browser access was unavailable during this audit.

No implementation or test-pass claim is made for this follow-up. Root owns the encompassing commit and paused automation.
