"""Record source weapon/hand trajectories to review authored release phases."""
import json
from pathlib import Path
import sys
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from animation_replacement import OUT,ROOT

sets=json.loads((OUT/'retarget.json').read_text())['profiles']
grips=json.loads((ROOT/'scripts/unreal/animation-recipes/corrections/prelate-grip.json').read_text())
head=grips['gripsWorld']['head_center_local']
point=unreal.Vector(head[0]*100,-head[1]*100,head[2]*100)
entry=sets['civic_battle_prelate_m']
visual=unreal.load_asset('/Game/MigrationProof/Visual_civic_battle_prelate_m')
options=unreal.AnimPoseEvaluationOptions(); options.optional_skeletal_mesh=visual.skeletal_mesh
records={}
for key in ('two.slash','two.slide','two.jump_attack','two.spin'):
    clip=entry['clips'][key]; animation=unreal.load_asset(clip['animation']); frames=[]
    for frame in range(round(clip['duration']*30)+1):
        seconds=min(clip['duration'],frame/30)
        pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(animation,seconds,options)
        hand=unreal.AnimPoseExtensions.get_bone_pose(pose,'hand_R',unreal.AnimPoseSpaces.WORLD)
        position=(visual.weapon_grip*hand).transform_location(point)
        frames.append(dict(time=seconds,fraction=seconds/clip['duration'],head=[position.x,position.y,position.z]))
    records[key]=dict(duration=clip['duration'],maximumForward=max(frames,key=lambda r:r['head'][1]),frames=frames)
(OUT/'source-contact-trajectories.json').write_text(json.dumps(records,indent=2)+'\n')

shield_records={}
for profile in ('civic_sunfire_templar_m','mire_warbrute_m'):
    entry=sets[profile]
    visual=unreal.load_asset('/Game/MigrationProof/Visual_'+profile)
    options.optional_skeletal_mesh=visual.skeletal_mesh
    description=visual.weapon_mesh.get_static_mesh_description(0)
    tip=max((description.get_vertex_position(unreal.VertexID(i))
             for i in range(description.get_vertex_count())),key=lambda v:v.z)
    for key in ('shield.slash','shield.combo','shield.kick','shield.block','shield.power'):
        clip=entry['clips'][key]; animation=unreal.load_asset(clip['animation']); frames=[]
        for frame in range(round(clip['duration']*30)+1):
            seconds=min(clip['duration'],frame/30)
            pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(animation,seconds,options)
            bone=lambda name:unreal.AnimPoseExtensions.get_bone_pose(pose,name,unreal.AnimPoseSpaces.WORLD)
            point=(visual.weapon_grip*bone('hand_R')).transform_location(tip)
            vector=lambda v:[v.x,v.y,v.z]
            frames.append(dict(time=seconds,fraction=seconds/clip['duration'],tip=vector(point),
                footRight=vector(bone('foot_R').translation),footLeft=vector(bone('foot_L').translation)))
        shield_records[profile+':'+key]=dict(duration=clip['duration'],frames=frames)
(OUT/'shield-contact-trajectories.json').write_text(json.dumps(shield_records,indent=2)+'\n')
