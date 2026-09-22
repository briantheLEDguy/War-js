# Capital appearance preview

The city originally inherited 50,000 lux sunlight with manual exposure compensation
0. Its review capture also added another light and reduced exposure independently,
so the review image did not describe the saved editor lighting. The appearance
preview follows the owner's dark fantasy direction: 18,000 lux, 7,800 K sunlight,
9,000 lux cool shadowless fill, and exposure compensation 0. This uses restrained
lighting and low-chroma surfaces; street and doorway readability still requires native game verification. Saved saturation
0.65 and cold distance haze (density 0.005, starting 35 metres away, opacity capped
at 0.45) reduce the cheerful daylight look. The capture uses these saved lights
and volume settings without capture-only compensation.

The authored main sun has forward-shading priority 1; the cool fill remains at 0.
This gives fog, water and translucent rendering an explicit primary directional
light without changing the scene's brightness or palette. The zone environment
uses the same priority ordering. `scripts/unreal/fix-capital-light-priority.py`
repairs existing capital packages with backups and updates their partition hashes;
close editor/game instances first so the affected level can be saved. Evidence and
backups are under `artifacts/unreal/light-priority/`.
The saved priorities were read back in a fresh capital PIE run; native zone-light
regressions passed with the rebuilt module. Rendered appearance approval remains
separate from these settings checks.

`scripts/unreal/capital_appearance.py` creates a timestamped private copy beneath
`/Game/Capitals/crownward/Appearance_.../AegisCapital_AppearancePreview`. It never
replaces the working map or an earlier preview. The receipt in
`artifacts/unreal/licensed-kits/capital-appearance-preview.json` identifies the map,
source map hash and generated material instances. Saved source city content is
copied; unsaved editor edits are not included. Purchased source materials and mesh
assets are unchanged. Changes are component material overrides in the preview.

Weathered stone, charcoal, muted rust, moss stone and cold limestone palettes use
the kit's existing `Base_Color_Tint` parameter; wall modules use cold limestone. House identity determines stable variation, so actor
iteration order does not reshuffle colors. Textures, normals and shading remain
inherited from the purchased material. Ground and mountain instances use private
copies of the existing textured granite graph with a tint multiplication before
base color; no original terrain material is edited. These are appearance previews,
not full asset visual approval or production GM color-editing support.

## Editing it yourself

In the World Outliner select **Aegis daylight exposure**. In Details search for
**Exposure Compensation** and edit its checked override. A lower value darkens
the scene. This volume is unbound, so its setting applies throughout the city.
Select **Aegis workbench sun** to change **Intensity**, **Temperature** (with Use
Temperature enabled), and rotation for sun direction. Save the level to retain
these changes. The viewport's own exposure override only changes that viewport;
it is not a replacement for editing the saved Post Process Volume.

For a building, select it and inspect its Static Mesh Component's **Materials**.
Open its preview `MI_...` material instance and adjust **Base_Color_Tint**. The
instance may be shared by other buildings; duplicate it and assign the duplicate
to that component when only one building should change. Keep purchased source
materials unchanged. Preview materials live beside the preview map and remain
editable in the Content Browser.

The live working map remains unchanged while the owner has it open. Applying a
preview back to it must preserve any newer saved or unsaved editor work; do not
blindly regenerate or replace the working map.

For the complete pass in your currently open main city, use **Tools > Execute Python Script** and select `scripts/unreal/apply-capital-appearance-in-editor.py`. This optional action operates on the current actors without reloading the level, creates new private instances, and leaves the level unsaved for review. It refuses a different map or a second application; afterward edit the lights and instances directly. Asset creation persists independently of undo; only save the level after reviewing it. This owner-run entry point has not been exercised against a live interactive editor.

The **Crownward cold distance haze** actor controls Fog Density, Start Distance and Fog Max Opacity. Keep the near streets clear when adjusting it. **Crownward soft sky fill** lifts shaded surfaces without changing the primary sun direction. This is an initial gritty color/lighting pass; terrain texture repetition and detailed surface weathering remain unfinished.

The commandlet capture currently under-renders saved environment lights compared with a freshly spawned diagnostic light. Its near-black output is not accepted visual evidence. Use an actual game/editor view to assess the saved preview before applying the pass. The optional editor utility has executed only through its shared appearance function in isolated commandlets, not interactively in the owner editor. Native GM palette selection and appearance editing workflows are not yet verified.
