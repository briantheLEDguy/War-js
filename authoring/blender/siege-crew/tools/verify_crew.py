"""Reimport literal packs, verify selected actions, roots, contacts and clearance."""
import json
import math
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_common as common

ROOT=common.ROOT


def posed_points(obj):
    graph=bpy.context.evaluated_depsgraph_get()
    evaluated=obj.evaluated_get(graph)
    mesh=evaluated.to_mesh()
    try: return [obj.matrix_world @ v.co for v in mesh.vertices]
    finally: evaluated.to_mesh_clear()


def combined_bvh(objects):
    points,faces=[],[]
    graph=bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        if obj.type!='MESH' or obj.hide_render: continue
        evaluated=obj.evaluated_get(graph)
        mesh=evaluated.to_mesh()
        mesh.calc_loop_triangles()
        offset=len(points)
        points.extend(obj.matrix_world @ v.co for v in mesh.vertices)
        faces.extend(tuple(offset+i for i in p.vertices) for p in mesh.loop_triangles)
        evaluated.to_mesh_clear()
    return BVHTree.FromPolygons(points,faces,all_triangles=True),points,faces


def action_on(rig,record):
    action,slot=record
    rig.animation_data_create()
    rig.animation_data.action=action
    rig.animation_data.action_slot=slot


