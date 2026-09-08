# Cinderfen regional architecture

This original construction kit serves the autumn geothermal marsh described in
`docs/orvr-zone-art-briefs.md`: Greenskin fen workers and Dark Elf supply officers,
peat causeways, mineral vents, dead alder, reed and rust sedge. Its reference for
craftsmanship is the current Battle Prelate rebuild: deliberate shape, fitted
construction, material thickness, retained source, real PBR channels and reviewed
runtime exports. Sunmeadow is a pipeline reference, not a geometry or texture donor.

The regional vocabulary is mineral-crusted dark basalt, low raised tarred-alder
decks and splayed bents, curved overlapping reed roofs, shaped ceramic weather
caps and blackened iron fittings. Weather follows lower splash bands, heated
mineral seepage, exposed reed tips, worn thresholds and forged contact surfaces.
Dark Elf supply details remain practical and finely fitted. No generic spikes,
primitive assemblies or recolored Sunmeadow buildings substitute for regional art.

## Intended module contracts

All runtime coordinates are metres, Y-up, front +Z; Blender source uses Z-up and
front −Y. The package's final build report will contain measured bounds.

| Module | Main footprint | Floor / opening | Access |
|---|---|---|---|
| Dwelling | 8 × 9 m | Floor 0.6 m; doorway 1.8 × 2.6 m | 2.2 × 3 m ramp in front |
| Raised workshop | 10 × 8 m | Floor 0.6 m; doorway 2.6 × 3 m | 3 × 3 m front ramp |
| Supply shelter | 8 × 6 m | Floor 0.35 m; open bay 5.8 m | 3 × 1.75 m front ramp |
| Curtain and walkway | 8 × 2.4 m | Walk 6.3 m; crest about 8.4 m | Fitted end planes X ±4, Z 0 |
| Gatehouse | 28 × 12 m | Ground passage 6 × 4.8 m minimum | Full depth Z ±6; wing sockets X ±14, Z 0 |
| Hinged gate leaves | 6 m closed span | Height 4.8 m; grounded | Hinges X ±3; paired 90° open/close clips |
| Wall stair | About 5.6 × 8.8 m | Intermediate landing 3.15 m; top 6.3 m | Two real stepped flights and landing |

Gatehouse wing walks, sentry floors and central defense deck connect at Y 6.3 m,
with actual upper access openings. Raised buildings and stairs require the shared
walkable-surface system; their decks cannot be represented solely by blocking
boxes. Source records will include each horizontal/ramp surface and collision
segment, including the absolute entrance level and exact defense access sockets.
The stair's ground socket is `(-1.3, 0, 4.2)` and top socket is
`(1.3, 6.3, 4.5)`. Thirty-six horizontal tread supports match the real 0.175 m
risers; underside colliders prevent passing through a flight from below.
The eight-metre curtain and twenty-eight-metre gatehouse use nominal joint planes;
hewn end-stave shoulders project at most 0.062 m beyond them to overlap the next
bay. Export bounds include those shoulders, roof eaves and complete front ramps.

## Acceptance

Seven editable Blender masters, original control cages and surface-paint records,
three meaningful LODs, shared content-addressed textures, neutral and gameplay-
distance actual-GLB views, doorway/deck/hinge checks and signed internal review.
Technical validation does not grant visual approval. Maps, campaign generation,
the global registry and broad project documentation remain with the integration
task. Blender jobs use bounded threads and are coordinated with concurrent art work.
