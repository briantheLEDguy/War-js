# Aegis reference citadel

The replacement uses the supplied **Bastion of Aegis: Citadel War Board** as its
architectural reference. The main perspective governs massing and proportions;
the inset governs route roles. The lower city and external connections remain
outside the bounded castle replacement.

## Authoring and protected baseline

`scripts/unreal/survey-aegis-citadel.py` reads actual saved Unreal actors, current
shared scenery dependencies, siege anchors and approach ground heights. It does
not save a level. Its receipt is
`artifacts/unreal/aegis-citadel/baseline.json`. A routing-package mismatch must be
reconciled through the shared-city workflow before surveying, with saved native
edits and GM drafts preserved.

`aegis_citadel_blueprint.py --baseline <receipt>` produces a versioned scaled
architectural sheet and route ledger. Coordinates are Unreal centimetres: X
uphill, Y east and Z up. Each route has explicit endpoints, intermediate points,
clear width, elevation and a stage-gate restriction. Projected crossings do not
add graph connections. The current plan contains 30 nodes and 43 bidirectional
routes. The survey binds 2,267 existing castle actor identities and separately
records upper-enclosure components intersecting the new stairs and courtyard.
Only surveyed geometry inside the signed upper-precinct mask can be replaced;
an unrecognized edit or an unresolved spanning mesh blocks staging. Actor and
component bounds, ground hits, capsule hits, services and all 36 campaign
connections are recorded from native levels. Historical coordinates alone do
not establish clearance.

`aegis_citadel_mesh.py` constructs detailed Gothic source geometry;
`build-aegis-citadel.py` exports the Blender master, source review images and
native mesh data. Existing reviewed repository furnishings and original city
textures are referenced by hash. Native Content and purchased kit data remain
private and ignored. Source renders help refine the architecture; they are not
native visual or gameplay acceptance.

The next source revision replaces the rejected crown with six substantial,
unequal attached belfry towers, a central octagonal lantern with satellite
turrets, long slate spires, sloping roof ridges and deeper Gothic window reveals.
It adds sculpted sentinel armor and gives terrace stairs continuous structural
supports. Native corridor failures determine
support cutouts and portal reveals; signed walking widths remain mandatory.
Blender's reflected scene transform is applied only at its export boundary,
with corresponding winding and normal conversion. Native source coordinates
and the independently checked native import convention remain explicit.

The signed blueprint also records all same-floor intersections and shared route
segments, distinguishes them from projected crossings at different heights, and
binds eight review camera positions and lenses. Source and native captures use
the same horizontal field of view; native camera receipts reject reframing.
The plaza monument remains at the radial center. Its actual capture standing
point is ten metres to the west, with explicitly recorded clear detours around
the monument base.

The dimensioned comparison includes projected portal-to-spire and core-crown
height ratios. An earlier upper keep was rejected because its spire-to-portal
ratio was roughly twice the reference. The revised core preserves physical
surfaces through Z9000 cm and retains its Z14200 cm compression. Its separate
supported crown extends to Z17200 cm with varied attached towers; fresh combined
native views must establish the final proportions. Playable floors, stairs and
the full-height gate openings retain their coordinates.
Decorative winches use signed pads outside the capture rings and route corridors;
staging checks their actual native bounds instead of placing them on side anchors.

`stage-aegis-citadel.py` creates isolated scenery, a candidate city definition,
`ReviewCandidate` and `SiegeCandidate` under
`/Game/WorldRebuild/AegisCitadel_<revision>/`. It copies each affected layer,
removes only surveyed castle actors and contained enclosure components, proves
the remaining lower-city/outside geometry unchanged, and records all
source/candidate hashes. It does not publish or set review flags. Interrupted
staging retains a journal for explicit recovery; changed candidates are preserved.

Blender source faces use counterclockwise winding with outward normals. The
native import boundary checks that convention and reverses triangle order to
Unreal's clockwise convention, preserving positions, outward normals and UVs.
Double-sided collision alone does not repair Recast floor orientation. A bounded
repair backs up exact owned meshes and maps, preserves gameplay transforms, and
derives the new city revision from the genuinely saved native dependencies.
The isolated siege overlay also has a floor- and capsule-checked proof start at
its surveyed lower-city spawn. Scenery never owns that gameplay actor.

The candidate records the exact canonical revision payload and final saved
scenery/dependency hashes. Late child-level saves, conflicting source/owned hash
bindings or changed staging contracts invalidate that receipt. Navigation saves
only the owned siege overlay and records its final map hash separately.

Original weathered ashlar texture trials live under
`public/assets/textures/aegis_citadel/`; their provenance file records the built-in
imagegen prompts and source hashes. Generated height is an artistic approximation.
Tile continuity, mip behavior, physical course scale and native material lighting
remain review requirements before adoption.

The scene lighting follows the reference's cool mountain atmosphere and warm
gate, brazier and interior light. Directional light should reveal carved stone,
while sky fill keeps stairs, objective rings and gallery entrances readable.
Fog and exposure must preserve that readability from ordinary player cameras.
Lighting belongs to the private shared scenery, so campaign, scenario and
frontend see the same treatment. Conflicting copied siege lights are removed
only by exact identity; original city packages remain unchanged. A graded source
render or one hero camera cannot establish native lighting acceptance.
The version 2 treatment binds seven original fixtures by stable ID, source
package, actor class, label, tag and state hash. This distinguishes the authored
sun from the Dutch street fill even though both have the native name
`DirectionalLight_0`. Actual readback found excessive retained Rayleigh
scattering removed nearly all blue sunlight; the bounded repair changes only
its scale and distribution to the measured engine defaults. Cool shadowed fill,
local screen-space indirect lighting and reflections, shadowed architectural
practicals and an owned volumetric cloud actor complete the proposed treatment.
The cloud uses a candidate-owned material instance whose parent is the exact
installed Engine cloud material, bound by path and file hash. Registered scalar
and color parameter names and actual getter readbacks must match the recipe;
Unreal 5.8's material setter return value does not report these writes reliably.
The Engine asset is not copied into the public repository. Final game-camera views must establish
color, exposure, interior visibility and route readability before approval.
`stage-citadel-lighting-study.py` copies historical candidate geometry into a
separate private lighting study for settled game-camera diagnostics. It verifies
all original and historical candidate package bytes remain unchanged and grants
no visual, traversal, gameplay or publication approval. Unsaved SceneCapture
images do not establish effective game-camera exposure.
Exposure uses the project's existing luminance units. The signed adaptation
limits of 64 and 4096 correspond to EV100 6 and 12 at the engine's unit scale;
the scene records the actual disabled extended-EV100 mode. A scene authoring
change must not switch global exposure units for unrelated zones.
Color constructors use explicit channel names: Unreal's reflected byte-color
positional order is BGRA, whereas the signed lighting contract records RGBA.
Actual property readback must match the requested channels; swapped values are
rejected before saving shared scenery. Import recipes are part of the signed
blueprint, so a corrected importer receives a new private namespace.

