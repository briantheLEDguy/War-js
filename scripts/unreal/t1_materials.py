"""Fingerprint reviewed repository terrain channels for isolated native studies."""
import hashlib
import json
import math
from pathlib import Path
import struct

ZONES = ('sunmeadow_march', 'cinderfen_outskirts')
sha = lambda file: hashlib.sha256(file.read_bytes()).hexdigest()


def terrain_recipe(root, identity):
    if identity not in ZONES:
        raise ValueError('Material studies admit only the first terrain batch')
    region = 'sunmeadow' if identity == ZONES[0] else 'cinderfen'
    directory = root/'authoring/blender'/(region+'-terrain')
    approval_file = directory/'review/visual_review.json'
    render_file = directory/'review/render_receipt.json'
    approval, render = json.loads(approval_file.read_text()), json.loads(render_file.read_text())
    if approval.get('status') != 'approved' or approval['renderReceiptSha256'] != sha(render_file):
        raise ValueError('Regional source review is missing or stale')
    for field in ('buildSha256', 'sourceSha256'):
        if approval[field] != render[field]:
            raise ValueError('Regional review refers to a different terrain build')
    # These two reviewed sectors contain both the substrate and the road channels.
    source = root/'public/assets/models'/('frontier_'+identity+'_terrain_'+('0_0' if region == 'sunmeadow' else '0_1')+'.glb')
    digest = sha(source)
    admitted = [m for view in render['views'] for m in view['models'] if m['model'] == source.name and m['sha256'] == digest]
    if not admitted:
        raise ValueError('Source material sector differs from its reviewed binary')
    data = source.read_bytes()
    if len(data) < 20 or struct.unpack_from('<III', data) != (0x46546c67, 2, len(data)):
        raise ValueError('Invalid source material GLB')
    length, kind = struct.unpack_from('<II', data, 12)
    if kind != 0x4e4f534a or length > len(data)-20:
        raise ValueError('Missing source material JSON')
    doc = json.loads(data[20:20+length])
    reviewed_textures = {t['uri']: t['sha256'] for m in admitted for t in m['externalTextures']}
    def channel(index):
        image = doc['images'][doc['textures'][index]['source']]
        file = (source.parent/image['uri']).resolve()
        if not file.is_relative_to((root/'public/assets/textures'/ (region+'_terrain')).resolve()):
            raise ValueError('Regional texture escapes its reviewed source folder')
        fingerprint = sha(file)
        if reviewed_textures.get(image['uri']) != fingerprint:
            raise ValueError('Regional texture differs from its source review')
        return dict(path=file.relative_to(root.resolve()).as_posix(), sha256=fingerprint)
    layers = {}
    for role, name in [('terrain', region.capitalize()+'_short_grass'), ('roads', region.capitalize()+'_limestone_road')]:
        material = next(m for m in doc['materials'] if m['name'] == name)
        pbr = material['pbrMetallicRoughness']
        layers[role] = dict(sourceMaterial=name, color=channel(pbr['baseColorTexture']['index']),
            normal=channel(material['normalTexture']['index']), tint=pbr.get('baseColorFactor', [1, 1, 1, 1]),
            roughness=pbr['roughnessFactor'], metallic=pbr['metallicFactor'], tileMetres=2,
            macroMetres=[53, 91], macroMinimum=.82 if role == 'terrain' else .94,
            slopeNormalRange=[.78, .95], rockColor=[.24, .21, .15] if region == 'sunmeadow' else [.038, .032, .027],
            softVerge=role == 'roads')
    return dict(zone=identity, source=source.relative_to(root).as_posix(), sourceSha256=digest,
        review=approval_file.relative_to(root).as_posix(), reviewSha256=sha(approval_file),
        renderReceipt=render_file.relative_to(root).as_posix(), renderReceiptSha256=sha(render_file), layers=layers,
        visualApproved=False, collisionChanged=False)


def world_uv(native_position_cm, tile_metres):
    """Source U follows source X; V follows -Z, independent of rectangular UV grids."""
    if not math.isfinite(tile_metres) or not .1 <= tile_metres <= 100:
        raise ValueError('Texture scale must be finite physical metres')
    if len(native_position_cm) != 3 or any(not math.isfinite(n) for n in native_position_cm):
        raise ValueError('Texture coordinates must be finite')
    return [native_position_cm[1]/(tile_metres*100), -native_position_cm[0]/(tile_metres*100)]


def protected_saved(root):
    """New study packages may be added; existing packages and owner documents stay exact."""
    project = root/'unreal/AegisWar'
    files = [p for p in (project/'Content/WorldRebuild').rglob('*') if p.suffix in ('.uasset', '.umap')]
    files.extend((project/'Saved/WorldEdit').rglob('*.json'))
    return {p.relative_to(root).as_posix(): sha(p) for p in files}


def verify_protected(root, hashes):
    for file, digest in hashes.items():
        if sha(root/file) != digest:
            raise RuntimeError('Preserve edited saved content: '+file)
    prefix = 'unreal/AegisWar/Saved/WorldEdit/'
    expected = {file for file in hashes if file.startswith(prefix)}
    actual = {p.relative_to(root).as_posix() for p in (root/prefix).rglob('*.json')}
    if expected != actual:
        raise RuntimeError('Owner document inventory changed')


def same_state(left, right):
    """Quaternion reconstruction permits only sub-micrometre/degree numeric rounding."""
    if isinstance(left, bool) or isinstance(right, bool): return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isfinite(left) and math.isfinite(right) and math.isclose(left, right, rel_tol=0, abs_tol=1e-6)
    if type(left) is not type(right): return False
    if isinstance(left, dict): return left.keys() == right.keys() and all(same_state(left[k], right[k]) for k in left)
    if isinstance(left, list): return len(left) == len(right) and all(same_state(a, b) for a, b in zip(left, right))
    return left == right
