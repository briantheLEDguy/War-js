"""Measure actual authored bridge rows independently of attachment contacts."""
import bpy,hashlib,json,math,sys
from pathlib import Path
WORK=Path(__file__).resolve().parents[1];KEY='frontier_sunmeadow_empire_field_captain'
prefit='--prefit' in sys.argv
master=WORK/'sources'/f'{KEY}{".prefit" if prefit else ""}.blend'
bpy.ops.wm.open_mainfile(filepath=str(master));records=[]
for obj in bpy.data.objects:
    if not obj.name.startswith('captain_structural_shoulder_bridge'):continue
    vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
    if len(vertices)%2:raise RuntimeError('Bridge lost authored paired edge rows')
    centers=[(vertices[i]+vertices[i+1])*.5 for i in range(0,len(vertices),2)]
    across=[vertices[i+1]-vertices[i] for i in range(0,len(vertices),2)]
    delta=[b-a for a,b in zip(centers,centers[1:])]
    records.append({'object':obj.name,'rows':len(centers),'maximumRowStep':max(v.length for v in delta),
        'minimumWidth':min(v.length for v in across),'maximumWidth':max(v.length for v in across),
        'minimumWidthDirectionDot':min(a.normalized().dot(b.normalized()) for a,b in zip(across,across[1:])),
        'maximumTurnDegrees':max(math.degrees(a.angle(b)) for a,b in zip(delta,delta[1:]))})
if len(records)!=2:raise RuntimeError('Missing structural shoulder bridge')
report={'master':master.relative_to(WORK).as_posix(),'masterSha256':hashlib.sha256(master.read_bytes()).hexdigest(),
    'strips':records,'scope':'Actual authored paired-edge geometry. Does not substitute for final exported attachment/layer checks.'}
(WORK/'review'/f'{"diagnostic-" if prefit else ""}shoulder-routing.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
