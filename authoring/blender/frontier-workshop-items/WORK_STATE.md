# Published September 20, 2026

Both workshop items are delivered to the game and GM builder under standing
user approval. All six packed runtime GLBs have exact reimport neutral/gameplay
proofs, LOD0 detail views, closed positional topology and zero Khronos errors or
warnings. Original editable masters and per-LOD exporter sources are retained.
The six exports share 54 content-addressed texture files. Measured collision is
12 part boxes for the bench and 13 for the cradle, with clear working approaches.

Registry version approved-f9b3eda3d5936d96 contains 254 static props, 69 character
profiles and 57 equipment records; the GM catalog has 442 definitions. Campaign
generation adds 72 workshop placements across all 36 keeps in the eighteen ORvR
zones. Local/shared/GM LOD thresholds are 16m and 42m, with campaign cull at 160m.
These are static props: repair and ammunition interaction behavior is not claimed.

The complete validation and public model hashes are in validation.json,
builder-metadata.json and review/*_publication.json. The earlier export and
pause records below are historical and superseded by this publication.

# Resumed September 20, 2026

The user resumed work. Bench LOD0/1/2 exports are complete; retain those exact bytes.
Cradle source geometry and UVs are unchanged. One LOD0 hemp corner had an averaged
normal almost tangent to its face (dot 0.001534), producing a zero Mikk tangent.
The exporter now moves only invalid smooth grazing normals slightly toward their
own face. The actual affected corner changed 0.573 degrees; all other source
geometry is preserved. Actual-source regressions pass for all three LODs, with
zero invalid tangents after correction; LOD1/2 required no adjustment. Evidence:
review/tangent-regression.json and tools/test_atlas_tangents.py.

Cradle LOD0/1/2 bake/export completed successfully with three Blender threads;
unified session 31794 exited 0. Log: review/export-cradle-tangentfix-20260920.log.
All three actual embedded GLBs match their build receipts, preserve geometry,
and pass Khronos with zero errors/warnings. Triangle counts: 31,746 / 12,954 / 3,070.
Embedded pre-packing hashes (texture sharing will intentionally replace these):
- LOD0: dc95ddf332073d9be2ba6a21643274093abdebfd2967bc61f07225d7d6817715
- LOD1: 6666298919b0a97b181723687bfbd985735072e47de74d468947f7e389527a07
- LOD2: 18f3f81cfb9a6c29f4387876079bbdf9e191d1504ad3afd914893c5c67a171e1
The current exporter is retained by content hash in review/tool_sources.
Validation now verifies each exact retained exporter, rather than forcing correct
older bench exports to match the latest tool; it separately records its own hash.
Root owns subsequent texture sharing, reimport review, validation and publication.
No package Blender process remains active from this agent.

The historical paused checkpoint follows; its partial-export counts are superseded.
# Workshop-item checkpoint

PAUSED at the user's request on 2026-09-09. No further builds or fixes authorized
until resumed. Unified exec session `9341` was interrupted with Ctrl-C and
returned exit code 1. `Get-Process blender` then found no remaining Blender
process. This was the only active package subprocess. Prior source-proof session
`53560`, source-build session `15165`, and failed exporter sessions `34833`,
`9006`, and `95261` had already ended. No stair fixes were started.

Bounded task: `frontier_siege_repair_bench` and
`frontier_siege_ammunition_cradle`. Regional workshop and published siege renders
inspected. Both are universal internal town/keep props, shared across pairings.
The user has given standing asset approval; root will integrate after technical
completion, with no more art-approval waiting loops.

All six finished source masters pass closed positional topology. Source triangle
counts: bench 22,720 / 12,126 / 3,904; cradle 31,746 / 12,954 / 3,070.
The bench retains 17 real cut sockets and the cradle six rail mortises. Ground
faces are flat; shaped tool necks, slide, lead screw and handle remain seated.
Cradle projectiles use an irregular 43-point dressed survey with eight distinct
dressing variants. All three LODs have measured deck/load support; the upper
stones have at least three nearby supports beneath their projected center.
Four source/mechanical tests passed again immediately before pause. Source PBR
overall/detail proofs completed; they predate the small tool-rest station fix,
so they are historical source-direction evidence rather than current exports.

Partial export stage: bench LOD0 completed at 22,720 triangles. Its embedded
texture GLB is `runtime/frontier_siege_repair_bench_lod0.glb` (23,687,744 bytes),
SHA256 `0656e52c2e24ab1c31146fa2d830f36923f49d1ea0b97c1c492188538b5b55a7`.
The packed editable LOD0 master and `review/frontier_siege_repair_bench_build.json`
were saved. This output is technically unvalidated and is not published.

Bench LOD1 stopped after timber baseColor/ORM/normal and metal baseColor were
saved; its bake textures are partial. No LOD1 GLB/master/export receipt exists.
Bench LOD2 and all three cradle exports have not run. Preserve these partial
files as checkpoint evidence; restart the interrupted LOD from its saved source
master when resumed. `review/export.log` records the exact boundary.

The first exporter found two long, thin tool-rest bevel facets with invalid
Mikk tangents. UV allocation alone did not fix them. Collinear original source
stations now divide the long tool-rest surface, preserving its silhouette and
making tangents valid. All six source masters and measured builder contracts
were rebuilt. A separate stale Blender UV-layer pointer crash was fixed by
reacquiring UV data after tangent/edit-mode operations.

Texture packing, exact reimport renders, Khronos validation and local readiness
remain pending for every GLB. No QC sidecars, blueprints or public outputs have
been written. Do not interpret source PBR proofs as runtime evidence.

`builder-contract.json` measures collision from finished masses in Y-up model
space: 12 bench and 13 cradle boxes. The documented working approaches remain
clear. Small fasteners/repair tools are excluded from movement collision.

The old published nature package remains frozen. Root additionally authorized
a technical-only export of the existing woodland-floor draft, without redesign;
this is deferred behind the reported stair/railing bug after workshop export.
No public/catalog/map change has been made here.

Read-only stair findings: Cinderfen has 16 authored stairs in the current map.
Its contract has tread/landing slabs and isolated rail posts, but omits the
continuous sloping handrails and rear landing rail, explaining walking through
post gaps. Sunmeadow currently has no authored stair props. Root assigned this
agent a separate stair metadata/helper/test fix and only stair placement lines
in `scripts/campaign/cinderfen-environment.mjs`; no edits have been made there.
Actual full stair/wall geometry interference still needs diagnosis after resume.

Root owns publication and integration. This package owns source, material,
Blender build and local review evidence only. Blender uses three CPU threads.
