# Siege crew work state

## Resumed and runtime integration verified — 2026-09-20

- User resumed the work. Published GLB bytes are unchanged. Production seat placement now updates position and inward facing together on boarding, driving and strikes.
- Voluntary dismount rejects `dismount_position_blocked` and preserves the occupied seat if every tested landing/traversal is blocked. Forced death/disconnect/destruction clears ownership without teleporting through an obstruction. Legacy partial/duplicate/invalid seat records normalize to unique stable seats; stale records are removed on cleanup and restore.
- `runtime-siege-review.html` now renders the two actual equipped Battle Prelate avatars with the same crew/gear presenters as the shared game. Its isolated authority fixture is in `siege-review-authority.ts`; the ram starts 8m outside the closed gate. Controls cover drive, turn, strike, left/right dismount, reboard, detail changes and reset.
- Browser verification on September 20: both avatars loaded, strike accepted and frozen at 0.70s, LOD0/1/2 preserved that phase, left dismount restored the hammer and ground placement while right seat stayed fixed, reboarding succeeded, 90-degree turn carried both actors, and live driving reported 2.50m/s. This is the production presenter/authority review page, not a full networked multiplayer gameplay acceptance.
- New focused tests cover blocked exits, legacy seat repair, the authority review fixture, actual renderer LOD/release lifecycle, and signed dependency loading/tamper rejection. Final combined check passed **40 tests in 9 files**, and typecheck passed after the facing synchronization change.
- A broader ORVR/presenter run passed 194 tests in 27 files; the road-network suite was temporarily blocked by Cinderfen stair contract publication in progress. Root owns final full-suite validation and documentation/commit.
- Vite preview was last started on port 5173 as session **55684** for root's collision/workshop review. In this environment, edits to authoring HTML inline module scripts were not invalidating Vite's cached HTML proxy module, even after browser reload. Restart Vite after those edits before claiming a fresh browser check. No commit or deployment performed by this agent.
- Crew fitting remains limited to the approved male Battle Prelate body family. Other player bodies remain their actual existing avatars; no body substitutions or fabricated fit claims.
- Root's follow-up road task: fitted generic inner keep footpaths to actual scaled door leaves, preserving the broad 5m forecourt approach and 12m supply route. The path width leaves space for the existing 0.6m ribbon feather on each side. Sunmeadow and Cinderfen retain their authored road widths even before regional architecture replaces initial legacy props. Root regenerated campaign outputs; all 39 road tests pass within the final 1,322-test integrated suite.

## PAUSED by user — 2026-09-09

No further implementation, fixes, renders, or tests. All owned build/render/test processes have finished; remaining session handles were closed at pause. Preserve these edits and runtime packs.

### Saved and verified

- Two animation-only runtime packs are published under `public/assets/models/`: `frontier_ram_crew_left_animations.glb` SHA `f321c11885807db51c8939d397feaf4cb3a84d404cde20f0284c3250397f78a7`; right SHA `699c385c4a08d5af326b46b3a2a55a7b33e12fb58960a228482b6094cbea48a4`.
- Each contains 60Hz `ram_crew_idle` (4s), `ram_crew_drive` (1.6s), and `ram_crew_strike` (1.5s, impact .7s). Canonical body/equipment and ram GLBs were not changed. User standing approval is saved in `review/approved_crew.json`.
- Actual imports: max hand marker error .772mm, foot origin drift .313mm, rest-matrix difference 4.28e-6, source/export difference 1.49e-6. Crew/crew and mantlet/frame triangle intersections are zero at rest, retract, impact and recovery. `review/actual_contact.json` passed; two Khronos checks report zero errors/warnings. `review/actual_strike_contact.png` and `review/actual_import_assembly.blend` exist.
- Editable master: `masters/frontier_ram_crew_animations.blend`. Runtime packages and copies in this package are preserved.
- Focused tests completed immediately before pause: **25 tests passed in 5 files** (`orvrRamCrew`, `campaignSiegeCrewPresentation`, `orvrEquipmentOperator`, `orvrSiegeOperations`, `campaignSiegePresentation`). TypeScript check passed after runtime code changes.

