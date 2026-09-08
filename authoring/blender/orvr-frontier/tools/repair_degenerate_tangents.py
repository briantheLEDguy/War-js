"""Repair only zero exported tangent vectors using adjacent UV derivatives.

Collapsed UV corners occasionally leave MikkTSpace without a tangent. Derive an
orthogonal unit tangent from neighboring textured triangles, then geometric
edges only if no UV derivative exists. Retain exact affected vertex records.
"""
import argparse
import json
import math
from pathlib import Path
import struct
from repair_normal_projection import ROOT, digest, unpack, pack


def dot(a,b): return sum(x*y for x,y in zip(a,b))
def subtract(a,b): return tuple(x-y for x,y in zip(a,b))
def length(a): return math.sqrt(dot(a,a))
def projected(a,n):
    along=dot(a,n)
    return tuple(a[i]-along*n[i] for i in range(3))


def accessor(document,binary,index):
    item=document['accessors'][index]; view=document['bufferViews'][item['bufferView']]
    fmt={5121:'B',5123:'H',5125:'I',5126:'f'}[item['componentType']]
    width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[item['type']]
    size=struct.calcsize('<'+fmt*width); stride=view.get('byteStride',size)
    start=view.get('byteOffset',0)+item.get('byteOffset',0)
    return [struct.unpack_from('<'+fmt*width,binary,start+i*stride) for i in range(item['count'])],(start,stride)


def repair(asset_id,level,build):
    row=next(lod for lod in build['lods'] if lod['level']==level)
    filepath=ROOT/row['path'].replace('\\','/')
    original=filepath.read_bytes(); original_hash=digest(original); tool_hash=digest(Path(__file__).read_bytes())
    old=row.get('degenerate_tangent_repair')
    if old and old['output_glb_sha256']==original_hash and old['tool_sha256']==tool_hash: return old
    if original_hash!=row['sha256']: raise ValueError(f'Unexpected GLB hash: {filepath.name}')
    document,bin_input=unpack(original); binary=bytearray(bin_input); changes=[]
    for mesh_id,mesh in enumerate(document['meshes']):
        for primitive_id,primitive in enumerate(mesh['primitives']):
            attributes=primitive['attributes']
            tangents,(start,stride)=accessor(document,binary,attributes['TANGENT'])
            invalid=[index for index,value in enumerate(tangents) if length(value[:3])<1e-8]
            if not invalid: continue
            normals,_=accessor(document,binary,attributes['NORMAL'])
            positions,_=accessor(document,binary,attributes['POSITION'])
            uvs,_=accessor(document,binary,attributes['TEXCOORD_0'])
            indices,_=accessor(document,binary,primitive['indices'])
            triangles=[tuple(indices[j+i][0] for i in range(3)) for j in range(0,len(indices),3)]
            for vertex in invalid:
                normal=normals[vertex]; candidates=[]; geometric=[]
                for triangle in triangles:
                    if vertex not in triangle: continue
                    a,b,c=triangle
                    edge1=subtract(positions[b],positions[a]); edge2=subtract(positions[c],positions[a])
                    geometric.extend([edge1,edge2])
                    uv1=subtract(uvs[b],uvs[a]); uv2=subtract(uvs[c],uvs[a]); determinant=uv1[0]*uv2[1]-uv2[0]*uv1[1]
                    if abs(determinant)>1e-12: candidates.append(tuple((edge1[i]*uv2[1]-edge2[i]*uv1[1])/determinant for i in range(3)))
                options=[('adjacent_uv_derivative',vector) for vector in candidates]+[('adjacent_geometric_edge',vector) for vector in geometric]
                tangent=None
                for method,vector in options:
                    direction=projected(vector,normal); magnitude=length(direction)
                    if magnitude>1e-8:
                        tangent=tuple(value/magnitude for value in direction)+(tangents[vertex][3],); break
                if tangent is None: raise ValueError(f'No surface tangent at {asset_id}/{level}/{mesh_id}/{vertex}')
                struct.pack_into('<ffff',binary,start+vertex*stride,*tangent)
                changes.append({'mesh':mesh_id,'primitive':primitive_id,'vertex':vertex,'old':list(tangents[vertex]),'new':list(tangent),'method':method})
    result=pack(document,binary,{}) if changes else original
    filepath.write_bytes(result)
    record={'asset_id':asset_id,'level':level,'tool_sha256':tool_hash,'input_glb_sha256':original_hash,'output_glb_sha256':digest(result),'vertices':changes}
    row['sha256']=digest(result); row['bytes']=len(result); row['degenerate_tangent_repair']=record
    return record


def main():
    source=json.loads((ROOT/'source/frontier_collection.json').read_text())
    parser=argparse.ArgumentParser(); parser.add_argument('--assets',default=','.join(source['assets'])); args=parser.parse_args()
    records=[]
    for asset_id in args.assets.split(','):
        path=ROOT/'review'/f'{asset_id}_build.json'; build=json.loads(path.read_text())
        for level in (0,1,2):
            record=repair(asset_id,level,build); records.append(record)
            print(f"{asset_id} LOD{level}: repaired {len(record['vertices'])} zero-length tangent vectors")
        path.write_text(json.dumps(build,indent=2)+'\n')
    (ROOT/'review/degenerate_tangent_repairs.json').write_text(json.dumps({'records':records,'visual_approval':False},indent=2)+'\n')


if __name__=='__main__': main()
