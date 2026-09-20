# Field arms rack — published and locally verified

Frozen release `6eac77928a01ab79cb2e` is published with three actual LODs:
28,246 / 17,116 / 9,606 triangles; 10.00 / 3.77 / 1.24 MB. Five embedded PBR
material sets retain deliberate timber, forged iron, brass, leather and blade steel.
Six packed editable masters pass closed-mesh and material checks. All three GLBs
have zero Khronos errors/warnings and valid UV/normal/tangent data. All nine final
actual-import views were inspected. The reduced grip ring radii account for the
coarser polygon chords, preserving continuous leather coverage at LOD2.

Four original polearms sit in shaped receiving cuts, including closed supporting
heel sockets. Trestle feet, mortised uprights, pegged rails and riveted iron braces
have 162 verified fitting contacts. Five collision masses derive from named actual
geometry; the 1.02m working point supports a half-metre actor. No walkable top or
weapon pickup is claimed.

All 36 keeps now contain one rack and the GM builder includes the same three LODs
and collision contract. Twenty focused furnishing/integration tests pass, including
grounded skids, actual regional wall/stair/furnishing clearance, all keep enclosure
and breach progression, and reachable work fronts. The production build passes;
33 maps, 897 model records and 448 GM definitions validate. The complete suite
passes 1,428 tests in 170 files with one worker. An earlier concurrent run hit
one enclosure timeout; the unchanged 75-test enclosure rerun also passed.

In the actual Cinderfen Game/Player, a two-second northward press stops against
the rack at (-358, 0, 2.562), from (-358, 0, 3.020). The rack is visibly grounded
and clear of the nearby stairs and walls. One unavailable legacy asset remains.
`review/runtime-integration-20260920.json` retains exact model/map/harness hashes
and this bounded check; it is not an exhaustive walk of all 36 placements.
Full shared-campaign and performance acceptance remain unfinished.
