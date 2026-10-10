"""Exact admitted scenery channels adapted onto steep ground in private candidates."""
import hashlib
import json
import math
from t1_strata_surface import strata_recipe

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
                geological=dict(**geological_palette(identity),
                    noiseMetres=6.3,fineMetres=.8,bumpHeightCm=[60,8],strata=strata_recipe(identity),macroMinimum=.72,macroMaximum=1.12,fineMinimum=.88),
                reviewInputs={p.relative_to(root).as_posix():sha(p) for p in (source,manifest_file,registry_file,geometry)})


def geological_palette(identity):
    """Regional source mixing tested in native comparisons; lighting and contact geometry stay separate."""
    if identity not in MODELS:raise ValueError('No admitted regional stone palette')
    return dict(baseColor=[.22,.235,.215] if identity=='sunmeadow_march' else [.012,.016,.02],
                sourceMix=.14 if identity=='sunmeadow_march' else .04)


def rock_projection_weights(normal):
    if len(normal)!=3 or any(not math.isfinite(n) or abs(n)>1 for n in normal):
        raise ValueError('Invalid rock projection normal')
    weights=[n**4 for n in normal]; total=sum(weights)
    if total<=0: raise ValueError('Rock projection needs a nonzero normal')
    return [w/total for w in weights]


def geological_color(recipe,projected,macro_noise,fine_noise):
    """Bounded source-derived cliff color without magnifying atlas seams or painted joint normals."""
    g=recipe['geological']
    if len(projected)!=3 or any(not math.isfinite(v) or not 0<=v<=1 for v in [*projected,macro_noise,fine_noise]):
        raise ValueError('Invalid geological color sample')
    macro=g['macroMinimum']+(g['macroMaximum']-g['macroMinimum'])*macro_noise
    fine=g['fineMinimum']+(1-g['fineMinimum'])*fine_noise
    return [(a*(1-g['sourceMix'])+b*g['sourceMix'])*macro*fine for a,b in zip(g['baseColor'],projected)]
