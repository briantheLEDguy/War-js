"""Compare actual position triangles against the pre-projection basalt export."""
from pathlib import Path
import hashlib,json,struct
ROOT=Path(__file__).resolve().parents[1]
baseline=json.loads((ROOT/'review/basalt-before-continuity-geometry.json').read_text())
rows=[]
for old in baseline:
    path=ROOT/'runtime'/f"frontier_cinderfen_basalt_outcrop_lod{old['level']}.glb"
    raw=path.read_bytes();length=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
    def accessor(index):
        item=doc['accessors'][index];view=doc['bufferViews'][item['bufferView']]
        count={'SCALAR':1,'VEC3':3}[item['type']];kind={5126:'f',5125:'I',5123:'H',5121:'B'}[item['componentType']]
        size=struct.calcsize('<'+kind*count);offset=view.get('byteOffset',0)+item.get('byteOffset',0);stride=view.get('byteStride',size)
        return [struct.unpack_from('<'+kind*count,binary,offset+i*stride) for i in range(item['count'])]
    triangles=[]
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            points=accessor(primitive['attributes']['POSITION']);indices=[row[0] for row in accessor(primitive['indices'])]
            triangles.extend(sorted([list(points[j]) for j in indices[i:i+3]]) for i in range(0,len(indices),3))
    digest=hashlib.sha256(json.dumps(sorted(triangles),separators=(',',':')).encode()).hexdigest()
    assert digest==old['positionTriangleSha256'],f"LOD{old['level']} changed actual triangle positions"
    assert len(triangles)==old['triangles']
    rows.append({'level':old['level'],'modelSha256':hashlib.sha256(raw).hexdigest(),'positionTriangleSha256':digest,'triangles':len(triangles),'matchesPreviousActualGeometry':True})
(ROOT/'review/basalt-continuity-geometry-comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Basalt all-LOD actual position triangles exactly match pre-projection exports.')
