"""Bake distant authored material detail without cross-shell normal rays.

Preserves the previous LOD2 geometry and mechanical pivots exactly. The runtime
surface has enough silhouette geometry for distance; its own painted bump is
more faithful than rays that can strike unrelated adjacent assembled shells.
"""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_collection as build

ROOT=build.ROOT


def refine(asset_id):
    if asset_id=='frontier_supply_wagon': raise ValueError('Wagon has its own fitted LOD2 authoring pass')
    report_path=ROOT/'review'/f'{asset_id}_build.json'
    record=json.loads(report_path.read_text()); old=next(row for row in record['lods'] if row['level']==2)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection,parts=build.setup_asset(asset_id,2)
    low=build.evaluated_join(parts,f'{asset_id}.lod2_refined')
    for obj in parts: obj.hide_render=True; obj.hide_set(True)
    bpy.context.view_layer.objects.active=low
    modifier=low.modifiers.new('inspected_lod_reduction','DECIMATE'); modifier.ratio=.38
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    pieces,contract=build.split_rigid_nodes(low,asset_id)
    low.hide_render=True; low.hide_set(True)
    for image in bpy.data.images:
        if image.source=='FILE': image.pack()
    lod_master=ROOT/'masters'/f'{asset_id}_lod2.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(lod_master))
    texture_paths={}; wheel_mesh=None
    for piece in pieces:
        component=piece.name
        if component.startswith('wheel_') and wheel_mesh is not None:
            piece.data=wheel_mesh; continue
        resolution=512 if asset_id=='frontier_oil_cauldron' else 1024
        texture_paths[component]=build.baker.bake_module_atlas(piece,f'{asset_id}_lod2_{component}',ROOT/'textures/baked',resolution=resolution)
        piece.data.materials[0].name=f'frontier.atlas.{asset_id}.lod2.{component}'
        modifier=piece.modifiers.new('stable_runtime_triangles','TRIANGULATE')
        bpy.context.view_layer.objects.active=piece; bpy.ops.object.modifier_apply(modifier=modifier.name)
        if component.startswith('wheel_'): wheel_mesh=piece.data
    triangle_count=sum(len(piece.data.polygons) for piece in pieces)
    if triangle_count!=old['triangles']: raise ValueError(f'Unexpected LOD2 geometry change: {triangle_count} != {old["triangles"]}')
    bpy.ops.object.select_all(action='DESELECT')
    for piece in pieces: piece.select_set(True)
    runtime=ROOT/'runtime'/f'{asset_id}_lod2.glb'
    bpy.ops.export_scene.gltf(filepath=str(runtime),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True,export_texcoords=True,export_normals=True)
    bounds={'minimum':[min((low.matrix_world@Vector(c))[i] for c in low.bound_box) for i in range(3)],'maximum':[max((low.matrix_world@Vector(c))[i] for c in low.bound_box) for i in range(3)]}
    replacement={'level':2,'path':str(runtime.relative_to(ROOT)),'sha256':build.sha(runtime),'bytes':runtime.stat().st_size,
                 'triangles':triangle_count,'vertices':sum(len(piece.data.vertices) for piece in pieces),
                 'materials':len({material.name for piece in pieces for material in piece.data.materials}),'bounds_z_up':bounds,'textures':texture_paths,'rigid_nodes':contract,
                 'lod_refinement':{'tool':'tools/refine_distance_normals.py','tool_sha256':build.sha(Path(__file__)),
                                   'previous_glb_sha256':old['sha256'],'master':str(lod_master.relative_to(ROOT)),'master_sha256':build.sha(lod_master),
                                   'normal_source':'evaluated LOD2 mesh and original authored material bump; no cross-shell ray projection',
                                   'geometry_policy':'original evaluated LOD2 finishing and 38 percent reduction retained; exact rendered triangle count preserved'}}
    record['lods']=[replacement if row['level']==2 else row for row in record['lods']]
    report_path.write_text(json.dumps(record,indent=2)+'\n')
    print(f"FRONTIER_DISTANCE_REFINED {asset_id} triangles={triangle_count} bytes={replacement['bytes']}",flush=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--assets',default=','.join(key for key in build.SOURCE['assets'] if key!='frontier_supply_wagon'))
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for asset_id in args.assets.split(','): refine(asset_id)


if __name__=='__main__': main()
