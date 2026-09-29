# Portal travel and reference models

The two owner-supplied September 29 sheets define the Aegis and Riftbound portal
art. They are visual requirements, not authorization to change campaign rules,
purchase assets or grant release approval.

## Travel

`AWarZonePortal` rechecks player entry on the authority every 100 ms. A capsule
first overlaps the sphere while its centre is still outside the permitted
radius. Previously that single overlap attempted travel, failed the distance
check, and never retried as the player continued walking inside.

Automatic entry now attempts once per visit to the centre-admission volume.
Moving out resets the attempt; the normal Interact binding explicitly retries
without leaving. The controller RPC uses its possessed pawn and the existing
authority, development-session, life, visual, destination, distance, cooldown,
streaming and landing checks. Clients cannot choose a landing point. Disabled
portal actors do not poll. Loading/failure use the existing travel-status display.
Loading timeouts now include the specific readiness reason and an Interact retry
instruction; admission still requires safe destination collision.

The `ZonePortal` regression checks capsule-contact versus centre entry, scaled
range and invalid actors. `WarPortalProof` alternates direct requests with
outside-centre capsule contact followed by movement inside. Run the read-only
`scripts/unreal/inspect-portal-entry.py` through Unreal's Python commandlet to
write `artifacts/unreal/portal-models/entry-survey.json`.

The selected `DutchBastion_*/Bastion_Campaign_v3` map retains local GM workbench
eligibility, needed by the traversal proof's isolated draft fixture. This does
not grant shared-server GM privileges or admit preview/unselected maps.

The September 29 local native proof passed all 70 directed routes, 20 resource
sites, asynchronous failure/cancellation, respawn and GM draft/undo history across
actual capital unload. The final diagnostic run prioritized the Sunmeadow return
to Aegis after an earlier run timed out there; all routes still ran exactly once.
This verifies local development travel, not Steam/multiplayer acceptance or the
absence of timeouts under load. See local `artifacts/unreal/world-portals/verification.json`.

## Model candidates

Run Blender in background with `scripts/unreal/author-portal-models.py`. Supplied
references must exist at `artifacts/unreal/portal-models/references/aegis.png`
and `riftbound.png`. No assets are downloaded. References and generated binaries
remain in ignored local artifacts.

The recipe writes Aegis/Riftbound `.blend`, `.fbx` and `.glb` files, four-view
renders, vortex textures and a hash-bound `models.json`. Procedural Blender
stone/metal detail is not preserved completely by interchange export. The
Blender file is the editable material source, not native-material evidence.

`bake-portal-models.py` prepares a separate `baked/` candidate folder with 2K
color/normal/roughness/metallic atlases, explicit tangent space, a structural FBX,
a separate non-colliding-effects FBX and a fully textured GLB. Originals remain
editable. `import-portal-candidates.py` targets unique private
`/Game/PortalCandidates/` packages and never changes a map. The shared importer
rejects `KHR_materials_transmission`; the candidate importer explicitly translates
constant crystal transmission to Unreal's Thin Translucent shading with Surface
Forward Shading, transmittance tint and the source factor. Textured transmission
remains unsupported and fails closed. This shader translation needs native visual
parity review; compilation does not establish a match to the sheet. See
[Epic's lit-translucency documentation](https://dev.epicgames.com/documentation/unreal-engine/lit-translucency-in-unreal-engine).
Commandlet exit codes alone are not success: require both
fresh `WAR_PORTAL_CANDIDATE_IMPORTED` markers and `baked/native-candidates.json`.
`review-portal-candidates.py` renders both imported candidates from front and
three-quarter views in an unsaved Unreal world. It requires commandlet rendering,
writes `baked/native-frames.json`, and never sets an approval or installation flag.

| Feature | Aegis | Riftbound |
| --- | --- | --- |
| Frame | Pointed arch, midnight stone, gilding | Thorned arch, blackened stone, copper |
| Crest | Solid solar disc and rays | Hollow ring and directional thorn rays |
| Focus | Blue crystals in metal cradles | Crimson crystals in metal cradles |
| Decoration | Intact navy standards, gold borders, original luminous sigils | Torn oxblood standards, chains, carved skull clusters, red sigils |
| Base | Dressed stone treads and inlaid upper rim | Dark stone treads and bone clusters |
| Energy | Blue spiral and warm core | Crimson spiral and dark surrounding field |

**Both candidates are installed as visible local development entrances; art
acceptance is still outstanding.** Fine
tracery, sculpted damage, crystal refraction, the exact reference silhouette and
native material/animated-effect fidelity require further art work. Do not label
them reference-accurate or use Blender renders as native acceptance.

Structure and effects remain nonblocking entrance landmarks with baked materials.
Approved walkable stairs, frame collision and equipped capsule clearance through
the detailed aperture remain future art work. Variants follow each source-zone's
authored realm; an unknown realm requires an explicit choice. Preserve all
70 route IDs, reciprocal arrivals, streaming bindings and landing checks.

## Installing visible entrances

`install-portal-visuals.py` binds the imported structure and effects at each of
the 70 entrances in the currently selected private routing layer. The source
zone's authored `campaign.realm` chooses the variant; an unknown realm fails
instead of substituting another model. The installer backs up the routing file,
replaces only its tagged visual actors, and preserves all portal travel data.
Close the campaign in the editor before running it: Windows prevents replacing
a map held open by another Unreal process.

The visual landmarks use no collision and preserve the existing approach and
activation boundary. They are not a replacement for approved walkable stairs or
sculpted frame collision. `verify-portal-visuals.py` reopens the saved world and
requires all 140 mesh parts, correct asset bindings, gameplay visibility,
materials and clear collision before capturing both variants in their zones.
Destination labels sit above the tallest spire at 1300 cm from the model base,
with their text plane aligned to the portal and facing its approach. Saved-world
verification checks every label's height and facing as well as its mesh pair.
`artifacts/unreal/portal-models/installation.json` records actual installation;
candidate import receipts alone do not establish world placement. Neither step
grants reference-fidelity or release approval.

The installed energy materials are separate derivatives under
`/Game/PortalCandidates/WorldGlow_v1`, with daylight emission gain. The original
imported materials remain unchanged. Reopened native captures and binding checks
cover all 70 entrances and 140 visible mesh parts; the blue/red energy is reviewed
in the actual campaign lighting, not only the studio preview.
Each entrance also has two warm, movable fill lights with a 19 m attenuation
radius and no shadows, illuminating its metalwork and stone without changing
the zone's global lighting. These lights are owned by the same installer tags
and replaced on rerun, so repeated installation cannot accumulate duplicates.
Saved visual verification is separate from full traversal acceptance; the latter
is invalidated by a routing save and must be renewed with the gameplay proof.
