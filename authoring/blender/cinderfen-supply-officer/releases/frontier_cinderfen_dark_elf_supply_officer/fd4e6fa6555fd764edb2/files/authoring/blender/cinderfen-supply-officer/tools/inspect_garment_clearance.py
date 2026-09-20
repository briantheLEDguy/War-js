"""Check actual exported knee/apron overlap at literal keys and midpoints."""
import bpy
import hashlib
import json
import math
import struct
import sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WORK=Path(__file__).resolve().parents[1]
key=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--asset=')),'frontier_cinderfen_dark_elf_supply_officer')
lod=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--lod=')),'0'))
selected=next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--clips=')),None)
source=WORK/'runtime'/f'{key}_lod{lod}.glb';raw=source.read_bytes()
length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE')
body=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH' and any(mod.type=='ARMATURE' and mod.object==rig for mod in obj.modifiers))
body.data.calc_loop_triangles();imported_triangles=len(body.data.loop_triangles)
expected_triangles=sum(doc['accessors'][primitive['indices']]['count']//3 for mesh in doc['meshes'] for primitive in mesh['primitives'])
if imported_triangles!=expected_triangles:raise RuntimeError('Garment inspection imported a different mesh than the hashed GLB')
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()


def positions():
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    array=np.empty(len(evaluated.data.vertices)*3,dtype=np.float64)
    evaluated.data.vertices.foreach_get('co',array)
    matrix=np.array(body.matrix_world)
    return array.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]


rest=positions();height_scale=1.045/(1.86/1.76);belt=1.02*height_scale
coat=[tuple(face.vertices) for face in body.data.polygons if any(term in body.data.materials[face.material_index].name for term in ('_woven_linen','officer_split_coat'))]
apron=[face for face in coat if all(rest[i,1]<-.018 for i in face) and any(rest[i,2]<belt-.035 for i in face)]
parents={}
def root(point):
    parents.setdefault(point,point)
    if parents[point]!=point:parents[point]=root(parents[point])
    return parents[point]
band_faces=[tuple(face.vertices) for face in body.data.polygons
            if body.data.materials[face.material_index].name=='officer_belt_attachment_support'
            and all(abs(rest[i,2]-belt)<.032 for i in face.vertices)]
parents={};keys={i:tuple(np.round(rest[i],6)) for face in band_faces for i in face}
for face in band_faces:
    first=root(keys[face[0]])
    for i in face[1:]:parents[root(keys[i])]=first
bands={}
for face in band_faces:bands.setdefault(root(keys[face[0]]),[]).append(face)
band=max(bands.values(),key=len)
band_vertices=sorted({i for face in band for i in face})
band_extent=[float(np.ptp(rest[band_vertices,axis])) for axis in (0,1)]
if band_extent[0]<.26 or band_extent[1]<.15:raise RuntimeError('Missing complete worker waist belt inspection surface: '+str(band_extent))
band_edges=sorted({tuple(sorted((a,b))) for face in band for a,b in zip(face,face[1:]+face[:1])})
trousers={i for face in body.data.polygons if '_wool' in body.data.materials[face.material_index].name for i in face.vertices}
probes=np.array(sorted(i for i in trousers if belt-.28<rest[i,2]<belt-.035 and rest[i,1]<-.035 and .042<abs(rest[i,0])<.24),dtype=int)
if not apron or len(probes)<100:raise RuntimeError('Missing authored apron or trouser inspection surface')
def indexed_surface(faces):
    indices=sorted({i for face in faces for i in face});remap={i:j for j,i in enumerate(indices)}
    return np.array(indices,dtype=int),[tuple(remap[i] for i in face) for face in faces]
apron_surface=indexed_surface(apron)
coat_surface=indexed_surface(coat)
tail_faces=[tuple(face.vertices) for face in body.data.polygons if body.data.materials[face.material_index].name=='officer_split_coat']
tail_edges=sorted({tuple(sorted((a,b))) for face in tail_faces for a,b in zip(face,face[1:]+face[:1])})
trouser_surface=indexed_surface([tuple(face.vertices) for face in body.data.polygons if '_wool' in body.data.materials[face.material_index].name])
if len(tail_edges)<100:raise RuntimeError('Missing complete split coat inspection surface')
boot_triangles={};hem_probes={}
for side,sign in [('L',1),('R',-1)]:
    boot_triangles[side]=[tuple(face.vertices) for face in body.data.polygons
                          if '_worked_leather' in body.data.materials[face.material_index].name
                          and all(rest[i,2]<.48 and sign*rest[i,0]>.12 for i in face.vertices)]
    # Include the actual scaled .215m pattern hem and its thickness lining;
    # a fixed taller-race height slice can miss that loop after LOD reduction.
    hem_probes[side]=np.array(sorted(i for i in trousers if .215*height_scale-.006<rest[i,2]<.295*height_scale and sign*rest[i,0]>.12),dtype=int)
    if not boot_triangles[side] or len(hem_probes[side])<30:raise RuntimeError('Missing boot/hem inspection surface: '+side)
