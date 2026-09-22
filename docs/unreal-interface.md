# Native in-game interface

The controller-owned UMG/Slate shell uses shared charcoal/gold styling and server-validated gameplay panels. `WarInterfaceWidget` owns navigation; `WarPlayerControllerInterface` owns modal transitions and preferences; `WarPlayerControllerControls` persists bindings and rebuilds controller/pawn mappings. `WarInterfaceCatalog` reads the existing campaign/wiki export. `WarAtlasPage`, `WarGuidePage` and `WarGmPage` provide maps, the reference library and GM utilities. `WarQuestHud` displays replicated vitals, progression, quests and radar.

## Controls and options

Defaults: Escape menu/resume, M map, C character, I inventory/crafting, L quests, H/F1 guide, F2 GM tools, G builder, E interaction. Options > Keyboard & mouse bindings changes native actions and saves immediately. Escape and F1 remain reserved; conflicts are rejected. Click an action, then press a key or mouse button. Wheel zoom is fixed. Guide controls describe defaults.

Camera look/zoom sensitivity, inversion and volume save immediately. The shared [Graphics page](unreal-graphics-settings.md) is available from character entry and Options. It adds display modes and supported resolutions alongside quality, view distance, render scale, VSync and frame cap, with draft editing, timed confirmation, rollback and startup recovery. Touch controls and automatic dynamic resolution remain unfinished. Panels do not pause the world. One gameplay panel owns input capture; entry errors retain their separate input block.

## Original-game comparison

Compared directly with `src/ui/hud/Hud.tsx`, `CampaignMapPanel.tsx`, `WikiPanel.tsx`, `GmPanel.tsx`, `WorldEditorPanel.tsx` and `SettingsPanel.tsx`.

| Original feature | Native coverage |
| --- | --- |
| Exit to Login | Confirmed session exit/reload into character entry; warns that development progression is session-only |
| Settings/guide/map/campaign/GM navigation | Available in the styled shell |
| Clean Map | Dedicated menu entry and map button hide optional markers, retaining geometry/player |
| Zone / Route / Campaign | Click deeper, right-click out, pan, pointer-centred zoom, Fit and Current |
| Map layers | People, quests, crafting, resources, enemies, exits, objectives and places; loaded actors for current zone, reference data elsewhere |
| Campaign state | Complete 32-zone authored graph; homeland colours, **not live ownership** |
| How-to/wiki | Four native how-to pages plus all 305 original pages; section, full-text, tag and table search; browser pages labelled as references |
| GM movement/recovery | Fly/walk, 0.25–6x speed, spawn return, coordinates, health/mana restore and implemented cooldown reset |
| GM travel | Exact unique current-world character lookup; trusted loaded reciprocal zone arrivals with safe landing checks. Saved-character lookup and unbuilt destinations unavailable |
| Builder | Trusted model catalog, selection, transform, snapping, surface placement/drop, rows, duplicate, bounds/distance measurement, hide/restore, undo/redo and draft save/load |
| Draft reset | Two-click confirmation; revision checked and undoable; Save explicitly persists reset |
| Terrain/collider authoring | **Unfinished:** voxel add/subtract/smooth/flatten/roughen/paint, generic collision/walkability editing, point-to-point ruler and placement ghost |
| Shared publication | **Unfinished:** shared persistence, production GM roles and publication transaction |
| Other gameplay UI | Configurable bars and hostile target selection are native; class skill execution/resources, chat/social and remaining browser settings still require migration |

GM commands recheck authority and `UWarWorldEditSubsystem::CanUse`. Open `unreal/AegisWar/AegisWar.uproject`, use local Play or Standalone Game, and enter a character; F2 opens GM tools and G opens the builder. The repository enables `bEnableLocalDevelopmentGM=True` in `Config/DefaultGame.ini`, so standalone development launches no longer need extra arguments. Disable **Enable local development GM** under Project Settings > Aegis War migration to restore standalone opt-in through `-WarDevelopmentGM`; local PIE retains access. Rebuild the Editor (and Game for direct game launches) and restart running sessions after this code change.

