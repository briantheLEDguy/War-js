"""Repair undefined exported tangents from the mesh's own UV derivatives.

LOD collapse can leave MikkTSpace a zero tangent at a retained UV corner. Only
those vectors change; geometry, UVs, normals, skinning and clips remain exact.
"""
import hashlib
import json
import math
import struct
from pathlib import Path


def repair_export_tangents(path):
    data=bytearray(path.read_bytes());before=hashlib.sha256(data).hexdigest()
    length=int.from_bytes(data[12:16],'little');doc=json.loads(data[20:20+length]);base=28+length
    def read(index):
        entry=doc['accessors'][index];view=doc['bufferViews'][entry['bufferView']]
        width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[entry['type']]
        fmt='<'+{5121:'B',5123:'H',5125:'I',5126:'f'}[entry['componentType']]*width
        start=base+view.get('byteOffset',0)+entry.get('byteOffset',0);stride=view.get('byteStride',struct.calcsize(fmt))
        return [struct.unpack_from(fmt,data,start+i*stride) for i in range(entry['count'])],start,stride
    sub=lambda a,b:tuple(x-y for x,y in zip(a,b))
    dot=lambda a,b:sum(x*y for x,y in zip(a,b))
    changes=[]
    for mi,mesh in enumerate(doc['meshes']):
        for pi,primitive in enumerate(mesh['primitives']):
            attributes=primitive['attributes']
            if 'TANGENT' not in attributes:continue
            tangents,start,stride=read(attributes['TANGENT'])
            invalid=[i for i,t in enumerate(tangents) if dot(t[:3],t[:3])<1e-12]
            if not invalid:continue
            normals,_,_=read(attributes['NORMAL']);positions,_,_=read(attributes['POSITION']);uvs,_,_=read(attributes['TEXCOORD_0'])
            indices,_,_=read(primitive['indices'])
            triangles=[tuple(indices[i+j][0] for j in range(3)) for i in range(0,len(indices),3)]
            for vertex in invalid:
                candidates=[]
                for triangle in triangles:
                    if vertex not in triangle:continue
                    a,b,c=triangle;e1=sub(positions[b],positions[a]);e2=sub(positions[c],positions[a])
                    u1=sub(uvs[b],uvs[a]);u2=sub(uvs[c],uvs[a]);det=u1[0]*u2[1]-u2[0]*u1[1]
                    if abs(det)>1e-12:candidates.append(tuple((e1[j]*u2[1]-e2[j]*u1[1])/det for j in range(3)))
                normal=normals[vertex];resolved=None
                for candidate in candidates:
                    projection=dot(candidate,normal);direction=tuple(candidate[j]-projection*normal[j] for j in range(3))
                    magnitude=math.sqrt(dot(direction,direction))
                    if magnitude>1e-8:
                        resolved=tuple(value/magnitude for value in direction)+(tangents[vertex][3],);break
                if resolved is None:raise RuntimeError(f'No neighboring UV derivative for {mi}/{pi}/{vertex}')
                struct.pack_into('<ffff',data,start+vertex*stride,*resolved)
                changes.append({'mesh':mi,'primitive':pi,'vertex':vertex,'before':list(tangents[vertex]),'after':list(resolved)})
    if changes:path.write_bytes(data)
    return {'inputSha256':before,'outputSha256':hashlib.sha256(data).hexdigest(),
            'toolSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'changes':changes}
