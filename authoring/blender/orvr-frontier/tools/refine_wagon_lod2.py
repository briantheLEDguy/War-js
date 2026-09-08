"""Retain fitted canopy edges and wood bevel support in the distant wagon.

This is an explicit LOD authoring pass. Unlike the initial whole-object
reduction, construction surfaces retain the topology needed for their fit.
"""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_collection as build

ROOT=build.ROOT
ASSET='frontier_supply_wagon'


def main():
    report_path=ROOT/'review'/f'{ASSET}_build.json'
    record=json.loads(report_path.read_text()); old=next(row for row in record['lods'] if row['level']==2)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection,parts=build.setup_asset(ASSET,2)
    policies={}
    for obj in parts:
        kind=obj['authored_part']; part=build.SOURCE['parts'][kind]
        obj.modifiers.clear()
        if kind in ('cloth_canopy','canopy_seam'):
            build.apply_modifiers(obj,part,0)
            # Extra seam thickness closes the visible seam/cloth subpixel gap at
            # distance without adding a proxy or changing the authored outline.
            for modifier in obj.modifiers:
                if modifier.type=='SOLIDIFY': modifier.thickness=max(modifier.thickness,.025)
            policy='full authored subdivision; retained cloth edge thickness'
        elif kind.startswith('wheel_'):
            build.apply_modifiers(obj,part,2)
            modifier=obj.modifiers.new('wheel_distance_reduction','DECIMATE'); modifier.ratio=.42
            policy='distance wheel finishing; 42 percent reduction after bevel'
        else:
            build.apply_modifiers(obj,part,1)
            policy='two-segment wood/hardware bevel support; no global collapse'
        policies[kind]=policy
    bpy.context.view_layer.update()
    for image in bpy.data.images:
        if image.source=='FILE': image.pack()
    lod_master=ROOT/'masters'/f'{ASSET}_lod2.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(lod_master))
    low=build.evaluated_join(parts,f'{ASSET}.lod2_refined')
    for obj in parts: obj.hide_render=True; obj.hide_set(True)
    pieces,contract=build.split_rigid_nodes(low,ASSET)
    low.hide_render=True; low.hide_set(True)
    texture_paths={}; wheel_mesh=None
    for piece in pieces:
        component=piece.name
        if component.startswith('wheel_') and wheel_mesh is not None:
            piece.data=wheel_mesh; continue
        texture_paths[component]=build.baker.bake_module_atlas(piece,f'{ASSET}_lod2_{component}',ROOT/'textures/baked',resolution=1024)
        piece.data.materials[0].name=f'frontier.atlas.{ASSET}.lod2.{component}'
        modifier=piece.modifiers.new('stable_runtime_triangles','TRIANGULATE')
        bpy.context.view_layer.objects.active=piece; bpy.ops.object.modifier_apply(modifier=modifier.name)
        if component.startswith('wheel_'): wheel_mesh=piece.data
    bpy.ops.object.select_all(action='DESELECT')
    for piece in pieces: piece.select_set(True)
    runtime=ROOT/'runtime'/f'{ASSET}_lod2.glb'
    bpy.ops.export_scene.gltf(filepath=str(runtime),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True,export_texcoords=True,export_normals=True)
    bounds={'minimum':[min((low.matrix_world@Vector(c))[i] for c in low.bound_box) for i in range(3)],'maximum':[max((low.matrix_world@Vector(c))[i] for c in low.bound_box) for i in range(3)]}
    replacement={'level':2,'path':str(runtime.relative_to(ROOT)),'sha256':build.sha(runtime),'bytes':runtime.stat().st_size,
                 'triangles':sum(len(piece.data.polygons) for piece in pieces),'vertices':sum(len(piece.data.vertices) for piece in pieces),
                 'materials':len({material.name for piece in pieces for material in piece.data.materials}),'bounds_z_up':bounds,'textures':texture_paths,'rigid_nodes':contract,
                 'lod_refinement':{'tool':'tools/refine_wagon_lod2.py','tool_sha256':build.sha(Path(__file__)),
                                   'previous_glb_sha256':old['sha256'],'master':str(lod_master.relative_to(ROOT)),'master_sha256':build.sha(lod_master),
                                   'part_finishing':policies,'normal_source':'evaluated LOD mesh and original authored material bump; no cross-shell ray projection'}}
    if replacement['triangles']>=next(row['triangles'] for row in record['lods'] if row['level']==1): raise ValueError('Refined LOD2 must stay below LOD1 geometry count')
    record['lods']=[replacement if row['level']==2 else row for row in record['lods']]
    report_path.write_text(json.dumps(record,indent=2)+'\n')
    print(f"FRONTIER_WAGON_REFINED triangles={replacement['triangles']} bytes={replacement['bytes']}",flush=True)


if __name__=='__main__': main()
