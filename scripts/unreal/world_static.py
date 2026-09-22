"""Strict source GLB surface export for development world construction; never grants native art approval."""
import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/unreal/world-portals/static'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rotate(v, q):
    x, y, z, w = q
    tx, ty, tz = 2 * (y*v[2]-z*v[1]), 2 * (z*v[0]-x*v[2]), 2 * (x*v[1]-y*v[0])
    return [v[0]+w*tx+y*tz-z*ty, v[1]+w*ty+z*tx-x*tz, v[2]+w*tz+x*ty-y*tx]


def read_glb(source):
    data = source.read_bytes()
    if len(data) < 28 or struct.unpack_from('<III', data) != (0x46546c67, 2, len(data)):
        raise ValueError('Invalid GLB header')
    length, kind = struct.unpack_from('<II', data, 12)
    if kind != 0x4e4f534a: raise ValueError('Missing GLB JSON')
    doc = json.loads(data[20:20+length])
    size, kind = struct.unpack_from('<II', data, 20+length)
    blob = data[28+length:28+length+size]
    if kind != 0x004e4942 or len(blob) != size: raise ValueError('Missing GLB binary')
    if doc.get('skins') or doc.get('animations') or not doc.get('nodes'):
        raise ValueError('Only static source scenes are supported')
    nodes = doc['nodes']
    if doc.get('scenes') and set(doc['scenes'][doc.get('scene',0)]['nodes']) != set(range(len(nodes))):
        raise ValueError('Unsupported source hierarchy')
    for node in nodes:
        if node.get('children') or node.get('matrix') or 'mesh' not in node:
            raise ValueError('Unsupported source hierarchy')
        translation, rotation, scale = node.get('translation', [0,0,0]), node.get('rotation', [0,0,0,1]), node.get('scale', [1,1,1])
        if any(not math.isfinite(x) for x in translation+rotation+scale) or min(scale) <= 0 or abs(sum(x*x for x in rotation)-1) > 1e-5:
            raise ValueError('Invalid source transform')

    def accessor(index, allow_normalized=False):
        a = doc['accessors'][index]
        if a.get('sparse') or (a.get('normalized') and not allow_normalized): raise ValueError('Unsupported compressed/normalized accessor')
        view = doc['bufferViews'][a['bufferView']]
        if view.get('buffer', 0) != 0: raise ValueError('External buffer')
        fmt, width = {5126:('f',4),5125:('I',4),5123:('H',2),5121:('B',1)}[a['componentType']]
        dimensions = {'SCALAR':1, 'VEC2':2, 'VEC3':3, 'VEC4':4}[a['type']]
        stride = view.get('byteStride', dimensions*width)
        offset = a.get('byteOffset',0)
        if a['count'] < 1 or stride < dimensions*width or offset+(a['count']-1)*stride+dimensions*width > view['byteLength']:
            raise ValueError('Accessor exceeds buffer view')
        start = view.get('byteOffset',0)+offset
        values = [struct.unpack_from('<'+fmt*dimensions, blob, start+i*stride) for i in range(a['count'])]
        if a.get('normalized'):
            divisor = {5121:255, 5123:65535}.get(a['componentType'])
            if not divisor: raise ValueError('Unsupported normalized color format')
            values = [tuple(value/divisor for value in row) for row in values]
        if any(not math.isfinite(x) for row in values for x in row): raise ValueError('Nonfinite vertex data')
        return values

    parts = []
    for number, (node, primitive) in enumerate((node, primitive) for node in nodes for primitive in doc['meshes'][node['mesh']]['primitives']):
        translation, rotation, scale = node.get('translation', [0,0,0]), node.get('rotation', [0,0,0,1]), node.get('scale', [1,1,1])
        if primitive.get('mode',4) != 4 or primitive.get('extensions'):
            raise ValueError('Unsupported mesh topology/compression')
        attributes = primitive['attributes']
        positions, normals = accessor(attributes['POSITION']), accessor(attributes['NORMAL'])
        uvs = accessor(attributes['TEXCOORD_0']) if 'TEXCOORD_0' in attributes else [(0,0)]*len(positions)
        colors = accessor(attributes['COLOR_0'], True) if 'COLOR_0' in attributes else None
        if colors is not None:
            if len(colors) != len(positions) or any(len(c) not in (3,4) or any(v < 0 or v > 1 for v in c) for c in colors):
                raise ValueError('Invalid vertex colors')
            colors = [list(c) if len(c)==4 else [*c,1] for c in colors]
        if len(positions) != len(normals) or len(positions) != len(uvs): raise ValueError('Mismatched attributes')
        converted, normal_vectors = [], []
        for p, n in zip(positions,normals):
            p = rotate([p[i]*scale[i] for i in range(3)], rotation)
            p = [p[i]+translation[i] for i in range(3)]
            n = rotate([n[i]/scale[i] for i in range(3)], rotation)
            magnitude = math.sqrt(sum(x*x for x in n))
            if magnitude < 0.01: raise ValueError('Invalid source normal')
            converted.append([p[2]*100,p[0]*100,p[1]*100])
            normal_vectors.append([n[2]/magnitude,n[0]/magnitude,n[1]/magnitude])
        raw = [row[0] for row in accessor(primitive['indices'])] if 'indices' in primitive else list(range(len(positions)))
        if len(raw)%3 or any(i < 0 or i >= len(positions) for i in raw): raise ValueError('Invalid mesh indices')
        indices, removed = [], 0
        for i in range(0,len(raw),3):
            a,b,c = [converted[index] for index in raw[i:i+3]]
            u,v = [b[j]-a[j] for j in range(3)], [c[j]-a[j] for j in range(3)]
            cross = [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            # Match UE FVector::IsNearlyZero's per-component geometric tolerance.
            if max(abs(x) for x in cross) <= 1e-4: removed += 1; continue
            indices.extend([raw[i],raw[i+2],raw[i+1]])
        if not indices: raise ValueError('Empty mesh surface')
        material = doc.get('materials',[])[primitive['material']]
        textures = {}
        pbr = material.get('pbrMetallicRoughness',{})
        for name, definition in [('color',pbr.get('baseColorTexture')), ('normal',material.get('normalTexture'))]:
            if not definition: continue
            image = doc['images'][doc['textures'][definition['index']]['source']]
            if 'uri' in image:
                image_path = (source.parent/image['uri']).resolve()
                if not image_path.is_relative_to((ROOT/'public/assets').resolve()): raise ValueError('Texture escapes source asset root')
            else:
                view = doc['bufferViews'][image['bufferView']]
                if image.get('mimeType') != 'image/png': raise ValueError('Unsupported embedded texture')
                payload = blob[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
                image_path = OUT/'textures'/(hashlib.sha256(payload).hexdigest()+'.png')
                image_path.parent.mkdir(parents=True,exist_ok=True); image_path.write_bytes(payload)
            textures[name] = {'path':image_path.relative_to(ROOT).as_posix(),'sha256':digest(image_path)}
        parts.append({'index':number,'name':node.get('name',''),'extras':node.get('extras',{}),
            'positions':converted,'normals':normal_vectors,'uvs':uvs,'indices':indices, 'colors':colors,
            'removedDegenerateTriangles':removed,'material':{'textures':textures,'color':pbr.get('baseColorFactor',[1,1,1,1]),
                'roughness':pbr.get('roughnessFactor',1),'metallic':pbr.get('metallicFactor',0),
                'doubleSided':material.get('doubleSided',False),'alphaMode':material.get('alphaMode','OPAQUE'),
                'alphaCutoff':material.get('alphaCutoff',0.5),'vertexColors':colors is not None}})
    return {'model':source.name,'sourceSha256':digest(source),'parts':parts,'nativeArtApproved':False}


def combine_parts(parts):
    """Keep source coordinates, vertex colors and ordered material sections intact."""
    if not parts: raise ValueError('Cannot combine an empty source')
    combined = {key:[] for key in ('positions','normals','uvs','indices','colors','triangleMaterials','materials')}
    for slot, part in enumerate(parts):
        offset = len(combined['positions'])
        if len(part['indices']) % 3 or any(i < 0 or i >= len(part['positions']) for i in part['indices']):
            raise ValueError('Invalid source part topology')
        for key in ('positions','normals','uvs'): combined[key].extend(part[key])
        combined['colors'].extend(part.get('colors') or [[1,1,1,1] for _ in part['positions']])
        combined['indices'].extend(offset+i for i in part['indices'])
        combined['triangleMaterials'].extend([slot]*(len(part['indices'])//3))
        combined['materials'].append(part['material'])
    return combined


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = json.loads((OUT.parent/'plan.json').read_text())
    registry = json.loads((ROOT/'public/assets/models/asset-index.json').read_text())['staticProps']
    models, placements, pending = {}, [], []
    for zone in plan['zones']:
        if zone['id'] == 'aegis_capital': continue
        source = json.loads((ROOT/'public/assets/maps'/(zone['id']+'.json')).read_text())
        for prop in source.get('props',[]):
            binding = registry.get(prop.get('assetKey',prop.get('kind')))
            model = prop.get('model') or (binding or {}).get('model')
            reason = None
            if prop.get('interaction') or prop.get('interactionId') or prop.get('kind') == 'riftspire_lift': reason = 'interactive-prop-not-yet-native'
            elif not binding or binding.get('runtimeReady') is not True or binding.get('approvalState') != 'approved': reason = 'no-approved-source-binding'
            elif model != binding.get('model'): reason = 'source-binding-mismatch'
            elif digest(ROOT/'public/assets/models'/model) != binding['modelSha256']: reason = 'source-hash-mismatch'
            if not reason and model not in models:
                try:
                    asset = read_glb(ROOT/'public/assets/models'/model)
                    filename = Path(model).stem+'.json'
                    file = OUT/filename
                    file.write_text(json.dumps(asset,separators=(',',':')))
                    models[model] = {'file':filename,'sha256':digest(file),'parts':len(asset['parts'])}
                except (ValueError,KeyError,IndexError,struct.error) as error:
                    models[model] = {'error':str(error)}
            if not reason and models[model].get('error'): reason = models[model]['error']
            if reason:
                pending.append({'zone':zone['id'],'id':prop['id'],'reason':reason})
            else:
                placements.append({'zone':zone['id'],'id':prop['id'],'model':model,'source':prop})
    result = {'schemaVersion':1,'planSha256':digest(OUT.parent/'plan.json'),'registrySha256':digest(ROOT/'public/assets/models/asset-index.json'),
        'models':models,'placements':placements,'pending':pending,'nativeArtApproved':False}
    (OUT/'plan.json').write_text(json.dumps(result,separators=(',',':')))
    print(json.dumps({'models':len(models),'placements':len(placements),'pending':len(pending),'failedModels':[name for name,row in models.items() if 'error' in row]}))


if __name__ == '__main__': main()
