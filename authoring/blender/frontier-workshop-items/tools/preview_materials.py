"""Source PBR assembly and mechanical detail proofs; not runtime approval."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from materials_items import apply_materials
from review_items import render
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--assets',default='frontier_siege_repair_bench,frontier_siege_ammunition_cradle');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
for key in args.assets.split(','):
    source=ROOT/'masters'/f'{key}_lod0.source.blend';bpy.ops.wm.open_mainfile(filepath=str(source));objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render];apply_materials(objects)
    master=ROOT/'masters'/f'{key}_lod0.material-source.blend';bpy.ops.wm.save_as_mainfile(filepath=str(master))
    modes={'overall':{}}
    if key.endswith('repair_bench'):
        modes.update({'vise':{'detail':True,'detail_target':(-.74,-.50,1.005),'detail_frame':.76,'camera_direction':(.65,-1,.55)},'joinery':{'detail':True,'detail_target':(.93,-.27,.43),'detail_frame':.74,'camera_direction':(1,-1,.35)},'tools':{'detail':True,'detail_target':(.34,.17,1.10),'detail_frame':1.25,'camera_direction':(.3,-1,.8)}})
    else:modes.update({'loads':{'detail':True,'detail_target':(0,0,.56),'detail_frame':1.65,'camera_direction':(.35,-1,.60)},'binding':{'detail':True,'detail_target':(.87,-.49,.45),'detail_frame':.56,'camera_direction':(1,-1,.45)}})
    record={'asset':key,'stage':'source PBR direction only; no GLB or approval','master':str(master.relative_to(ROOT)),'masterSha256':sha(master),'sourceMasterSha256':sha(source),'materialToolSha256':sha(ROOT/'tools/materials_items.py'),'reviewToolSha256':sha(Path(__file__)),'views':{}}
    for name,options in modes.items():
        path=ROOT/'review'/f'{key}_{name}_material_source.png';camera=render(objects,path,**options);record['views'][name]={'image':path.name,'sha256':sha(path),'camera':camera}
    target=ROOT/'review'/f'{key}_material_source.json';temporary=target.with_suffix('.json.tmp');temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(target)
    print('WORKSHOP_PBR_SOURCE',key,flush=True)
