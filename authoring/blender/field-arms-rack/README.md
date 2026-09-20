# Universal field arms rack

Original keep/town furnishing with four individually proportioned polearms.
The shaped timber feet receive the pegged uprights; mortised rails include open
upper rests and closed heel sockets. Spear shafts taper into forged sockets,
brazed rings and ridged leaf blades. Continuous leather strips overlap around
the grips. Geometry is authored from explicit polygon cages and profiles;
no mesh primitive operators or placeholder geometry are used.

`masters/` retains source and finished packed Blender files at three LODs.
`textures/` holds five original embedded PBR sets (oak, forged iron, brass,
leather and blade steel) at 1024/512/256 resolution. `runtime/` holds literal
GLBs. `tools/run_delivery.py` rebuilds and checks master closure and packed materials,
162 construction contacts, actual GLB reimport views and material tangent bases.
Zero exported MikkTSpace tangents are reconstructed only from the same surface's
UV derivatives; each build records every change. No geometry or UV is hidden by
that correction, and final normals/tangents must be finite, unit and orthogonal.

The collision contract measures five structural masses and reserves a standing
front for a half-metre actor. Two planed skids establish the ground datum.
No walkable top, weapon pickup or inventory interaction is claimed.

Root publishes with `node scripts/campaign/publish-field-arms-rack.mjs --publish`
after reviewing matching final views and all technical checks. Publication freezes
literal source/export evidence, then registry, campaign and GM generation follow.
See `WORK_STATE.md` for current delivery status and gameplay limits.
