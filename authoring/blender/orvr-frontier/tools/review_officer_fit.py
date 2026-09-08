"""Fit the independent belt kit to the literal approved equipped humanoid."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_collection as build
from review_caravan_assembly import PUBLIC, PROJECT, imported, equipped_actor, snapshots
ROOT=build.ROOT


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30
    catalog=json.loads((PUBLIC/'asset-index.json').read_text());inputs=[]
    def load(path,expected=None):
        actual=build.sha(path)
        if expected and expected!=actual:raise ValueError('Approved actor input hash mismatch')
        inputs.append({'path':str(path.relative_to(PROJECT)),'sha256':actual});return imported(path)
    rig,body,equipment,hidden=equipped_actor(catalog,load)
    action=bpy.data.actions[rig['review_idle_action']]
    rig.animation_data_create();rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    kit=load(ROOT/'runtime/frontier_supply_officer_kit_lod0.glb')
    socket=next(obj for obj in kit if obj.name=='socket.belt_mount')
    # The pouch clears the left cuisse and hangs from the actual existing belt.
    desired=Matrix.Translation(Vector((.24,-.015,1.065))) @ Matrix.Rotation(1.0,4,'Z') @ Matrix.Translation(-socket.location)
    attachment=rig.data.bones['hips'].matrix_local.inverted() @ desired
    bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
    posed=rig.pose.bones['hips'].matrix @ attachment
    for obj in kit:
        if obj.parent not in kit:obj.matrix_world=posed @ obj.matrix_world
    all_objects=body+equipment+kit;bpy.context.view_layer.update();proof=snapshots(all_objects)
    for obj in all_objects:
        if obj.type=='MESH':obj.hide_render=True;obj.hide_set(True)
    output=ROOT/'review/frontier_supply_officer_equipped.png';build.set_view(proof,output)
    conversion=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))
    # Bone-local transforms preserve their exported basis; only the parent world
    # frame is converted. Matrix composition is tested against the actual GLB.
    bone_world_gltf=conversion @ rig.data.bones['hips'].matrix_local
    kit_world_gltf=conversion @ desired @ conversion.inverted()
    local_gltf=bone_world_gltf.inverted() @ kit_world_gltf
    record={'status':'pending_visual_review','inputs':inputs,'asset_id':'frontier_supply_officer_kit',
      'profile_key':'civic_battle_prelate_m','skeleton_id':'humanoid_game_v2','bone':'hips',
      'attachment_matrix_gltf_column_major':[local_gltf[row][column] for column in range(4) for row in range(4)],
      'rest_mount_avatar_gltf':[.24,1.065,.015], 'image':str(output.relative_to(ROOT)),'image_sha256':build.sha(output),
      'scope':'Fitted only to this approved body and novitiate armor at scale1; other body/race profiles require a separate fit.'}
    (ROOT/'review/frontier_supply_officer_fit.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':main()
