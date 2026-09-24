"""Background Blender inventory of all supplied FBXs; never changes sources."""
import hashlib
import json
from pathlib import Path
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from animation_replacement import ROOT, SOURCE, OUT, CLIPS, coverage, presentation_catalog

OUT.mkdir(parents=True,exist_ok=True)
uses = coverage()
expected = {str((SOURCE / path).resolve()) for path in CLIPS.values()}
actual = {str(p.resolve()) for folder in ("Two-handed","swordandshield","Spellcast") for p in (SOURCE/folder).glob("*.fbx")}
if expected != actual:
    raise RuntimeError("Source inventory differs: " + str(expected ^ actual))
rows = {}
for key,relative in CLIPS.items():
    path = SOURCE / relative
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
    rigs = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if len(rigs) != 1 or not rigs[0].animation_data or not rigs[0].animation_data.action:
        raise RuntimeError("Source requires exactly one animated skeleton: " + relative)
    rig = rigs[0]
    action = rig.animation_data.action
    first,last = action.frame_range
    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    bones = [(b.name, b.parent.name if b.parent else None) for b in rig.data.bones]
    hips = next(b for b in rig.pose.bones if b.name.split(":")[-1] == "Hips")
    positions = []
    for frame in (first,last):
        bpy.context.scene.frame_set(int(frame))
        positions.append(list(rig.matrix_world @ hips.matrix.translation))
    row = dict(file=relative,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),fps=fps,
               frameRange=[first,last],duration=(last-first)/fps,bones=bones,
               skeletonHash=hashlib.sha256(json.dumps(bones).encode()).hexdigest(),
               hipsStart=positions[0],hipsEnd=positions[1],gameplayUses=uses[key],gameplayVerified=False)
    rows[key] = row
    print("WAR_ANIMATION_SOURCE",key,row["duration"],len(bones),flush=True)
(OUT/"sources.json").write_text(json.dumps(dict(schemaVersion=1,clipCount=len(rows),clips=rows),indent=2)+"\n")
(ROOT/'shared/game/animation/suppliedPresentationCatalog.json').write_text(json.dumps(presentation_catalog(rows),indent=2)+'\n')