Mesh inspection also records the actual packed tangent X/Z axes and reconstructed
Y axis for every render LOD. Finite, unit-length and orthogonality diagnostics
help investigate importer warnings without changing geometry or accepting a
warning as proof of a visible defect. Existing source-corner and UV checks remain
mandatory.

`DescribeStaticMeshSourceData` reads committed native MeshDescription bulk data
without accepting uncommitted editor changes or building, saving or modifying
the mesh. It records corner order, all UV channels, material groups, colors,
normals, tangents and binormal signs with original vertex and corner identities.
The bounded mountain carve intersects only the commander's hall volume. Its
deterministic clip preserves original attribute prefixes and unaffected faces;
the original mountain, transform, materials and outside geometry remain intact.
`DescribeStaticMeshStoredCorners` also reads unused committed corners, so an
unreferenced corner cannot conceal dropped UVs, colors, normals or tangents.
Saved clone readbacks are compared against the deterministic clip, and the
signed carve binds the independent original-policy survey by path and file hash.
The private native clone must preserve source build and collision policy and
pass fresh physical hall, throne and corridor checks. Whole-mountain removal or
flattened attributes cannot satisfy this exception.
The original mountain recomputes render normals from shared native topology.
Expanding its corners into separate vertices changes exterior shading even when
all corner attributes survive. The clone must retain original vertices,
instances and edge connectivity, including unused vertices. Its render proof
compares unchanged exterior faces against the original built mesh; matching raw
authored normals cannot prove preservation when the source itself recomputes them.

All three native render LODs must pass the fixed finite, unit-length and
orthogonality checks. A nonzero source UV determinant alone is insufficient:
very thin decorative triangles can still produce invalid native tangents.
`ConfigureCitadelSurfaceLods` applies the same three LOD and build policies in
one synchronous build. It accepts only the exact original-owned private citadel
mesh namespace, preserves LOD0 source corners, materials and collision, and does
not save packages. Staging still reads and validates every actual render LOD.

## Progression and physical restrictions

The eight main anchors are supplies, two convoy checkpoints, outer breach, left
side, right side, central plaza and commander. The three optional defenses are
independent. Captured sides are permanent milestones, can progress concurrently
and unlock the player-captured center only when both finish. Center capture opens
the keep. The default rules retain 90-second solo captures, 14-minute stages,
60-second transitions and bounded overtime.

The outer stage cut has three physical portcullis leaves: main and both flanks.
The inner cut has five leaves: main, two ground portals and two elevated gallery
portals. Stairs and balconies cannot bypass a locked stage. Raised platforms and
interior galleries have recorded stair access. Unshown interiors are newly
authored; existing room functions and services require individual reconciliation.
Historical capabilities that do not work in the native runtime remain unfinished.

The campaign adapter checkpoints full character documents through the trusted
Node journal. `FWarCampaignMutation` groups nested inventory, equipment,
progression, quest and reward changes into one full-document write-ahead record.
The native file is flushed before success and retained until the owning host
acknowledges its revision and sequence. Failed commits restore the original
document, including receipts and defeat intent. Startup replays pending records
before restoring characters; unidentified corrupt records retain host-wide
protected recovery. Native process-crash proofs, transient combat effects and
physical returns remain separate acceptance work.
Version 2 snapshots serialize supported active pawn statuses, stack-group replacement, periodic
cadence and consumed shields with the exact applied definition and source
identity. The recovery codec subtracts elapsed UTC downtime from effects and
cooldowns and skips offline damage and healing ticks. Unknown native gameplay
effects hold recovery rather than disappearing. The native Foundation suite
passed all 95 tests on 2026-10-05, including effect/cooldown restoration, natural expiry,
source rebinding, opaque-effect rejection and the return-custody barrier. Actual
multi-process crash acceptance remains pending; inventory-only evidence cannot
establish transient combat continuity.
Status, class, global and supported native cooldown deadlines are fixed when
applied or restored. Repeated captures and avatar replacement cannot renew them.
Periodic cadence retains its unrounded epoch internally and rounds only at the
serialization boundary; recovery advances to the next future tick without
applying ticks missed during downtime.
The value codec covers saved vitals, resources, receipts, class/global/native
cooldowns and pawn statuses, including periodic cadence and consumed shields.
Active casts and projectiles are outside this value snapshot. Recovery claims
must distinguish these values from a complete in-flight combat reconstruction.
Its durability boundary is the latest owning-host acknowledged full document
plus flushed critical-mutation WAL, not every uncheckpointed combat event.
Participant return acknowledgement precedes any new evacuation checkpoint for
that character. The native bridge defers evacuation while return is pending;
Node preserves the unreturned record's scope and activation even when processing
a cached request. After a durable return, a separate evacuation can begin if the
character is still in the besieged capital.
A restore acknowledgement alone cannot mark a character returned. Return
requires the full current character document after physical relocation or
respawn, under the original activation and scope. The character remains protected
through this durable checkpoint, including a replacement controller on reconnect.
Native execution and process-crash acceptance for this barrier remain pending.

