"""Measure conservative model-space collision from actual finished source masses."""
import hashlib,json
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bounds(objects):
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    return {'minimum':[min(p[i] for p in points) for i in range(3)],'maximum':[max(p[i] for p in points) for i in range(3)]}
source=json.loads((ROOT/'source/items.json').read_text());record={'schemaVersion':1,'units':'metres','upAxis':'+Y','frontAxis':'+Z','sourceSha256':sha(ROOT/'source/items.json'),'measurementToolSha256':sha(Path(__file__)),'runtimeReady':False,'assets':{}}
for key,definition in source['assets'].items():
    master=ROOT/'masters'/f'{key}_lod0.source.blend';bpy.ops.wm.open_mainfile(filepath=str(master));objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render];groups={}
    for obj in objects:
        name=obj['original_piece'];group=None
        if key.endswith('repair_bench'):
            if '.' not in name and name.startswith(('trestle_leg_','shouldered_long_stretcher_','shouldered_end_stretcher_','pegged_upper_apron_')):group=name
            elif name.startswith(('individual_worktop_plank_','breadboard_end_')):group='worktop'
            elif name.startswith(('forged_vise_fixed_body','forged_vise_moving_jaw','vise_handle_cross_hub')):group='vise_body'
        else:
            if name.startswith(('ammunition_sled_foot_','crib_shouldered_corner_','shouldered_crib_long_retainer_','sculpted_open_crib_end_')):group=name
            elif name.startswith('crib_floor_board_'):group='crib_floor'
            elif name.startswith('individually_cut_siege_stone_'):group='loaded_stone_mass'
        if group:groups.setdefault(group,[]).append(obj)
    colliders=[];evidence=[]
    approach=definition['contract']['approachSource'];alo=approach['minimum'];ahi=approach['maximum']
    for name,parts in groups.items():
        b=bounds(parts);lo=b['minimum'];hi=b['maximum']
        if all(max(lo[i],alo[i])<min(hi[i],ahi[i]) for i in range(3)):raise RuntimeError('Collider enters working approach: '+name)
        colliders.append({'x':(lo[0]+hi[0])/2,'z':-(lo[1]+hi[1])/2,'width':hi[0]-lo[0],'depth':hi[1]-lo[1],'minY':max(0,lo[2]),'maxY':hi[2]});evidence.append({'name':name,'parts':[o['original_piece'] for o in parts],'boundsZUp':b})
    b=bounds(objects);lo=b['minimum'];hi=b['maximum'];record['assets'][key]={'label':definition['name'],'group':'Universal Siege Workshop','kind':definition['contract']['kind'],'model':key+'_lod0.glb','runtimeReady':False,'defaultScale':{'x':1,'y':1,'z':1},'colliderSpace':'model','footprint':{'width':hi[0]-lo[0],'depth':hi[1]-lo[1],'chainAxis':'x'},'boundsYUp':{'minimum':[lo[0],lo[2],-hi[1]],'maximum':[hi[0],hi[2],-lo[1]]},'placementDatum':'Flat finished feet at model Y0. Keep the documented working approach clear.','colliders':colliders,'walkableSurfaces':[],'cameraSolid':True,'sourceMasterSha256':sha(master),'collisionMeasurements':evidence,'approachSource':approach}
target=ROOT/'builder-contract.json';temporary=target.with_suffix('.json.tmp');temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(target);print('MEASURED_WORKSHOP_COLLIDERS',[(k,len(v['colliders'])) for k,v in record['assets'].items()])
