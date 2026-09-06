"""Set an editable presentation view on the finished master; no mesh edits."""
from pathlib import Path
import json
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
master=ROOT/"battle_prelate_game_master.blend"
bpy.ops.wm.open_mainfile(filepath=str(master))
rig=bpy.data.objects["humanoid_game_v2"]
rig.animation_data.action=bpy.data.actions["idle"]
rig.animation_data.action_slot=bpy.data.actions["idle"].slots[0]
rig.data.pose_position="POSE"
bpy.context.scene.frame_set(12)
scene_data=json.loads((ROOT/"source/scene.json").read_text())
camera=next(record for record in scene_data["cameras"] if record["id"]=="full_three_quarter")
rotation=(Vector(camera["target"])-Vector(camera["position"])).to_track_quat("-Z","Y")
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=="VIEW_3D":
            space=area.spaces.active
            space.region_3d.view_location=Vector((0,0,.97))
            space.region_3d.view_rotation=rotation
            space.region_3d.view_distance=3.0
            space.region_3d.view_perspective="ORTHO"
            space.overlay.show_overlays=False
            space.shading.type="MATERIAL"
bpy.ops.object.select_all(action="DESELECT")
rig["master_note"]="Opens in the corrected idle presentation pose. Switch armature to Rest Position for fitting. Authored source cages are retained in the hidden source collection."
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(master),compress=True)
print("MASTER_PRESENTATION_SAVED",master)
