"""Deduplicate embedded GLB images without changing mesh or material data."""
import hashlib
import json
import struct
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
texture_dir = WORK / 'textures' / 'aegis_gardens'
texture_dir.mkdir(exist_ok=True)
report = json.loads((WORK / 'build-report.json').read_text())
for asset in report:
    for lod in asset['lods']:
        file = WORK / 'runtime' / lod['model']
        data = file.read_bytes()
        length = struct.unpack_from('<I', data, 12)[0]
        doc = json.loads(data[20:20+length])
        binary = data[28+length:]
        image_views = set()
        for image in doc.get('images', []):
            if 'bufferView' not in image:
                continue
            index = image.pop('bufferView'); image_views.add(index)
            view = doc['bufferViews'][index]
            chunk = binary[view.get('byteOffset', 0):view.get('byteOffset', 0)+view['byteLength']]
            name = hashlib.sha256(chunk).hexdigest()[:20] + '.png'
            (texture_dir / name).write_bytes(chunk)
            image['uri'] = '../textures/aegis_gardens/' + name
        if image_views:
            result = bytearray(); views=[]; indices={}
            for i, view in enumerate(doc['bufferViews']):
                if i in image_views:
                    continue
                while len(result) % 4: result.append(0)
                start=view.get('byteOffset',0)
                chunk=binary[start:start+view['byteLength']]
                indices[i]=len(views)
                views.append({**view, 'byteOffset':len(result)})
                result.extend(chunk)
            for accessor in doc.get('accessors',[]):
                if 'bufferView' in accessor: accessor['bufferView']=indices[accessor['bufferView']]
            doc['bufferViews']=views; doc['buffers'][0]['byteLength']=len(result)
            raw=json.dumps(doc,separators=(',',':')).encode()
            raw+=b' '*((-len(raw))%4); result+=b'\0'*((-len(result))%4)
            file.write_bytes(struct.pack('<III',0x46546c67,2,28+len(raw)+len(result))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(result),0x004e4942)+result)
        lod['bytes']=file.stat().st_size
        lod['sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
(WORK/'build-report.json').write_text(json.dumps(report,indent=2))
print('Mesh MB:',round(sum(l['bytes'] for a in report for l in a['lods'])/1e6,2))
print('Shared texture MB:',round(sum(p.stat().st_size for p in texture_dir.glob('*.png'))/1e6,2))

