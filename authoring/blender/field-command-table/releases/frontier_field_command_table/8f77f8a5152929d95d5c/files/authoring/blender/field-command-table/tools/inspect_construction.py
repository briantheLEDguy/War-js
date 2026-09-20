"""Verify named final fitting surfaces against the literal reimported GLB geometry.

The exporter batches by material for six draw calls. The retained part receipt is
the exact finished triangulation immediately before batching. Bidirectional vertex
and triangle counts prove those same surfaces survived actual import before any
contacts are accepted; source-only cages cannot satisfy this gate.
"""
import json,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build_table import KEY,sha,save

def kd(points):
    tree=KDTree(len(points))
    for i,p in enumerate(points):tree.insert(p,i)
    tree.balance();return tree

def samples(part):
    vertices=[Vector(p) for p in part['vertices']];points=list(vertices)
    edges=set()
    for triangle in part['triangles']:
        for a,b in zip(triangle,triangle[1:]+triangle[:1]):edges.add(tuple(sorted((a,b))))
        points.append(sum((vertices[i] for i in triangle),Vector())/3)
    points.extend((vertices[a]+vertices[b])/2 for a,b in edges)
    return points

records=[]
for lod in(0,1,2):
    build=json.loads((ROOT/'review'/f'{KEY}_lod{lod}_build.json').read_text())
    finishedPath=ROOT/build['finishedParts'];assert sha(finishedPath)==build['finishedPartsSha256']
    parts=json.loads(finishedPath.read_text());model=ROOT/'runtime'/build['model']
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(model))
    actual={}
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH':continue
        name=obj.data.materials[0].name.split('.')[-1];obj.data.calc_loop_triangles()
        actual[name]={'points':[obj.matrix_world@v.co for v in obj.data.vertices],'triangles':len(obj.data.loop_triangles)}
    deviations=[];surfaceRecords=[]
    for name,data in actual.items():
        related=[p for p in parts.values() if p['material']==name];points=[Vector(v) for part in related for v in part['vertices']]
        sourceTree=kd(points);actualTree=kd(data['points'])
        deviation=max([sourceTree.find(p)[2] for p in data['points']]+[actualTree.find(p)[2] for p in points]);deviations.append(deviation)
        triangleCount=sum(len(p['triangles']) for p in related)
        surfaceRecords.append({'material':name,'maximumVertexDeviationM':deviation,'triangles':data['triangles'],'finishedPartTriangles':triangleCount,'passed':deviation<=.000002 and data['triangles']==triangleCount})
    verified=all(r['passed'] for r in surfaceRecords) and len(actual)==6
    if not verified:raise RuntimeError('Finished part evidence does not reproduce actual imported GLB surface '+json.dumps(surfaceRecords))
    trees={name:BVHTree.FromPolygons([Vector(v) for v in p['vertices']],p['triangles'],all_triangles=True) for name,p in parts.items()}
    probes={name:samples(part) for name,part in parts.items()};contacts=[]
    for joint in build['joints']:
        a,b=joint['part'],joint['support'];tolerance=joint['toleranceM']
        witnessA=min(((trees[b].find_nearest(p)[3],p,trees[b].find_nearest(p)[0]) for p in probes[a]),key=lambda row:row[0])
        witnessB=min(((trees[a].find_nearest(p)[3],p,trees[a].find_nearest(p)[0]) for p in probes[b]),key=lambda row:row[0])
        gap,p,q=min((witnessA,witnessB),key=lambda row:row[0]);contacts.append({**joint,'minimumSurfaceGapM':gap,'witnessZUp':[list(p),list(q)],'passed':gap<=tolerance})
    record={'level':lod,'sourceMasterSha256':build['sourceMasterSha256'],'modelSha256':sha(model),'finishedParts':build['finishedParts'],'finishedPartsSha256':sha(finishedPath),'actualImportSurface':{'passed':verified,'maximumVertexDeviationM':max(deviations),'materials':surfaceRecords},'contacts':contacts,'passed':verified and all(c['passed'] for c in contacts)}
    records.append(record);print('COMMAND_TABLE_CONTACTS_LOD',lod,len(contacts),record['passed'],flush=True)
report={'passed':all(r['passed'] for r in records),'toolSha256':sha(Path(__file__)),'records':records};save(ROOT/'review/construction-contacts.json',report)
if not report['passed']:raise RuntimeError('Disconnected fittings: '+json.dumps([c for r in records for c in r['contacts'] if not c['passed']]))
print('COMMAND_TABLE_CONNECTIONS_VERIFIED',sum(len(r['contacts']) for r in records),flush=True)
