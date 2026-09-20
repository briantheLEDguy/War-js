# Model Pipeline Style Policy

The model pipeline uses the research report as its source of truth.

## Authoring Rules

- Treat manifests as authoritative. Blender object names are labels only.
- Runtime geometry exports in meters, right-handed, `+Y` up and `+Z` forward.
- Skinned body-worn modules share the canonical humanoid bind pose and root.
- Missing model files must never hard-fail the browser runtime.
- Use glTF-compatible metallic/roughness PBR channels by default.

## Visual Readiness

- Characters should read as layered dark-fantasy silhouettes at gameplay distance: helmet/hood, shoulders, torso, waist, cloth, boots, and carried/accessory forms must separate clearly.
- Materials must break up by function: blackened or worn metal, dark leather, saturated cloth, skin, trim, and gem/emissive accents should not collapse into one flat color family.
- Visible primitive/proxy models are not acceptable for the Unreal migration target. Use finished complex repository models or adaptations, with actual silhouette, fitting, animation and material review. Preserve invisible collision/navigation, terrain construction, editor guides and intentional effects. Replace legacy dependencies before deleting them; no new primitive fallback may hide a missing character or prop.
- Preview renders are part of QC for playable characters. If front/side/back/isometric previews reveal broken proportions, exposed fit seams, or fake-looking blocky gear, the asset should fail review even if the GLB exports.

## AI Use

- AI can be recorded for concept, silhouette, material seed, and QC triage stages.
- AI is not the authority for final topology, UVs, skinning, LOD seams, or collider policy.
- Every AI-assisted asset must record `aiAssisted`, `aiStages`, prompt/reference IDs when available, and similarity-review state.

## IP-Safe Generated Assets

Generated asset IDs, filenames, material labels, manifests, prompts, and GLTF extras must use neutral names. Do not use protected faction, character, deity, heraldry, or branded-world terms in generated asset semantics.

Existing gameplay identifiers may still be mapped to neutral asset profiles by runtime code until the broader game-content layer is renamed.
