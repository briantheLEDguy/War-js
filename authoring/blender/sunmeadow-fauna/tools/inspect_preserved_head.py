"""Compare literal exported head attributes and atlas islands to a saved model."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def read_glb(path):
    payload = path.read_bytes()
    length = int.from_bytes(payload[12:16], 'little')
    return json.loads(payload[20:20+length]), payload[28+length:], hashlib.sha256(payload).hexdigest()


def dense(doc, binary, index):
    accessor = doc['accessors'][index]
    view = doc['bufferViews'][accessor['bufferView']]
    if 'sparse' in accessor: raise ValueError('Expected dense base attribute')
    dtype = {5121: '<u1', 5123: '<u2', 5125: '<u4', 5126: '<f4'}[accessor['componentType']]
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[accessor['type']]
    item = np.dtype(dtype).itemsize
    return np.ndarray((accessor['count'], width), dtype=dtype, buffer=binary,
                      offset=view.get('byteOffset', 0)+accessor.get('byteOffset', 0),
                      strides=(view.get('byteStride', width*item), item)).copy()


def head_signature(doc, binary):
    values = []
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            attributes = primitive['attributes']
            positions = dense(doc, binary, attributes['POSITION'])
            selected = (positions[:, 1] > .76)&(positions[:, 2] > .40)
            values.extend(np.concatenate([dense(doc, binary, attributes[name])[selected] for name in ['POSITION', 'NORMAL', 'TANGENT', 'TEXCOORD_0', 'COLOR_0']], axis=1).tolist())
    return np.asarray(sorted(values, key=lambda row: tuple(row[:3]+row[10:12])), dtype=np.float64)


def atlas_signatures(doc, binary):
    results = []
    for image in doc['images']:
        view = doc['bufferViews'][image['bufferView']]
        offset = view.get('byteOffset', 0)
        pixels = np.asarray(Image.open(io.BytesIO(binary[offset:offset+view['byteLength']])).convert('RGBA'))
        height, width, _ = pixels.shape
        # PNG raster is top-down. Source islands0..3 occupy the bottom half,
        # islands4..7 the top half. The new horn exclusively occupies island7.
        signatures = []
        for tile in range(7):
            x = (tile%4)*(width//4); y = (1-tile//4)*(height//2)
            signatures.append(hashlib.sha256(pixels[y:y+height//2, x:x+width//4].tobytes()).hexdigest())
        results.append(signatures)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', default='runtime/frontier_sunmeadow_roe_deer_buck_lod0.glb')
    parser.add_argument('--model', default='review/candidates/buck_differential/frontier_sunmeadow_roe_deer_buck_lod0.glb')
    args = parser.parse_args()
    reference = read_glb(ROOT/args.reference); model = read_glb(ROOT/args.model)
    old = head_signature(*reference[:2]); new = head_signature(*model[:2])
    fields = {'position': (0, 3), 'normal': (3, 6), 'tangent': (6, 10), 'uv': (10, 12), 'color': (12, 16)}
    errors = {name: float(np.max(np.abs(old[:, start:end]-new[:, start:end]))) for name, (start, end) in fields.items()} if old.shape == new.shape else None
    # Blender rounds exported tangent components to four decimal places.
    # Keep that reported precision separate from exact authored attributes.
    authored_equal = bool(errors and all(errors[name] == 0 for name in ['position', 'normal', 'uv', 'color']))
    tangent_roundoff = bool(errors and errors['tangent'] <= .000101)
    geometry_equal = authored_equal and tangent_roundoff
    textures_equal = atlas_signatures(*reference[:2]) == atlas_signatures(*model[:2])
    result = {'reference': args.reference, 'reference_sha256': reference[2], 'model': args.model,
              'model_sha256': model[2], 'reference_head_vertices': len(old), 'model_head_vertices': len(new),
              'head_attribute_maximum_errors': errors, 'head_positions_exact': bool(errors and errors['position'] == 0),
              'head_authored_position_normal_uv_color_exact': authored_equal, 'tangents_within_exporter_decimal_rounding': tangent_roundoff,
              'original_atlas_islands_0_through_6_exact': textures_equal,
              'passed': bool(geometry_equal and textures_equal)}
    (ROOT/'review/buck_preserved_head.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
