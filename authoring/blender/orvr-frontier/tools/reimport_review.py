"""Render actual exported GLBs in a clean scene, not their source proxies."""
import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('frontier_build',ROOT/'tools'/'build_collection.py')
build=importlib.util.module_from_spec(spec); spec.loader.exec_module(build)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--assets',default=','.join(build.SOURCE['assets'])); parser.add_argument('--lods',default='0,1,2'); parser.add_argument('--wait-build',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    review_path=ROOT/'review'/'reimport_renders.json'
    requested={(asset,int(lod)) for asset in args.assets.split(',') for lod in args.lods.split(',')}
    previous=json.loads(review_path.read_text()).get('renders',[]) if review_path.exists() else []
    records=[record for record in previous if (record['asset'],record['lod']) not in requested]
    for asset in args.assets.split(','):
        if args.wait_build:
            deadline=time.monotonic()+900
            while True:
                try:
                    report=json.loads((ROOT/'review'/f'{asset}_build.json').read_text())
                    ready=report['source_sha256']==build.sha(build.SOURCE_PATH) and report.get('builder_sha256')==build.sha(ROOT/'tools'/'build_collection.py') and len(report['lods'])==3
                    if ready and all(build.sha(ROOT/lod['path'].replace('\\','/'))==lod['sha256'] for lod in report['lods']): break
                except (OSError,KeyError,json.JSONDecodeError): pass
                if time.monotonic()>deadline: raise RuntimeError(f'Timed out waiting for complete current exports: {asset}')
                time.sleep(1)
        for lod in args.lods.split(','):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            filepath=ROOT/'runtime'/f'{asset}_lod{lod}.glb'
            bpy.ops.import_scene.gltf(filepath=str(filepath))
            objects=[obj for obj in bpy.context.scene.objects if obj.type=='MESH' and not obj.hide_render and obj.visible_get()]
            output=ROOT/'review'/f'{asset}_lod{lod}_reimport.png'
            bounds=build.set_view(objects,output)
            records.append({'asset':asset,'lod':int(lod),'glb_sha256':build.sha(filepath),'image':str(output.relative_to(ROOT)),
                            'image_sha256':build.sha(output),'bounds':bounds,'review_decision':'pending','renderer':'Cycles 32 samples, AgX, orthographic review camera'})
            (ROOT/'review'/'reimport_renders.json').write_text(json.dumps({'renders':records,'visual_approval':False},indent=2)+'\n')
            print(f'FRONTIER_REVIEW {asset} LOD{lod}',flush=True)
    (ROOT/'review'/'reimport_renders.json').write_text(json.dumps({'renders':records,'visual_approval':False},indent=2)+'\n')


if __name__=='__main__': main()
