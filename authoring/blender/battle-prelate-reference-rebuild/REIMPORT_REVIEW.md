# Review the exported bundle

`tools/reimport_review.py` runs in a fresh **background** Blender process and
imports the staged GLBs. It does not use the authoring meshes for the final review.
It requires a passed binary validation report matching the requested LOD files.

```powershell
$assetPython = 'C:/Users/bschm/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$assetBlender = 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe'
& $assetPython -B tools/validate_runtime.py
& $assetBlender --background --factory-startup --threads 8 --python-exit-code 1 --python tools/reimport_review.py -- --lods 0,1,2 --samples 16
& $assetPython -B tools/reimport_review.py --compose review/reimport_report.json
```

The default still renders use Cycles, 16 samples, and the exact full-character
cameras/resolutions from `source/scene.json`. Stress renders use EEVEE at 40% of
the same three-quarter camera resolution. Position, target, orthographic scale,
and aspect ratio stay fixed. Engine, samples, resolution scale, frame, camera
record, source/build hashes, and every image hash are saved in the report.

The body is imported first. It must expose the named 56-bone rig, four socket
EMPTYs, and nine actions. Each armor file must have identical bone names,
hierarchy, rest matrices, and armature world matrix. Rebinding must preserve every
evaluated rest vertex within 0.00001 m. The duplicate armor rigs are then removed.
The standalone weapon uses its exported grip origin/local transforms and attaches
to `socket_hand_R`; no new fitting translation or rotation is introduced.

Outputs include four equipped material views, a neutral front view, LOD1/2 front
views, and 27 motion frames: 15%, 50%, and 85% through each of the nine exported
clips. The Pillow command assembles those actual frames into a labeled contact
sheet. `battle_prelate_reimport_review.blend` saves the clean LOD0 assembly.

`review/reimport_report.json` remains `rendered_pending_visual_review`. Successful
reimport and rendering do not establish likeness, correct material appearance,
clearance, grip, or good deformation. Inspect the images and actual local game
before writing the accepted review described in `PROMOTION.md`. Its evidence
records can use the paths/hashes from the reimport report. Never mark checks
passed merely because a render completed.

For an explicitly partial early inspection, run the binary validator and review
with matching `--lods 0`. `--skip-motion` omits stress frames. Such a report has
`complete_evidence: false` and cannot substitute for the full promotion evidence.
