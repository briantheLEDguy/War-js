"""Publish source-to-gameplay coverage only from successful native executions."""
import hashlib
import json
from pathlib import Path
from animation_replacement import ROOT, OUT, CLIPS, PROFILES, RECIPES, locomotion


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def evidence(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def published_capture_matches(previous, receipts, images):
    """An identical deterministic rerun may update only the gameplay file's mtime."""
    return (previous.get('gameplayVerified') is True
            and all(previous.get('evidence',{}).get(key)==value for key,value in receipts.items())
            and previous.get('gameplayImages')==images)


def build_coverage(scenarios, presentations):
    clips={key:[] for key in CLIPS}
    abilities={}
    for index,row in enumerate(scenarios):
        profile=row['profile']; role=row['role']; scenario=row['scenario']
        career,style=PROFILES[profile]
        executor=next((kind for kind in ('participant_bot','player') if scenario.startswith(kind+'_')),None)
        if not executor: continue
        keys=[]
        if scenario.endswith('_ability'):
            for ability,recipe in presentations[profile]['presentations'].items():
                if role not in recipe['variantRoles']: continue
                keys=recipe['suppliedSources']
                if recipe['choreography']=='smash': keys=[keys[recipe['variantRoles'].index(role)]]
                abilities.setdefault(ability,[]).append(dict(profile=profile,role=role,executor=executor,scenarioIndex=index))
                break
        elif role in locomotion(style): keys=[locomotion(style)[role]]
        for key in keys:
            clips[key].append(dict(profile=profile,role=role,executor=executor,scenarioIndex=index))
    for key,rows in clips.items():
        if {r['executor'] for r in rows}!={'participant_bot','player'}:
            raise ValueError('Source lacks both player and participant-bot gameplay: '+key)
    expected={career+'.'+recipe[0] for career,recipes in RECIPES.items() for recipe in recipes}
    if set(abilities)!=expected: raise ValueError('Ability gameplay coverage differs from the forty recipes')
    for ability,rows in abilities.items():
        if {row['executor'] for row in rows}!={'player','participant_bot'}:
            raise ValueError('Ability lacks both player and participant-bot execution: '+ability)
    return clips,abilities


def main():
    gameplay_path=ROOT/'unreal/AegisWar/Saved/supplied-animation-gameplay.json'
    gameplay=read(gameplay_path)
    if not gameplay['passed'] or gameplay['abilityExecutions']!=82: raise ValueError('Native gameplay proof failed')
    technical_path=OUT/'technical-verification.json'
    technical=read(technical_path)
    presentations=read(OUT/'presentations.json')['profiles']
    manifest_hash=hashlib.sha256((OUT/'presentations.json').read_bytes()).hexdigest()
    if gameplay_path.stat().st_mtime<(OUT/'presentations.json').stat().st_mtime: raise ValueError('Gameplay evidence predates the current presentations')
    if technical.get('presentationManifestSha256')!=manifest_hash: raise ValueError('Structural evidence is stale')
    if not technical['structuralChecksPassed'] or set(technical['profiles'])!=set(presentations):
        raise ValueError('Every installed playable and NPC rig needs structural verification')
    equipment_path=OUT/'equipped-motion-measurements.json'
    equipment=read(equipment_path)
    if not equipment['passed'] or equipment.get('presentationManifestSha256')!=manifest_hash:
        raise ValueError('Equipped motion verification failed or is stale')
    network_paths=sorted((OUT/'network').glob('*/report.json'),key=lambda p:p.stat().st_mtime)
    if not network_paths: raise ValueError('Missing multiplayer proof')
    network_path=network_paths[-1]; network=read(network_path)
    if network.get('presentationManifestSha256')!=manifest_hash: raise ValueError('Multiplayer evidence is stale')
    if not network['passed'] or not network['reports'][2]['joinedDuringAction']: raise ValueError('Late join was not verified')
    clips,abilities=build_coverage(gameplay['scenarios'],presentations)
    capture_path=gameplay_path.parent/'AnimationGameplayCapture/frames.json'
    captures=read(capture_path)
    if not captures['gameplayPassed']:
        raise ValueError('Gameplay captures are missing or failed')
    captured={(row['profile'],row['role']) for row in captures['frames']}
    for key,rows in clips.items():
        if not any((row['profile'],row['role']) in captured for row in rows):
            raise ValueError('Source has no recorded gameplay image: '+key)
    for profile in PROFILES:
        for recipe in presentations[profile]['presentations'].values():
            if any((profile,role) not in captured for role in recipe['variantRoles']):
                raise ValueError('Ability variant lacks a gameplay capture: '+profile)
    images=[]
    for frame in captures['frames']:
        if Path(frame['file']).name!=frame['file']: raise ValueError('Invalid capture filename')
        images.append(evidence(capture_path.parent/frame['file']))
    if capture_path.stat().st_mtime<gameplay_path.stat().st_mtime:
        published_path=ROOT/'migration/supplied-animation-coverage.json'
        previous=read(published_path) if published_path.exists() else {}
        receipts=dict(gameplay=evidence(gameplay_path),captures=evidence(capture_path),
                      presentations=evidence(OUT/'presentations.json'))
        if not published_capture_matches(previous,receipts,images):
            raise ValueError('Gameplay captures predate changed or unpublished gameplay evidence')
    removal_path=OUT/'removal-verification.json'
    registry_path=OUT/'native-animation-removal-verification.json'
    if not read(removal_path)['passed'] or not read(registry_path)['passed']:
        raise ValueError('Legacy animation removal has not passed')
    inventory=read(OUT/'sources.json')['clips']
    report=dict(schemaVersion=1,gameplayVerified=True,graphicalAcceptance=False,steamAcceptance=False,
        clips={key:dict(source=CLIPS[key],sha256=inventory[key]['sha256'],executions=rows) for key,rows in clips.items()},
        abilities=abilities,gameplayImages=images,evidence=dict(gameplay=evidence(gameplay_path),technical=evidence(technical_path),
            equipment=evidence(equipment_path),network=evidence(network_path),presentations=evidence(OUT/'presentations.json'),
            captures=evidence(capture_path),removal=evidence(removal_path),registry=evidence(registry_path)))
    (ROOT/'migration/supplied-animation-coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    print('WAR_PLAYABLE_ANIMATION_COVERAGE=44 sources, 40 abilities, player and participant bot')


if __name__=='__main__': main()