boot_surfaces={side:indexed_surface(faces) for side,faces in boot_triangles.items()}
records=[];boot_records=[];belt_records=[];tail_records=[]
for clip in doc['animations']:
    if selected is not None and clip['name'] not in selected:continue
    measure_apron=clip['name'] in ('walk','run','jump')
    action=next(action for action in bpy.data.actions if action.name==clip['name'] or action.name.endswith('_'+clip['name']))
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    times=set()
    for sampler in clip['samplers']:
        accessor=doc['accessors'][sampler['input']];view=doc['bufferViews'][accessor['bufferView']]
        start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        times.update(round(struct.unpack_from('<f',binary,start+i*view.get('byteStride',4))[0],8) for i in range(accessor['count']))
    keys=sorted(times);times.update((a+b)/2 for a,b in zip(keys,keys[1:]))
    samples=[];boot_samples=[];belt_samples=[];tail_samples=[]
    for seconds in sorted(times):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update()
        posed=positions();indices,faces=coat_surface
        tree=BVHTree.FromPolygons(posed[indices],faces,all_triangles=True)
        intersections=[]
        for a,b in band_edges:
            start=Vector(posed[a]);delta=Vector(posed[b])-start
            if delta.length<.00003:continue
            direction=delta.normalized()
            hit=tree.ray_cast(start+direction*.00001,direction,delta.length-.00002)[0]
            if hit is not None:intersections.append({'edge':[a,b],'point':list(hit)})
        belt_samples.append({'seconds':seconds,'intersections':len(intersections),'firstCrossings':intersections[:4]})
        indices,faces=apron_surface
        tree=BVHTree.FromPolygons(posed[indices],faces,all_triangles=True)
        gaps=[];worst_apron=None
        for i in probes if measure_apron else []:
            point=posed[i]
            hit=tree.ray_cast(Vector((point[0],-2,point[2])),Vector((0,1,0)),3)[0]
            if hit is not None:
                gap=float(point[1]-hit.y);gaps.append(gap)
                if worst_apron is None or gap<worst_apron['gap']:worst_apron={'gap':gap,'rest':rest[i].tolist(),'posed':point.tolist(),'apronHit':list(hit)}
        if measure_apron:
            samples.append({'seconds':seconds,'raysIntersectingApron':len(gaps),'minimumGap':min(gaps) if gaps else None,
                            'penetrationCount':sum(gap<-.002 for gap in gaps),'worstProbe':worst_apron})
        indices,faces=trouser_surface
        tree=BVHTree.FromPolygons(posed[indices],faces,all_triangles=True);crossings=[]
        for a,b in tail_edges:
            start=Vector(posed[a]);delta=Vector(posed[b])-start
            if delta.length<.001:continue
            direction=delta.normalized()
            hit=tree.ray_cast(start+direction*.00025,direction,delta.length-.0005)[0]
            if hit is not None:crossings.append(list(hit))
        tail_samples.append({'seconds':seconds,'crossings':len(crossings),'firstCrossings':crossings[:3]})
        sides={}
        for side in ('L','R'):
            indices,faces=boot_surfaces[side]
            tree=BVHTree.FromPolygons(posed[indices],faces,all_triangles=True)
            shin=rig.matrix_world@rig.pose.bones['shin_'+side].matrix;inverse=shin.inverted()
            gaps=[];worst=None
            for i in hem_probes[side]:
                point=Vector(posed[i]);local=inverse@point
                origin=shin@Vector((0,local.y,0));direction=point-origin
                distance=direction.length
                if distance<.001:continue
                hit=tree.ray_cast(origin,direction.normalized(),.3)[0]
                if hit is not None:
                    gap=(hit-origin).length-distance;gaps.append(gap)
                    if worst is None or gap<worst['gap']:worst={'gap':gap,'vertex':int(i),'rest':rest[i].tolist(),'posed':list(point),'bootHit':list(hit)}
            sides[side]={'raysIntersectingBoot':len(gaps),'minimumGap':min(gaps) if gaps else None,
                         'penetrationCount':sum(gap<-.002 for gap in gaps),'worstProbe':worst}
        boot_samples.append({'seconds':seconds,'sides':sides})
    if measure_apron:
        records.append({'clip':clip['name'],'samples':samples,'maximumPenetration':max(0,-min((sample['minimumGap'] for sample in samples if sample['minimumGap'] is not None),default=0))})
    boot_records.append({'clip':clip['name'],'samples':boot_samples,
                         'maximumPenetration':max(0,-min((side['minimumGap'] for sample in boot_samples for side in sample['sides'].values() if side['minimumGap'] is not None),default=0))})
    belt_records.append({'clip':clip['name'],'samples':belt_samples,'maximumIntersections':max(sample['intersections'] for sample in belt_samples)})
    tail_records.append({'clip':clip['name'],'samples':tail_samples,'maximumCrossings':max(sample['crossings'] for sample in tail_samples)})
report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'importedTriangles':imported_triangles,'probeVertices':len(probes),
        'apronTriangles':len(apron),'status':'inspection_only','clips':records,
        'bootHemProbeVertices':{side:len(indices) for side,indices in hem_probes.items()},'bootClips':boot_records,
        'beltEdges':len(band_edges),'beltClips':belt_records,'coatTailEdges':len(tail_edges),'coatTailClips':tail_records}
(WORK/'review'/f'{key}_lod{lod}_{"selected_" if selected else ""}garment_clearance.json').write_text(json.dumps(report,separators=(',',':')))
print(json.dumps({clip['clip']:clip['maximumPenetration'] for clip in records}),flush=True)
print(json.dumps({'boot/'+clip['clip']:clip['maximumPenetration'] for clip in boot_records}),flush=True)
print(json.dumps({'belt/'+clip['clip']:clip['maximumIntersections'] for clip in belt_records}),flush=True)
print(json.dumps({'coatTail/'+clip['clip']:clip['maximumCrossings'] for clip in tail_records}),flush=True)
if any(row['maximumPenetration']>.002 for row in records+boot_records):
    raise RuntimeError('Coat or trouser hem exceeds the 2mm clearance gate')
if any(row['maximumIntersections'] for row in belt_records) or any(row['maximumCrossings'] for row in tail_records):
    raise RuntimeError('Belt or joined coat tails intersect moving clothing')
