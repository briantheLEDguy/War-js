# Cinderfen quartermaster - paused unfinished WIP

Owns only this new package. Root owns publication and game/GM integration.
User requested wrapping the current part and committing to change focus.
The already-running K save/export finished successfully. No further model
iteration, rendering or quality sweep was started; all authoring writes stopped.
RuntimeReady remains false. All candidate exports are diagnostic, not released.
Historical H evidence clears eight clips, but it does not validate K bytes.

Current map identity: cinderfen_outskirts_quartermaster; Vask Rauth;
Riftbound Quartermaster; vendor; x419/z-239/rotation0. The map has no custom
inventory/service fields. Existing profile npc_riftbound_vask_rauth_riftbound_quartermaster
resolves to Chaos in the original roster. The new task requested Greenskin;
root confirmed the generated production assignment is Greenskin vendor and that
the Chaos roster was placeholder presentation. Proceeding with approved retained
mire_brutish_v1_m anatomy.
Name, ID, title, vendor role, location and services are to be preserved.

Planned construction: distinct supply-vendor layers with continuous shirt,
fitted waistcoat panels and turned openings, sturdy boots, supply tally/ledger
carrier mounted with measured load-bearing contact. No primitive replacement
meshes. Use retained original anatomical source, matched joints/weights, packed
editable master, embedded PBR, three actual LODs and nine clips. Source/current
export arm, contact, clothing, equipment and attachment gates plus six mandatory
actual-import views must pass before freeze. Presence of an export is not readiness.

Revision A has produced the packed editable master and three atomic candidate
GLBs. Thirteen source surfaces pass connected/closed/UV/weight checks. The fitted
waistcoat and two bellows pockets are new shaped surfaces; carried equipment uses
closed loops fitted against actual belt/case patches and the full animated body
and clothing envelope. Numerical limits remain unchanged. There are thirteen
export regression gates, including the new waistcoat-versus-linen/anatomy gate.

Actual-export checks and front/head/side/rear/run_side/death:2/gameplay renders
are in progress. No candidate is technically ready or frozen yet. The previous
officer package belongs to root and remains untouched.

Revision A was rejected by actual-export layer checks and close views. Its cut
neckline was jagged; the waistcoat crossed the trouser waist, neck and concave
underarm shirt. Measured rest witnesses identify these surfaces. Revision B
smooths the actual closed pattern loops on their support, cuts below the shirt
collar, preserves the shirt normal orientation at the concave axilla, and fits
the lower waistcoat around the combined shirt/trouser envelope. All numerical
limits remain unchanged. B exported with smooth cut loops and cleared neck/body/trouser rest contacts,
but 163 underarm linen crossings remained. A and B are diagnostic only.

Current revision D is building. Its deeper armholes clear the concave sleeve
space, while a local inner-collar cut preserves proper shoulder bridges (the
horizontal B crop did not). C was interrupted before export because it shared
that cropped-shoulder issue. D source preflight measures zero rest layer
crossings before animation fitting. Actual-export proof is still pending.

D actual-export rest clearance passed, but its master had one tiny disconnected
quad offcut (18 evaluated vertices), and moving poses revealed 93-223 layer
crossings while idle/combat_idle/jump stayed clear. The cut now removes isolated
single-quad offcuts and preserves the upper shoulder bridges. E was interrupted
before export when the D motion results identified the skin-binding problem.

Current F is rebuilding. It retains the original shirt cage's skin-weight
identity for the waistcoat, smoothing fields along cut loops together with their
geometry; nearest-triangle transfer across a folded axilla/collar is avoided.
The fit around the trouser waist remains explicit. All limits remain unchanged.
Only final matching-byte master, all-clip/all-LOD gates and actual GLB views can
establish readiness. Runtime/ files still contain an older diagnostic candidate
until F completes its atomic export. No candidate is publishable yet.

F finished its atomic master/three-LOD export and passed all thirteen source
continuity/closure/UV/weight surfaces. The current all-LOD export sweep is
running with 20 retained validation inputs; no final pass is claimed yet.
Final-candidate actual-import views use suffix _f. The byte-verifying Three.js
viewer is review/inhabitant.html. Current contract readiness remains false.

F completed its diagnostic sweep: neutral export layer contact is zero, but
moving layers still show 127 melee, 106 ranged, 306 cast, 212 death, 129 run
and 173 walk crossings. Equipment remains clear throughout all nine clips.
Parent accepted F's visible cut; side, rear, run and prone views were inspected.
Revision G retains that cut and derives its surface/skin fields from the
finished shirt itself, removing the independent second subdivision path. No
underlying cloth is removed and no numerical gate is relaxed. RuntimeReady
remains false; F is held and G is in progress.

