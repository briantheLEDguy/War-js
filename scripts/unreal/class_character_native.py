"""Source-bound class bodies for the native development roster."""
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'artifacts/unreal/class-characters/anatomy-v10'
OUT = ROOT / 'artifacts/unreal/class-character-native/anatomy-v10'
STYLES = {
    'ember_arcanist': 'spell', 'hex_inquisitor': 'two', 'sunfire_templar': 'shield', 'battle_prelate': 'two',
    'stoneguard': 'shield', 'doomseeker': 'two', 'glyphbinder': 'spell', 'siegewright': 'two',
    'blade_savant': 'two', 'pride_warden': 'two', 'aether_sage': 'spell', 'veil_ranger': 'two',
    'dreadsworn': 'shield', 'warped_reaver': 'two', 'void_magister': 'spell', 'ruin_oracle': 'spell',
    'warbrute': 'shield', 'fang_herder': 'two', 'bog_hexer': 'spell', 'cleaver': 'two',
    'blood_dancer': 'two', 'dread_guard': 'shield', 'dusk_weaver': 'spell', 'crimson_acolyte': 'spell',
}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def gltf_joint_positions(path):
    """Read the actual source bind hierarchy in Unreal centimetres (glTF X/Z/Y)."""
    data = Path(path).read_bytes()
    length, kind = struct.unpack_from('<II', data, 12)
    if data[:4] != b'glTF' or kind != 0x4e4f534a:
        raise ValueError('Expected a GLB JSON chunk')
    doc = json.loads(data[20:20+length])
    nodes = doc['nodes']
    parents = {child: parent for parent, node in enumerate(nodes) for child in node.get('children', [])}
    worlds = {}
    def world(index):
        if index in worlds: return worlds[index]
        node = nodes[index]
        if 'matrix' in node:
            m = node['matrix']; local = [[m[c*4+r] for c in range(4)] for r in range(4)]
        else:
            x, y, z, w = node.get('rotation', [0, 0, 0, 1])
            scale = node.get('scale', [1, 1, 1]); position = node.get('translation', [0, 0, 0])
            rotation = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
            local = [[rotation[r][c]*scale[c] for c in range(3)] + [position[r]] for r in range(3)] + [[0, 0, 0, 1]]
        if index in parents:
            parent = world(parents[index])
            local = [[sum(parent[r][k]*local[k][c] for k in range(4)) for c in range(4)] for r in range(4)]
        worlds[index] = local
        return local
    result = {}
    for index in set(joint for skin in doc['skins'] for joint in skin['joints']):
        m = world(index)
        result[nodes[index]['name']] = [m[0][3]*100, m[2][3]*100, m[1][3]*100]
    return result


def roster_config(text, revisions):
    """Replace only the playable roster, preserving world and legacy proof settings."""
    if len(revisions) != 48 or len(set(revisions)) != 48:
        raise ValueError('The main roster requires all 48 unique body revisions')
    if any(not re.fullmatch(r'classbody_[a-z_]+_[mf]_[a-f0-9]{12}', key) for key in revisions):
        raise ValueError('Invalid class-body revision')
    lines = text.splitlines()
    indices = [i for i, line in enumerate(lines) if line.startswith('+PlayableRoster=')]
    if not indices:
        raise ValueError('Missing existing playable roster')
    replacement = ['+PlayableRoster=/Game/Characters/ClassBodies/Visual_' + key + '.Visual_' + key
                   for key in sorted(revisions)]
    lines[indices[0]:indices[0]+1] = replacement
    lines = lines[:indices[0]+len(replacement)] + [line for line in lines[indices[0]+len(replacement):]
                                                    if not line.startswith('+PlayableRoster=')]
    cook = '+DirectoriesToAlwaysCook=(Path="/Game/Characters/ClassBodies")'
    if cook not in lines:
        lines.append(cook)
    return '\n'.join(lines) + '\n'


def selected_bodies(checkpoint, requests, playable):
    if (checkpoint['built'] != 48 or checkpoint['sourcePosePassed'] != 48
            or checkpoint['dentitionPassed'] != 8 or len(checkpoint['characters']) != 48):
        raise ValueError('Expected the complete verified 48-body checkpoint')
    profiles = {(row['race'], row['className'], row['bodyVariant']): row['profileKey'] for row in playable}
    result = {}
    for row in checkpoint['characters']:
        identity = row['identity']
        request = requests[identity]
        if (identity != request['classKey'] + '_' + request['bodyVariant']
                or not re.fullmatch('[a-f0-9]{64}', row['modelSha256'])):
            raise ValueError('Changed class/body identity or invalid source hash')
        expected = identity + ('/dentition-v1/body.glb' if request['race'] == 'greenskin' else '/optimized-v2/body.glb')
        if row['model'] != expected or not row['technicalPassed'] or not row['suppliedPosePassed']:
            raise ValueError('Unverified or unexpected class body: ' + identity)
        key = profiles[(request['race'], request['className'], request['bodyVariant'])]
        if key in result:
            raise ValueError('Duplicate playable identity')
        result[key] = dict(identity=identity, profileKey=key, classId=request['classKey'],
            race=request['race'], bodyVariant=request['bodyVariant'], className=request['className'],
            style=STYLES[request['classKey']], source=row['model'], sourceSha256=row['modelSha256'],
            expectedHeightM=row['heightM'], triangles=row['triangles'])
    if len(result) != 48:
        raise ValueError('Incomplete playable identity set')
    return result