Access still requires a supported workbench map, an authoritative local controller with a pawn, and successful character entry. Shipping builds and every networked mode (including listen servers and networked PIE) reject local GM access regardless of the setting or launch flag. This is not a production Steam/admin-role implementation. Invalid destinations preserve the character position. Missing models never produce primitive substitutes. Cooldown reset targets only implemented cooldown tags, preserving other effects. Reset/duplicate use revisioned history and trusted native templates. `AegisWar.Foundation.LocalGmAccess` covers the launch policy, network/Shipping denials and actual standalone workbench access.

Local GM verification (2026-09-22): Windows Editor and Game builds passed, along with 32 native automation groups, 94 tooling tests, tooling typecheck and migration audit. Native automation ran without `-WarDevelopmentGM` and verified access through the configured default. This change was not manually checked through the rendered UI; packaging and release acceptance remain blocked.

## Verification

```sh
npm run unreal:audit
npm run test:unreal
npm run typecheck:unreal-tools
npm run unreal:build -- --target Editor
npm run unreal:test-native
npm run unreal:build -- --target Game
```

Launch UnrealEditor-Cmd with the project, configured capital map and `-game -WarDevelopmentGM -WarInterfaceProof -WarProofScreenshot -RenderOffscreen -windowed -ResX=1280 -ResY=800 -unattended` for rendered verification. `Saved/InterfaceProof/report.json` records twelve interface views, including UI Settings/Edit UI, Slate drag/save/release, live duplication/reset/undo, modal handoffs, complete catalog counts, GM recovery/cooldown isolation, rejected teleport stability, control/camera storage and entry-error isolation. Screenshots are beside it. Only a fresh successful process/report counts. The fixture never runs in Shipping or saves world edits.

Focused native automation covers catalog routes/search, GM input/landing validation, key conflicts/reserved keys and reset undo/redo. Windows builds and local smoke tests do not establish Steam, packaging, three-platform, production admission or full UI acceptance. The release gate remains blocked until those requirements are independently verified.

## Verified on 2026-09-21

Windows Unreal 5.8.2 Editor and Game builds passed, together with 26 native automation groups, 91 tooling tests, tooling typecheck and the required migration audit. The fresh 1280x800 rendered proof passed all ten panels, GM duplication/reset/undo on real imported actors, recovery/cooldown isolation, rejected teleports, binding/camera storage and modal input checks. Campaign, local map, guide, GM and builder screenshots were inspected under `unreal/AegisWar/Saved/InterfaceProof/`. The final report has `passed: true` and `fullUiParity: false`.

This does not verify every mouse/keyboard gesture, live campaign ownership, remote GM authorization, audio listening, packaging or other platforms. Existing world lighting warnings remain outside this UI change.

## Owner-provided menu artwork

`Content/UI/menuback.png` is an unchanged copy of the supplied 1672x941 RGBA image (SHA-256 `05b4cac5c09897b4e30cce658f597a4ae2646e837e09be4b156852ee4dc54dba`). `SWarMenuFrame` paints five columns and three rows directly from UV regions: fixed-aspect corners and centre crest, extensible rails and a mirrored repeating stone centre that keeps its texture proportions. `WarMenuFrameLayout` aligns slices for wide/tall panels. Content receives safe interior padding and retains scrolling. Entry and field journal windows use this component. Inventory, quest, service and builder windows now use the separate owner-provided window artwork described below. `DefaultGame.ini` stages the UI directory as UFS for the runtime brush path; packaging acceptance remains separate.

Menu-art validation: Windows Editor and Game builds, 27 native automation groups, 94 tooling tests, tooling typecheck and migration audit passed. The final rendered smoke passed; wide menu, tall builder and entry screenshots were inspected and copied to `artifacts/unreal/menu-art/`. The original image hash is unchanged. These are layout/runtime checks, not packaging or full UI parity acceptance.

## Configurable action bars and Edit UI

