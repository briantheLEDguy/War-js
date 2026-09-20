# Sunmeadow field captain

Original fitted adult male Empire field uniform for the existing Corren Vale,
Tier 1 Campaign Marshal. This package preserves his NPC identity and role;
publication, map/GM integration and runtime verification belong to the campaign
pipeline. The immutable identity is in `character-contract.json`.

The retained male civic anatomical foundation has its literal GLB, quad cage,
editable master and QC hashes in `foundation-provenance.json`. Source construction
uses continuous tailored surfaces, explicit panels, section lofts and shaped
sweeps. `tools/captain_details.py` builds the brigandine, fitted shoulder padding
and three steel lames, Aegis field shield, two distinct belt cases, and their
physical suspension. It does not construct primitive replacement models.

`sources/` retains packed editable source and final LOD masters. `runtime/`
contains three actual skinned GLBs with embedded materials/textures and the same
nine fitted animation clips. `review/` retains actual import renders and measured
anatomy, topology, motion, boot, layer, garment and attachment evidence. Every
receipt refers to the exact model/source bytes it measured. A receipt from an
older revision cannot approve a newer export.

Run Blender in background mode with two threads. Source construction and tagged
export use `tools/build_inhabitants.py` and `tools/export_tagged.py`. The tagged
exporter protects the actual reviewed LOD1 boot topology and skin weights in
LOD2; direct binary tests verify exact preservation and closed boot surfaces.
The rest of LOD2 remains reduced.

For each LOD, the independent Blender inspection tools are
`inspect_arm_volume.py`, `inspect_export_motion.py`, `inspect_boot_clearance.py`,
`inspect_boot_welt.py`, `inspect_outfit_clearance.py`, and
`inspect_equipment_attachment.py`. They accept `--lod=N` after Blender's `--`.
Use `--report=frontier_sunmeadow_empire_field_captain_lodN_arm-volume.json` for the
arm report. `inspect_master.py` and `inspect_shoulder_routing.py` measure the
editable master. `review_inhabitants.py` imports the actual GLB and renders
`--views=head,front,side,rear,run_side,death:2,gameplay --suffix=_final`.

After current reports and reviews exist, run the Node validator, retain the exact
validation inputs, and run the read-only technical gate:

```powershell
node authoring/blender/sunmeadow-field-captain/tools/validate_inhabitants.mjs
python authoring/blender/sunmeadow-field-captain/tools/retain_validation_inputs.py
python authoring/blender/sunmeadow-field-captain/tools/test_exports.py
```

Diagnostic or selected-clip reports are development aids and do not satisfy the
complete gate. Clearance, anatomical volume, topology, motion and attachment are
independent checks; none substitutes for actual visual inspection. The outfit is
one fitted NPC asset, not modular armor or a weapon-draw system. Authoring checks
do not establish in-game collision, navigation or network behavior.

Current status is recorded in `WORK_STATE.md`. This draft is not publication-ready
until all gates and current import views are complete.
