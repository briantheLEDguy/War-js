# Crownward capital and castle

Open `unreal/AegisWar/AegisWar.uproject`. The editor startup map is now
`/Game/Capitals/crownward/AegisCapital_Workbench`. If the editor is already open,
open that level through the Content Browser. Press Play, then **G** for City
Builder. **Fly / walk**, **Arrival**, and speed controls remain available.

This is a new editable Aegis capital layout using the installed Medieval Houses
Modular Vol2 and Medieval Modular Town kits. It contains 32 complete house assemblies, a central avenue,
market square with eight stalls, benches, barrels and crates, cross streets, outer ramparts and towers, and a northern castle.
The castle has a 72 × 60 metre curtain enclosure, four projecting corner towers,
a twin-tower gatehouse, courtyard, an 18 × 24 metre keep with upper floors,
windows and buttresses, roof battlements and stone stairs. The terrain is
independent of the original capital's slopes and canals.

There are 3,779 editable placements and 14 unique authored mesh types. Every
visible building piece comes from the purchased kit. Independent ground is
allowed terrain construction, not a scenery fallback. The kit's incomplete
04a/b/c construction stages were excluded from housing after visual inspection.
The other town kit's merged building remains outside this map pending its
entrance/door adaptation.

The original workbench, campaign source identities and drafts remain intact.
Crownward saves local GM edits to `Saved/WorldEdit/crownward-draft.json`; the
reference capital retains `aegis_capital-draft.json`. Drafts remain revision
checked, bounded to 8 MB, and protected against unnoticed external changes.
The generator refuses to overwrite a map whose saved bytes have changed since
its last generation receipt, and refuses regeneration once an owner Crownward
draft exists until that baseline is explicitly reconciled. Save in-game drafts
before leaving Play.

## Reproduction and verification

Purchased source packages are private and Git-ignored. A fresh checkout requires
the licensed pack in CityKitStaging and the existing terrain/character bootstrap.
Run these Unreal Python scripts in order with `UnrealEditor-Cmd`, unattended:

1. In CityKitStaging, `stage-capital-kit.py` stages an explicit mesh selection
   and its checked dependency closure. Run `inspect-capital-kit-props.py` and
   `stage-capital-kit-props.py` there as well for town-kit market furnishings.
2. In AegisWar, `build-kit-capital.py` builds the new map from the deterministic
   `capital_kit_layout.py` specification. `-NullRHI` is sufficient.
3. `npm run unreal:crownward-proof` runs native GM construction, undo/redo,
   save and fresh-process reload checks, plus capsule sweeps along the arrival,
   avenue, castle gate and main-hall route. It uses isolated test drafts.
4. `render-kit-capital.py` runs with `-RenderOffscreen -AllowCommandletRendering
   -NoTextureStreaming` and exports city/castle/avenue/courtyard images under
   `artifacts/unreal/licensed-kits/` without using desktop input.

`python tests/unrealCapitalLayout.test.py` checks deterministic identities,
castle sections, main-route wall gaps and builder bounds. Native foundation
tests include a 4,000-object draft round trip and rejection above the size cap.

This is a development city for exploration and GM authoring, not complete
campaign/world parity. NPCs, services, encounters and travel from the original
capital have not been transferred into this new layout. Every house interior,
stair route, wall walk, collision seam, lighting condition and district-scale
performance still needs full playtesting. Windows editor checks do not establish
Linux/macOS, packaged-build or release acceptance. Shared GM authentication and
licensed-asset distribution review remain open; release admission stays closed.

Verified locally on 2026-09-21: the final 3,779-placement native GM/route/reload
receipt is `artifacts/unreal/capital-proof/crownward-1790004111151/report.json`.
All 21 native foundation groups, 85 migration-tooling tests and six layout/owner
draft protection tests passed; tooling typecheck and Python syntax checks passed.
City, castle, courtyard, avenue and market offscreen renders were inspected.
