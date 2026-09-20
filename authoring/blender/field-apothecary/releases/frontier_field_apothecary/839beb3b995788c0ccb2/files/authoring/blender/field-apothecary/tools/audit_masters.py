"""Measure actual saved source/finished masters and geometry-derived collision."""
import json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build_station import KEY,audit,sha,save,bounds

records=[]
for lod in(0,1,2):
    build=json.loads((ROOT/'review'/f'{KEY}_lod{lod}_build.json').read_text())
    for kind in('sourceMaster','master'):
        target=ROOT/build[kind];bpy.ops.wm.open_mainfile(filepath=str(target));objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
        result=audit(objects)
        if any(result[key] for key in('boundary','multi','loose')):
            save(ROOT/'review/master-audit-failure.json',{'path':build[kind],'audit':result})
            raise RuntimeError('Saved master topology failed')
        packed=[image for image in bpy.data.images if image.source=='FILE']
        if not packed or any(not image.packed_file for image in packed):raise RuntimeError('Master has unpacked PBR images')
        record={'level':lod,'kind':kind,'path':build[kind],'sha256':sha(target),'audit':result,'packedImages':len(packed)}
        if kind=='sourceMaster' and lod==0:
            contract=json.loads((ROOT/'builder-contract.json').read_text())['assets'][KEY]
            footnames=[f'pegged_tapered_leg_{x}_{y}' for x in(-1,1) for y in(-1,1)]
            record['feet']=[{'part':name,'minimumZ':min(v.co.z for v in bpy.data.objects[name].data.vertices),'contactVertices':sum(abs(v.co.z)<1e-7 for v in bpy.data.objects[name].data.vertices)} for name in footnames]
            if any(abs(foot['minimumZ'])>1e-6 or foot['contactVertices']<4 for foot in record['feet']):raise RuntimeError('Ground feet failed')
            record['collisionMeasurements']=[]
            for group in contract['collisionMeasurements']:
                measured=bounds([bpy.data.objects[name] for name in group['parts']])
                maximum=max(abs(measured[side][axis]-group['boundsZUp'][side][axis]) for side in('minimum','maximum') for axis in range(3))
                if maximum>.005:raise RuntimeError('Collision diverges from actual source mass: '+group['name'])
                record['collisionMeasurements'].append({'name':group['name'],'boundsZUp':measured,'finishedDifferenceM':maximum})
        records.append(record)
report={'passed':True,'toolSha256':sha(Path(__file__)),'records':records}
save(ROOT/'review/master-audit.json',report);print('APOTHECARY_MASTERS_VERIFIED',len(records),flush=True)
