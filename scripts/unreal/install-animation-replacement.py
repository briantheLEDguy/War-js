"""Replace every native visual binding, then publish the complete import registry."""
import hashlib
import json
from pathlib import Path
import sys
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from animation_replacement import ROOT, OUT, PROFILES

library=unreal.EditorAssetLibrary
sets=json.loads((OUT/"presentations.json").read_text())["profiles"]
bodies=json.loads((OUT/"bodies.json").read_text())["profiles"]
registry_path=ROOT/"unreal/AegisWar/Content/Migration/visual-imports.json"
registry=json.loads(registry_path.read_text())
entries={e["profileKey"]:e for e in registry["entries"]}
removed={row['path']:row for row in json.loads((OUT/'source-track-removal.json').read_text())}
for entry in entries.values():
    row=removed.get(entry['sourceModel'])
    if row and entry['sourceSha256']==row['beforeSha256']:
        if hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()!=row['afterSha256']:
            raise RuntimeError('Changed body after track removal: '+row['path'])
        entry['sourceSha256']=row['afterSha256']
template=unreal.load_asset("/Game/MigrationProof/Visual_civic_battle_prelate_m")
for profile,(career,_) in PROFILES.items():
    path="/Game/MigrationProof/Visual_"+profile
    visual=unreal.load_asset(path) if library.does_asset_exist(path) else library.duplicate_asset(template.get_path_name(),path)
    if not visual: raise RuntimeError("Could not create playable profile: "+profile)
    visual.set_editor_properties(dict(profile_key=profile,source_profile_key=profile,class_id=career,
        race_id="greenskin" if profile.startswith("mire_") else "empire",body_variant="m",
        realm=unreal.WarRealm.RIFTBOUND if profile.startswith("mire_") else unreal.WarRealm.AEGIS))
    body=bodies[profile]
    entries[profile]=dict(profileKey=profile,sourceModel=body["source"],sourceSha256=body["sourceSha256"],
        skeletalMeshPath=body["mesh"],animationPaths=[],artApproval=False,developmentOnly=True)

assets=unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_class(unreal.TopLevelAssetPath("/Script/AegisWar","WarCharacterVisualDefinition"),True)
installed=[]
for data in assets:
    visual=data.get_asset()
    source=str(visual.source_profile_key)
    if source in ("None",""): source=str(visual.profile_key)
    if source not in sets:
        raise RuntimeError("Active visual has an unaudited source rig: "+visual.get_path_name()+" -> "+source)
    entry=sets[source]; binding=entries[source]
    animations={role:unreal.load_asset(path) for role,path in entry["bindings"].items()}
    if any(a is None for a in animations.values()): raise RuntimeError("Missing supplied binding: "+source)
    mesh=unreal.load_asset(entry["mesh"])
    presentations={}
    for ability,recipe in entry["presentations"].items():
        value=unreal.WarAbilityPresentation()
        value.set_editor_properties(dict(variant_roles=recipe["variantRoles"],supplied_sources=recipe["suppliedSources"],
            duration=recipe["duration"],contact_seconds=recipe["contactSeconds"],blend_seconds=recipe["blendSeconds"],
            stow_equipment=recipe["stowEquipment"],movement=recipe["movement"],capsule_heights=recipe["capsuleHeights"]))
        presentations[ability]=value
    visual.set_editor_properties(dict(skeletal_mesh=mesh,source_model=binding["sourceModel"],source_sha256=binding["sourceSha256"],
        animation_blueprint=None,idle_animation=animations["idle"],imported_animations=animations,
        animation_style=entry["style"],ability_presentations=presentations,basic_contact_seconds=entry['basicContactSeconds'],locomotion_speeds=entry['locomotionSpeeds']))
    if source in PROFILES:
        body=bodies[source]
        if hashlib.sha256((ROOT/body["source"]).read_bytes()).hexdigest()!=body["sourceSha256"]: raise RuntimeError("Body source changed")
        options=unreal.AnimPoseEvaluationOptions(); options.optional_skeletal_mesh=mesh
        pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(animations["idle"],0,options)
        chest=unreal.AnimPoseExtensions.get_ref_bone_pose(pose,"upper_chest",unreal.AnimPoseSpaces.WORLD)
        for slot,bone in (("weapon","hand_R"),("shield","hand_L")):
            if slot not in body:
                visual.set_editor_property(slot+"_mesh",None); continue
            equipped=unreal.load_asset(body[slot]["mesh"])
            reference=unreal.AnimPoseExtensions.get_ref_bone_pose(pose,bone,unreal.AnimPoseSpaces.WORLD)
            # Static equipment retains its authored world coordinates. Inverse
            # bind transforms account for the rig's actual scale and bone axes.
            grip=reference.inverse()
            from supplied_stow import stored_transform
            stored=stored_transform(source,slot,equipped,grip,chest)
            visual.set_editor_properties({slot+"_mesh":equipped,slot+"_grip":grip,slot+"_stowed":stored})
    error=visual.validate_for_spawn(visual.realm)
    if error: raise RuntimeError("Native visual validation: "+visual.get_path_name()+": "+error)
    if not library.save_loaded_asset(visual,False): raise RuntimeError("Save failed: "+visual.get_path_name())
    binding["animationPaths"]=sorted(set(entry["bindings"].values()))
    binding["skeletalMeshPath"]=entry["mesh"]
    installed.append(dict(visual=visual.get_path_name(),source=source,bindings=len(animations),abilities=len(presentations)))
registry["entries"]=list(entries.values())
registry_path.write_text(json.dumps(registry,indent=2)+"\n")
(OUT/"installed.json").write_text(json.dumps(dict(schemaVersion=1,visuals=installed,nativeSpawnValidation=True,
    gameplayVerified=False,artApproval=False),indent=2)+"\n")
unreal.log("WAR_REPLACEMENT_INSTALLED="+str(len(installed)))
