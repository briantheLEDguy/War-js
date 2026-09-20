# Cinderfen peat worker

Original Greenskin marsh laborer for Cinderfen Outskirts. This isolated editable
package uses the retained `mire_brutish_v1_m` sculpted anatomy, its actual weights,
and original embedded textures. It does not alter the published dwarf or share
mutable build inputs with another in-progress character.

The outfit is fitted waxed linen with continuous shoulder/axilla topology, turned
collar and closed sleeve bindings; waterproof tall boots, coarse wool trousers,
a short leather work bib, and a seated tool belt with a sheathed peat knife.
All added visible surfaces are authored mesh profiles or garment surfaces.
No primitive modeling operators or visible imported rig helpers are permitted.

Standing user approval covers aesthetics. Publication still requires actual
three-LOD export verification, all nine runtime clips, surface/arm and clothing
deformation checks, contact measurements, and close/gameplay review images.
Current evidence and limitations are recorded in `WORK_STATE.md`.

Build with Blender 5.0 using `--background --threads 2 --python-exit-code 1
--python authoring/blender/cinderfen-peat-worker/tools/build_inhabitants.py`.
`python authoring/blender/cinderfen-peat-worker/tools/run_quality.py` runs the
actual-export contact, arm-volume, clothing and sole-welt inspections for all
three LODs, then Khronos validation and the eleven focused export regression gates.
Run `inspect_master.py` through the same Blender command before the export suite
to refresh the editable garment continuity receipt after a master rebuild.

`review/inhabitant.html` verifies the selected binary's SHA-256 before loading it
with Three.js, and offers all nine clips, a scrubber and all three LODs. It does
not change campaign state. Generating inputs are hashed at build start and checked
again before atomic publication of the three candidate exports; the master packs
its material image bytes. Retained anatomy and original fitting-tool references
are recorded under `source/`, without duplicating historical release trees.
