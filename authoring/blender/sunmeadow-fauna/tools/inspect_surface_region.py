"""Read actual GLB attributes around the deer haunch for material discontinuities."""
import json
import struct
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1];payload=(root/'runtime/frontier_sunmeadow_roe_deer_buck_lod0.glb').read_bytes();length=struct.unpack_from('<I',payload,12)[0];doc=json.loads(payload[20:20+length]);binary=payload[28+length:]
def attribute(index):
    a=doc['accessors'][index];view=doc['bufferViews'][a['bufferView']];dtype=np.dtype({5126:'<f4',5123:'<u2',5121:'u1',5125:'<u4'}[a['componentType']]);width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    result=np.ndarray((a['count'],width),dtype=dtype,buffer=binary,offset=view.get('byteOffset',0)+a.get('byteOffset',0),strides=(view.get('byteStride',dtype.itemsize*width),dtype.itemsize)).astype(np.float64)
    if a.get('normalized'):result/=np.iinfo(dtype).max
    return result
records=[]
for mesh in doc['meshes']:
    for primitive in mesh['primitives']:
        a=primitive['attributes'];positions=attribute(a['POSITION']);uv=attribute(a['TEXCOORD_0']);color=attribute(a['COLOR_0']);indices=attribute(primitive['indices']).astype(int).ravel().reshape(-1,3)
        region=(np.abs(positions[:,0])>.05)&(positions[:,1]>.38)&(positions[:,1]<.69)&(positions[:,2]>-.37)&(positions[:,2]<-.035)
        suspect=region&((uv[:,0]>=.25)|(uv[:,1]<.5)|(color[:,:3].min(axis=1)>.8))
        for face in indices[np.any(suspect[indices],axis=1)]:records.append({'vertices':face.tolist(),'positions':positions[face].tolist(),'uv':uv[face].tolist(),'color':color[face].tolist()})
print(json.dumps({'suspect_triangles':len(records),'examples':records[:3]},indent=2))
