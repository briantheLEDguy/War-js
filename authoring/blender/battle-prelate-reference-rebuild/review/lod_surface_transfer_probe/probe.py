"""Isolated fresh LOD1/2 surface transfer compared with the actual staged LOD0."""
import hashlib,json,sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector,Matrix

OUTPUT=Path(__file__).resolve().parent
ROOT=OUTPUT.parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import rig_character as builder
import build_proof as authored
import reimport_review as review
import bake_atlas
from smoke_bake_atlas import signature
review.bpy=bpy;review.Matrix=Matrix
SLOTS=('head','chest','shoulders')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_signature(objects):
    return {obj.name:{'vertices':[tuple(v.co) for v in obj.data.vertices],
        'faces':[(tuple(p.vertices),p.material_index) for p in obj.data.polygons],
        'uv':[(uv.name,[tuple(loop.uv) for loop in uv.data]) for uv in obj.data.uv_layers],
        'materials':[signature(mat) for mat in obj.data.materials],
        'modifiers':[(mod.type,getattr(mod,'levels',None),getattr(mod,'render_levels',None),getattr(mod,'segments',None)) for mod in obj.modifiers]}
        for obj in objects}

def image_pixels(image):
    values=np.empty(len(image.pixels),dtype=np.float32)
    image.pixels.foreach_get(values)
    return values.reshape((-1,4))

def render(objects,lod,mode,view):
    for obj in bpy.data.objects:
        if obj.type=='MESH':obj.hide_render=obj not in objects
    scene=bpy.context.scene
    camera=scene.camera
    record={
      'chest':{'target':(0,-.13,1.40),'offset':(0,-3,0),'scale':.53,'resolution':(1100,1100)},
      'shoulder':{'target':(.265,-.015,1.565),'offset':(2,-3,.18),'scale':.39,'resolution':(1100,1100)},
      'gorget':{'target':(0,-.005,1.608),'offset':(0,-3,.12),'scale':.37,'resolution':(1100,650)},
    }[view]
    target=Vector(record['target']);camera.location=target+Vector(record['offset'])
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=record['scale']
    scene.render.resolution_x,scene.render.resolution_y=record['resolution']
    scene.render.resolution_percentage=100
    scene.render.filepath=str(OUTPUT/f'lod{lod}_{view}_{mode}.png')
    bpy.ops.render.render(write_still=True)
    path=Path(scene.render.filepath)
    return {'path':str(path),'sha256':digest(path),'camera':record}

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    inputs=[ROOT/'source/scene.json',ROOT/'source/humanoid_game_v2_animation_contract.blend',
            ROOT/'runtime/runtime_report.json',ROOT/'battle_prelate_game_master.blend',
            ROOT/'tools/rig_character.py',ROOT/'tools/bake_atlas.py',ROOT/'tools/build_proof.py']
    inputs+=list((ROOT/'source').glob('*.json'))
    inputs+=[ROOT/'runtime'/review.model_name(slot,lod) for slot in SLOTS for lod in (0,1,2)]
    before_files={str(path):digest(path) for path in set(inputs) if path.exists()}
    scene_data=json.loads((ROOT/'source/scene.json').read_text())
    control,_=authored.load_sources(scene_data=dict(scene_data,comparison_pose={}))
    rig=builder.import_contract_rig(ROOT/'not_used_frozen_contract_exists.glb')
    sources={slot:[obj for obj in control.all_objects if obj.type=='MESH' and builder.source_slot(obj)==slot] for slot in SLOTS}
    all_sources=[obj for slot in SLOTS for obj in sources[slot]]
    source_before=source_signature(all_sources)
    modules={0:[],1:[],2:[]}
    report={'scope':'Isolated fresh low evaluation and source surface-channel transfer; staged files are read only',
            'input_hashes':before_files,'lods':{},'evidence':[]}
    for slot in SLOTS:
        objects,import_report=review.rebind_armor(ROOT/'runtime'/review.model_name(slot,0),rig,slot)
        modules[0].extend(objects)
        report['lods'].setdefault('0',{})[slot]={'reference_glb':import_report}
    for lod in (1,2):
        collection=bpy.data.collections.new(f'ISOLATED_PROBE_LOD{lod}')
        bpy.context.scene.collection.children.link(collection)
        report['lods'][str(lod)]={}
        for slot in SLOTS:
            parts=[builder.evaluate_runtime_part(source,collection,rig,lod) for source in sources[slot]
                   if not(lod==2 and source['source_part'] in builder.LOD2_OMIT)]
            obj=builder.join_slot(parts,slot,lod)
            modules[lod].append(obj)
            resolution=1024 if lod==1 else 512
            paths=bake_atlas.bake_module_atlas(obj,f'probe_{slot}_lod{lod}',OUTPUT/f'lod{lod}',
                resolution=resolution,high_sources=sources[slot],transfer_surface_channels=True)
            material=obj.data.materials[0]
            base=image_pixels(material.node_tree.nodes['Base Color Atlas'].image)
            normal=image_pixels(material.node_tree.nodes['Normal Atlas'].image)
            gold=(base[:,0]>base[:,1]*1.10)&(base[:,1]>base[:,2]*1.18)&(base[:,0]>.15)
            obj.data.calc_loop_triangles()
            report['lods'][str(lod)][slot]={'triangles':len(obj.data.loop_triangles),'resolution':resolution,
                'gold_candidate_texels':int(gold.sum()),'normal_xy_range':np.ptp(normal[:,:2],axis=0).tolist(),
                'textures':{name:{'path':path,'sha256':digest(Path(path))} for name,path in paths.items()}}
            assert len(paths)==6 and len(obj.data.materials)==1 and len(obj.data.uv_layers)==1
            print('LOD_SURFACE_BAKED',lod,slot,flush=True)
    assert source_signature(all_sources)==source_before,'Retained source geometry, UV, modifier, or material state changed'
    authored.setup_review(scene_data)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
    camera_data=bpy.data.cameras.new('isolated_surface_probe_camera');camera_data.type='ORTHO'
    camera=bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera);scene.camera=camera
    for lod,objects in modules.items():
        for view in ('chest','shoulder','gorget'):
            report['evidence'].append(render(objects,lod,'material',view))
    # Color-only emission renders remove metallic highlights from the comparison.
    original_surfaces=[]
    for obj in [obj for objects in modules.values() for obj in objects]:
        for material in obj.data.materials:
            tree=material.node_tree;output,shader=bake_atlas._source_shader(material)
            original_surfaces.append((tree,output,output.inputs['Surface'].links[0].from_socket))
            emission=tree.nodes.new('ShaderNodeEmission')
            color=shader.inputs['Base Color']
            if color.is_linked:tree.links.new(color.links[0].from_socket,emission.inputs['Color'])
            else:emission.inputs['Color'].default_value=color.default_value
            tree.links.new(emission.outputs['Emission'],output.inputs['Surface'])
    scene.view_settings.view_transform='Standard'
    for lod,objects in modules.items():
        for view in ('chest','shoulder','gorget'):
            report['evidence'].append(render(objects,lod,'basecolor',view))
    for tree,output,socket in original_surfaces:tree.links.new(socket,output.inputs['Surface'])
    after_files={str(path):digest(path) for path in map(Path,before_files)}
    assert after_files==before_files,'Frozen inputs or staged outputs changed during probe'
    report['retained_sources_unchanged']=True;report['frozen_files_unchanged']=True
    report['status']='bakes_complete_pending_visual_inspection'
    (OUTPUT/'probe_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('LOD_SURFACE_PROBE_COMPLETE',str(OUTPUT),flush=True)

if __name__=='__main__':main()
