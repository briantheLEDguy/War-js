"""Read the installed body and supplied animation set as separate contracts."""
import hashlib
import json
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'unreal/AegisWar/Content/Migration/visual-imports.json'
PRESENTATIONS=ROOT/'artifacts/unreal/animation-replacement/presentations.json'


def installed(profile):
    rows=json.loads(REGISTRY.read_text())['entries']
    binding=next((row for row in rows if row['profileKey']==profile),None)
    entry=json.loads(PRESENTATIONS.read_text())['profiles'].get(profile)
    if not binding or not entry: raise RuntimeError('Install the supplied animation set for '+profile)
    source=ROOT/binding['sourceModel']
    if hashlib.sha256(source.read_bytes()).hexdigest()!=binding['sourceSha256']:
        raise RuntimeError('Body source differs from installed evidence: '+profile)
    if entry['mesh']!=binding['skeletalMeshPath'] or sorted(set(entry['bindings'].values()))!=sorted(binding['animationPaths']):
        raise RuntimeError('Installed body/animation contracts disagree: '+profile)
    mesh=unreal.load_asset(entry['mesh'])
    clips=[]
    for role,path in entry['bindings'].items():
        sequence=unreal.load_asset(path)
        if not sequence or sequence.get_editor_property('skeleton')!=mesh.skeleton:
            raise RuntimeError('Supplied animation has the wrong skeleton: '+profile+':'+role)
        clips.append(dict(sourceClipName=role,path=path,durationSeconds=unreal.AnimationLibrary.get_sequence_length(sequence)))
    return dict(profileKey=profile,sourceSha256=binding['sourceSha256'],meshes=[dict(path=entry['mesh'])],animations=clips)