G source and neutral GLB layer preflights pass with zero crossings and all13
source surfaces remain closed/connected/weighted. The full moving sweep still
fails: melee93, ranged56, cast186, death185, run50, walk133. Actual triangle
witnesses in layer-motion-contact-probe.json identify non-neighboring surfaces:
upper-arm-dominant sleeve triangles move through the chest-dominant waistcoat.
A cast1.25 render confirms the broad lateral raise. H tests natural civilian
forward gestures and lateral elbow clearance around the actual broad chest,
retaining meaningful gait/gesture motion. This is a source diagnostic first;
all13 current-export gates, full pose sampling and limits remain mandatory.

H2 source motion diagnostics now show zero layer crossings across13 sampled
poses each for walk, run, melee, ranged and cast. The fitted arm chain keeps
natural bent counter-swing, with a lateral elbow plane and wrist clearance for
the wider torso. This diagnostic is not the full gate. H is rebuilding all
three exports from the unchanged G outfit construction plus this source arm
fit, followed by the existing grounded fall/equipment fit. Final all-key and
midpoint checks remain required for all nine clips and all three LODs.

H actual LOD0 moving layer check passes8of9clips with zero crossings. Only the
mid-fall fails (0.5-1.17seconds; maximum384 linen crossings; final prone2s0).
Current-byte witnesses show the early world-ground wrist interpolation pulls
the arm almost straight down into the wide torso before the body has lowered.
I replaces this with a protective brace in the moving chest frame, then blends
to the same final grounded palm targets. Elbows retain lateral clearance.
H remains held; I is rebuilding. All gates and floor/contact limits unchanged.

I's exact death0.9s witness still shows197 sleeve crossings. The brace path
alone did not solve premature ground reach: its vertical coordinate was still
interpolated toward the floor while the torso was too high, straightening the
arm beside the torso. J retains the chest-frame braced hand height until body
descent makes the same final ground plane reachable; horizontal placement and
actual palm grounding remain fitted. No clothing change or gate relaxation.

J exact death0.9s still showed115 crossings. Root cause is now isolated in the
inherited palm-contact solver: five repeated downward floor corrections were
applied even while the hand was intentionally above the floor, overriding the
reachable brace height. K permits downward contact snapping only after the
braced wrist reaches the ground plane; upward penetration correction remains
active at all times. The same final grounded palm target and limits remain.
J held; K rebuilding. No model/cut changes and no numerical gate changes.


## Paused save snapshot - candidate K

The already-running K build exited0 and saved its editable packed master and
three GLBs atomically. No further quality sweep or render was started.
RuntimeReady is false; K is an unfinished draft and is not publishable.
Historical H/G/F reports and images do not establish current-byte readiness.

Master SHA256: d3b0a4d081653a8def392072f7245fc0a9789ab28badda70d76dcd0709ebcff0
LOD0 SHA256: 5a88e9b122859b112ab3b29114931eea35bb6d8680a9f5fb880aba388efa5d18; 147602 triangles.
LOD1 SHA256: 42102c3da9edbebad2e2cb195661b2eff4c07b1f4120960ed050cd2075080095; 85593 triangles.
LOD2 SHA256: ee08d74687b50a92d4fdff33d38ee47b99cb6a424825414b2036b9174f622b87; 39821 triangles.

Exact file paths/bytes/hashes and next steps are in WIP_HANDOFF.json.

1. Resume only when the user authorizes this work again. Do not publish this WIP.
2. Inspect the K actual-export fall at the previous failure interval0.5-1.17seconds, including0.9seconds; then run the full existing zero-crossing layer gate. The latest downward palm-contact correction has not been tested on K exports.
3. Run Blender tools/inspect_master.py, then python tools/run_quality.py. All13 unchanged regression gates must pass on all3 current GLBs, including all9clip key/midpoint layer/equipment/attachment/contact checks and all3 Khronos validations.
4. Render and inspect current-byte front/head/side/rear/run_side/death:2 with suffix_k, plus lower-LOD fronts/gameplay and the fall transition. Existing rendered suffix_h and older images are historical.
5. If a technical check fails, correct the actual source defect and rebuild; do not loosen limits, hide underlay geometry, or publish from source-only evidence. The approved outfit appearance should be retained.
6. Only after all current-byte checks and views pass: retain final validation-input hashes, set runtimeReady true, freeze exact source/master/export bytes and hand off to root for game/GM publication.

No shared, public, registry, map, runtime integration or global documentation
files were edited by this authoring task. Root owns the requested WIP commit.
All authoring processes are stopped; no further writes are planned.
