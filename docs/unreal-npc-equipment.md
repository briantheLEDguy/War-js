# Combat NPC equipment

Every native humanoid combat NPC requires an explicit equipment binding. The
current saved world has nine equipped combat actors: three Sunmeadow raiders
carry patrol spears; three Bastion guards carry spears and Aegis heater shields;
Corren Vale and Cinderfen's supply officer carry sheathed officer sidearms; the
Sunmeadow scout retains her source-authored recurve bow, arrows and quiver.
Civilian services do not automatically receive weapons. Unbuilt campaign NPCs
and enemies remain unfinished; this does not claim world-wide population completion.

`WarNpcEquipment` resolves exact profile, actor identity, role and native body
bindings from `CombatLoadouts`. Missing weapons, bones, materials, body provenance
or ambiguous bindings prevent enemy combat readiness and destination admission.
The scout's embedded equipment is checked against its exact body and material
slots, so another bow is not added over the existing one. Creature combat will
need explicit natural-weapon contracts when its native models are implemented.

Attachments are transient components, visible in the editor and during play.
They follow animated bones, have no collision or navigation contribution, and
are reconstructed without duplication after streaming reload. They do not alter
authored actor identities or level packages. Authored-state snapshots exclude
only components bearing both the native equipment tag and Unreal's transient
flag. The catalog uses soft body/weapon references to avoid retaining other
zones' character meshes after unload.

`migration/npc-equipment-sources.json` fingerprints the existing guard authoring
records and lists exact extracted parts. `export-npc-weapons.py` evaluates their
authored geometry, preserves UV/PBR surfaces, and consolidates identical material
bindings. `import-npc-equipment.py` creates isolated native assets, calibrates
bone-relative attachments from the saved NPCs, and saves only the separate
catalog. It backs up an unchanged owned catalog before regeneration and rejects
owner edits. Identical reruns leave the catalog untouched.

Run the export with Blender, then the import in the Unreal Python commandlet.
Run `verify-npc-equipment.py` with `-AllowCommandletRendering -RenderOffscreen
-NoTextureStreaming`; it checks every currently placed combat NPC, repeated
attachment, idle/run/attack/death bone following and unchanged saved map hashes.
Captures include temporary inspection fill and do not approve zone lighting.
Evidence is stored under `artifacts/unreal/npc-equipment/`.

Native automation includes `AegisWar.Foundation.CombatNpcEquipment`. The live
`-WarEnemyProof` also requires the raider's weapon before combat and after
unload/reload/respawn. Run the portal and two-client zone regressions whenever
readiness changes. Source-specific grip poses, weapon-specific attacks, guard
combat behavior and final visual approval remain open. A carried officer sword
is not an implemented draw/sheathe or melee system. Release acceptance stays blocked.

## Paused checkpoint — 2026-09-22

Paused at the owner's request after saving the equipment catalog and source.
Editor and game builds passed, as did 35 native automation groups, 94 tooling
tests, tooling typecheck and the Unreal audit. The strict release check still
exits 1 because release acceptance remains incomplete. Saved-world verification
covered all nine equipped actors, 36 animated bone-follow samples, repeat import
and attachment without duplicates, unchanged map packages, and all 9,150 saved
capital actors. The equipped raider's live combat, reward, unload/reload and
respawn proof passed.

The subsequent 70-route portal regression was deliberately stopped for this
pause; its partial log is not a passing result. The two-client regression after
the equipment readiness changes has not run. Resume with those two checks and
refresh the travel receipt before continuing first-pair content. Grip poses,
officer draw/sheathe, guard combat and final player-view approval remain open.
No zone or production release is accepted as complete.

The local checkpoint and evidence paths are recorded in
`artifacts/unreal/world-portals/equipment-pause-receipt.json`. Existing dirty
worktree changes were retained; no commit or publication was made.
