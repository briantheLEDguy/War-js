"""Measure full equipped motion, including the capsule-owned leap and stowing."""
import itertools
import hashlib
import json
from pathlib import Path
import sys
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from animation_replacement import OUT,PROFILES

sets=json.loads((OUT/'presentations.json').read_text())['profiles']
rows=[]
for profile in PROFILES:
    entry=sets[profile]; visual=unreal.load_asset('/Game/MigrationProof/Visual_'+profile)
    options=unreal.AnimPoseEvaluationOptions(); options.optional_skeletal_mesh=visual.skeletal_mesh
    options.evaluation_type=unreal.AnimDataEvalType.COMPRESSED
    equipment={}
    for slot in ('weapon','shield'):
        mesh=visual.get_editor_property(slot+'_mesh')
        if not mesh: continue
        description=mesh.get_static_mesh_description(0)
        if not description: raise RuntimeError('Missing equipment mesh description')
        equipment[slot]=[]
        for index in range(description.get_vertex_count()):
            vertex_id=unreal.VertexID(index)
            if not description.is_vertex_valid(vertex_id): raise RuntimeError('Sparse equipment vertex IDs require remapping')
            v=description.get_vertex_position(vertex_id)
            equipment[slot].append((v.x,v.y,v.z))
    for role,path in entry['bindings'].items():
        if role in entry['presentations'] or role in ('combat_idle','attack_melee','attack_ranged','cast'): continue
        sequence=unreal.load_asset(path); duration=unreal.AnimationLibrary.get_sequence_length(sequence)
        recipe=next((r for r in entry['presentations'].values() if role in r['variantRoles']),None)
        held={} if role=='death' else equipment
        minima={slot:dict(height=100000,time=0) for slot in held}; feet=[]
        for frame in range(round(duration*30)+1):
            seconds=min(duration,frame/30)
            pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(sequence,seconds,options)
            bone=lambda name:unreal.AnimPoseExtensions.get_bone_pose(pose,name,unreal.AnimPoseSpaces.WORLD)
            lift=recipe['capsuleHeights'][min(frame,len(recipe['capsuleHeights'])-1)] if recipe and recipe['capsuleHeights'] else 0
            stow=max(0,min(1,seconds/.3,(duration-seconds)/.3)) if recipe and recipe['stowEquipment'] else 0
            if entry['style']=='spell': stow=1
            feet.append(min(bone('foot_L').translation.z,bone('foot_R').translation.z)+lift)
            for slot,vertices in held.items():
                drawn=visual.get_editor_property(slot+'_grip')*bone('hand_R' if slot=='weapon' else 'hand_L')
                stored=visual.get_editor_property(slot+'_stowed')*bone('upper_chest')
                from_transform=stored if stow>=1 else drawn
                origin=from_transform.transform_location(unreal.Vector()).z
                axes=[from_transform.transform_location(v).z-origin for v in (unreal.Vector(1,0,0),unreal.Vector(0,1,0),unreal.Vector(0,0,1))]
                height=min(x*axes[0]+y*axes[1]+z*axes[2] for x,y,z in vertices)+origin+lift
                if height<minima[slot]['height']: minima[slot]=dict(height=height,time=seconds)
        rows.append(dict(profile=profile,role=role,duration=duration,equipmentVerticesMinZ=minima,minFootJointZ=min(feet),maxLowerFootJointZ=max(feet)))
failures=[dict(profile=row['profile'],role=row['role'],slot=slot,**value) for row in rows for slot,value in row['equipmentVerticesMinZ'].items() if value['height'] < -2]
for row in rows:
    entry=sets[row['profile']]
    recipe=next((r for r in entry['presentations'].values() if row['role'] in r['variantRoles']),None)
    if recipe and recipe['movement']!='leap' and row['maxLowerFootJointZ']>35:
        failures.append(dict(profile=row['profile'],role=row['role'],error='Airborne action lacks capsule ownership'))
(OUT/'equipped-motion-measurements.json').write_text(json.dumps(dict(measurement='Every LOD0 equipment vertex at 30Hz',passed=not failures,
    presentationManifestSha256=hashlib.sha256((OUT/'presentations.json').read_bytes()).hexdigest(),
    deathEquipmentEvidence='SuppliedAnimationGameplay native release test',rows=rows,failures=failures),indent=2)+'\n')
unreal.log('WAR_EQUIPPED_MOTION_MEASUREMENTS='+str(len(rows)))
if failures: raise RuntimeError('Equipped motion crosses the ground: '+str(failures))
