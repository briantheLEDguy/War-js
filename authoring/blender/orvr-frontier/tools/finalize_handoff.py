"""Collect measured staging metadata without granting publication approval."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def read(path):return json.loads((ROOT/path).read_text())
def main():
    contract=read('source/runtime_contract.json');contract['status']='exported_and_reviewed_for_integration; unpublished'
    assets=contract['assets'];pose=read('review/frontier_teamster_animations_build.json');fit=read('review/frontier_supply_officer_fit.json')
    wagon=assets['frontier_supply_wagon']
    wagon['driverSeatNote']='Socket is butt contact, not the hips joint. Use the fitted canonical pose and avatar origin below; omit the hand-held weapon.'
    wagon['driverAnimationAsset']='frontier_teamster_animations'
    wagon['driverAvatarOriginGltf']=pose['avatar_origin_wagon_local_gltf'];wagon['driverClip']='driver_seated'
    wagon['reinAsset']='frontier_caravan_reins';wagon['reinOriginGltf']=[0,0,0]
    assets['frontier_draft_horse'].update({'nominalGaits':{'idle':0,'walk':1.5,'draft_trot':3.5},
      'skinMeshes':['frontier_draft_horse_coat','frontier_draft_horse_tack'],
      'footPlantMeasuredMaximumMetres':{'authoredKeys':.001,'interpolatedMidpoints':.006111},
      'limitations':['Stylized short coat; no hair cards or free-roaming wildlife behavior.', 'Harness is fitted to this horse and the documented wagon shafts.']})
    assets['frontier_draft_horse'].pop('plannedClips',None)
    assets['frontier_draft_horse']['clips']=read('review/frontier_draft_horse_build.json')['lods'][0]['clips']
    assets['frontier_caravan_reins']={'originGltf':[0,0,0],'mountParent':'wagon root','driverGripGltf':pose['rein_grip_wagon_local_gltf'],
      'socketNodes':['socket.driver_hand_left','socket.driver_hand_right'],
      'canonicalGripBones':{'socket.driver_hand_left':'hand_R','socket.driver_hand_right':'hand_L'},
      'limitations':['Static loose leather; use the fitted horse offset and subtle exported head motion. Do not attach to arbitrary horse sizes.']}
    assets['frontier_supply_officer_kit']={'socketNodes':['socket.belt_mount'],'profileFit':fit,
      'limitations':['Rigid belt attachment. The provided fit is only for civic_battle_prelate_m with novitiate armor; no race substitution is implied.']}
    assets['frontier_teamster_animations']={'model':'frontier_teamster_animations.glb','sha256':pose['sha256'],
      'skeletonId':'humanoid_game_v2','bindPoseId':'a_pose_v2','clips':pose['clips'],
      'avatarOriginWagonLocalGltf':pose['avatar_origin_wagon_local_gltf'],
      'notes':['Every bone is keyed, including rest channels. No world-root motion.','Use one AnimationMixer per independently skinned actor; separate horse and driver roots.','This is a fitted held pose; no enter/exit or separate ram-crew action is included.']}
    display={'frontier_draft_horse':'Bay Draft Horse with Full Harness','frontier_caravan_reins':'Fitted Wagon Reins and Bit','frontier_supply_officer_kit':'Supply Officer Ledger Pouch'}
    for key,asset in assets.items():
        report=read(f'review/{key}_build.json')
        if 'lods' not in report:continue
        asset.setdefault('builder',{'displayName':display.get(key,key),'defaultScale':1,'units':'metres','forwardAxis':'+Z','originGltf':[0,0,0],
          'lodModels':[f'{key}_lod{level}.glb' for level in (0,1,2)],'category':'siege_logistics','reviewStatus':'pending'})
        asset['exportedLods']=[{'level':row['level'],'model':Path(row['path'].replace('\\','/')).name,'sha256':row['sha256'],'triangles':row['triangles'],'bytes':row['bytes']} for row in report['lods']]
    contract['integrationNotes']=['Preserve fixed pivot.* parents and named driven children. Flattening this hierarchy collapses mechanical motion.',
      'Initialize catapult_fire at time zero to show the cocked ready pose. The default bind pose is vertical.',
      'The Sunmeadow wheat standard is regional artwork. This package does not include exported realm/color variants.',
      'Projectile, poured liquid, damage, ownership and replacement timing remain authoritative runtime responsibilities.',
      'Static and animated reimport reviews, hashes, measured counts and contact fits are in review/. Publication remains a separate root integration decision.']
    (ROOT/'source/runtime_contract.json').write_text(json.dumps(contract,indent=2)+'\n')


if __name__=='__main__':main()
