"""Authored fold and turned-hem controls; run after author_novitiate_core.py."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'source/garments.json'
data=json.loads(path.read_text())
front,rear=data['parts'][:2]

FRONT_LOWER=[
(-.156,-.180,.936),(-.110,-.224,.933),(-.066,-.176,.931),(-.023,-.223,.933),(.022,-.179,.936),(.072,-.226,.934),(.119,-.188,.930),(.154,-.180,.934),
(-.159,-.178,.823),(-.112,-.229,.822),(-.066,-.180,.819),(-.021,-.225,.821),(.025,-.178,.820),(.074,-.231,.822),(.120,-.188,.824),(.155,-.175,.826),
(-.158,-.176,.714),(-.112,-.221,.710),(-.065,-.174,.712),(-.019,-.222,.707),(.028,-.172,.709),(.076,-.225,.714),(.120,-.185,.717),(.154,-.173,.721),
(-.157,-.172,.698),(-.112,-.218,.693),(-.065,-.173,.695),(-.018,-.219,.688),(.030,-.171,.691),(.077,-.222,.696),(.119,-.182,.699),(.153,-.171,.704),
]
FRONT_EDGE=[(-.157,-.169,.676),(-.112,-.215,.671),(-.065,-.170,.673),(-.018,-.216,.666),(.030,-.168,.669),(.077,-.219,.674),(.119,-.179,.677),(.153,-.168,.682)]
REAR_INNER=[(-.229,.106,.678),(-.167,.184,.672),(-.087,.158,.670),(.012,.191,.667),(.106,.155,.673),(.180,.183,.681),(.235,.101,.685)]
REAR_EDGE=[(-.229,.104,.655),(-.167,.182,.649),(-.087,.156,.647),(.012,.189,.644),(.106,.153,.650),(.180,.181,.658),(.235,.099,.662)]

def turned_hem(part, base_count, face_count, edge, columns, orientation):
    part['vertices']=part['vertices'][:base_count]
    part['faces']=part['faces'][:face_count]
    part['creases']=[c for c in part['creases'] if all(int(v[1:])<base_count for v in c['edge'])]
    inner=base_count-len(edge)
    for face in part['faces']:
        for i,vertex in enumerate(face['vertices']):
            n=int(vertex[1:])
            if n>=inner: face['uv'][i]=[columns[n-inner],.09]
    for i,coordinate in enumerate(edge):
        part['vertices'].append({'id':f'v{base_count+i:03}','co':list(coordinate)})
    for i in range(len(edge)-1):
        vertices=[inner+i,base_count+i,base_count+i+1,inner+i+1] if orientation=='front' else [inner+i,inner+i+1,base_count+i+1,base_count+i]
        uvs=[[columns[i],.09],[columns[i],.04],[columns[i+1],.04],[columns[i+1],.09]] if orientation=='front' else [[columns[i],.09],[columns[i+1],.09],[columns[i+1],.04],[columns[i],.04]]
        part['faces'].append({'id':f'f{face_count+i:03}','vertices':[f'v{n:03}' for n in vertices],'uv':uvs,'material':'crimson'})
        part['creases'].append({'edge':[f'v{base_count+i:03}',f'v{base_count+i+1:03}'],'value':.78})
    for a,b in [(inner,base_count),(base_count-1,base_count+len(edge)-1)]:
        part['creases'].append({'edge':[f'v{a:03}',f'v{b:03}'],'value':.75})

for vertex,coordinate in zip(front['vertices'][16:48],FRONT_LOWER): vertex['co']=list(coordinate)
for vertex,coordinate in zip(rear['vertices'][28:35],REAR_INNER): vertex['co']=list(coordinate)
turned_hem(front,48,35,FRONT_EDGE,[0,.14,.28,.43,.58,.72,.86,1],'front')
turned_hem(rear,35,24,REAR_EDGE,[0,.16,.32,.50,.68,.84,1],'back')
front['landmarks']['hem_tip']='v051'
data['refinement']={'method':'Literal fold coordinates and thirteen connected turned-hem faces. Same authored cloth UV boundary on front and rear for hand-painted linen stitching.',
 'shared_body_part_unchanged':'padded_abdominal_doublet','hem_uv':{'inner':.09,'outer':.04,'stitch_center':.07}}
path.write_text(json.dumps(data,indent=2)+'\n')
(ROOT/'review/cloth_refinement.json').write_text(json.dumps({'source':'source/garments.json','front_vertices':len(front['vertices']),'rear_vertices':len(rear['vertices']),'new_faces':13,'fold_coordinates':'tools/refine_novitiate_cloth.py','hem_width_m':.022,'purpose':'More natural folded cloth and visible stitched turned hems without adding ornate decoration.'},indent=2)+'\n')
