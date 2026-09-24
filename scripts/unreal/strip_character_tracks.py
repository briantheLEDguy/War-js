"""Remove GLB character tracks, including their binary payloads, losslessly.

Geometry, materials, skin weights, inverse bind matrices and rest nodes are
compared independently of buffer offsets before any file is replaced. Mechanical
props have no skin and are outside this operation. No backup binaries are made;
the receipt retains hashes and removed clip names, and Git retains history.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct

JSON, BIN = 0x4E4F534A, 0x004E4942


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decode(data):
    if len(data) < 20 or struct.unpack_from('<4sII', data) != (b'glTF', 2, len(data)):
        raise ValueError('Invalid GLB')
    chunks, offset = {}, 12
    while offset < len(data):
        size, kind = struct.unpack_from('<II', data, offset)
        offset += 8
        if kind in chunks or offset + size > len(data):
            raise ValueError('Invalid GLB chunk')
        chunks[kind] = data[offset:offset + size]
        offset += size
    if set(chunks) - {JSON, BIN}:
        raise ValueError('Unknown GLB chunk; preservation needs explicit support')
    document = json.loads(chunks[JSON])
    if any('uri' in b for b in document.get('buffers', [])) or len(document.get('buffers', [])) > 1:
        raise ValueError('Only self-contained GLB buffers are supported')
    return document, chunks.get(BIN, b'')


def encode(document, binary):
    data = json.dumps(document, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    data += b' ' * (-len(data) % 4)
    chunks = struct.pack('<II', len(data), JSON) + data
    if binary:
        binary += b'\0' * (-len(binary) % 4)
        chunks += struct.pack('<II', len(binary), BIN) + binary
    return struct.pack('<4sII', b'glTF', 2, len(chunks) + 12) + chunks


def geometry_references(document):
    """Yield mutable accessor references in every supported non-animation use."""
    for mesh in document.get('meshes', []):
        for primitive in mesh['primitives']:
            if primitive.get('extensions'):
                raise ValueError('Compressed/extended geometry needs explicit preservation support')
            if 'indices' in primitive:
                yield primitive, 'indices'
            for attributes in [primitive['attributes'], *primitive.get('targets', [])]:
                for key in attributes:
                    yield attributes, key
    for skin in document.get('skins', []):
        if 'inverseBindMatrices' in skin:
            yield skin, 'inverseBindMatrices'
    for node in document.get('nodes', []):
        if node.get('extensions'):
            raise ValueError('Extended nodes need explicit preservation support')


def views_in_accessor(accessor):
    if 'bufferView' in accessor:
        yield accessor, 'bufferView'
    if 'sparse' in accessor:
        for kind in ('indices', 'values'):
            yield accessor['sparse'][kind], 'bufferView'


def preservation_signature(document, binary):
    """Hash all non-animation semantics and the exact referenced payload bytes."""
    result = deepcopy(document)
    result.pop('animations', None)
    def view_value(index):
        view = deepcopy(document['bufferViews'][index])
        start = view.pop('byteOffset', 0)
        if view.pop('buffer', 0) != 0:
            raise ValueError('External buffer')
        payload = binary[start:start + view['byteLength']]
        if len(payload) != view['byteLength']:
            raise ValueError('Buffer view exceeds its buffer')
        return dict(view=view, payloadSha256=digest(payload))
    def accessor_value(index):
        accessor = deepcopy(document['accessors'][index])
        for owner, key in views_in_accessor(accessor):
            owner[key] = view_value(owner[key])
        return accessor
    for owner, key in geometry_references(result):
        owner[key] = accessor_value(owner[key])
    for image in result.get('images', []):
        if 'bufferView' in image:
            image['bufferView'] = view_value(image['bufferView'])
    for key in ('accessors', 'bufferViews', 'buffers'):
        result.pop(key, None)
    return digest(json.dumps(result, sort_keys=True, separators=(',', ':')).encode())


def strip(data):
    original, binary = decode(data)
    if not original.get('animations') or not original.get('skins'):
        return data, None
    before = preservation_signature(original, binary)
    document = deepcopy(original)
    animated = {s[k] for a in document['animations'] for s in a['samplers'] for k in ('input', 'output')}
    geometry = {owner[key] for owner, key in geometry_references(document)}
    removed_accessors = animated - geometry
    retained_accessors = [i for i in range(len(document.get('accessors', []))) if i not in removed_accessors]
    access_map = {old: new for new, old in enumerate(retained_accessors)}
    for owner, key in geometry_references(document):
        owner[key] = access_map[owner[key]]
    candidate_views = {owner[key] for i in removed_accessors for owner, key in views_in_accessor(document['accessors'][i])}
    document['accessors'] = [document['accessors'][i] for i in retained_accessors]
    view_refs = [(owner, key) for accessor in document['accessors'] for owner, key in views_in_accessor(accessor)]
    view_refs += [(im, 'bufferView') for im in document.get('images', []) if 'bufferView' in im]
    used_views = {owner[key] for owner, key in view_refs}
    removed_views = candidate_views - used_views
    # Animation and geometry may legally share an accessor. Partial/interleaved
    # sharing is rejected instead of silently retaining animation-only payload.
    if candidate_views & used_views and any(i in removed_accessors and any(owner[key] in used_views for owner,key in views_in_accessor(original['accessors'][i])) for i in animated):
        raise ValueError('Animation-only accessor shares a geometry buffer view')
    retained_views = [i for i in range(len(document.get('bufferViews', []))) if i not in removed_views]
    view_map = {old: new for new, old in enumerate(retained_views)}
    for owner, key in view_refs:
        owner[key] = view_map[owner[key]]
    packed, views = bytearray(), []
    for index in retained_views:
        view = document['bufferViews'][index]
        start, length = view.get('byteOffset', 0), view['byteLength']
        packed += b'\0' * (-len(packed) % 4)
        view['byteOffset'] = len(packed)
        packed += binary[start:start + length]
        views.append(view)
    document['bufferViews'] = views
    if document.get('buffers'):
        document['buffers'][0]['byteLength'] = len(packed)
    names = [a.get('name', '') for a in document.pop('animations')]
    output = encode(document, bytes(packed))
    after_document, after_binary = decode(output)
    after = preservation_signature(after_document, after_binary)
    if before != after:
        raise ValueError('Non-animation content changed; refusing replacement')
    return output, dict(beforeSha256=digest(data), afterSha256=digest(output),
                        preservationSha256=before, removedClips=names,
                        removedAccessors=len(removed_accessors), removedBufferViews=len(removed_views),
                        removedBytes=len(data)-len(output))


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    receipt = root/'artifacts/unreal/animation-replacement'/('source-track-removal.json' if args.apply else 'source-track-plan.json')
    rows = json.loads(receipt.read_text()) if receipt.exists() else []
    for folder in ('public/assets/models', 'authoring', 'artifacts'):
        for file in (root/folder).rglob('*.glb'):
            path = file.resolve()
            path.relative_to(root)
            data = path.read_bytes()
            output, record = strip(data)
            if record:
                record['path'] = path.relative_to(root).as_posix()
                if args.apply:
                    temporary = path.with_suffix('.glb.track-strip-tmp')
                    temporary.write_bytes(output)
                    temporary.replace(path)
                rows.append(record)
                receipt.parent.mkdir(parents=True, exist_ok=True)
                receipt.write_text(json.dumps(rows, indent=2)+'\n')
    print(f'{len(rows)} character GLBs checked; apply={args.apply}')


if __name__ == '__main__':
    main()