Durable enrollment and evacuation records have separate per-realm budgets:
18 unreturned participant documents and 18 unreturned visitor documents for
each activation. Remote enrollment therefore cannot exhaust the evacuation
budget. A durable visitor return frees its visitor slot; the journal preserves
the returned character document. Historical unreturned documents from distinct
activations and returned history remain preserved; these are per-activation
capacity bounds, not a global journal-size limit. These bounds do not increase the 18-human
participation limit. Snapshot validation also rejects a same-stage transition
back to active combat, or an increase in a recorded preparation clock.
Approved remote seats retain ordinary travel through intermediate campaign zones.
The live departure restriction applies after physical entry into the capital;
an old zone label alone cannot impose it. Scenario departure restrictions remain
separate. Remote enrollment also leaves normal protection and death handling
outside the capital intact.

## Verification and admission

`build-citadel-navigation.py` builds navigation only in the exact receipted
candidate and probes every ledger waypoint. Navigation availability does not
prove physical traversal or convoy clearance.

Version 2 encounter members use a dedicated navigation query filter with an
8,192-node search budget. Actual native diagnostics found that 49 of 50 earlier
global failures exhausted the engine's 2,048-node search limit; the remaining
spawn was inside stair masonry. Adjacent route endpoint queries passed in both
directions, but do not prove corridor traversal. The larger budget changes no
collision, area cost or agent dimensions. Ordinary visitors, historical version 1
rounds and characters after encounter return keep the engine's default filter.

Recipe version 5 records all six retained spawn anchors and their full-width
approaches. Four first stair flights move inward to reserve the existing upper
spawn pads; route IDs, endpoints, widths, gates and objectives remain unchanged.
The physical proof checks 25 real floor/capsule positions on each spawn pad and
walks every multi-point upper approach in both directions. Historical recipes
retain their recorded geometry and do not acquire these new claims.

Recipe version 6 binds a ground gradient for each footprint. A fresh read-only
native survey records both unchanged lower-city pads, all 25 support/clearance
samples, actual floor actor/component identities, source mesh and package hashes,
and actor-state hashes. The retained first pad lies on a measured 1:2 uphill ramp;
its anchor stays unchanged and its footprint follows that plane. Upper pads stay
flat. This changes expected sampling height, never the actual native floor,
capsule, slope or distance limits. Missing, obstructed or changed survey evidence
blocks staging; earlier recipes keep their recorded flat-footprint interpretation.

The latest imported revision `4ef82f28e502` projects and connects all 137 navigation
waypoints. Its physical run completed all 92 center walks, but failed 75 of
27,460 width samples and 28 gate/spawn checks. It is unapproved. The next source
recipe reserves full-height side gate openings in structural stair masonry and
separates gallery landings from lower north stairs and diagonal wall approaches.
It removes the foundation's walking-edge chamfer at the actual failed 6.5 cm
road seam and replaces two whole surveyed wall-toe modules in narrow approach
reservations. Higher enclosure modules, other lower-city structures and services
remain preserved. These source changes pass 69 geometry/behavior tests and 17
publication tests; they still require fresh native import and physical proof.
Objectives, stage gates, spawn anchors and corridor widths stay fixed.

Native corridor diagnostics require an already-walking proof pawn, real full-size
capsule sweeps and native floor/step limits. Ramp movement follows the engine's
projection/speed policy and second-ramp sweep; successful StepUp floor results
remain authoritative through native height adjustment. Genuine line fallback
requires independent same-component support traces before and after adjustment,
agreement with actual capsule displacement and the unchanged floor-distance
interval. Destination and failed intermediate-step evidence are recorded separately.
`--width-diagnostic` completes every signed lane sample without the longer center
walks and always records `passed: false`; neither publication nor traversal
admission accepts it. Fresh complete candidate proofs remain mandatory.

Lighting studies duplicate owned private layers/materials and preserve source,
candidate and Engine bytes. The first dusk study reduced statue overexposure but
remains rejected for sunny brown lighting and hard shadow contrast. Diagnostic
captures do not establish reference fidelity or visual acceptance.

The reviewed Engine cloud parent is a read-only, byte-bound dependency of the
new shared city definition. Staging, navigation and publication require its
signed source hash. This exception neither permits arbitrary Engine assets nor
copies the parent into owned candidate Content.

Dependency collection refreshes the on-disk registry for each saved Game folder
before reading its rows. An actual isolated native material regression reproduced
the missing row immediately after save and recovered the exact cloud parent after
refresh, while the protected Engine bytes remained unchanged. The failed first
recipe 5 staging journal is preserved; current revision `4ef82f28e502` includes
the corrected collector and identical source geometry.

`citadel-proof.ts --blueprint <blueprint.json> --map <candidate> --city-revision
<revision>` uses a real equipped native character to walk each route in both
directions. The route proof constrains movement to each intended segment, checks
collision and grounded completion, and records actual travel distance. Gate-open
traversal is an unsaved fixture. The proof sweeps the actual equipped character
capsule across all eight gate leaves in both directions and at the center and
both edges, in all three claim phases (144 checks). Closed leaves must block on
their gate actor and opened leaves must clear. An additional 144 centerline
sweeps at three elevations test the full portal height for raised-route bypasses.
Local sweep length defaults to four metres on each side. A shorter level landing
requires its exact approach lengths in the signed ledger; the launcher derives
the span from route geometry, capsule radius and floor margin. Native checks also
verify the actual leaf thickness and nonpenetrating capsule positions at both
ends. This does not replace traversal of the complete corridor or permit reduced
width, slope or step limits.
Five lateral lanes independently probe the full signed width of every route at
no more than one metre spacing. The outer capsule centers retain the exact route
edge, with native floor, slope, step and headroom checks. Transitions use swept
movement in steps no greater than ten centimetres, including corner continuity;
wide evidence spacing cannot falsely reject ordinary stair treads. Every failed
lane retains its actual obstruction and blocks acceptance. Completed native views
remain available for diagnosis even when a physical fixture fails.
Curved approach ramps may carry a signed world-X piecewise-linear floor profile.
The source receipt binds the exact profile and actual upward floor triangles;
every top vertex must lie on that surface, knot seams must remain continuous and
the complete walking lane must have support. Native samples use the expected
height at each lane's actual X coordinate and at every movement substep. They
still require the real collision floor and the same capsule, slope, step,
headroom and 120 cm elevation limits. Profiles cannot fill missing floors,
extrapolate outside their recorded domain or carry a player over a tall wall.
The width prepass also writes a diagnostic checkpoint before the longer route
walk. A checkpoint is explicitly failed diagnostic data and cannot replace the
completed native report. Architectural captures suppress local Canvas HUDs and
viewport widgets, record their actual visibility, and restore each previous
state before movement or shutdown. Public visual evidence must bind these clean
captures to the signed camera configuration and saved candidate revision.
Native import inspection reads the built render buffers of every LOD, including
UV channel counts, finite UV ranges and normals. Reduced LODs can lack a source
mesh description while retaining valid render UVs; the source-description count
cannot establish an import failure. LOD0 render normals must match the committed,
source-bound normals. Every LOD0 triangle must also match the oriented source
face, material slot, three corner normals and UV0 values; a coincident adjacent
face's valid normal cannot satisfy that check. The position, normal-dot and UV
tolerances are fixed in the import contract. Imported assets retain their
material section bindings.
Unintended shortcuts, objective
floor/line-of-sight checks, the actual convoy hull, camera clearance and populated
18v18 movement need separate physical evidence. Hero, front, top-down, gate,
plaza, balcony and interior captures require comparison to the reference.

