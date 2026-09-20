# Cinderfen supply officer

Original female Dark Elf supply officer for Nyra Vex in Cinderfen Outskirts.
The isolated package uses retained `civic_humanoid_v2_f` anatomy and weights,
with racial facial/ear changes and matching rest-joint changes. Exact source
provenance is recorded without copying historical release trees.

The original uniform has a continuous indigo coat from shoulders through its
joined split skirt, full trousers, fitted tall boots, rank bars, a shaped ledger
case and inventory stylus. The scalp, swept hair and tied coil are authored mesh
surfaces. All added visible geometry uses shaped profiles or garment surfaces;
no primitive models or imported rig-display helpers are exported.

`sources/` retains the editable packed Blender master. `runtime/` holds three
actual GLB LODs, each with nine embedded clips. `textures/` retains PBR images,
`tools/` contains generation and current-export inspectors, and `review/` holds
byte-bound reports and actual-import views. `source/` records foundation
measurements and fitting-source provenance. Read `WORK_STATE.md` for progress
and limitations; presence of an export alone does not establish readiness.

Use Blender 5.0 with `--background --threads 2 --python-exit-code 1 --python`
and `tools/build_inhabitants.py` to rebuild. Run `tools/inspect_master.py` with
the same Blender flags, then `python tools/run_quality.py` from this directory.
The quality runner checks literal exported clip keys and midpoints across all
LODs before glTF validation and thirteen focused regression gates. Reports keep complete
measurements in compact JSON. `tools/review_inhabitants.py` renders imported
front/head/side/run/prone and gameplay views with capped render threads.

`tools/inspect_equipment_attachment.py` checks both loaded ends of both ledger
suspension loops against the actual finished belt and case, in the master and
every exported animation key/midpoint. Its per-LOD `equipment_attachment.json`
receipts require contact patches of at least 90 square millimetres, at least
80% of their probes within 1.5mm, a maximum gap of 3mm, and no signed intrusion
deeper than 1.5mm. Rear and side views are required publication evidence.
The rear belt carrier is fitted against all nine source animations in the hip
frame before its loops are constructed; `review/carrier-fit.json` retains the
measured envelope and clearance. The independent export check includes hands
and other exposed anatomy as well as clothing.

`tools/inspect_female_foundation.py` records the actual retained female forearm
and hand section dimensions after the authored racial scale. The arm inspector
requires 90–110% of those per-axis dimensions in every sampled pose, alongside
the unchanged 80–120% area-preservation and 75-degree angular-coverage limits.
Female wrists are not enlarged to meet an absolute width from a different race.
The reference receipt is hash-bound to its foundation and each arm audit.

Standing user approval covers aesthetics. Frozen release `fd4e6fa6555fd764edb2`
is published in the runtime registry, game and GM builder. Nyra Vex retains her
existing identity and placement; local gameplay verified all three distance LODs.
This complete fitted uniform uses its own embedded clips; modular armor,
facial/lip-sync animation and interactive inventory-tool use are not claimed.
