"""Fast actual-GLB transform proof before expensive material atlases are baked."""
import argparse
import json
from pathlib import Path
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_collection as build


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default='frontier_supply_wagon,frontier_battering_ram,frontier_oil_cauldron,frontier_field_catapult,frontier_keep_gate')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    destination=build.ROOT/'review'/'mechanics_proof';destination.mkdir(exist_ok=True)
    for asset in args.assets.split(','):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        _,source=build.setup_asset(asset,1)
        joined=build.evaluated_join(source,asset+'.proof');pieces,contract=build.split_rigid_nodes(joined,asset)
        for obj in source+[joined]:obj.hide_render=True;obj.hide_set(True)
        for piece in pieces:piece.hide_set(False);piece.hide_render=False
        clips=build.mechanics.author_mechanical_actions(pieces,asset)
        bpy.ops.object.select_all(action='DESELECT')
        for piece in pieces:
            piece.select_set(True)
            if piece.parent:piece.parent.select_set(True)
        filepath=destination/f'{asset}.glb'
        bpy.ops.export_scene.gltf(filepath=str(filepath),export_format='GLB',use_selection=True,export_apply=True,
            export_animations=True,export_animation_mode='NLA_TRACKS',export_anim_slide_to_zero=True,export_frame_range=False)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(filepath))
        meshes=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']
        report={'glb_sha256':build.sha(filepath),'clips':clips,'components':[]}
        for component in contract:
            obj=bpy.data.objects.get(component['node']);expected=component['pivot_z_up']
            actual=list(obj.matrix_world.translation)
            if max(abs(a-b) for a,b in zip(actual,expected))>1e-5:raise ValueError(f'{asset}/{obj.name}: actual exported pivot {actual} != {expected}')
            report['components'].append({'node':obj.name,'world_pivot_z_up':actual})
        (destination/f'{asset}.json').write_text(json.dumps(report,indent=2)+'\n')
        build.set_view(meshes,destination/f'{asset}.png')
        print('MECHANICS_EXPORT_PROOF '+asset,flush=True)


if __name__=='__main__':main()
