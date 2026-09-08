# Capital performance verification — 8 September 2026

## Scope and recovery

Local `main` was fast-forwarded to `5eb9ed118ec476f30355ac1f324822376f21f474`
(`codex/map-readability`), recovering the expanded world, authored models,
Riftspire and GM integration. Git LFS runtime assets and checkpoint dependencies
were restored. No push or deployment was performed.

Performance work is on `codex/capital-performance`, based on that checkpoint.
It was isolated in `tmp/capital-performance` because another task continued
world authoring in the primary checkout. The user subsequently authorized committing
and merging these optimizations. Commit `bc102cf` was fast-forwarded into local
`main`; pushing/deployment remain excluded.

## Implementation

- Opaque capital meshes share material/render-state batches using Three.js
  `BatchedMesh` with `WEBGL_multi_draw`. Native geometry instancing remains the
  fallback. Whole incompatible roots retain their original rendering, including
  transparent, animated, mirrored and custom shader objects.
- Source objects, transforms and IDs remain available to collision and GM tools.
  LOD/detail ranges and shadow settings are unchanged. Edits, suppression and
  undo/redo refresh batch transforms; mirrored edits restore original rendering.
- A static spatial index replaces per-frame full-city camera scans. Larger rigid
  meshes use indirect BVHs, preserving shared render indices. Terrain clearance,
  padding and all forward/reverse probe intersections remain intact. Gates,
  lifts and active interiors remain dynamic; editor revisions invalidate caches.
- NPCs retain full population, geometry and animation rate. Conservative
  whole-rig bounds permit independent main-camera and shadow-pass culling,
  without changing shared geometry bounds.
- Loading now uploads textures, waits for asynchronous world actors, compiles
  final batch and room-light variants, and exercises shadow rendering offscreen.
  Cancellation, fallback rendering and shared-resource disposal remain supported.

The planned `three-mesh-bvh@0.7.8` version is deprecated for Three.js version
incompatibility. The dependency is pinned to `0.8.0`, which supports this project's
Three.js `0.167.0`. No Three.js upgrade was introduced.

## Measurement method

`scripts/benchmark-capitals.mjs` uses fresh local Chrome browser contexts, a
1280×720 viewport, device scale 1, native render resolution, view distance 350
and an explicit 60 FPS limit. Player settings outside these contexts are untouched.
Each run warms four camera orbits, then measures 60 seconds: a stationary view,
two orbits, and short forward/backward steps. The route stays near each capital's
entry area. It is not a complete traversal of every district.

The shell-launched measurements of both versions reported
`ANGLE (AMD, AMD Radeon(TM) Graphics (0x0000164E)
Direct3D11 vs_5_0 ps_5_0, D3D11)` with multi-draw available. This is the integrated
GPU selected by that Chrome launch environment, even with high-performance flags.
Separate direct-runtime measurements below verified the discrete GPU. These two
adapter groups must be compared separately.

Samples count actual rendered frames, excluding skipped scheduling callbacks.
Frame intervals use raw animation timestamps rather than the simulation's 100 ms
delta clamp. Simulation includes camera work. Submission is CPU time covering
culling and `renderer.render`; it is **not GPU execution time**. Draw and triangle
counts describe the main pass. Program counts include compiled warmup variants.

Artifacts are under `artifacts/performance/`: recovered production measurements
in `baseline-production`, final optimized measurements in `final-production`,
and development checks in `baseline-dev-final` / `optimized-development`.
Earlier `optimized-production` samples precede the final per-pass NPC bounds
and are not the final implementation. Initial reload/zone-transition-interrupted
experiments were discarded from comparison.

Baseline runs overlapped some local editing/build verification, and another
world-authoring task was active on this computer. Treat wall-time differences
as local observations, not a controlled hardware certification. CPU camera
timings and render counts additionally identify the changed work directly.

## RX 7700 XT results

Running the same benchmark through the direct browser runtime selected the
computer's RX 7700 XT (`0x747E`). One matching Aegis control pair measured
53.5 → 60.0 FPS, p95 22.3 → 18.6 ms, and zero frames over 100 ms on both builds.
The Riftspire baseline on this adapter measured 44.0 FPS and p95 29.9 ms.
Three final optimized runs per capital completed in
`artifacts/performance/discrete-production`:

| Capital | FPS, runs 1 / 2 / 3 | p95, runs 1 / 2 / 3 | Frames over 100 ms |
|---|---|---|---:|
| Aegis | 59.98 / 59.99 / 59.70 | 17.7 / 17.8 / 18.7 ms | 0 |
| Riftspire | 60.00 / 59.95 / 60.00 | 18.7 / 18.7 / 18.7 ms | 0 |

**Every final run met the ≥58 FPS and ≤20 ms p95 targets on this adapter.**
There were no uncaught JavaScript errors or frames over 100 ms in the six
measured minutes. This establishes repeatability for the documented entry-area
route, not for every district or higher resolutions. The discrete baseline
has one run per capital, so its before/after comparison has less evidence than
the three-run integrated baseline.

