"""Bake and export the retained original horse, rig and fitted harness at three LODs."""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_collection as build

ROOT=build.ROOT
ASSET='frontier_draft_horse'


def export_lod(level):
    source=ROOT/'masters'/f'{ASSET}_rigged.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    rig=bpy.data.objects['draft_horse_rig'];rig.animation_data_clear()
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
    sources=[obj for obj in rig.children if obj.type=='MESH' and obj.name.endswith('.weighted')]
    groups={'coat':[],'tack':[]}
    for obj in sources:
        obj.hide_set(False);obj.hide_render=False
        for modifier in obj.modifiers:
            if modifier.type=='ARMATURE':modifier.show_viewport=False;modifier.show_render=False
        if level or 'continuous_skin' in obj.name:
            reduction=obj.modifiers.new('anatomy_aware_lod','DECIMATE')
            reduction.ratio=[.48,.18,.045][level] if 'continuous_skin' in obj.name else [1,.65,.28][level]
            bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=reduction.name)
        if 'hoof' in obj.name:
            ground=min(vertex.co.z for vertex in obj.data.vertices)
            for vertex in obj.data.vertices:vertex.co.z-=ground
        if not obj.data.uv_layers:
            obj.data.uv_layers.new(name='construction_uv')
            bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
            bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.012)
            bpy.ops.object.mode_set(mode='OBJECT')
        group='tack' if any(word in obj.name for word in ('collar','hame','trace','bridle','noseband','shaft_tug','tug_support','saddle','girth','breeching','hip_strap')) else 'coat'
        groups[group].append(obj)
    meshes=[];textures={}
    for name,objects in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();mesh=bpy.context.object
        mesh.name=ASSET+'_'+name
        bpy.ops.object.vertex_group_limit_total(limit=4)
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
        resolution=(2048 if name=='coat' else 1024)//(2 if level==2 else 1)
        textures[name]=build.baker.bake_module_atlas(mesh,ASSET+'_lod'+str(level)+'_'+name,ROOT/'textures'/'baked',resolution=resolution)
        modifier=mesh.modifiers.new('stable_runtime_triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=modifier.name)
        for modifier in mesh.modifiers:
            if modifier.type=='ARMATURE':modifier.show_viewport=True;modifier.show_render=True
        meshes.append(mesh)
    rig.animation_data_create()
    clip_records=[]
    for name,start in [('idle',140),('walk',300),('draft_trot',400)]:
        action=bpy.data.actions[name];track=rig.animation_data.nla_tracks.new();track.name=name
        strip=track.strips.new(name,start,action);strip.extrapolation='NOTHING';strip.blend_type='REPLACE'
        if action.slots:strip.action_slot=action.slots[0]
        clip_records.append({'name':name,'seconds':(action.frame_range[1]-action.frame_range[0])/30,'root_motion':False})
    bpy.context.scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for mesh in meshes:mesh.select_set(True)
    for name in ('hitch_shaft_left','hitch_shaft_right'):
        socket=bpy.data.objects[name];socket.select_set(True)
    destination=ROOT/'runtime'/f'{ASSET}_lod{level}.glb'
    bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',use_selection=True,
        export_apply=False,export_animations=True,export_animation_mode='NLA_TRACKS',export_anim_slide_to_zero=True,
        export_frame_range=False,export_tangents=True,export_skins=True,export_def_bones=True)
    master=ROOT/'masters'/f'{ASSET}_lod{level}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(master))
    return {'level':level,'path':str(destination.relative_to(ROOT)),'sha256':build.sha(destination),'bytes':destination.stat().st_size,
        'triangles':sum(len(mesh.data.polygons) for mesh in meshes),'vertices':sum(len(mesh.data.vertices) for mesh in meshes),
        'master':str(master.relative_to(ROOT)),'master_sha256':build.sha(master),'textures':textures,'clips':clip_records}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--lods',default='0,1,2');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    record={'asset_id':ASSET,'approval':'pending_visual_review','source_sha256':build.sha(ROOT/'tools'/'author_draft_horse.py'),
        'rig_source_sha256':build.sha(ROOT/'tools'/'rig_draft_horse.py'),'exporter_sha256':build.sha(Path(__file__)),'lods':[]}
    for level in map(int,args.lods.split(',')):
        record['lods'].append(export_lod(level));(ROOT/'review'/f'{ASSET}_build.json').write_text(json.dumps(record,indent=2)+'\n')
        print('DRAFT_HORSE_EXPORTED_LOD '+str(level),flush=True)


if __name__=='__main__':main()
