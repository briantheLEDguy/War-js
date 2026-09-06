"""Uncovered before/after head review under fixed cameras and lighting."""
import json
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_guards import proof, materials, studio, camera

bpy.ops.wm.read_factory_settings(use_empty=True)
materials(); studio()
skin=bpy.data.materials['proof.skin'].node_tree
shader=skin.nodes.get('Principled BSDF')
for link in list(shader.inputs['Base Color'].links): skin.links.remove(link)
shader.inputs['Base Color'].default_value=(.52,.36,.27,1)
scene=bpy.context.scene; scene.cycles.samples=24
scene.render.resolution_x=640; scene.render.resolution_y=800
for label,source in [('before',ROOT.parent/'battle-prelate-reference-rebuild/source/head.json'),('after',ROOT/'anatomy/head_refined.json')]:
    proof.COLLECTION='ANATOMY_'+label
    collection,_=proof.load_sources(root=ROOT,snapshots={'head.json':source.read_bytes()},scene_data={'comparison_pose':{}})
    for view,loc in [('front',(0,-3,1.73)),('side',(3,0,1.73)),('three_quarter',(2,-3,1.77))]:
        scene.camera=camera(label+'_'+view,loc,(0,-.025,1.716),.35)
        scene.render.filepath=str(ROOT/'review'/f'anatomy_{label}_{view}.png')
        bpy.ops.render.render(write_still=True)
    for obj in list(collection.all_objects): obj.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'anatomy/head_anatomy_review.blend'),compress=True)
