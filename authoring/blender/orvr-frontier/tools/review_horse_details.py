"""Literal GLB anatomy, harness and shoulder/hip pose close views."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_collection as build
from review_motion import activate_clip
from review_caravan_assembly import snapshots
ROOT=build.ROOT


def render(objects, name, centre, direction, scale):
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
    scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('anatomy_review_world');scene.world.color=(.20,.20,.20)
    camera_data=bpy.data.cameras.new('anatomy_review_camera');camera=bpy.data.objects.new('anatomy_review_camera',camera_data);scene.collection.objects.link(camera)
    camera.location=Vector(centre)+Vector(direction);camera.rotation_euler=(Vector(centre)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.type='ORTHO';camera_data.ortho_scale=scale;scene.camera=camera
    for label,offset,power,size,color in [('key',(-3,-4,5),950,3,(1,.87,.70)),('fill',(4,-2,3),700,3,(.72,.84,1)),('rim',(0,4,5),1000,2,(1,.93,.8))]:
        data=bpy.data.lights.new(label,'AREA');data.energy=power;data.size=size;data.color=color
        light=bpy.data.objects.new(label,data);scene.collection.objects.link(light);light.location=Vector(centre)+Vector(offset)
        light.rotation_euler=(Vector(centre)-light.location).to_track_quat('-Z','Y').to_euler()
    output=ROOT/'review'/f'{name}.png';scene.view_settings.view_transform='AgX';scene.render.filepath=str(output)
    bpy.ops.render.render(write_still=True)
    return {'image':str(output.relative_to(ROOT)),'image_sha256':build.sha(output)}


def main():
    path=ROOT/'runtime/frontier_draft_horse_lod0.glb';records=[]
    for name,clip,time,centre,offset,scale in [
      ('frontier_draft_horse_head_close','idle',0,(0,-1.34,1.84),(2.1,-3,1.0),1.63),
      ('frontier_draft_horse_side_anatomy','idle',0,(0,-.15,1.18),(6,-.25,1.1),3.65),
      ('frontier_draft_horse_trot_side','draft_trot',.1666666667,(0,-.15,1.18),(6,-.25,1.1),3.65)]:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(path))
        sources=[obj for obj in bpy.context.scene.objects if obj.type=='MESH' and not obj.hide_render and obj.visible_get()]
        activate_clip(clip,time);objects=snapshots(sources)
        for obj in sources:obj.hide_render=True;obj.hide_set(True)
        records.append({'asset':'frontier_draft_horse','glb_sha256':build.sha(path),'clip':clip,'seconds':time,
                        'decision':'pending_visual_review',**render(objects,name,centre,offset,scale)})
    (ROOT/'review/frontier_draft_horse_details.json').write_text(json.dumps({'views':records},indent=2)+'\n')


if __name__=='__main__':main()
