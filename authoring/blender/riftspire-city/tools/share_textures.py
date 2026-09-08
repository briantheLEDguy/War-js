"""Deduplicate embedded GLB images without changing mesh or material data."""
import hashlib
import json
import struct
import sys
import io
from PIL import Image
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
texture_dir = WORK / 'textures' / 'riftspire_city'
texture_dir.mkdir(exist_ok=True)
report_path = WORK / next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report=')), 'build-report.json')
original = json.loads(report_path.read_text())
report = original if isinstance(original,list) else [original]
requested = next((set(arg.split('=', 1)[1].split(',')) for arg in sys.argv if arg.startswith('--assets=')), set())
for asset in report:
    if requested and asset['kind'] not in requested: continue
    for lod in asset['lods']:
        file = WORK / 'runtime' / lod['model']
        data = file.read_bytes()
        length = struct.unpack_from('<I', data, 12)[0]
        doc = json.loads(data[20:20+length])
        binary = data[28+length:]
        image_views = set()
        changed = False
        for image in doc.get('images', []):
            if 'bufferView' not in image:
                if 'uri' in image:
                    source=WORK/'runtime'/image['uri'];chunk=source.read_bytes();decoded=Image.open(io.BytesIO(chunk))
                    if decoded.size != (2048,2048) or decoded.format != 'PNG':
                        stream=io.BytesIO();decoded.resize((2048,2048),Image.Resampling.LANCZOS).save(stream,format='PNG');chunk=stream.getvalue()
                        name=hashlib.sha256(chunk).hexdigest()[:20]+'.png';(texture_dir/name).write_bytes(chunk)
                        image['uri']='../textures/riftspire_city/'+name;image['mimeType']='image/png';changed=True
                continue
            index = image.pop('bufferView'); image_views.add(index)
            view = doc['bufferViews'][index]
            chunk = binary[view.get('byteOffset', 0):view.get('byteOffset', 0)+view['byteLength']]
            decoded=Image.open(io.BytesIO(chunk))
            if decoded.size != (2048,2048) or decoded.format != 'PNG':
                stream=io.BytesIO();decoded.resize((2048,2048),Image.Resampling.LANCZOS).save(stream,format='PNG');chunk=stream.getvalue()
            name = hashlib.sha256(chunk).hexdigest()[:20] + '.png'
            (texture_dir / name).write_bytes(chunk)
            image['uri'] = '../textures/riftspire_city/' + name
            image['mimeType']='image/png'
        if image_views or changed:
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
report_path.write_text(json.dumps(report if isinstance(original,list) else report[0],indent=2))
print('Mesh MB:',round(sum(l['bytes'] for a in report for l in a['lods'])/1e6,2))
print('Shared texture MB:',round(sum(p.stat().st_size for p in texture_dir.glob('*.png'))/1e6,2))

