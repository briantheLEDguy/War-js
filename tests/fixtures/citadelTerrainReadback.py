"""Portable fabricated readback arrays for consumer tests, never native evidence."""
from copy import deepcopy
import json
import sys

from aegis_citadel_terrain_readback import checked_committed_carve, _stored, SOURCE_POLICY, CORNER_POLICY
from aegis_citadel_terrain_render_readback import checked_rendered_carve, RENDER_POLICY


def generate(wrapper, target):
    old=json.loads(wrapper['sourceExportPayload']);source=old['data'];data=wrapper['data'];ids=data['indices']
    prefix=len(source['positions']);count=len(data['positions']);attrs=set(data)-{'indices','triangleMaterials'}
    vertices=[dict(id=i,position=p) for i,p in enumerate(_stored(source['positions']))]
    edges=[];edge_ids={}
    def edge(a,b):
        key=tuple(sorted((a,b)))
        if key not in edge_ids:
            edge_ids[key]=len(edges);edges.append(dict(id=len(edges),vertices=[a,b],hard=False))
        return edge_ids[key]
    old_triangles=[]
    for offset in range(0,prefix,3):
        corners=list(range(offset,offset+3))
        old_triangles.append(dict(id=offset//3,polygonId=offset//3,groupId=0,instances=corners,
            edges=[edge(corners[i],corners[(i+1)%3]) for i in range(3)]))
    topology=dict(vertices=vertices,edges=edges,triangles=old_triangles)
    common=dict(schemaVersion=1,readOnly=True,available=True,valid=True,lod=0,sourcePolicy=SOURCE_POLICY,
        optionalAttributePolicy='stored_registered_values_authorship_not_inferred',invalidValues=0)
    original_stored=dict(**common,mesh=old['mesh'],cornerPolicy=CORNER_POLICY,instanceIds=list(range(prefix)),
        vertexIds=old['cornerVertexIds'],sourceVertexCount=prefix,sourceVertexInstanceCount=prefix,
        sourceTriangleCount=prefix//3,topology=deepcopy(topology),data={k:_stored(source[k]) for k in attrs})
    mapped=list(old['cornerVertexIds']);created={}
    for row in sorted(wrapper['carveReceipt']['addedBoundaryVertices'],key=lambda row:row['index']):
        support=tuple(sorted({old['cornerVertexIds'][i] for i,w in zip(row['sourceIndices'],row['weights']) if w>1e-12}))
        point=tuple(_stored(data['positions'][row['index']]))
        if len(support)==1:vertex=support[0]
        else:
            key=(('edge',support) if len(support)==2 else ('face',row['sourceIndices'][0]//3))+point
            if key not in created:
                created[key]=len(vertices);vertices.append(dict(id=len(vertices),position=list(point)))
            vertex=created[key]
        mapped.append(vertex)
    outside=set(wrapper['carveReceipt']['outsidePreservation']['sourceTriangleIds']);next_triangle=prefix//3
    triangles=[]
    for offset in range(0,len(ids),3):
        corners=ids[offset:offset+3]
        original=next((i for i in outside if corners==source['indices'][i*3:i*3+3]),None)
        if original is not None:triangle=deepcopy(old_triangles[original])
        else:
            triangle=dict(id=next_triangle,polygonId=next_triangle,groupId=0,instances=corners,
                edges=[edge(mapped[corners[i]],mapped[corners[(i+1)%3]]) for i in range(3)])
            next_triangle+=1
        triangles.append(triangle)
    topology['triangles']=triangles
    counts=dict(sourceVertexCount=len(vertices),sourceVertexInstanceCount=count,sourceTriangleCount=len(ids)//3)
    stored=dict(**common,**counts,mesh=target,cornerPolicy=CORNER_POLICY,instanceIds=list(range(count)),
        vertexIds=mapped,topology=topology,data={k:_stored(data[k]) for k in attrs})
    expanded={k:_stored([[channel[i] for i in ids] for channel in data[k]] if k=='uvChannels' else [data[k][i] for i in ids]) for k in attrs}
    expanded.update(indices=list(range(len(ids))),triangleMaterials=data['triangleMaterials'])
    referenced=dict(**common,**counts,mesh=target,coordinateSpace='mesh_local_cm',triangleOrder='native_triangle_ids_and_corner_order',
        data=expanded,materialSlots=old['materialSlots'],polygonGroups=old['polygonGroups'],trianglePolygonGroupIds=[0]*(len(ids)//3),
        cornerVertexInstanceIds=ids,cornerVertexIds=[mapped[i] for i in ids])
    comparison=checked_committed_carve(wrapper,referenced,stored,target,original_stored)
    policy=dict(sourceLods=1,buildSettings=[dict(bGenerateLightmapUVs=True,srcLightmapIndex=0,dstLightmapIndex=1,
        buildScale3D=dict(x=1,y=1,z=1))],reductionSettings=[dict(percentTriangles=1,percentVertices=1,maxDeviation=0,bRecalculateNormals=False)],
        mesh={'nanite_settings':{'bEnabled':False}},bodySetup={})
    def faces(data,mesh):
        rows=[]
        for offset in range(0,len(data['indices']),3):
            corners=data['indices'][offset:offset+3]
            rows.append(dict(index=offset//3,section=0,materialIndex=data['triangleMaterials'][offset//3],vertexIds=corners,
                positions=[data['positions'][i] for i in corners],normals=[[0,0,1]]*3,tangents=[[1,0,0]]*3,binormals=[[0,1,0]]*3,
                uvChannels=[[channel[i] for i in corners] for channel in data['uvChannels']]+[[[.1,.1],[.3,.1],[.1,.3]]]))
        return dict(schemaVersion=1,readOnly=True,available=True,valid=True,mesh=mesh,lod=0,policy=RENDER_POLICY,uvChannels=2,invalidValues=0,triangles=rows)
    original_faces=faces(source,old['mesh']);rendered_faces=faces(data,target)
    rendered_comparison=checked_rendered_carve(wrapper,original_faces,rendered_faces,policy,target)
    render=dict(readOnly=True,available=True,mesh=target,lods=[dict(lod=0,cpuReadable=True,vertices=len(ids),indices=len(ids),uvChannels=2,
        invalidPositions=0,invalidNormals=0,nonUnitNormals=0,invalidUVs=0,tangentBasis=dict(invalidVertices=0,orthogonalVertices=len(ids)),
        # Deliberately differs: actual terrain policy may recompute normals.
        committedSourceTriangleMatches=0)])
    return dict(referenced=referenced,stored=stored,originalStored=original_stored,comparison=comparison,
        originalFaces=original_faces,renderedFaces=rendered_faces,renderedComparison=rendered_comparison,render=render,policy=policy)


if __name__=='__main__':
    value=json.load(sys.stdin)
    print(json.dumps(generate(value['document'],value['mesh'])))
