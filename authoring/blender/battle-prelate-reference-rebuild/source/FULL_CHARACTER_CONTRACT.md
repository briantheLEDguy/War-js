# Full figure expansion

The user reviewed progress and explicitly authorized completing the entire figure,
armor set and runtime integration. Continue refining likeness as components expand.
The upper-body comparison cameras remain frozen; add full-figure cameras separately.

Use source/CONTRACT.md JSON format and explicit authored coordinates/connectivity.
No previous body, armor or weapon meshes may be reused. Rig matrices and compatible
animation data may be reused. `rig_reference.dat` contains the existing canonical
armature matrices/positions and all nine action names, read without reusing meshes.

Global source coordinates: meters, Z up, face toward -Y, character-left +X.
Crown1.86, chin1.65, neck1.60; chest front Y=-.19, back +.12; chest X+- .24.
Waist/belt1.12 to1.22, width X+- .23, Y-front-.145/back+.12.
Pelvis about Z.99; skirt plates start1.14 end.82; tabard starts1.12 ends.36 with
pointed/fringed hem. Tabard front Y approximately-.20, central width .23-.30 m;
back garment Y+.15 and longer, with deliberate folds, not a flat rectangle.

Left leg rig landmarks: hip(.117,.005,.992), knee(.161,-.037,.542),
ankle(.213,-.017,.077), foot front(.217,-.152,.009), toe(.208,-.302,.024).
Right mirrors X. Use custom plated silhouette: thigh width .17-.22m, knee shield
outerwidth .18m, greave width .14-.20m, boot width .18-.21m. Boots ground atZ0,
front Y~-.31, heel Y+.09. Knee shield centerZ~.54 and frontY~-.15. Calf armor tapers
to ankleZ.13 then overlaps sabaton/boot. Build positive-X side; Mirror allowed.
The reference foot stance is posed; keep the rest proportions compatible with rig.

Left arm rest landmarks from canonical rig: shoulder(.199,-.020,1.486),
elbow(.377,-.019,1.283), wrist(.518,-.221,1.148), handtip(.536,-.264,1.125).
Right mirrored X (consult exact matrices). Armor should cover the padded arm;
authored hanging comparison poses and animation are separate from source/rest.
Upper arm radius~.085m, elbowarmor~.075m, vambrace wristradius~.047m and forearm
radius~.073m. Gloves/fingers must have separately authored structure.

Module mapping: body=head/eyes/ears plus covered anatomy/underlayers; head slot=
gorget; chest=breastplate/upper torso fittings; shoulders=paired pauldrons;
hands=arm plates/vambraces/gauntlets; waist=belt/tassets/belt attachments;
legs=thigh/knee/greave; feet=boots/sabatons; back=backplate/rear attachments;
tabard=front/rear crimson cloth and parchment drapes. Warhammer separate socket.
Source records can add `slot` and `rigid_bone` metadata to each part. Root handles
rig/export integration. Max14k triangles per armor module after finishing;
total equipped LOD0 target110k max120k. Source detail can be richer separately.

Weapon: tall ceremonial rectangular double-face hammer, not a mallet sphere.
Author standalone localZshaft, bottomspikeZ0, shaftZ.12 to1.43, head centeredZ1.51,
head widthX .27-.31, depthY .20-.23, bodyheight .20-.24; topfinial to1.80.
Dark leather wrapped handle, brass bands, beveled steel faces, raised Gothic
cross/skull icon using custom literal patches, explicit studs. Mainhand grip
at localZ~1.09, offhand~.75; these are provisional socket offsets for animation
correction, not body height normalization. Source faces/thickness contours govern.

Book: belt relic approx .17m wide, .24m high, .065m thick; hinged spine and metal
corners/raised central emblem. Frontref hangs on anatomical-left hip (image-right),
center about(+.25,-.18,1.00), angled awayfrom vertical. Author centered local origin
and explicit transform, root can adjust attachment after full integration.
