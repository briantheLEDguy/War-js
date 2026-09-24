"""Blender inspection of available authored geometry and canonical attachments."""
import bpy
import json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"artifacts/unreal/animation-replacement"
rows={}
for key,path in {
    "prelate_master":"authoring/blender/battle-prelate-reference-rebuild/battle_prelate_game_master.blend",
    "warbrute":"public/assets/models/chr_mire_warbrute_t1_m.glb",
    "ember":"public/assets/models/chr_civic_ember_arcanist_t1_m.glb"}.items():
    if path.endswith(".blend"): bpy.ops.wm.open_mainfile(filepath=str(ROOT/path))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(ROOT/path),disable_bone_shape=True)
    rows[key]=[]
    for obj in bpy.data.objects:
        if obj.type not in ("MESH","ARMATURE","EMPTY"): continue
        row=dict(name=obj.name,type=obj.type,properties={k:str(v)[:100] for k,v in obj.items()},collections=[c.name for c in obj.users_collection])
        if obj.type=="MESH": row.update(vertices=len(obj.data.vertices),materials=[m.name for m in obj.data.materials],bounds=[list(obj.matrix_world@Vector(c)) for c in obj.bound_box])
        if obj.type=="ARMATURE": row.update(bones=[b.name for b in obj.data.bones])
        rows[key].append(row)
(OUT/"source-models.json").write_text(json.dumps(rows,indent=2)+"\n")