Open Escape > UI Settings (also under Options). Add any number of bars and select 1-10 buttons for each. Each button offers an action selector, key capture and Clear key binding. Duplicate keys, Escape/F1, axes and modifier-only keys are rejected. Bindings are individual keyboard or mouse buttons, without modifier chords. The first bar defaults to 1-0; additional bars start empty and unbound.

Edit UI closes the menu and shows gold drag handles. Drag bars and click Done or press Escape to save and return to UI Settings. Normalized positions keep bars within the viewport after resolution changes. Bars can overlap by choice. Resizing preserves assignments and keys for hidden buttons; those keys remain reserved but hidden buttons do not execute. Removal releases the keys. There is no fixed application bar-count limit.

Tab cycles visible nearby hostile NPC/player targets; V enables cursor interaction with bars. Actions and target state remain subject to server validation. Basic strike reads its real GAS cooldown and mana/range requirements; potion shortcuts find a matching item in bag-slot order and use the existing revision-checked inventory RPC. Class kits, resources, global cooldowns and effects are now connected; see [native abilities](unreal-abilities.md). Multiple target frames and chat/social remain outside this migration.

Implementation: WarActionBarWidget builds the bar buttons and drag handles; WarPlayerControllerActionBar handles targeting and activation; WarPlayerControllerUiLayout owns stable bar IDs and layout persistence in AegisWar.ActionBar and action assignments in AegisWar.ClassActionBar.<career>; WarPlayerControllerControls saves individual keys in AegisWar.Controls. WarActionBarTests uses a disposable config to cover creation, resizing, reload, conflicts, removal and unavailable actions. The opt-in interface proof includes UI Settings, Edit UI and the live HUD.

Action-bar verification (2026-09-22): Windows Editor and Game builds passed; 39 native automation groups, 94 tooling tests, the required migration audit and tooling typecheck passed. The full rendered proof passed with 10-, 5- and 1-button bars using a separate preferences file. Real Slate pointer routing verified movement, saved position and mouse release, then restored the fixture position. Final UI Settings/Edit UI/HUD screenshots were inspected and copied to artifacts/unreal/action-bars/. Add -WarActionBarProof to the normal proof flags for a focused drag check. That historical proof predates the class-ability integration; three-platform/Steam release acceptance remains unfinished.

## Additional owner-provided UI artwork

The six PNGs in `unreal/AegisWar/graphics-new/` are copied unchanged to `Content/UI/`. `WarUiArtwork.h` paints ability artwork and the expandable `SWarArtWindow` from UV slices. The first and last buttons of multi-button bars use the supplied endcaps, which include their button interiors; single-button bars and middle buttons use `abilitybarsingle.png`. `WarAbilityBarLayout` maps each source inner rectangle onto the same 84x84 logical square. Shared gold rails meet at one common cell pitch, with no transparent gutters. Endcap ornaments extend outside the row into reserved bounds; the complete bar scales uniformly to fit smaller viewports. Labels use identical padding on all buttons. The Edit UI handle reserves the same height when hidden so entering edit mode does not resize the artwork.

`WarQuestHud` loads `healthbar.png` and `minimap.png` once into retained textures. Replicated health, mana and XP fill the three tracks; the radar retains its live service and player markers. Inventory, quest log, city services and world builder use `window.png` with fixed corners and expandable rails/interior. The earlier `menuback.png` remains on entry and main menus. No supplied images are regenerated or destructively cropped. Native `UiArtwork` automation checks all six runtime PNGs decode at their expected UV source dimensions and match the supplied bytes. `AbilityArtworkLayout` verifies equal square interiors, adjoining rails, contained ornaments and viewport fit for 1-10 buttons.

Artwork verification (2026-09-22): Windows Editor and Game builds passed, together with 43 native automation groups, 97 tooling tests, tooling typecheck and migration audit. The final full rendered interface proof passed, including Slate bar drag/save/release. HUD, Edit UI and tall builder screenshots were inspected and saved under `artifacts/unreal/ui-art/`. All six runtime PNG hashes match their supplied originals. These checks do not establish packaged, Steam or three-platform acceptance; full UI parity remains false.
