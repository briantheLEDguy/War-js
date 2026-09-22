"""Export the complete, source-approved first pair of authored terrain sectors."""
import json
from pathlib import Path
from world_static import read_glb, digest

ROOT = Path(__file__).resolve().parents[2]
PAIR = ('sunmeadow_march', 'cinderfen_outskirts')


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
        chunks = definition['orvrLayout']['terrain']['chunks']
        if len(chunks) != 16 or len({row['id'] for row in chunks}) != 16:
            raise ValueError('Expected a complete 4x4 terrain set')
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