All receipts bind the exact package, city revision and ledger hashes. Geometry
changes invalidate earlier traversal, visual and performance evidence. Publishing
must update the shared `UWarCityDefinition` used by campaign, scenario and
frontend while keeping gameplay overlays separate and preserving rollback copies.

Full-siege admission is fail-closed. The backend requires fresh
`artifacts/unreal/citadel-siege/full-siege-approval.json` and its matching
`route-plan.json`, actual package hashes, rules/battlefield version 2, eight main
anchors, three optional anchors and capacity 18. Source code, exported meshes,
navigation availability and unit tests cannot substitute for physical, visual,
scenario, live-capital and evacuation evidence. Steam, platform and release gates
remain independently enforced.

`npm run unreal:citadel-siege-proof -- --map <candidate>` runs an isolated
physical fixture with 18 native avatars per realm, ordinary movement and ability
execution, and the real capture and stage timers. The scenario fixture exercises
an attacker completion and a defended timeout. The prepared campaign candidate
uses synthetic ordinary player controllers and a private loopback Node authority
to exercise enrollment and authoritative settlement. Its seeded territorial
eligibility is fixture data. These receipts explicitly exclude human enrollment,
reconnect, process-crash recovery, visual approval and production admission;
those require their own evidence.

`citadel-recovery-proof.ts --map <prepared CampaignCandidate>` exercises one
authority fixture across three real native processes. It interrupts two owned
processes on opposite sides of the durable checkpoint acknowledgement, then
checks replay, ordinary character stats and participant-return/evacuation order.
The publication recovery report must bind its configuration, process receipts,
native and authority journals, full character documents and HTTP acknowledgements
to the current map, native binary and source hashes. A generic
`characterRestored: true` field cannot substitute for this subproof. This fixture
does not establish interrupted commander outcomes, equipment mutations, defeat
intent, human reconnect or production acceptance.

Native receipt hashing uses the installed engine `PlatformCrypto` provider and
checks known SHA-256 vectors and actual files in the native foundation suite.
Unavailable providers and invalid inputs return recoverable errors. The generic
platform SHA-256 stub is unsuitable for these proof paths because it can assert
before gameplay begins. Windows verification does not establish Linux or macOS
verification.

Rendered crowd performance uses a separate explicit fixture at 1920×1080 and
100% screen percentage with VSync, frame caps, fixed timestep and dynamic
resolution disabled. It records actual settings, hardware, model/loadout hashes
and raw wall/game/render/RHI/GPU frame timings. Each of the three stages needs a
settled 60-second window with 18 enrolled characters per realm and 36 visible,
loaded avatars; normal death and respawn continue and are counted. Signed crowd
positions require actual floor, full capsule clearance, pedestrian navigation
and exclusion from capture rings. NullRHI runs and the earlier 30 FPS capped
architecture captures do not establish populated-scene performance.
Comparison requires a separately hashed native run of the unchanged published
Aegis city with matching hardware, settings and roster. Any different floor or
camera arrangement is disclosed. The existing 60 FPS / p95 frame time at most
16.7 ms target applies independently of that comparison. No accepted populated
baseline or replacement performance result has been recorded yet.
The private baseline overlay uses an explicitly signed `earned_progression`
fixture with version 2 and 18 characters per realm over the original native
anchors and spawns. It starts normally in the lower city and earns gate opening
through real captures and convoy progress. Assigning later stages with zero
claims, forcing gates open or inventing milestone claims cannot establish the
comparison. The benchmark stops after its real keep-stage exposure window and
grants no victory or progression acceptance. Existing saved rounds are untouched.

The native objective fixture compares all eleven anchor positions with the
signed ledger and samples eight points around each capture ring. At least four
must have a real capture-height floor, full capsule clearance and the same
Visibility line of sight used by gameplay. The source architecture remains
unapproved: the first hero candidate was rejected for insufficient scale,
layered fortress massing and detail, and must be materially rebuilt before
rendered acceptance or publication.
The subsequent native captures also remain rejected: dark wall/floor surfaces,
coarse masonry, shallow roofs, banner shape/color, lighting and framing need
correction. Actual capsule sweeps identified corner towers, gallery rails and
portal niches obstructing opened gate approaches. Native navigation reaches
the objectives and spawns, but several elevated stair and balcony connections
remain disconnected. These failures require geometry and native verification;
neither a source render nor relaxed traversal tolerances resolves them.
The complete b619 physical diagnostic walked all 86 route directions at their
centers, but 396 of 26,060 full-width samples failed. This is a failed corridor
result, not route acceptance. The revised support, portal and approach geometry
requires a fresh survey, navigation build and complete native width proof.
The subsequent full-width fan survey inspected 6,858 actual native positions.
Its remaining paving contact reproduced with the old flat capsule pose and
cleared with the signed ramp's exact spherical support pose. The fresh survey
records both poses, reports no retained obstruction after the planned castle
replacement and bounded mountain carve, and confirms all 1,343 original native
packages are unchanged. This read-only result permits private staging work;
saved geometry still requires real grounded walking, gate and convoy proofs.