def main():
    contract=json.loads((ROOT/'review/crew_contract.json').read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=30
    inputs=[]
    ram=common.imported(common.PUBLIC/'frontier_battering_ram_lod0.glb',inputs,common.RAM_SHA)
    common.pin_clip(ram,'ram_strike')
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    striker=bpy.data.objects['ram_striker']
    ram_body=bpy.data.objects['body']
    rest=striker.matrix_world.translation.copy()
    actors=[]
    max_rest=0
    for record in contract['outputs']:
        rig,meshes,assembly=common.equipped_actor(inputs)
        pack=common.imported(ROOT/record['path'],inputs,record['sha256'])
        pack_rig=next((o for o in pack if o.type=='ARMATURE'),None)
        if pack_rig is None: raise ValueError('Animation export did not preserve a reusable skeleton')
        # The importer adds a hidden Icosphere custom bone-display helper.
        # validate_gltf.mjs verifies the literal binary contains no meshes.
        if set(rig.data.bones.keys())!=set(pack_rig.data.bones.keys()): raise ValueError('Bone set changed')
        rest_error=max(abs(n) for b in rig.data.bones
                       for row in b.matrix_local-pack_rig.data.bones[b.name].matrix_local for n in row)
        max_rest=max(max_rest,rest_error)
        if rest_error>1e-5: raise ValueError(f'Canonical rest mismatch: {rest_error}')
        actions={t.name:(t.strips[0].action,t.strips[0].action_slot) for t in pack_rig.animation_data.nla_tracks}
        if set(actions)!={c['name'] for c in record['clips']}: raise ValueError('Clip names differ')
        for c in record['clips']:
            bounds=actions[c['name']][0].frame_range
            if abs(bounds[0])>1e-6 or abs(bounds[1]/30-c['duration_seconds'])>1e-6:
                raise ValueError(f'Clip timing changed: {c["name"]} {bounds}')
        for obj in pack: bpy.data.objects.remove(obj,do_unlink=True)
        origin=Vector((record['origin_gltf'][0],-record['origin_gltf'][2],record['origin_gltf'][1]))
        rig.matrix_world=Matrix.Translation(origin) @ Matrix.Rotation(record['yaw_gltf_radians'],4,'Z')
        expected=json.loads((ROOT/'review'/f'{record["seat"]}_expected_pose.json').read_text())
        expected={(row['clip'],row['frame']):row for row in expected}
        initial=expected['ram_crew_strike',0]
        sign=-1 if record['seat']=='left' else 1
        markers={side:Matrix(initial['bone_world_matrices']['hand_'+side]).inverted() @
                 Vector((sign*.53,-.185-sign*s*.092,1.66)) for side,s in [('L',1),('R',-1)]}
        boot=next(o for o in meshes if 'boot_contoured_welt' in o.data.name or 'boot_contoured_welt' in o.name)
        sole_indices={side:[v.index for v in boot.data.vertices if v.co.z<.007 and (v.co.x>0)==(side=='L')]
                      for side in ['L','R']}
        if any(len(v)<3 for v in sole_indices.values()): raise ValueError('No actual sole vertices')
        actors.append({'rig':rig,'meshes':meshes,'boot':boot,'sole_indices':sole_indices,'actions':actions,
            'record':record,'expected':expected,'markers':markers,'sign':sign,'origin':origin})
    results=[]
    maximum_matrix=maximum_marker=maximum_root=maximum_sole_drift=0
    support=[]
    rest_soles={}
    for clip,last in [('ram_crew_idle',120),('ram_crew_drive',48),('ram_crew_strike',45)]:
        for actor in actors: action_on(actor['rig'],actor['actions'][clip])
        for half in range(last*4+1):
            frame=half/4
            # Direct actions use frame zero; imported NLA strips are offset by one.
            for obj in ram:
                if obj.animation_data and obj.animation_data.action:
                    if clip!='ram_crew_strike':
                        obj.animation_data.action=None
            if clip=='ram_crew_strike' and half==0: common.pin_clip(ram,'ram_strike')
            bpy.context.scene.frame_set(int(frame),subframe=frame%1)
            bpy.context.view_layer.update()
            delta=striker.matrix_world.translation-rest if clip=='ram_crew_strike' else Vector()
            for actor in actors:
                rig=actor['rig']
                maximum_root=max(maximum_root,max(abs(n) for row in rig.pose.bones['root'].matrix_basis-Matrix.Identity(4) for n in row))
                for side,s in [('L',1),('R',-1)]:
                    actual=rig.matrix_world @ rig.pose.bones['hand_'+side].matrix @ actor['markers'][side]
                    target=Vector((actor['sign']*.53,-.185-actor['sign']*s*.092,1.66))+delta
                    maximum_marker=max(maximum_marker,(actual-target).length)
                if half%2==0:
                    expected=actor['expected'][clip,int(frame*2)]
                    for bone,rows in expected['bone_world_matrices'].items():
                        maximum_matrix=max(maximum_matrix,max(abs(n) for row in rig.matrix_world @ rig.pose.bones[bone].matrix-Matrix(rows) for n in row))
                # Foot world transforms must remain fixed throughout every clip.
                for side in ['L','R']:
                    matrix=rig.matrix_world @ rig.pose.bones['foot_'+side].matrix
                    key=actor['record']['seat'],side
                    if key not in rest_soles: rest_soles[key]=matrix.copy()
                    maximum_sole_drift=max(maximum_sole_drift,(matrix.translation-rest_soles[key].translation).length)
            if half in {0,last*2,last*4}: print('CONTACT_SAMPLE',clip,frame,flush=True)
        results.append({'clip':clip,'sampled_keys_and_midpoints':last*4+1})
    # Check actual skinned boot soles against the unchanged board surfaces.
    for actor in actors:
        points=posed_points(actor['boot'])
        for side,indices in actor['sole_indices'].items():
            gaps=[]
            seams=0
            for index in indices:
                point=points[index]
                hit,surface,normal,triangle=ram_body.ray_cast(Vector((point.x,point.y,1.18)),Vector((0,0,-1)),distance=.4)
                if hit and surface.z>.88: gaps.append(point.z-surface.z)
                elif hit: seams+=1
                else: raise ValueError('A sole extends beyond the real footboards')
            if len(gaps)<len(indices)*.7: raise ValueError('Insufficient actual footboard support')
            support.append({'seat':actor['record']['seat'],'foot':side,'sole_vertices':len(gaps),
                            'vertices_over_plank_seams':seams,'min_gap_m':min(gaps),'max_gap_m':max(gaps)})
    clearance=[]
    for frame in [0,15,21,45]:
        for actor in actors: action_on(actor['rig'],actor['actions']['ram_crew_strike'])
        common.pin_clip(ram,'ram_strike')
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        bvhs=[combined_bvh(a['meshes'])[0] for a in actors]
        body_bvh=combined_bvh([ram_body])[0]
        overlap=len(bvhs[0].overlap(bvhs[1]))
        shell=[]
        for actor in actors:
            # Boots intentionally touch the boards; inspect all other character shells.
            shell.append(len(combined_bvh([o for o in actor['meshes'] if o!=actor['boot']])[0].overlap(body_bvh)))
        clearance.append({'strike_frame':frame,'crew_pair_triangle_intersections':overlap,
                          'mantlet_frame_intersections_by_seat':shell})
    report={'status':'measured','inputs':inputs,'canonical_rest_matrix_max_error':max_rest,
      'source_to_export_matrix_max_error':maximum_matrix,'hand_grip_marker_max_error_m':maximum_marker,
      'root_basis_max_error':maximum_root,'foot_origin_max_drift_m':maximum_sole_drift,
      'clips':results,'sole_support':support,'clearance':clearance}
    (ROOT/'review/actual_contact.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    # Tight kinematic thresholds are independent of the existing uneven wooden deck.
    assert maximum_matrix<.00005 and maximum_marker<.001 and maximum_root<.00001 and maximum_sole_drift<.0005
    assert all(c['crew_pair_triangle_intersections']==0 and not any(c['mantlet_frame_intersections_by_seat']) for c in clearance)
    assert all(s['min_gap_m']>-.015 and s['max_gap_m']<.025 for s in support)
    report['status']='passed'
    (ROOT/'review/actual_contact.json').write_text(json.dumps(report,indent=2)+'\n')
    bpy.context.scene.frame_set(21)
    bpy.context.view_layer.update()
    master=ROOT/'review/actual_import_assembly.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    common.render(ROOT/'review/actual_strike_contact.png',(0,-.1,1.86),(0,6,.05),3.25)
    print('ACTUAL_CONTACT_PASSED',flush=True)


if __name__=='__main__': main()
