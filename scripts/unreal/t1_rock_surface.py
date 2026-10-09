"""Exact admitted scenery channels adapted onto steep ground in private candidates."""
import hashlib
import json
import math

MODELS = dict(sunmeadow_march='frontier_sunmeadow_limestone_lod0.glb', cinderfen_outskirts='frontier_cinderfen_basalt_outcrop_lod0.glb')
sha=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()


def rock_surface(root, identity):
    if identity not in MODELS:
        raise ValueError('Rock channels require an admitted first-pair region')
    model=MODELS[identity]; base=root/'artifacts/unreal/t1-redesign'
    manifest_file=base/'models.json'; registry_file=root/'public/assets/models/asset-index.json'
    manifest=json.loads(manifest_file.read_text()); registry=json.loads(registry_file.read_text())['staticProps']
    row=manifest['models'][model]; source=root/'public/assets/models'/model
    bindings=[r for r in registry.values() if r.get('model')==model and r.get('approvalState')=='approved' and r.get('runtimeReady') is True]
    if not bindings or sha(source)!=row['sourceSha256'] or not any(r['modelSha256']==row['sourceSha256'] for r in bindings):
        raise ValueError('Rock source is no longer admitted or differs from its review')
    if row['file'] != model.removesuffix('.glb')+'.json':
        raise ValueError('Rock export must retain its admitted basename')
    geometry=base/row['file']
    if sha(geometry)!=row['sha256']:
        raise ValueError('Rock material export changed')
    materials=json.loads(geometry.read_text())['materials']
    if len(materials)!=1 or materials[0].get('alphaMode')!='OPAQUE':
        raise ValueError('Rock layer needs a single reviewed opaque surface')
    textures=materials[0]['textures']
    for key in ('color','normal'):
        channel=textures[key]; file=(root/channel['path']).resolve()
        if not any(file.is_relative_to((root/p).resolve()) for p in ('public/assets','artifacts/unreal/world-portals/static/textures')) or sha(file)!=channel['sha256']:
            raise ValueError('Rock texture escaped or changed from its admitted channel')
    return dict(color=textures['color'],normal=textures['normal'],tileMetres=3.6 if identity=='sunmeadow_march' else 3,
                tint=materials[0]['color'][:3],sourceModel=model,
                reviewInputs={p.relative_to(root).as_posix():sha(p) for p in (source,manifest_file,registry_file,geometry)})


def rock_projection_weights(normal):
    if len(normal)!=3 or any(not math.isfinite(n) or abs(n)>1 for n in normal):
        raise ValueError('Invalid rock projection normal')
    weights=[n**4 for n in normal]; total=sum(weights)
    if total<=0: raise ValueError('Rock projection needs a nonzero normal')
    return [w/total for w in weights]