The subsequent recipe 5 survey inspected 6,954 actual native positions and
again preserved all 1,343 original Game package hashes. Source revision
`e53757ed9a81` passed 15,870 floor samples, 5,208 body/head samples and 350
upper spawn pad/exit samples. These are source diagnostics, not native traversal
or visual acceptance. The full native Foundation suite passed 95 tests after
the scoped navigation filter change; the revised candidate still requires fresh
physical, cinematic, scenario, campaign and recovery evidence.

## Shared workspace resource coordination

The corrected recipe 5 diagnostic completed 27,460 width samples with 70 failures
(`proofs/1791227585268-24716`). Actual game-world support and failure poses are
recorded separately from the destination placement. A diagnostic-only run never
grants route admission. The latest line-fallback and walking-state fixtures passed
95/95 Foundation tests (`editor/test-1791227472278-29820`). Editor-world profile
sweeps are not interchangeable with the game-world overlap admission query.
Matched diagnostic queries retain exact capsule orientation, dimensions, collision
responses, ignored objects and live component/body setup identities. Zero-length
and both 0.01 cm vertical sweeps disclose contact differences; they never waive a
blocking overlap. All changed geometry requires fresh physical evidence.

Recipe 6 private revision `68cc73797d81` imported successfully with its source
package hashes preserved. It reserves full gate openings, moves gallery landings,
removes the walking-edge foundation chamfer and removes two wholly bounded
surveyed approach wall toes. The failed `f2da203b062a` staging journal and partial
private packages remain preserved: its new approach reservations were not yet
recognized by the staging guard. The guard now validates every requested edit
before writes and accepts only the exact signed, complete toe modules.
Fresh native navigation connected all 137 waypoints. The physical/view proof
`1791231363287-10192` passed 288 gate sweeps, 88 objective samples and 150 spawn
samples with no physical failures. Its eight views remain rejected visually.
The width-only diagnostic `1791231249146-7120` retains 54/27,500 failures (38
approach and 16 gallery samples); it grants no route acceptance. Gallery source
revision `42db92b9d784` adds a 600 cm level tangent before the first riser and
passes 70 source tests and 17 publication guards. Its native evidence is pending.
The preserved `42db` build was superseded by survey-bound revision
`8bb3168368e3`: the fresh read-only survey recorded 6,988 precinct and 50 lower
spawn samples while preserving all 1,343 original Game package hashes. Its private
import succeeded, and fresh navigation connected all 139 recorded waypoints on
6 October. Gallery physical traversal and fresh visual acceptance remain pending;
the earlier `68cc` receipts cannot approve the changed gallery geometry.

Diagnostic-only live collision witnesses read attached cooked geometry under a
physics read lock. Version 2 keeps exact affine matrices through nested wrappers,
inverse-transforms all eight query-box corners and verifies roundtrips. Rotated
nonuniform and sheared compositions have focused native controls. The portable
analyzer includes both failed-substep and destination contacts; version 1 bounds
cannot establish version 2 coverage. The minimum candidate-surface gap is neither
the globally nearest mesh clearance nor a penetration depth. Overlap, MTD and
short-sweep differences remain diagnostic and never waive corridor admission.
Triangle certificates now export their winning unit axis, capsule midpoint,
complete capsule and triangle projection intervals, both directed gaps and
versioned numerical guard. `citadel_separation_certificate.py` independently
audits these projections using Decimal arithmetic and the full spherical radius.
It rejects missing vertices, reduced guards, invalid axes and inconsistent native
claims. Saved JSON never authorizes movement. The conservative guard is an
engineering policy, not a formal error theorem for the Chaos query implementation.

The fresh `8bb` width-only diagnostic `1791293820739-3716` sampled 27,680
positions. Both directions of both revised galleries passed; 38 approach samples
retained raw overlap failures. All 52 unique live body/pose witnesses were static,
complete and geometrically separated, and 315 exported triangle certificates
passed the independent projection audit. That diagnostic grants no traversal
acceptance.

Width proof schema 3 now confines typed live separation resolution to route
placement and actual route-movement poses. The wrapper performs the original
scene query and reads the exact original component/item body synchronously on
the game thread. Welded children, foreign welded-root shapes, unsupported items,
unknown/incomplete shapes, inconsistent duplicates and uncertain separation
remain blocked or unresolved. Any positive native MTD query vetoes separation.
Actual mixed-wall/ceiling, same-shape obstruction, two native instance bodies and
real welded-child controls passed in the 98-test Foundation suite before use.
The two gate endpoint paths retain raw overlap admission; native swept movement,
StepUp, slope, floor support and headroom rules remain independent checks.
Per-sample receipts preserve raw/resolved/blocked/unresolved counts and the live
certificates. Rejected lift seeds may precede a valid swept floor placement;
the final floor and actual movement pose must be clear. TypeScript and Python
publication guards independently audit the full capsule projection intervals.
Complete native schema 3 traversal is recorded below; its header still prevents
portable admission.

The first complete schema 3 attempt (`1791295382983-21596`) passed every
27,680 width sample, then failed while serializing its provisional checkpoint
through Unreal's 32-bit JSON memory archive. It produced no completed traversal
receipt and grants no admission. Proof reports now stream condensed UTF-8 to a
file archive. Rejected lift seeds retain every body identity, disposition and
count without unused triangle payloads; every separated clearance still retains
its complete live shape and triangle certificates. The writer, non-ASCII round
trip and real inconsistent duplicate physics-object controls passed in the fresh
99-test Foundation suite. All 283 Unreal tooling tests passed after updating
the two synthetic route-surface fixtures to schema 3. The fresh complete rerun
is `1791295932610-16344`. It completed all 92 actual character walks, 27,680
width samples, 288 gate sweeps, 88 objective samples and 150 spawn samples with
zero route or physical failures. Its native result is successful, but portable
full-width admission rejects its incomplete collision-policy header.

