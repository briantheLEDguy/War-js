"""Bake reachable movement adaptations and forty supplied-source choreographies.

Every variant has the same authoritative contact and recovery duration. Source
holds, combinations, edited preparations and full recoveries distinguish actions.
"""
import json
import hashlib
import math
from pathlib import Path
import sys
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from animation_replacement import ROOT, OUT, PROFILES, RECIPES, locomotion, selected
from supplied_stow import bake_stowing,stored_transform

retarget=json.loads((OUT/"retarget.json").read_text())
library=unreal.EditorAssetLibrary
RATE=30
prelate_contacts=json.loads((Path(__file__).parent/'animation-recipes/corrections/prelate-contacts.json').read_text())
shield_contacts=json.loads((Path(__file__).parent/'animation-recipes/corrections/shield-contacts.json').read_text())

def blend(a,b,alpha):
    alpha=max(0.,min(1.,alpha)); alpha=alpha*alpha*(3-2*alpha)
    result=unreal.Transform(); result.translation=a.translation*(1-alpha)+b.translation*alpha
    result.scale3d=a.scale3d*(1-alpha)+b.scale3d*alpha
    qa,qb=a.rotation,b.rotation; va=[qa.x,qa.y,qa.z,qa.w]; vb=[qb.x,qb.y,qb.z,qb.w]
    dot=sum(x*y for x,y in zip(va,vb))
    if dot<0: vb=[-x for x in vb]; dot=-dot
    theta=math.acos(min(1.,dot))
    values=va if theta<1e-6 else [(x*math.sin((1-alpha)*theta)+y*math.sin(alpha*theta))/math.sin(theta) for x,y in zip(va,vb)]
    q=unreal.Quat(*values); q.normalize(); result.rotation=q
    return result

def row_blend(a,b,t): return {n:blend(a[n],b[n],t) for n in a}


def transfer_airborne_lift(rows,component,reference_pose):
    """Move vertical travel from the visual root to the swept capsule."""
    parent=unreal.AnimPoseExtensions.get_ref_bone_pose(reference_pose,'root',unreal.AnimPoseSpaces.WORLD)
    floor=min(unreal.AnimPoseExtensions.get_ref_bone_pose(reference_pose,b,unreal.AnimPoseSpaces.WORLD).translation.z for b in ('foot_L','foot_R'))
    heights=[]
    for index,row in enumerate(rows):
        world={}
        def transform(bone):
            if bone not in world:
                ancestor=str(component.get_parent_bone(bone))
                world[bone]=row[bone]*transform(ancestor) if ancestor in row else row[bone]
            return world[bone]
        lift=max(0.,min(transform('foot_L').translation.z,transform('foot_R').translation.z)-floor)
        # The authored action starts/finishes in its supplied ready pose.
        if index in (0,len(rows)-1): lift=0.
        origin=parent.inverse_transform_location(unreal.Vector())
        delta=parent.inverse_transform_location(unreal.Vector(0,0,lift))-origin
        row['hips'].translation=row['hips'].translation-delta
        heights.append(lift)
    return heights

