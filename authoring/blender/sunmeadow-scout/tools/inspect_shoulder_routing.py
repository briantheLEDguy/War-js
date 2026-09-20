"""Measure source strip continuity; actual GLB views/contact remain required."""
import bpy,hashlib,json,math,sys
from pathlib import Path
from mathutils import Vector
WORK=Path(__file__).resolve().parents[1];KEY='frontier_sunmeadow_high_elf_scout'
prefit='--prefit' in sys.argv
master=WORK/'sources'/f'{KEY}{".prefit" if prefit else ""}.blend'
bpy.ops.wm.open_mainfile(filepath=str(master))
records=[]
for obj in bpy.data.objects:
    if not obj.name.startswith(('scout_tapered_shoulder_yoke','scout_over_shoulder_harness')):continue
    vertices=[obj.matrix_world@vertex.co for vertex in obj.data.vertices]
    if len(vertices)%2:raise RuntimeError('Shoulder strip lost its authored paired edge rows')
    centers=[(vertices[i]+vertices[i+1])*.5 for i in range(0,len(vertices),2)]
    across=[vertices[i+1]-vertices[i] for i in range(0,len(vertices),2)]
    deltas=[b-a for a,b in zip(centers,centers[1:])]
    records.append({'object':obj.name,'rows':len(centers),'maximumRowStep':max(v.length for v in deltas),
        'minimumWidth':min(v.length for v in across),'maximumWidth':max(v.length for v in across),
        'minimumWidthDirectionDot':min(a.normalized().dot(b.normalized()) for a,b in zip(across,across[1:])),
        'maximumTurnDegrees':max(math.degrees(a.angle(b)) for a,b in zip(deltas,deltas[1:]))})
if len(records)!=3:raise RuntimeError('Expected both shoulder yokes and the carrying harness')
record={'master':master.relative_to(WORK).as_posix(),'masterSha256':hashlib.sha256(master.read_bytes()).hexdigest(),
        'strips':records,'scope':'Actual paired-edge source geometry; no projected guide or invisible support substitutes.'}
out=WORK/'review'/f'{"diagnostic-" if prefit else ""}shoulder-routing.json'
out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