That rerun saved its streamed width checkpoint, and both independent per-row
auditors passed all 27,680 samples (188 separated-query receipts and 95,538
rejected lift-seed receipts). Full-width admission still rejects the header:
the real native character uses the `Custom` profile label after its existing
visibility-blocking constructor setting, whereas the earlier consumer required
the label `Pawn`. A new collision-policy receipt is required; do not relabel or
accept the old receipt. Its prepared guard independently audits all 64 UE 5.8
responses, the exact native character/default class, object channel and enabled
mode. Both portable consumers now require schema 4, its explicit capsule-policy
readback and checks on every proof tick and route placement query. The 287-test
Unreal tooling suite, 18 publisher controls and tooling typecheck passed. The
native exporter and continuous checks passed a fresh Editor build and all 100
Foundation tests. The actual-character regression changes every response channel
in turn and verifies rejection before any floor query, then restores the native
policy without modifying the class default. The diagnostic response dump now
iterates the actual 64-entry container instead of `ECC_MAX` (65). A fresh schema 4
traversal run (`1791297774170-16920`) was stopped after 24 walks to add continuous
geometry and walking-limit checks. Its 27,680-sample checkpoint passed both
consumers before that additional guard was required; it remains incomplete
diagnostic history and cannot grant admission. Schema 3 remains usable only as diagnostic history;
it cannot be promoted or rewritten into schema 4.

The new guard checks radius 42 cm, half-height 96 cm, unit scale, upright axis,
45 cm step height, native `0.71f` walkable-floor Z, standard gravity and the real
capsule as the movement body on every tick/query. Actual and class-default
settings must agree within the native spawn's single-float slope rounding. The
class default remains exactly `0.71f`; a spawned character reports
`0.7100000381469727` after Unreal reconstructs the slope from its angle, versus
the default's `0.7099999785423279`. A typed encounter-local baseline pins the
actual runtime slope, default slope, dimensions and step height exactly after
capture. Even a subsequent one-ULP slope change invalidates the proof. The width
header must also match its kinematics readback and attest that pinning is active.
Post-capture shrink, scale, tilt, step/slope, gravity and updated-component
controls fail closed. A first native suite exposed an incorrect sqrt-half slope
assumption; the focused native diagnostic and installed UE 5.8 constructor
verified `SetWalkableFloorZ(0.71f)`. The final focused native regression and all
100 Foundation tests passed after accounting for spawn rounding and adding the
exact baseline. Both portable consumers passed their focused controls and tooling
typecheck. Fresh complete run `1791300014775-28176` then passed all 92 actual
walks, 27,680 width samples, 288 gate checks, 88 objective checks and 150 spawn
checks, with zero route or physical failures. Both independent full-width
auditors passed. Its exact report hash is recorded in
`artifacts/unreal/citadel-reference/oct6-pinned-complete-traversal.json`.
These receipts bind the tested `8bb3168368e3` geometry; neither earlier receipt
can be promoted, and a later geometry revision requires new evidence.

Copied lighting studies `499983ebcbbf` (reference dusk) and `b7aacf04fca8`
(slate dusk) each passed 288 gate sweeps, 88 objective floor/sight checks and 150
spawn checks with eight actual signed-camera captures. The slate study changes
only owned masonry tints while retaining original PBR texture graphs and source
package hashes. Its grey/navy palette improves the rejected beige treatment,
but neither study approves architectural fidelity, the mountain backdrop or
cinematic completion. The default route candidate remains unchanged.

Private `alpine_sunset` study `27ffa51491e7` and cooler `alpine_storm` study
`343642dc512e` were staged and each completed eight actual game captures, 288
gate checks, 88 objective checks and 150 spawn checks. Both remain visually
rejected. The sunset key makes the mountain too brown and hides facade detail;
the cooler study improves the stone palette but retains the coarse mountain,
open-water horizon, repetitive roof silhouettes and short central banner.
They combine the copied slate palette with a height/slope snow treatment on the
exact retained mountain component and finer roof texture tiling.
The original granite textures remain dependencies; the mountain mesh,
transform, collision and all other actor properties must match their measured
state. This material cannot certify a better mountain silhouette or route
clearance. Shader compilation, actual game captures and performance review are
required before considering adoption. Successful basic capture checks do not
grant full traversal, reference fidelity or populated-scene performance approval.

The retained native rendered mountain normals differ from its source export:
all 9,209 corners above 170 m have negative render-normal Z, from -1 to
-0.21259842813014984. The original positive-Z snow mask therefore did not use
the actual render convention. A further private study binds the exact saved
render-buffer hash and unchanged transform before adapting the slope sign;
mixed normals, substituted bytes and coordinate-frame changes are rejected.
The mask also validates the noise-shifted band from 152 m and requires the exact
component transform, single LOD and disabled Nanite. Fine noise is gated by
height so it cannot add snow below that band. Its four focused controls passed.
Corrected study `648ff3474d32` completed eight actual game captures in run
`1791301465000-19496`, with 288 gate, 88 objective and 150 spawn checks passing.
Snow is visibly present, but the rounded mountain silhouette, open-water horizon,
flat facade lighting and short central banner still fail reference fidelity.
The study remains unapproved.

Campaign preparation also exposed two reproduction differences: text-mode reads
normalized the byte-bound native export's CRLF, and system Python 3.14 uses a
different floating-point summation algorithm from Unreal's Python 3.11. The
verifier now reads literal UTF-8 bytes. The existing document and preservation
witness reproduced exactly under Unreal's interpreter; no receipt was rewritten.
Recipe 7 uses explicit sequential binary64 reductions. The original complete
terrain document reproduces exactly under both Python 3.11 and 3.14 without
relaxing exact comparisons or rewriting old receipts.

Source revision `eb00703a2a63` retains all 30 junctions, 43 bidirectional routes,
objectives, gate restrictions, spawn approaches, rooms and bounded edit masks.
Its bespoke upper roofs add articulated pitch changes, full-width coping,
supported pointed dormers, iron arrises and gold finials. Upper masonry caps now
cover their tower footprints instead of retaining the earlier narrow cap clamp.
The source build and 70 architecture controls passed. Native staging completed
in 67 owned packages, and all 139 navigation waypoints connected. Complete
movement proof `1791302524498-26280` passed all 92 walks, 27,680 width samples,
288 gate checks, 88 objective checks and 150 spawn checks, with eight actual
camera captures. Both portable width auditors passed. Its report SHA is
`3542b80877d23cb03e4ac9196393e8a9a17786c84c4d21c41cfe9ea2b36cf1b8`.
Visual fidelity, cinematic lighting and full siege acceptance remain open.
The older `8bb3168368e3`
proof remains valid only for its recorded geometry.

