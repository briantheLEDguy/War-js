"""Identify leaf slots only from fingerprint-matched reviewed regional source models."""
import copy,hashlib,json,math
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
        result[model.removesuffix('.glb')]=dict(leafSlots=slots,materialCount=len(data['materials']),sourceModel=model,sourceSha256=fingerprint,data=data)
    return result,inputs


def softened_leaf_normals(data,slots):
    """Retain every source attribute except leaf normals; bark/leaf vertex sets must be disjoint."""
    if len(data['triangleMaterials'])*3!=len(data['indices']) or len(data['normals'])!=len(data['positions']):raise ValueError('Invalid canopy source topology')
    leaves=set();bark=set()
    for i,slot in enumerate(data['triangleMaterials']):
        (leaves if slot in slots else bark).update(data['indices'][i*3:i*3+3])
    if not leaves or leaves&bark:raise ValueError('Leaf normals must not alter shared bark vertices')
    centre=[(min(data['positions'][i][a] for i in leaves)+max(data['positions'][i][a] for i in leaves))/2 for a in range(3)]
    result=copy.deepcopy(data)
    for i in leaves:
        radial=[p-c for p,c in zip(data['positions'][i],centre)];length=math.sqrt(sum(v*v for v in radial))
        if not math.isfinite(length):raise ValueError('Nonfinite canopy source')
        if length<1e-6:continue
        n=[v/length*.65+old*.35 for v,old in zip(radial,data['normals'][i])];length=math.sqrt(sum(v*v for v in n))
        if not math.isfinite(length) or length<1e-6:raise ValueError('Invalid canopy shading normal')
        result['normals'][i]=[v/length for v in n]
    return result


def retained_native_canopy(before,after,slots):
    if not before.get('valid') or not after.get('valid'):raise ValueError('Missing committed native canopy geometry')
    a,b=before['data'],after['data']
    for key in ('positions','indices','uvs','uvChannels','triangleMaterials','vertexColors'):
        if a.get(key)!=b.get(key):raise ValueError('Canopy adaptation changed source '+key)
    if len(a['normals'])!=len(b['normals']) or len(a['normals'])!=len(a['indices']):raise ValueError('Native canopy normal inventory differs')
    for i,slot in enumerate(a['triangleMaterials']):
        if slot not in slots and a['normals'][i*3:i*3+3]!=b['normals'][i*3:i*3+3]:raise ValueError('Canopy adaptation changed bark normals')
    return True
