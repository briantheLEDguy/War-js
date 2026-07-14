# Equipped-character clearance audit

Run the zero-cost Blender audit against an assembled review GLB:

```bash
node scripts/blender-character-pipeline/tools/audit-equipped-clearance.mjs \
  --blender="C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"
```

Add `--strict` when a threshold failure should make the command fail. Use
`--model=<job GLB>` to compare a newer draft; its report is written beside the
model with the suffix `.clearance.json`. Bind and idle are checked by default.

The versioned policy is
`data/armor-clearance-policy.json`. Body penetration treats an armor vertex as
severe when it is more than 8 mm behind the nearest outward-facing body
triangle. A module may have at most 24 such vertices (or 0.5%, whichever is
larger), and no sampled penetration may exceed 30 mm.

Armor-to-armor crossings use BVH triangle overlap. Unrelated modules pass when
they remain within either 12 overlap pairs or 1% unique-triangle involvement,
but always fail above 192 pairs. Explicit adjacent layers such as
chest/shoulders, chest/waist, waist/tabard, legs/feet, and back/chest use
topology-aware pair overrides. Each override is calibrated from deterministic
bind and stress-pose evidence and retains a hard ceiling, so an
intentional-layer label cannot hide a gross collision. Reports record the
selected threshold source and world-space contact bounds so a failed seam can
be located and reproduced directly.

These are screening thresholds, not promotion approval. Signed distance relies
on consistent body normals, vertex sampling can miss a crossing contained
inside a large triangle, and overlap counts vary with topology density. The
required rendered stress-pose and human visual reviews remain authoritative.
