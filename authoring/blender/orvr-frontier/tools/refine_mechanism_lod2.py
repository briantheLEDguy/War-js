"""Finish distance surfaces without sacrificing wheel rings, pivots or clips."""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_collection as build
ROOT=build.ROOT


def refine(asset):
    report_path=ROOT/'review'/f'{asset}_build.json';record=json.loads(report_path.read_text())
    previous=next(lod for lod in record['lods'] if lod['level']==2)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection,parts=build.setup_asset(asset,2)
    policies={}
    for obj in parts:
        kind=obj['authored_part']
        # Recompute broad face normals after simplification. Normals baked
        # before collapsing bevel support made flat boards look dented.
        for modifier in list(obj.modifiers):
            if modifier.type=='WEIGHTED_NORMAL':obj.modifiers.remove(modifier)
            elif modifier.type=='BEVEL':modifier.segments=max(2,modifier.segments)
            elif modifier.type=='DECIMATE' and kind=='wheel_iron_tire':obj.modifiers.remove(modifier)
            elif modifier.type=='DECIMATE' and kind=='oil_cauldron':modifier.ratio=.68
        weighted=obj.modifiers.new('finished_distance_face_normals','WEIGHTED_NORMAL');weighted.keep_sharp=True;weighted.weight=50
        policies[kind]='retained rolled tire curvature' if kind=='wheel_iron_tire' else 'retained two-segment bevels; normals finished after reduction'
    bpy.context.view_layer.update()
    low=build.evaluated_join(parts,asset+'.finished_lod2')
    for obj in parts:obj.hide_render=True;obj.hide_set(True)
    pieces,contract=build.split_rigid_nodes(low,asset);low.hide_render=True;low.hide_set(True)
    textures={};wheel_mesh=None
    for piece in pieces:
        component=piece.name
        if component.startswith('wheel_') and wheel_mesh is not None:piece.data=wheel_mesh;continue
        resolution=512 if asset=='frontier_oil_cauldron' else 256 if component=='realm_standard' else 1024
        textures[component]=build.baker.bake_module_atlas(piece,f'{asset}_lod2_{component}',ROOT/'textures/baked',resolution=resolution)
        piece.data.materials[0].name=f'frontier.atlas.{asset}.lod2.{component}'
        modifier=piece.modifiers.new('stable_runtime_triangles','TRIANGULATE');bpy.context.view_layer.objects.active=piece;bpy.ops.object.modifier_apply(modifier=modifier.name)
        if component.startswith('wheel_'):wheel_mesh=piece.data
    triangles=sum(len(piece.data.polygons) for piece in pieces)
    if triangles>=next(lod['triangles'] for lod in record['lods'] if lod['level']==1):raise ValueError(f'LOD2 must remain below LOD1: {asset} / {triangles}')
    bpy.ops.object.select_all(action='DESELECT')
    for piece in pieces:
        piece.select_set(True)
        if piece.parent:piece.parent.select_set(True)
    for name,position in build.SOURCE['assets'][asset].get('sockets',{}).items():
        socket=bpy.data.objects.new('socket.'+name,None);bpy.context.scene.collection.objects.link(socket);socket.location=position
        parent_name=build.SOURCE['assets'][asset].get('socket_parents',{}).get(name)
        if parent_name:
            parent=next(piece for piece in pieces if piece.name==parent_name);socket.parent=parent;socket.location=parent.matrix_world.inverted()@Vector(position)
        socket.select_set(True)
    clips=build.mechanics.author_mechanical_actions(pieces,asset)
    runtime=ROOT/'runtime'/f'{asset}_lod2.glb'
    bpy.ops.export_scene.gltf(filepath=str(runtime),export_format='GLB',use_selection=True,export_apply=True,export_animations=True,
        export_animation_mode='NLA_TRACKS',export_anim_slide_to_zero=True,export_frame_range=False,export_tangents=True,export_texcoords=True,export_normals=True)
    master=ROOT/'masters'/f'{asset}_lod2_finished.blend';bpy.ops.wm.save_as_mainfile(filepath=str(master))
    bounds={'minimum':[min((low.matrix_world@Vector(c))[i] for c in low.bound_box) for i in range(3)],'maximum':[max((low.matrix_world@Vector(c))[i] for c in low.bound_box) for i in range(3)]}
    replacement={'level':2,'path':str(runtime.relative_to(ROOT)),'sha256':build.sha(runtime),'bytes':runtime.stat().st_size,'triangles':triangles,
      'vertices':sum(len(piece.data.vertices) for piece in pieces),'materials':len({mat.name for piece in pieces for mat in piece.data.materials}),
      'bounds_z_up':bounds,'textures':textures,'rigid_nodes':contract,'clips':clips,
      'lod_refinement':{'tool':'tools/refine_mechanism_lod2.py','tool_sha256':build.sha(Path(__file__)),'previous_glb_sha256':previous['sha256'],
        'master':str(master.relative_to(ROOT)),'master_sha256':build.sha(master),'part_finishing':policies}}
    record['lods']=[replacement if row['level']==2 else row for row in record['lods']]
    report_path.write_text(json.dumps(record,indent=2)+'\n');print('FINISHED_DISTANCE '+asset+' '+str(triangles),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default=','.join(build.SOURCE['assets']))
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for asset in args.assets.split(','):refine(asset)
