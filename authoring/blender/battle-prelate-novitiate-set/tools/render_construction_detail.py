"""Supplemental closeups of actual exports, without moving comparison cameras."""
import hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import reimport_review as review
import build_proof as proof
review.bpy=bpy; review.Matrix=Matrix
assembly=review.assemble(ROOT/'runtime',0)
proof.setup_review(json.loads((ROOT/'source/scene.json').read_text()))
neutral=proof.make_review_material()
data=bpy.data.cameras.new('diagnostic.construction')
camera=bpy.data.objects.new(data.name,data)
bpy.context.scene.collection.objects.link(camera)
data.type='ORTHO';data.ortho_scale=.78
scene=bpy.context.scene
scene.camera=camera
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1000;scene.render.resolution_y=1125;scene.render.resolution_percentage=100
records=[]
for name,clip,fraction,material in [('melee_fit_cycles','attack_melee',.25,neutral),('construction_detail','idle',.25,None)]:
    review.set_clip(assembly,clip,fraction)
    target=assembly['rig'].matrix_world@assembly['rig'].pose.bones['upper_chest'].head
    camera.location=target+Vector((1.6,-3,1))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.view_layers[0].material_override=material
    scene.render.filepath=str(ROOT/'review'/f'{name}.png')
    bpy.ops.render.render(write_still=True)
    records.append({'file':f'review/{name}.png','sha256':review.digest(Path(scene.render.filepath)),'clip':clip,'fraction':fraction,'position':list(camera.location),'target':list(target),'ortho_scale':data.ortho_scale})
(ROOT/'review/construction_detail.json').write_text(json.dumps({'model_hashes':{slot:item['sha256'] for slot,item in assembly['modules'].items()},'camera_policy':'Supplemental detail cameras; frozen comparisons unchanged','renders':records},indent=2)+'\n')
