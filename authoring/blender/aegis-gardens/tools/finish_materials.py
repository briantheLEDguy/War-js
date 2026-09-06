"""Canonicalize shared PBR bindings and preserve authored tint in exported glTF."""
import json
import struct
import hashlib
from pathlib import Path
from PIL import Image, ImageOps
WORK=Path(__file__).resolve().parents[1]
COLORS={'bark':(.18,.095,.045),'leaf':(.11,.25,.055),'leaf_light':(.23,.36,.075),
        'stone':(.38,.40,.31),'soil':(.09,.055,.03),'rose':(.48,.045,.09),
        'ivory':(.85,.76,.43),'violet':(.25,.13,.48)}
report=json.loads((WORK/'build-report.json').read_text())
image_paths={}
for asset in report:
    for lod in asset['lods']:
        file=WORK/'runtime'/lod['model']; data=file.read_bytes()
        length=struct.unpack_from('<I',data,12)[0]; doc=json.loads(data[20:20+length]); binary=data[28+length:]
        for im in doc['images']:
            old=im['uri']
            if old not in image_paths:
                source=WORK/'runtime'/old
                # Retain 2K detail, reduce unnecessary precision in neutral grain maps.
                image=ImageOps.posterize(Image.open(source).convert('RGB'),6)
                tmp=WORK/'textures'/('delivery_'+im['name']+'.png'); image.save(tmp,optimize=True)
                name=hashlib.sha256(tmp.read_bytes()).hexdigest()[:20]+'.png'
                target=WORK/'textures/aegis_gardens'/name; target.write_bytes(tmp.read_bytes())
                image_paths[old]='../textures/aegis_gardens/'+name
            im['uri']=image_paths[old]
        textures=[]; indices={}
        for i,texture in enumerate(doc['textures']):
            if texture not in textures:textures.append(texture)
            indices[i]=textures.index(texture)
        for mat in doc['materials']:
            pbr=mat['pbrMetallicRoughness']
            pbr['baseColorFactor']=[*COLORS[mat['name'].removeprefix('aegis_garden_')],1]
            for binding in [mat.get('normalTexture'),pbr.get('baseColorTexture'),pbr.get('metallicRoughnessTexture')]:
                if binding:binding['index']=indices[binding['index']]
        doc['textures']=textures
        raw=json.dumps(doc,separators=(',',':')).encode(); raw+=b' '*((-len(raw))%4)
        file.write_bytes(struct.pack('<III',0x46546c67,2,28+len(raw)+len(binary))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(binary),0x004e4942)+binary)
        lod['bytes']=file.stat().st_size; lod['sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
(WORK/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('Shared delivery texture MB',round(sum((WORK/'runtime'/uri).stat().st_size for uri in set(image_paths.values()))/1e6,2))
