"""Fit existing forged ornaments to the evaluated bowl; preserve the published package."""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

DRAFT = Path(__file__).resolve().parents[1]
ORIGINAL = DRAFT.parent
sys.path.insert(0, str(ORIGINAL / 'tools'))
import build_collection as backend

KEY = 'frontier_oil_cauldron'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prepare():
    for directory in ['source', 'review', 'runtime', 'masters', 'textures/source', 'textures/baked', 'tools']:
        (DRAFT / directory).mkdir(parents=True, exist_ok=True)
    source = json.loads((ORIGINAL / 'source/frontier_collection.json').read_text())
    source['assets'] = {KEY: source['assets'][KEY]}
    parts = {item['part'] for item in source['assets'][KEY]['instances'] if 'part' in item}
    source['parts'] = {key: value for key, value in source['parts'].items() if key in parts}
    materials = {part['material'] for part in source['parts'].values()}
    source['materials'] = {key: value for key, value in source['materials'].items() if key in materials}
    source['surface_fit'] = {'tool_sha256': sha(__file__), 'source_sha256': sha(ORIGINAL / 'source/frontier_collection.json'),
        'policy': 'Project existing washer perimeter cages onto each finished bowl, retaining raised clinch relief and UVs. No replacement primitives.'}
    (DRAFT / 'source/frontier_collection.json').write_text(json.dumps(source, indent=2) + '\n')
    for name in materials:
        for source_file in (ORIGINAL / 'textures/source').glob(name + '_*.png'):
            shutil.copyfile(source_file, DRAFT / 'textures/source' / source_file.name)
    for relative in ['textures/paint_records.json', 'tools/mechanical_animation.py']:
        shutil.copyfile(ORIGINAL / relative, DRAFT / relative)
    backend.ROOT = DRAFT
    backend.SOURCE = source
    backend.SOURCE_PATH = DRAFT / 'source/frontier_collection.json'


raw_setup = backend.setup_asset
fit_records = []


def fitted_setup(asset_id, lod=0):
    collection, objects = raw_setup(asset_id, lod)
    bowl = next(obj for obj in objects if obj.get('authored_part') == 'oil_cauldron')
    # The retained distance finisher uses this reduction. Fit to its final shell,
    # so the subsequent finishing pass cannot move the bowl away from a washer.
    if lod == 2:
        for modifier in bowl.modifiers:
            if modifier.type == 'DECIMATE': modifier.ratio = .68
            elif modifier.type == 'BEVEL': modifier.segments = max(2, modifier.segments)
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = bowl.evaluated_get(graph)
    mesh = evaluated.to_mesh()
    surface = BVHTree.FromPolygons([bowl.matrix_world @ vertex.co for vertex in mesh.vertices],
        [list(p.vertices) for p in mesh.polygons])
    evaluated.to_mesh_clear()
    ornaments = [obj for obj in objects if obj.get('authored_part') == 'forged_rosette']
    record = {'lod': lod, 'ornaments': []}
    for obj in ornaments:
        inverse = obj.matrix_world.inverted()
        samples = []
        for vertex in obj.data.vertices:
            old = obj.matrix_world @ vertex.co
            hit, normal, face, distance = surface.ray_cast(Vector((old.x, -2, old.z)), Vector((0, 1, 0)), 4)
            if hit is None or normal.y >= 0:
                raise ValueError(f'No outward bowl surface under {obj.name}/{vertex.index}')
            relief = max(0, -vertex.co.y - .022) * obj.scale.y
            seated = Vector((old.x, hit.y - .001 - relief, old.z))
            vertex.co = inverse @ seated
            samples.append({'vertex': vertex.index, 'previous_gap_m': hit.y - old.y,
                'fitted_relief_m': hit.y - seated.y, 'move_m': (old - seated).length})
        obj.data.update()
        obj['surface_fit'] = 'Perimeter seated 1 mm outside bowl before 5.85 mm closed washer thickness; clinch relief retained.'
        record['ornaments'].append({'name': obj.name, 'samples': samples})
    if len(ornaments) != 6:
        raise ValueError('Expected the six original forged washers.')
    fit_records.append(record)
    bpy.context.view_layer.update()
    return collection, objects


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    prepare()
    if not args.build:
        for mode in ['before', 'fitted']:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            collection, objects = (raw_setup if mode == 'before' else fitted_setup)(KEY, 0)
            backend.set_view(objects, DRAFT / 'review' / (mode + '_source.png'))
        bpy.ops.wm.save_as_mainfile(filepath=str(DRAFT / 'masters/fitted_source.blend'))
    else:
        backend.setup_asset = fitted_setup
        backend.build(KEY, SimpleNamespace(source_render=False, lods=[0, 1, 2]))
        import refine_mechanism_lod2 as distance_finish
        distance_finish.ROOT = DRAFT
        distance_finish.refine(KEY)
    (DRAFT / 'review/fit-samples.json').write_text(json.dumps({'tool_sha256': sha(__file__), 'records': fit_records}, indent=2) + '\n')


if __name__ == '__main__':
    main()
