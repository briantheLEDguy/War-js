"""A removable pair of fitted reins for the literal wagon/horse assembly."""
import json
from pathlib import Path
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
import author_draft_horse as geometry
import build_collection as build
ROOT=build.ROOT;ASSET='frontier_caravan_reins'


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    leather=geometry.material('caravan.rein_leather',(.027,.012,.004),.72)
    iron=geometry.material('caravan.bit_iron',(.14,.15,.16),.36,.86)
    objects=[]
    stations=[(.20,-1.61,1.895),(.32,-2.20,1.81),(.51,-3.00,1.68),(.49,-3.80,1.59),(.49,-4.50,1.57),(.34,-5.05,1.59),(.17,-5.51,1.54)]
    for side,label in [(-1,'left'),(1,'right')]:
        rein=geometry.strap('caravan_rein_'+label,[(side*x,y,z) for x,y,z in stations],leather,.023,(0,0,1));objects.append(rein)
        ring=[(side*.17,-5.51,1.54),(side*.17,-5.537,1.552),(side*.17,-5.551,1.577),(side*.17,-5.535,1.599),
          (side*.17,-5.508,1.603),(side*.17,-5.485,1.585),(side*.17,-5.487,1.559),(side*.17,-5.51,1.54)]
        objects.append(geometry.tube('caravan_bit_ring_'+label,ring,iron,.004))
    objects.append(geometry.tube('caravan_bit_mouthpiece',[(-.17,-5.514,1.565),(-.10,-5.526,1.557),(0,-5.532,1.56),(.10,-5.526,1.557),(.17,-5.514,1.565)],iron,.004))
    for obj in objects:obj['source_policy']='Original fitted rein paths and hand-shaped bit loops; no primitive geometry';obj['rigid_group']='reins'
    source=ROOT/'masters'/f'{ASSET}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(source))
    records=[]
    for level in (0,1,2):
        mesh=build.evaluated_join(objects,f'{ASSET}_lod{level}')
        if level:
            modifier=mesh.modifiers.new('rein_distance_reduction','DECIMATE');modifier.ratio=.65 if level==1 else .38
            bpy.context.view_layer.objects.active=mesh;bpy.ops.object.modifier_apply(modifier=modifier.name)
        mesh.data.uv_layers.new(name='construction_uv');bpy.context.view_layer.objects.active=mesh
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1,island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
        textures=build.baker.bake_module_atlas(mesh,f'{ASSET}_lod{level}',ROOT/'textures/baked',resolution=1024 if level<2 else 512)
        modifier=mesh.modifiers.new('stable_runtime_triangles','TRIANGULATE');bpy.context.view_layer.objects.active=mesh;bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);sockets=[]
        for side,label in [(-1,'left'),(1,'right')]:
            socket=bpy.data.objects.new('socket.driver_hand_'+label,None);bpy.context.scene.collection.objects.link(socket);socket.location=(side*.20,-1.61,1.895);socket.select_set(True);sockets.append(socket)
        runtime=ROOT/'runtime'/f'{ASSET}_lod{level}.glb'
        bpy.ops.export_scene.gltf(filepath=str(runtime),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True)
        records.append({'level':level,'path':str(runtime.relative_to(ROOT)),'sha256':build.sha(runtime),'bytes':runtime.stat().st_size,'triangles':len(mesh.data.polygons),'materials':len(mesh.data.materials),'textures':textures})
        for socket in sockets:bpy.data.objects.remove(socket,do_unlink=True)
        mesh.hide_set(True);mesh.hide_render=True
    (ROOT/'review'/f'{ASSET}_build.json').write_text(json.dumps({'asset_id':ASSET,'approval':'pending_visual_review','source_sha256':build.sha(Path(__file__)),'master':str(source.relative_to(ROOT)),'master_sha256':build.sha(source),'lods':records,'limitations':['Origin is the wagon origin; only mount with the horse at glTF[0,0,3.75]. Reins are loose static leather fitted for subtle head movement.']},indent=2)+'\n')


if __name__=='__main__':main()