### Integration edits saved, browser verification incomplete

- New `src/game/network/CampaignSiegeCrewPresentation.ts` applies signed compatible packs to existing Battle Prelate male avatars, suppresses hand-held equipment while mounted, restores prior visibility on dismount, and samples the confirmed zone clock. Other bodies are not replaced.
- `SharedCampaignRenderer.ts` integrates operator actors, follows the same interpolated engine transform, stops ordinary locomotion while posing, and supports optional scenery `defaultAnimation` with per-LOD mixers. Scenery animation was not separately tested in-browser.
- `src/shared/orvr/equipment.ts`, `protocol.ts`, and seat-specific portions of `simulation.ts` add authority yaw, distinct stable physical seats, boarding/dismount path checks, and ground dismount placement. No `blocked`, `moveBy`, navigation or keep-generator algorithm edits were made. Root/other agents own concurrent keep-collision work.
- `AssetLoader.ts` and `runtime-registry.mjs` resolve/preserve/validate signed `operatorAnimationPacks`. Existing ram approved manifest and LOD0 QC carry those dependencies. `npm run models:registry` completed (and its normal GM generation side effect ran). No fake animation-only GM mesh entries were created.
- Existing `tests/orvrSiegeOperations.test.ts` fixture now parks the ram outside the gate instead of inside its closed collision slab. New focused test files are saved.

### Still outstanding when resumed

- Update `authoring/blender/orvr-frontier/runtime-siege-review.html` for the two actual boarded-player avatars and its ram authority fixture; **this file was not edited**. Its old fixture parks inside a closed gate and is incompatible with the new boarding path check.
- Run actual shared-campaign/browser verification of boarding, seat persistence, movement/turning, strike, LOD changes, weapon restoration and disposal. No browser integration success claimed.
- Review the final diff, registry/publication dependency tests, and full relevant ORVR checks after root's concurrent collision changes. No build or complete regression suite was run.
- Editable master is at 60fps, while its imported ram source action still uses its original 0..45-frame range; retime that master-only preview action to synchronize its 1.5-second display if required. Published ram GLB and crew runtime timing are correct and must remain literal.
- Review the rare all-dismount-candidates-blocked case and legacy saved seat-map cleanup before calling the authority integration complete.

The notes below describe the earlier source-fit boundary and are retained as history.

Two standing operators fitted to the literal published Bull-brow Mantlet Ram. Stage only; root owns publication. No fauna work.

## Contract in progress

- Reuse canonical Battle Prelate body, approved novitiate equipment, and unchanged humanoid_game_v2 rest skeleton at scale 1.
- Author animation only: braced idle, braced drive, and strike synchronized to the published ram_strike (1.5 seconds, impact at 0.7 seconds). Ram and avatar world roots remain authority-owned.
- Measure the actual exported footboards, moving grips and operator sockets before choosing external actor transforms. Do not substitute socket height for measured sole contact.
- First deliver source assembly proof with both fitted operators; then animation export and actual-import contact/clearance evidence.
- No new body geometry or accepted asset edits. All new files remain in this package.

## Current boundary

Published ram LOD0 hash: b5e79265f4cd65759c6c1c0f60c10f21f11ffe095d4d5e5124ffc742ecb905ef. `review/input_measurements.json` binds actual ram nodes/socket bounds, full striker excursion and canonical source rest matrices.

The actual imported `ram_strike` action has multiple object slots and runs at action frames 0..45. Playback must preserve each NLA strip's selected action slot; using the first slot silently leaves the striker static. Measurement now asserts +.28m retract and -.34m impact excursions.

Initial source assembly is being built from literal approved public body/equipment GLBs (with resolver hash checks and equipment rest-matrix equality), rather than approximate proxy characters. Two inward-facing operators at x±.71 use per-boot raycast board heights and a supported crouch. Existing canonical hand fitting helper closes fingers around the actual 31mm-radius grips. Root matrices remain static. Sourceproof is pending; no exported crew animations or acceptance yet.