An isolated campaign preparation attempt on `8bb3168368e3` stopped after creating
four owned packages because Python attribute access did not expose reflected
`WarZoneAnchor` properties. Its pending journal and packages are preserved;
no shared city was published. The publisher now reads `zone_origin`, `half_size`
and `zone_id` through `get_editor_property`, with 19 focused controls passing.
Native preparation must be verified in the fresh recipe 7 namespace.

Recipe 7 preparation passed the reflected routing checks but stopped at the
frontend owner guard. A native diagnostic verified the original frontend owner
and unchanged source bytes, then reproduced `DuplicateAsset` dropping the tag on
an unsaved copy. The publisher now carries that verified owner only into its
exact isolated frontend candidate. Unowned sources, different native classes,
wrong destinations and conflicting candidate ownership are rejected before
metadata writes. All 20 publisher controls passed. The failed recipe 7 journal
is preserved; native verification of the fix needs a fresh namespace.

The copied storm-dusk study (`5a893aeceda9`) also remains rejected after eight
actual game views: excessive darkness hides stonework, and entrance/brazier light
is too weak. Further exposure, ambient and practical-light studies stay in owned
private packages with exact fixture identities and source-byte preservation.

Native headers and implementations must stay frozen throughout a shared Editor
build. One chat owns builds and Unreal/GPU verification at a time; it releases the
slot explicitly before another chat builds or mutates private Content. The local
coordination record is
`artifacts/unreal/citadel-reference/chat-coordination.json`. Python authoring and
backend tests can proceed in parallel when they do not edit frozen native sources
or contend for the active GPU slot. Unrelated dirty work is preserved throughout.

Recipe 8 `d7936ad95609` integrates a taller central blue-and-gold standard,
supported iron brackets and joined masonry backing. The pointed hem remains
311.5 cm above the conservative gate ornament bound, and the cloth clears its
backing wall. The source asset build and 71 architecture controls passed.
Objectives, route surfaces, crossings, gates, spawns, rooms and the bounded edit
mask match recipe 7 exactly. Native staging completed in 67 owned packages and
all 139 navigation waypoints connected. Complete native proof
`1791305174868-5128` passed all 92 walks, 27,680 width samples, 288 gate checks,
88 objective checks and 150 spawn checks, with eight native captures and zero
physical failures. Both independent width auditors passed. The report SHA is
`10e17a552eeeb2fbdeaca92a473f84f2adc4494249aef042caf0b09fa418c3dc`.
Visual and full siege approval remain open. The exact 20 source recipes are
archived alongside this revision before further architecture changes.

A read-only native support survey traced 126 wing and projected tower-base
points while ignoring only the owned replacement architecture layer. Every point
found retained ground at Z4200–5909.67. The flat ground mesh supplies support where
the mountain-only analysis showed lower terrain. Package hashes remained intact.
The extended 144-point survey also passed, including the remaining side towers,
with the same height range and unchanged package closure. The earlier sampling
version retains its original scope. These surveys do not approve a footing build.

Recipe 9 `4069b99e5f8d` joins the wing bases to the existing foundation and adds
bounded masonry under the ten-metre rear overhang and projected tower bases.
Exact route reservations stay in the construction path. Decorative shaft bundles
now use a broader rhythm, and six final-height cornices emphasize the stepped
wings. Pointed upper window crowns remain 30 cm below the cornices. The existing
foundation, terrain, objective/route data, gate restrictions, spawns, crossings,
rooms and edit mask remain unchanged. All 73 architecture controls and the asset
build passed. Native staging completed in 68 owned private packages, and replay
of all 144 signed ground samples matched their native positions exactly.
All 139 navigation waypoints passed. Fresh complete native proof
`1791308126754-24160` passed 92 continuous walks, 27,680 width placements,
288 gate checks, 88 objective samples and 150 spawn samples, with eight views.
Both independent width auditors passed. These receipts remain specific to this
geometry; visual, cinematic and full siege approval remain open.

Recipe 8 campaign preparation passed the frontend ownership repair, then stopped
on Python's unavailable `StaticMeshActor.is_hidden` method while collecting GM
rebase inputs. Its four saved candidate packages and pending journal are retained.
The publisher now uses the reflected `hidden` boolean, as existing repository
authoring tools do, and rejects nonboolean values. All 21 publisher controls
passed; the complete preparation still needs a fresh native retry.

Recipe 9 preparation passed after both native API repairs. Its independently
versioned Python and TypeScript mesh guards retain the 38-binding legacy scope
and require all 39 bindings, including `wing_foundation_repairs`, for recipe 9.
The first attempt stopped before any preparation writes on the old mesh-count
guard; its failure log is retained. The fresh native retry prepared four private
campaign/routing/overlay/frontend packages. No GM draft files were present in
this preparation input. Canonical publication and final admission remain false.

The first gameplay preflight found two stale retained-zone hashes in the copied
campaign manifest (Sunmeadow and Cinderfen). Their existing saved packages match
retained two-client streaming report `1790710918659-21324` for the current
campaign map. `reconcile-citadel-campaign.py` updates only private preparation
metadata against that exact evidence, retains the original receipt and records
both old/new hashes. It rejects unverified changes and changes to capital or
owned preparation packages. Content and canonical routing receipts stay intact;
this metadata reconciliation grants no traversal or production acceptance.
The strict campaign content preflight passed after this reconciliation. The
final Unreal tooling suite passed 295 tests across 53 files.

Actual recipe 9 recovery attempt `recovery-1791309351820-15096` timed out before
its first mutation. The repeated full preflight measured 24.3 seconds against
15-second HTTP and ownership windows. Python now reports all bytes consumed by
terrain reconstruction; repeated checks reuse it only while every input and
producer hash stays identical. Native package hashing remains mandatory on each
preflight. Repeated preflight measured 8.8 seconds. A second attempt was stopped
after the lease still expired before enrollment; both failures and protected
state are retained. The native bridge now holds a bounded subsystem-owned
startup residency pin and prioritizes renewal/reactivation ahead of queued
enrollment, with requests held during ownership backoff. A new recovery run
must verify this behavior; the timing improvement alone is not recovery approval.
For a new private preparation, use `python -B scripts/unreal/reconcile-citadel-campaign.py
--revision <revision> --network-evidence <retained-network-report>` only when its
current package hashes match that report.

