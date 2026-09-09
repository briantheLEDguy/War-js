"""Audit changed actual GLBs before spending time on their review renders."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from review_nature import audit
parser=argparse.ArgumentParser();parser.add_argument('--asset',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
build=json.loads((ROOT/'review'/f'{args.asset}_build.json').read_text())
rows=[]
for lod in build['lods']:
    model=ROOT/'runtime'/lod['model'];bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(model))
    result=audit([o for o in bpy.context.scene.objects if o.type=='MESH'])
    row={'model':model.name,'sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'triangles':lod['triangles'],'audit':result};rows.append(row)
    print('ACTUAL_PREFLIGHT',model.name,lod['triangles'],result['totalBoundaryEdges'],result['totalMultiFaceEdges'],result['totalLooseEdges'],flush=True)
(ROOT/'review'/f'{args.asset}_preflight.json').write_text(json.dumps(rows,indent=2)+'\n')
if any(r['audit'][k] for r in rows for k in ['totalBoundaryEdges','totalMultiFaceEdges','totalLooseEdges']):raise RuntimeError('Actual GLB positional topology failed')
if any(l['triangles']>[110000,40000,8000][l['level']] for l in build['lods']):raise RuntimeError('Actual nature LOD triangle budget exceeded')
