"""Strip FBX animation objects without re-exporting meshes, rigs or materials.

Blender's binary FBX reader/writer preserves each remaining typed property and
array. Both model objects and non-animation connections must match after the
candidate is reopened; the original is replaced only after that comparison.
"""
import hashlib
import json
from pathlib import Path
import sys
from io_scene_fbx import parse_fbx,encode_bin,data_types

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/animation-replacement/fbx-track-removal.json'
ANIMATION={b'AnimationStack',b'AnimationLayer',b'AnimationCurveNode',b'AnimationCurve'}
METHODS={getattr(data_types,k):'add_'+k.lower() for k in ('BOOL','CHAR','INT8','INT16','INT32','INT64','FLOAT32','FLOAT64','BYTES','STRING','INT32_ARRAY','INT64_ARRAY','FLOAT32_ARRAY','FLOAT64_ARRAY','BOOL_ARRAY','BYTE_ARRAY')}

def fingerprint(nodes):
    digest=hashlib.sha256()
    def node(element):
        digest.update(element.id);digest.update(bytes(element.props_type))
        for value in element.props:
            digest.update(value.tobytes() if hasattr(value,'tobytes') else repr(value).encode())
        for child in element.elems:node(child)
    for element in nodes:node(element)
    return digest.hexdigest()

def copy(element):
    result=encode_bin.FBXElem(element.id)
    for kind,value in zip(element.props_type,element.props):getattr(result,METHODS[kind])(value)
    result.elems=[copy(child) for child in element.elems]
    return result

rows=json.loads(OUT.read_text()) if OUT.exists() else []
files=list((ROOT/'authoring').rglob('Warior_Lowpoly_Anim.fbx'))
files += [p for p in (ROOT/'artifacts/unreal/converted').glob('*/*.fbx') if p.parent.name.startswith(('civic_','mire_','npc_','enemy_'))]
for path in files:
    path=path.resolve(); relative=path.relative_to(ROOT).as_posix()
    root,version=parse_fbx.parse(str(path)); objects=next(n for n in root.elems if n.id==b'Objects')
    removed={n.props[0] for n in objects.elems if n.id in ANIMATION}
    if not removed:continue
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    model=[n for n in objects.elems if n.props[0] not in removed]
    connections=next(n for n in root.elems if n.id==b'Connections')
    keep_connections=[n for n in connections.elems if not any(v in removed for v in n.props[1:3])]
    preservation=fingerprint(model+keep_connections)
    output=copy(root)
    for section in output.elems:
        if section.id==b'Objects':section.elems=[copy(n) for n in model]
        elif section.id==b'Connections':section.elems=[copy(n) for n in keep_connections]
        elif section.id==b'Takes':section.elems=[]
        elif section.id==b'Definitions':
            section.elems=[copy(n) for n in next(x for x in root.elems if x.id==b'Definitions').elems if not(n.id==b'ObjectType' and n.props[0] in ANIMATION)]
            for index,n in enumerate(section.elems):
                if n.id==b'Count':
                    count=encode_bin.FBXElem(b'Count');count.add_int32(len(model));section.elems[index]=count
    candidate=OUT.parent/'fbx-strip-candidate.fbx'
    if candidate.exists():raise RuntimeError('Unresolved FBX strip candidate')
    encode_bin.write(str(candidate),output,version)
    check,_=parse_fbx.parse(str(candidate))
    actual_objects=next(n for n in check.elems if n.id==b'Objects').elems
    actual_connections=next(n for n in check.elems if n.id==b'Connections').elems
    if any(n.id in ANIMATION for n in actual_objects) or fingerprint(actual_objects+actual_connections)!=preservation:
        raise RuntimeError('FBX model preservation failed: '+relative)
    candidate.replace(path)
    rows.append(dict(path=relative,beforeSha256=before,afterSha256=hashlib.sha256(path.read_bytes()).hexdigest(),preservationSha256=preservation,removedAnimationObjects=len(removed)))
    OUT.write_text(json.dumps(rows,indent=2)+'\n')
print('WAR_FBX_STRIPPED='+str(len(rows)),flush=True)