Matched recipe 7 storm and reduced-fill studies completed eight native views
each (`1791304249311-21320` and `1791304423909-12168`). Reducing the shadowless
fill from 500 to 200 improved contrast only modestly; both remain visually
rejected. A separate foreground-fog study changes only the volumetric fog start
distance to 10,000 cm relative to the reduced-fill treatment; ordinary
exponential fog stays unchanged. The installed engine exposes these separately.
Recipe 9 control `8760191850d2` and foreground study `05448f014c3a` each completed
eight native views. Native fog readbacks differ only in volumetric start distance
(0 versus 10,000 cm), and protected package bytes remained unchanged. The hero
comparison shows no clear improvement; neither treatment is approved. A read-only
native material survey found Engine cloud layout scale 256 versus the studies' 8;
further cloud tests must use those actual values rather than assumed defaults.
Distant mountain forms and warm entrance lighting remain unfinished.

The native lease/residency fix passed 101 Foundation tests; the subsequent
startup diagnostic passed all 21 targeted citadel tests. Recovery still stopped
before enrollment. Its actual `startup-readiness.json` reports missing convoy
navigation. The read-only campaign survey found both static baked Recast actors
in `CampaignSiegeOverlay`, with no persistent navigation actor. Unreal discards
streamed Recast actors in a normal game world, while commandlets retain them.
This explains why isolated Editor navigation evidence did not establish live
campaign readiness.

`stage-citadel-campaign-navigation.py` stages a private ownership correction,
then verifies it in a separate native process before changing preparation
metadata. `WarCampaignNavigationAuthoring.cpp` permits only an exact matching
private CampaignCandidate/overlay pair, rejects existing persistent navigation,
requires both approved static profiles and populated tiles, and transfers the
same actors in place. It also moves the matching bounds so a later normal Editor
save retains those tiles. Prop exclusions remain in the streamed overlay.
The operation compares every tile's bytes, counts and bounds around the move;
the reload checks them again along with all other private actor state. Exact
rollback copies, source/binary hashes and the original receipt are retained.
Neither this operation nor its receipt approves runtime convoy traversal,
crash recovery, canonical publication or production admission.

Recipe 9's transfer and independent reload passed with 5,765 character and
2,523 convoy tiles unchanged, and the strict campaign content preflight passed.
The prepared main map hash is now
`4de749109ed194229e04f67ab544b908ca26afc4a1c886675c474c1fdb16aa6c`.
`campaign-navigation-ownership.json` binds both actual process IDs, tile payloads,
preserved actor state and rollback hashes. Its first payload-audit attempt stopped
before saving because unused pool slots were counted as missing payloads; exact
private package hashes were verified intact before the corrected retry.
Native runtime readiness and crash recovery still require fresh game evidence.

Fresh game run `recovery-1791312241432-13592` enrolled 36 normal-stat characters,
completed the real 180-second preparation and flushed its first earned mutation
with a real catalog buff and cooldown. The process was killed before Node commit;
the restarted host durably replayed the target's 25 XP and 7 gold at WAL sequence
1, but native avatar restoration then hit repeated collisions at the ordinary
login anchor. The incomplete run and original WAL/HTTP evidence remain retained.
`ResolveRecoverySpawn` now selects collision-checked encounter entry or recorded
arrival space before creating a recovering avatar. Missing ownership or scene
readiness retains custody; unrelated player entry remains unchanged. The build,
tooling typecheck and all 103 Foundation tests passed. Actual restart/return
verification still requires a fresh fixture.

The next fixture, `recovery-1791313756981-26528`, stopped before its first
mutation after Windows denied atomic checkpoint replacement with `EPERM`.
Contemporaneous diagnostic reads may have caused the sharing contention; this
run does not establish a recovery-spawn regression. Its authority correctly
paused and rejected subsequent operations. The file repository now retries
`EPERM`, `EBUSY` and `EACCES` up to twenty times with asynchronous 25 ms waits.
It never deletes the old checkpoint, and advances its revision only after
replacement succeeds. Persistent failure retains both the durable journal and
flushed pending bytes. The 41 focused persistence, authority and native siege
tests and server typecheck passed. Fresh native recovery remains required;
do not inspect the actively replaced journal during a fixture.

Fresh lighting control `c74192ec04c5`, cloud-scale study `7c1c0892da9f` and
outside-wall portal study `5b1c4a1576a2` each completed eight native views with
the same archived producer and unchanged source packages. Changing cloud scale
8 to 256 did not demonstrate a convincing canopy. Moving the two portal lights
from X 26300 to 25000 cm cleared their editor collision rays but added only a
subtle warm tint in the actual gate view. The comparison is recorded in
`artifacts/unreal/citadel-reference/oct6-fresh-lighting-comparison.json`.
These studies remain visually rejected. Effective cloud binding, visibility,
renderer flags and resolved zone lighting must be witnessed at screenshot time;
material parameter readbacks alone do not prove the rendered cloud treatment.

Fixture `recovery-1791314232340-21012` reached both real crash boundaries and
72 restoration acknowledgements across its two restarts. The target retained
50 earned XP and 14 gold, with no stat normalization. All 36 participant-return
and evacuation-return acknowledgements completed, but physical-safe-return
acceptance remained false: characters occupied the same horizontal arrival
coordinates at successive capsule heights. The portal's channel trace could
hit standing characters as ground. The failed fixture and retained positions
are summarized in `oct6-recovery-portal-landing-review.json`.

`WarPortalLanding` now queries blocking WorldStatic objects for floor support.
Ordinary travel retains its exact authored arrival. Authorized evacuation can
search at most 600 cm inside the paired destination's radius allowance, requires
the same unambiguous destination zone, and checks supported capsule corridors
and unoccupied final space. It cannot jump to disconnected floor or stack on
another character. No available safe space leaves the character protected.
Recovery fixtures write separate immutable `progress-*.json` diagnostics and
compact counts to the native log, avoiding reads of the active campaign journal.
This source change requires fresh native collision and live return verification.
