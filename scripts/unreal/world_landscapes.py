"""Export the complete, source-approved first pair of authored terrain sectors."""
import json
import math
from pathlib import Path
from world_static import read_glb, digest

ROOT = Path(__file__).resolve().parents[2]
PAIR = ('sunmeadow_march', 'cinderfen_outskirts')


def validate_chunk_coverage(definition):
    chunks = definition['orvrLayout']['terrain']['chunks']
    bounds = definition.get('spatial', {}).get('bounds') or {
        'minX': -definition['size']/2, 'maxX': definition['size']/2,
        'minZ': -definition['size']/2, 'maxZ': definition['size']/2}
    if not chunks or len({c['id'] for c in chunks}) != len(chunks):
        raise ValueError('Missing or duplicate terrain tiles')
    rectangles=[]
    for chunk in chunks:
        if not all(math.isfinite(chunk[k]) for k in ('x','z','width','depth')) or chunk['width']<=0 or chunk['depth']<=0:
            raise ValueError('Invalid terrain tile dimensions')
        rectangle=(chunk['x']-chunk['width']/2,chunk['x']+chunk['width']/2,chunk['z']-chunk['depth']/2,chunk['z']+chunk['depth']/2)
        if rectangle[0]<bounds['minX']-1e-6 or rectangle[1]>bounds['maxX']+1e-6 or rectangle[2]<bounds['minZ']-1e-6 or rectangle[3]>bounds['maxZ']+1e-6:
            raise ValueError('Terrain tile leaves its content bounds')
        rectangles.append(rectangle)
    xs=sorted({bounds['minX'],bounds['maxX'],*(v for r in rectangles for v in r[:2])})
    zs=sorted({bounds['minZ'],bounds['maxZ'],*(v for r in rectangles for v in r[2:])})
    for left,right in zip(xs,xs[1:]):
        for bottom,top in zip(zs,zs[1:]):
            # Fractional tile thirds can differ at machine precision. Ignore only
            # sub-micrometre partition slivers; real gaps/overlaps still fail.
            if right-left<=1e-6 or top-bottom<=1e-6:
                continue
            x,z=(left+right)/2,(bottom+top)/2
            if sum(a<x<b and c<z<d for a,b,c,d in rectangles)!=1:
                raise ValueError('Terrain coverage has a gap or overlap')
    return chunks


def surface_kind(part):
    if part.get('extras', {}).get('noGroundSupport') is True:
        return 'water'
    if part['name'].endswith('_surface_LOD0'):
        return 'ground'
    if part['name'].endswith('_roads'):
        return 'road'
    raise ValueError('Unknown terrain surface: '+part['name'])


def main():
    directory = ROOT/'artifacts/unreal/world-portals/landscapes'
    directory.mkdir(parents=True, exist_ok=True)
    registry_file = ROOT/'public/assets/models/asset-index.json'
    registry = json.loads(registry_file.read_text())['staticProps']
    zones = []
    for zone in PAIR:
        source = ROOT/'public/assets/maps'/(zone+'.json')
        definition = json.loads(source.read_text())
        chunks = validate_chunk_coverage(definition)
        rows = []
        for chunk in chunks:
            binding = registry[chunk['assetKey']]
            model = ROOT/'public/assets/models'/binding['model']
            if binding.get('approvalState') != 'approved' or not binding.get('runtimeReady') or digest(model) != binding['modelSha256']:
                raise ValueError('Terrain source is not admitted: '+chunk['id'])
            data = read_glb(model)
            for part in data['parts']: part['kind'] = surface_kind(part)
            if not any(part['kind']=='ground' for part in data['parts']): raise ValueError('Missing ground')
            file = directory/(chunk['id']+'.json')
            file.write_text(json.dumps(data, separators=(',', ':')))
            rows.append({**chunk, 'file':file.name, 'sha256':digest(file), 'model':binding['model'], 'sourceSha256':digest(model)})
        zones.append({'id':zone, 'sourceSha256':digest(source), 'chunks':rows})
    result = {'schemaVersion':1, 'registrySha256':digest(registry_file), 'zones':zones, 'visualApproved':False}
    (directory/'plan.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'zones':len(zones), 'chunks':sum(len(z['chunks']) for z in zones), 'nativeBuilt':False}))


if __name__ == '__main__': main()