Camera p95 was 0.6–0.7 ms in Aegis and 0.9–1.0 ms in Riftspire; CPU submission
p95 was 13.1–14.3 ms and 9.4–10.7 ms respectively. Median main-pass draws were
125 and 174. The browser runtime's GPU selection is an environment difference;
the application does not force the discrete adapter.

The direct browser environment blocked Google Fonts. Both versions used the
same fallback fonts. Network receipts distinguish this from game/shader errors;
the control runs had no uncaught JavaScript errors. GPU-to-GPU differences must
not be presented as gains from the code changes.

## Integrated-GPU results

Production results use three warmed 60-second runs per capital. FPS is the mean
of the three run averages; p95 is shown as the range across runs. Stall counts
cover all three minutes. The baseline workload caveat above applies.

| Capital | Baseline FPS | Optimized FPS | Change | Baseline p95 | Optimized p95 | Frames over 100 ms, before → after |
|---|---:|---:|---:|---:|---:|---:|
| Aegis | 10.2 | 19.4 | +90% | 105.7–141.6 ms | 61.1–61.2 ms | 688 → 3 |
| Riftspire | 21.4 | 24.4 | +14% | 55.7–69.0 ms | 50.0 ms | 11 → 3 |

Median main-pass draw counts fell from 237 to 119 in Aegis and 592 to 174 in
Riftspire. Median main-pass triangles fell from 2.53 million to 1.08 million in
Aegis; Riftspire remained approximately 1.76 million. Camera p95 fell from
4.1–4.8 to 0.8–1.2 ms in Aegis and from 18.0–21.6 to 1.2–1.6 ms in Riftspire.
CPU submission p95 remained approximately 19–22 ms / 12–14 ms respectively;
fewer draw calls alone do not establish lower GPU execution time.

One development run per capital recorded 6.2 → 19.6 FPS in Aegis and
20.4 → 23.2 FPS in Riftspire. The baseline development run overlapped build/test
work, so these are diagnostic observations, not a reliable percentage comparison.

**The ≥58 FPS average and ≤20 ms p95 acceptance targets were not met on this
renderer.** Frequent stalls were greatly reduced, but isolated frames over
100 ms still occurred. The route is too limited to certify absence of recurring
stalls throughout every district. The remaining GPU/compositor contribution
needs direct profiling; CPU submission must not be reported as GPU time.

## Automated verification

| Check | Result |
|---|---|
| Full unit suite | 1,149 passed, 4 failed; 137 passing files and 2 failing files |
| Client typecheck and production build | Passed; existing large-bundle warning remains |
| Server typecheck | Passed |
| World validation | All 33 zone maps passed |
| Model validation | All 843 manifest/index/QC records passed |
| Whitespace/diff check | Passed |

The four failures were reproduced on the recovered checkpoint before these
changes: Cinderfen road connectivity, road regeneration idempotence, service
clearance and ground-actor patrol clearance, in `orvrRoadNetwork.test.ts` and
`worldLifeContent.test.ts`. They are separate world-authoring issues.

A fresh Windows checkout also exposed a Vite test-transform failure on the
unchanged roster promotion CLI's CRLF shebang. Pinning that file to LF in
`.gitattributes` fixes the import; its four tests pass without changing its code.

New coverage checks batch compatibility, LOD transitions, shadow retention,
GM transforms/mirroring/undo and suppression, shared-resource disposal, spatial
cache invalidation, moving lifts/gates, original-versus-indexed collision results,
NPC per-pass bounds, shader-warmup cancellation and bounded diagnostics.

The final cancellation safeguard uses Three.js r167's program readiness query
with cancellation checked before each poll. It avoids `compileAsync` continuing
to inspect disposed materials. Missing readiness support falls back to the
offscreen warmup draw. This loading-only safeguard and the unsupported-shadow
callback guard were added after the integrated-GPU timed runs; they do not change
their warmed rendering workload. The final build/tests, browser checks and
discrete-GPU runs include both safeguards.

## Visual and interaction checks

Matching baseline/optimized screenshots were inspected at an Aegis street,
Lantern Quays beside the canal, and the citadel entrance, plus Riftspire's rim
and market. Architecture, weathering, lighting and visible detail were reviewed.
The screenshots are not pixel-identical: pavement pattern differences at the
Riftspire rim and foreground occlusion near the lift remain unclassified.
Visual acceptance is therefore partial; further investigation stopped at the
user's instruction to perform no more tests and complete the merge.
The existing fallback avatar in Riftspire is present in both versions.
The Ashgate lift moved and carried the player in both builds; its geometry
remained attached. Sunmeadow loaded and rendered its frontier road/terrain.

Disabling `WEBGL_multi_draw` produced zero BatchedMesh objects and successfully
rendered the same Aegis views through native instancing. Screenshots and receipts
are in `artifacts/performance/visual-review`. These are targeted checks, not a
complete traversal of every district or a full GM interaction playthrough.
GM behavior is additionally covered by the focused automated regressions.