results=json.loads((OUT/'presentations.json').read_text())['profiles'] if (OUT/'presentations.json').exists() else {}
for profile,entry in retarget["profiles"].items():
    if not selected(profile): continue
    mesh=unreal.load_asset(entry["mesh"])
    skeleton_component=unreal.new_object(unreal.SkeletalMeshComponent); skeleton_component.set_skeletal_mesh_asset(mesh)
    options=unreal.AnimPoseEvaluationOptions(); options.set_editor_properties(dict(optional_skeletal_mesh=mesh,evaluation_type=unreal.AnimDataEvalType.RAW))
    career,style=PROFILES.get(profile,(None,"spell"))
    sources={k:unreal.load_asset(v["animation"]) for k,v in entry["clips"].items()}
    cache={}
    def sample(key,time):
        time=max(0.,min(float(time),entry["clips"][key]["duration"]))
        cache_key=(key,round(time,5))
        if cache_key not in cache:
            pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(sources[key],time,options)
            cache[cache_key]={str(n):unreal.AnimPoseExtensions.get_bone_pose(pose,n,unreal.AnimPoseSpaces.LOCAL) for n in unreal.AnimPoseExtensions.get_bone_names(pose)}
        return cache[cache_key]
    movement=locomotion(style)
    idle_key=movement["idle"]; idle=sample(idle_key,entry["clips"][idle_key]["duration"]*.5 if style=="shield" else 0)
    # A body revision owns a distinct skeleton asset even when its rest rig is
    # identical. Never reuse action assets carrying the previous body's rig.
    revision=hashlib.sha256(mesh.get_path_name().encode()).hexdigest()[:12]
    destination="/Game/Characters/AnimationReplacement/"+retarget["identity"]+"/"+profile+"/Actions_"+revision
    def write(name,rows,source_key):
        path=destination+"/"+name.replace(".","_")
        asset=unreal.load_asset(path) if library.does_asset_exist(path) else library.duplicate_asset(sources[source_key].get_path_name(),path)
        if not asset: raise RuntimeError("Could not create "+path)
        data=asset.controller; data.open_bracket("Supplied-source action recipe",False)
        data.set_frame_rate(unreal.FrameRate(RATE,1),False); data.set_number_of_frames(unreal.FrameNumber(len(rows)-1),False)
        for bone in rows[0]:
            if not data.set_bone_track_keys(bone,[r[bone].translation for r in rows],[r[bone].rotation for r in rows],[r[bone].scale3d for r in rows],False):
                raise RuntimeError("Failed action track: "+bone)
        data.close_bracket(False)
        asset.set_editor_property("allow_frame_stripping",False)
        asset.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Characters/AnimationReplacement/SuppliedPoseCompressionV1'))
        if not unreal.WarImportLibrary.finalize_animation_sampling(asset): raise RuntimeError("Sampling failed: "+name)
        library.set_metadata_tag(asset,"WarSuppliedAnimationSet",retarget["identity"])
        if not library.save_loaded_asset(asset,False): raise RuntimeError("Save failed: "+name)
        return asset.get_path_name()
    bindings={role:entry["clips"][key]["animation"] for role,key in movement.items()}
    if style=="shield":
        bindings["idle"]=bindings["combat_idle"]=write("shield_ready",[idle]*31,idle_key)
    if style=="spell":
        duration=entry["clips"]["spell.walk"]["duration"]
        bindings["walk_backward"]=write("caster_backward",[sample("spell.walk",duration-i/RATE) for i in range(round(duration*RATE)+1)],"spell.walk")
    bindings["attack_melee"]=entry["clips"]["two.slash" if style=="two" else "shield.slash" if "shield.slash" in sources else "spell.bolt"]["animation"]
    bindings["attack_ranged"]=entry["clips"].get("spell.bolt",entry["clips"].get("shield.slash"))["animation"]
    bindings["cast"]=entry["clips"].get("spell.focus",entry["clips"].get("shield.power"))["animation"]
    # Landing is a supplied jump recovery, never the retired generic jump clip.
    jump_key=movement["jump"]; duration=entry["clips"][jump_key]["duration"]
    landing=[row_blend(sample(jump_key,duration*.8+i/RATE),idle,0) for i in range(max(2,round(duration*.2*RATE)+1))]
    reference_pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(sources[jump_key],0,options)
    # Landing occurs on physical ground, including when the source's final fifth
    # still contains airborne frames. Keep its leg recovery without floating.
    for row in landing:
        transfer_airborne_lift([idle,row,idle],skeleton_component,reference_pose)
    bindings["landing"]=write("landing",landing,jump_key)
    # The capsule owns the actual jump. Remove positive hip rise from the
    # supplied jump while retaining crouch and joint articulation.
    jump_rows=[]
    initial=sample(jump_key,0)['hips'].translation
    for step in range(round(duration*RATE)+1):
        row=row_blend(sample(jump_key,step/RATE),sample(jump_key,step/RATE),0)
        hips=row['hips']; p=hips.translation
        hips.translation=unreal.Vector(p.x,p.y,min(p.z,initial.z))
        jump_rows.append(row)
    bindings['jump']=write('capsule_jump',jump_rows,jump_key)
    for role in ('turn_left','turn_right'):
        key=movement[role]; rows=[]
        initial=sample(key,0)['hips'].rotation.rotator().yaw
        for step in range(round(entry['clips'][key]['duration']*RATE)+1):
            row=row_blend(sample(key,step/RATE),sample(key,step/RATE),0)
            angles=row['hips'].rotation.rotator(); angles.yaw=initial; row['hips'].rotation=angles.quaternion()
            rows.append(row)
        bindings[role]=write(role+'_capsule_yaw',rows,key)
    presentations={}
    for suffix,keys,choreography,fraction,hold,equipment,motion in RECIPES.get(career,[]):
        ability=career+"."+suffix
        variants=[[key] for key in keys] if choreography=="smash" else [keys]
        built=[]; contacts=[]
        lead=.36 if equipment=="stowed" else .16
        tail=.4 if equipment=="stowed" else .3
        for variant in variants:
            frames=[idle]*round(lead*RATE)
            for part,key in enumerate(variant):
                duration=entry["clips"][key]["duration"]
                start,end=0.,duration
                if choreography=="finisher": start=duration*(.48 if key=="shield.combo" else .58)
                if choreography=="ground": start=duration*.64
                if choreography=="combo" and key=="shield.combo": end=duration*.77
                if choreography=="opener": end=duration*.78
                if choreography=="bash": start=duration*.25; end=duration*.72
                first=sample(key,start)
                bridge=frames[-1]
                for step in range(5): frames.append(row_blend(bridge,first,(step+1)/5))
                count=max(2,round((end-start)*RATE)+1); contact=round((count-1)*fraction)
                corrections=prelate_contacts if profile==prelate_contacts['profile'] else shield_contacts if profile in shield_contacts['profiles'] else None
                if corrections and key in corrections['markers']:
                    markers=corrections['markers'][key]
                    seconds=markers.get(choreography,markers['default'])
                    if not start<seconds<end: raise RuntimeError('Authored contact is outside the source segment: '+key)
                    contact=round((count-1)*(seconds-start)/(end-start))
                for step in range(count):
                    row=sample(key,start+(end-start)*step/(count-1)); frames.append(row)
                    if step==contact:
                        if part==len(variant)-1: contacts.append((len(frames)-1)/RATE)
                        frames.extend([row]*round(hold*(end-start)*RATE))
            last=frames[-1]
            for step in range(round(tail*RATE)): frames.append(row_blend(last,idle,(step+1)/round(tail*RATE)))
            built.append(frames)
        # Different smash takes share one event time and duration; clients only
        # receive a cosmetic variant identity, never a different damage schedule.
        duration=max((len(rows)-1)/RATE for rows in built)
        contact=max(contacts)
        roles=[]; heights=[]
        if motion=="leap" and choreography=="smash":
            # One capsule trajectory for both cosmetic smash variants. Landing
            # coincides with the common contact event and shares collision rules.
            for step in range(round(duration*RATE)+1):
                phase=max(0.,min(1.,(step/RATE-lead)/max(.01,contact-lead)))
                heights.append(55*math.sin(math.pi*phase)**2 if lead<step/RATE<contact else 0.)
        for index,rows in enumerate(built):
            original_duration=(len(rows)-1)/RATE; original_contact=contacts[index]
            normalized=[]
            for step in range(round(duration*RATE)+1):
                t=step/RATE
                source_t=t/contact*original_contact if t<=contact else original_contact+(t-contact)/(duration-contact)*(original_duration-original_contact)
                position=min(len(rows)-1,source_t*RATE); lo=math.floor(position); hi=min(len(rows)-1,lo+1)
                normalized.append(row_blend(rows[lo],rows[hi],position-lo))
            if motion=="leap":
                # Remove the supplied airborne root rise; retain crouch, limb
                # articulation and rotations. Capsule movement adds the rise.
                key=variants[index][0]
                root_pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(sources[key],0,options)
                transferred=transfer_airborne_lift(normalized,skeleton_component,root_pose)
                if choreography!='smash': heights=transferred
            if equipment=='stowed' and style!='spell':
                visual=unreal.load_asset('/Game/MigrationProof/Visual_'+profile)
                ref_pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(sources[idle_key],0,options)
                chest=unreal.AnimPoseExtensions.get_ref_bone_pose(ref_pose,'upper_chest',unreal.AnimPoseSpaces.WORLD)
                for slot in ('weapon','shield'):
                    equipped=visual.get_editor_property(slot+'_mesh')
                    if equipped:
                        visual.set_editor_property(slot+'_stowed',stored_transform(profile,slot,equipped,visual.get_editor_property(slot+'_grip'),chest))
                bake_stowing(normalized,skeleton_component,visual,idle,RATE)
            role=ability+"__"+str(index); roles.append(role)
            path=write(role,normalized,variants[index][0]); bindings[role]=path
            if index==0: bindings[ability]=path
        presentations[ability]=dict(variantRoles=roles,suppliedSources=keys,duration=duration,contactSeconds=contact,
            blendSeconds=.14,stowEquipment=equipment=="stowed",movement=motion,capsuleHeights=heights,choreography=choreography,
            gameplayVerified=False)
    basic_key={'battle_prelate':'litany_of_strikes','sunfire_templar':'sunbrand_strike',
               'warbrute':'sneaky_start','ember_arcanist':'spark_lash'}.get(career)
    basic_contact=unreal.AnimationLibrary.get_sequence_length(unreal.load_asset(bindings['attack_melee']))*.5
    if basic_key:
        recipe=presentations[career+'.'+basic_key]
        bindings['attack_melee']=bindings[recipe['variantRoles'][0]]
        basic_contact=recipe['contactSeconds']
    speeds={role:entry['clips'][key]['locomotionSpeedCm'] for role,key in movement.items()
            if role in ('walk','walk_backward','run','strafe_left','strafe_right')}
    results[profile]=dict(mesh=entry["mesh"],style=style,bindings=bindings,presentations=presentations,basicContactSeconds=basic_contact,locomotionSpeeds=speeds)
    (OUT/"presentations.json").write_text(json.dumps(dict(schemaVersion=1,profiles=results),indent=2)+"\n")
    unreal.log("WAR_PRESENTATIONS="+profile+":"+str(len(presentations)))
