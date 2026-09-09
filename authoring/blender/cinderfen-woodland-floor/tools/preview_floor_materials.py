"""Material direction proofs only; final acceptance requires GLB reimport."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from materials_floor import apply_materials
from review_floor import render
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--assets',default='frontier_cinderfen_fallen_alder_limb,frontier_cinderfen_fern_wood_sedge');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
for key in args.assets.split(','):
    source=ROOT/'masters'/f'{key}_lod0.source-preview.blend';bpy.ops.wm.open_mainfile(filepath=str(source));objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
    apply_materials(objects)
    master=ROOT/'masters'/f'{key}_lod0.material-preview.blend'
    for image in bpy.data.images:
        if image.source in ('FILE','GENERATED'):image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    modes={'overall':{}}
    if key.endswith('fallen_alder_limb'):
        modes.update({'large_break':{'detail':True,'detail_target':(-1.62,-.16,.21),'detail_frame':.75,'camera_direction':(-1,-.42,.34)},'side_stub':{'detail':True,'detail_target':(-.12,-.655,.515),'detail_frame':.43,'camera_direction':(1,-1,.7)},'bark':{'detail':True,'detail_target':(.48,.10,.31),'detail_frame':1.1,'camera_direction':(.3,-1,.8)}})
    else:modes['fronds']={'detail':True,'detail_target':(-.08,-.08,.26),'detail_frame':.75,'camera_direction':(.4,-1,.75)}
    record={'asset':key,'stage':'source PBR direction only; not exported or approved','master':str(master.relative_to(ROOT)),'masterSha256':sha(master),'toolSha256':sha(Path(__file__)),'materialToolSha256':sha(ROOT/'tools/materials_floor.py'),'views':{}}
    for name,options in modes.items():
        path=ROOT/'review'/f'{key}_{name}_material_source.png';camera=render(objects,path,**options)
        record['views'][name]={'image':path.name,'sha256':sha(path),'camera':camera}
    target=ROOT/'review'/f'{key}_material_source.json';temporary=target.with_suffix('.json.tmp');temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(target)
    print('FLOOR_MATERIAL_PREVIEW',key,flush=True)
