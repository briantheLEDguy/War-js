"""Fresh exact GLB inspection at neutral, detail and measured game distances."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from review_items import audit,render
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--assets');parser.add_argument('--lods',default='0,1,2');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
for report in sorted((ROOT/'review').glob('*_build.json')):
    build=json.loads(report.read_text());key=build['asset_id']
    if args.assets and key not in args.assets.split(','):continue
    for lod in build['lods']:
        if str(lod['level']) not in args.lods.split(','):continue
        path=ROOT/'runtime'/lod['model'];bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path));objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];result=audit(objects)
        if any(result[k] for k in ('totalBoundaryEdges','totalMultiFaceEdges','totalLooseEdges')):raise RuntimeError('Actual GLB positional topology failed: '+path.name)
        record={'model':path.name,'sha256':sha(path),'reviewerSha256':sha(Path(__file__)),'cameraToolSha256':sha(ROOT/'tools/review_items.py'),'audit':result,'views':{}}
        modes={'neutral':{},'gameplay':{'distance':[4,12,28][lod['level']]}}
        if lod['level']==0:
            modes['detail']={'detail':True,'detail_target':(-.74,-.50,1.005) if key.endswith('repair_bench') else (.24,-.17,.49),'detail_frame':.85 if key.endswith('repair_bench') else 1.37,'camera_direction':(.65,-1,.55)}
        for mode,options in modes.items():
            image=ROOT/'review'/f'{path.stem}_{mode}.png';camera=render(objects,image,**options);record['views'][mode]={'image':image.name,'sha256':sha(image),'camera':camera}
        output=ROOT/'review'/f'{path.stem}_reimport.json';temporary=output.with_suffix('.json.tmp');temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(output);print('WORKSHOP_REIMPORTED',path.name,flush=True)
