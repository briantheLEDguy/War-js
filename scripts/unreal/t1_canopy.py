"""Identify leaf slots only from fingerprint-matched reviewed regional source models."""
import hashlib,json
from world_static import read_glb,combine_parts

MODELS=('frontier_sunmeadow_oak_hedgerow_lod0.glb','frontier_sunmeadow_oak_pasture_lod0.glb','frontier_sunmeadow_hawthorn_lod0.glb')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def leaf_slots(materials):
    slots=[i for i,r in enumerate(materials) if r.get('doubleSided') is True and r.get('alphaMode')=='OPAQUE' and r.get('textures',{}).get('color')]
    if len(materials)!=2 or slots!=[1] or materials[0].get('doubleSided') is not False:
        raise ValueError('Reviewed canopy must retain its distinct bark and opaque double-sided leaf slots')
    return slots


def canopy_sources(root):
    registry=root/'public/assets/models/asset-index.json';rows=json.loads(registry.read_text())['staticProps'].values();inputs={registry.relative_to(root).as_posix():sha(registry)};result={}
    for model in MODELS:
        file=root/'public/assets/models'/model;fingerprint=sha(file)
        if not any(r.get('model')==model and r.get('runtimeReady') is True and r.get('approvalState')=='approved' and r.get('modelSha256')==fingerprint for r in rows):
            raise ValueError('Canopy source is not currently admitted: '+model)
        data=combine_parts(read_glb(file)['parts']);slots=leaf_slots(data['materials'])
        inputs[file.relative_to(root).as_posix()]=fingerprint
        for material in data['materials']:
            for channel in material.get('textures',{}).values():
                if sha(root/channel['path'])!=channel['sha256']:raise ValueError('Canopy source texture changed')
                inputs[channel['path']]=channel['sha256']
        result[model.removesuffix('.glb')]=dict(leafSlots=slots,materialCount=len(data['materials']),sourceModel=model,sourceSha256=fingerprint)
    return result,inputs
