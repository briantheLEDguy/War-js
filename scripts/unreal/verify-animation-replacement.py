"""Read-only native sampling checks. Structural evidence is not gameplay approval."""
import hashlib
import json
import math
from pathlib import Path
import sys
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from animation_replacement import ROOT, OUT, SOURCE, CLIPS, PROFILES, RECIPES, coverage, selected

sets=json.loads((OUT/'presentations.json').read_text())['profiles']
sources=json.loads((OUT/'sources.json').read_text())['clips']
retarget=json.loads((OUT/'retarget.json').read_text())
failures=[]
report=dict(schemaVersion=1,profiles={},coverage={},gameplayVerified=False,artApproval=False,
    presentationManifestSha256=hashlib.sha256((OUT/'presentations.json').read_bytes()).hexdigest())
def check(condition,detail):
    if not condition: failures.append(detail)
for key,uses in coverage().items():
    check(hashlib.sha256((SOURCE/CLIPS[key]).read_bytes()).hexdigest()==sources[key]['sha256'],'Source changed: '+key)
    report['coverage'][key]=dict(source=CLIPS[key],sha256=sources[key]['sha256'],reachableBindings=uses,gameplayEvidence=None)
check(sum(len(r) for r in RECIPES.values())==40,'Expected forty ability recipes')
for profile,entry in sets.items():
    mesh=unreal.load_asset(entry['mesh'])
    visual=unreal.load_asset('/Game/MigrationProof/Visual_'+profile) if profile in PROFILES else None
    check(bool(mesh),profile+': missing mesh')
    if visual: check(not visual.validate_for_spawn(visual.realm),profile+': native spawn validation failed')
    options=[]
    for kind in (unreal.AnimDataEvalType.RAW,unreal.AnimDataEvalType.COMPRESSED):
        opt=unreal.AnimPoseEvaluationOptions()
        opt.set_editor_properties(dict(optional_skeletal_mesh=mesh,evaluation_type=kind))
        options.append(opt)
    by_path={}
    for role,path in entry['bindings'].items(): by_path.setdefault(path,[]).append(role)
    measurements=[]
    for path,roles in by_path.items():
        sequence=unreal.load_asset(path)
        check(sequence.get_editor_property('skeleton')==mesh.skeleton,profile+': skeleton mismatch '+path)
        duration=unreal.AnimationLibrary.get_sequence_length(sequence)
        check(duration>0,profile+': zero-length motion '+path)
        count=max(2,math.ceil(duration*30)+1)
        maximum_error=0.; maximum_length_delta=0.; finite=True
        for frame in range(count):
            time=min(duration,frame/30)
            raw,compressed=[unreal.AnimPoseExtensions.get_anim_pose_at_time(sequence,time,opt) for opt in options]
            for bone in unreal.AnimPoseExtensions.get_bone_names(raw):
                a=unreal.AnimPoseExtensions.get_bone_pose(raw,bone,unreal.AnimPoseSpaces.WORLD)
                b=unreal.AnimPoseExtensions.get_bone_pose(compressed,bone,unreal.AnimPoseSpaces.WORLD)
                maximum_error=max(maximum_error,(a.translation-b.translation).length())
                local=unreal.AnimPoseExtensions.get_bone_pose(raw,bone,unreal.AnimPoseSpaces.LOCAL)
                finite=finite and all(math.isfinite(x) for x in (local.translation.x,local.translation.y,local.translation.z,local.scale3d.x,local.scale3d.y,local.scale3d.z,local.rotation.x,local.rotation.y,local.rotation.z,local.rotation.w))
                if str(bone) not in ('root','hips'):
                    ref=unreal.AnimPoseExtensions.get_ref_bone_pose(raw,bone,unreal.AnimPoseSpaces.LOCAL)
                    maximum_length_delta=max(maximum_length_delta,abs(local.translation.length()-ref.translation.length()))
        check(finite,profile+': non-finite pose '+path)
        check(maximum_error<.25,profile+': compression error '+str(maximum_error)+'cm '+path)
        check(maximum_length_delta<.005,profile+': changed limb length '+str(maximum_length_delta)+' '+path)
        package=ROOT/'unreal/AegisWar/Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
        measurements.append(dict(animation=path,packageSha256=hashlib.sha256(package.read_bytes()).hexdigest(),roles=roles,frames=count,duration=duration,
            maximumCompressionErrorCm=maximum_error,maximumLocalLimbLengthDelta=maximum_length_delta,finite=finite))
    for ability,recipe in entry['presentations'].items():
        check(0<recipe['contactSeconds']<recipe['duration'],ability+': contact outside action')
        check(all(k in CLIPS for k in recipe['suppliedSources']),ability+': legacy source')
        for role in recipe['variantRoles']:
            sequence=unreal.load_asset(entry['bindings'][role])
            duration=unreal.AnimationLibrary.get_sequence_length(sequence)
            check(abs(duration-recipe['duration'])<1/30+.001,ability+': variant changes recovery timing')
            idle=unreal.load_asset(entry['bindings']['idle'])
            end=unreal.AnimPoseExtensions.get_anim_pose_at_time(sequence,duration,options[0])
            ready=unreal.AnimPoseExtensions.get_anim_pose_at_time(idle,0,options[0])
            worst=0.
            for bone in unreal.AnimPoseExtensions.get_bone_names(end):
                a=unreal.AnimPoseExtensions.get_bone_pose(end,bone,unreal.AnimPoseSpaces.WORLD)
                b=unreal.AnimPoseExtensions.get_bone_pose(ready,bone,unreal.AnimPoseSpaces.WORLD)
                worst=max(worst,(a.translation-b.translation).length())
            check(worst<.1,ability+': incomplete recovery '+str(worst)+'cm')
            if visual and recipe['stowEquipment'] and entry['style']!='spell':
                for seconds in (.3,duration-.3):
                    pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(sequence,seconds,options[1])
                    chest=unreal.AnimPoseExtensions.get_bone_pose(pose,'upper_chest',unreal.AnimPoseSpaces.WORLD)
                    for slot,hand in (('weapon','hand_R'),('shield','hand_L')):
                        if not visual.get_editor_property(slot+'_mesh'): continue
                        wrist=unreal.AnimPoseExtensions.get_bone_pose(pose,hand,unreal.AnimPoseSpaces.WORLD)
                        drawn=visual.get_editor_property(slot+'_grip')*wrist
                        stored=visual.get_editor_property(slot+'_stowed')*chest
                        error=(drawn.translation-stored.translation).length()
                        check(error<1.,ability+': discontinuous '+slot+' stow attachment '+str(error)+'cm')
    report['profiles'][profile]=dict(mesh=entry['mesh'],animations=measurements,abilityCount=len(entry['presentations']))
report['failures']=failures; report['structuralChecksPassed']=not failures
(OUT/'technical-verification.json').write_text(json.dumps(report,indent=2)+'\n')
unreal.log('WAR_ANIMATION_TECHNICAL='+str(len(failures)))
if failures: raise RuntimeError('\n'.join(failures))
