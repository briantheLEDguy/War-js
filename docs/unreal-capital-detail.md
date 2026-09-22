# Capital street detail pass

The owner requested this pass directly in the official capital. The builder reads
the configured `GameDefaultMap` and adds tagged street fixtures without rebuilding
the city, changing startup configuration, removing actors, or replacing gameplay.
It refuses an unexpected map or a second application, preserving subsequent edits.

`scripts/unreal/capital-detail-stage.py` runs in private CityKitStaging and selects
only the owned town kit's authored `SM_Torch` and `SM_Wood_Plank_Pillar` meshes.
It checks the bounded dependency closure and preserves original package bytes.
Raw dependencies stay in the existing Git-ignored `Medieval_Mod_Town` mount;
generated material instances stay in the ignored `LicensedKits` mount. This is
local development use, not license or release approval.

`capital-detail-layout.py` derives street-side fixture candidates from the existing
city routes. Candidates retain space between fixtures, avoid NPC positions, and
exclude the upper castle. `capital-detail-build.py` rejects candidates overlapping
existing building bounds, adds authored posts and iron sconces with warm local
point lights, and groups existing barrel/crate models along the market edge.
The additions are cosmetic and have no collision, so this pass does not add
movement blockers. They are grouped beneath `Crownward/Street details` and tagged
`WarCapitalDetailV1`; they are not yet editable GM catalog entries.

Houses receive district-specific muted material instances. The instances inherit
the existing textures, normals and roughness; no purchased material is overwritten.
This adds district color variation, not new texture art or complete surface
weathering. The point lights do not implement animated flame effects.

Run the stage script with UnrealEditor-Cmd and `-run=pythonscript -NullRHI`.
Run the builder and `capital-detail-render.py` with `-run=pythonscript
-RenderOffscreen -AllowCommandletRendering -NoTextureStreaming -unattended`.
Use the main editor only when it is closed and its native modules are not being
compiled. An isolated compatible validation project with a main Content junction
can perform the same work without locking the main native binaries.

The build receipt is `artifacts/unreal/licensed-kits/capital-detail-build.json`;
it records the official map hash before/after, original actor count, new fixture
identities and material overrides. The verification script reloads the saved map,
checks preserved/added actor counts and missing meshes, and makes offscreen views.
`python tests/unrealCapitalDetail.test.py` checks the deterministic layout and
candidate spacing. Full interior traversal, GM catalog admission, performance,
three-platform packaging, Steam play and art acceptance remain separate gates.

Verified on 2026-09-21: the official capital contains 126 post/sconce/light sets
and 18 additional market supply props (396 added actors). The original 8,779
actors survived the save/reload; the resulting 9,175 actors contained no missing
static meshes. Houses have 628 overridden material slots using 100 new private
instances. Five fixture candidates were omitted because they overlapped existing
building bounds. Two focused layout tests passed.

Four saved-scene offscreen images were inspected: fixture close-up, market,
avenue and city. The authored sconces and clear avenue placement are visible.
The inherited commandlet light-state limitation still makes wide city views
too dark for final lighting acceptance; these images do not replace an actual
game/editor lighting review. No capture-only light was added and the render
script saved no level changes. The build fingerprints are recorded in the local
receipt; later campaign sublevel attachment will legitimately change the map hash.
