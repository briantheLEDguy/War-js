"""Pack 2k master surfaces into three shared 2k delivery atlases.

KHR_texture_transform preserves authored UVs and tangents. Padded tiles prevent
neighbouring material bleed; source masters retain the full-resolution maps.
"""
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image

WORK=Path(__file__).resolve().parents[1]
out=WORK/'textures/aegis_citadel_interiors'
out.mkdir(exist_ok=True)
SIZE=2048
NAMES=['stone','oak','iron','brass','wine']
atlases={name:Image.new('RGB',(SIZE,SIZE),color) for name,color in [
    ('baseColor',(70,70,70)),('normal',(128,128,255)),('metallicRoughness',(255,180,255))]}
transforms={}
for i,name in enumerate(NAMES):
    col,row=i%3,i//3
    x0,x1=round(col*SIZE/3),round((col+1)*SIZE/3)
    y0,y1=row*1024,(row+1)*1024
    width,height=x1-x0,y1-y0
    transforms[name]={'offset':[(x0+2)/SIZE,(y0+2)/SIZE],'scale':[(width-4)/SIZE,(height-4)/SIZE]}
    for channel in atlases:
        source='roughness' if channel=='metallicRoughness' else channel
        image=Image.open(WORK/'textures'/f'{name}_{source}.png').convert('RGB').resize((width,height),Image.Resampling.LANCZOS)
        if channel=='metallicRoughness':
            one=Image.new('L',image.size,255)
            image=Image.merge('RGB',(one,image.getchannel('R'),one))
        atlases[channel].paste(image,(x0,y0))
uris=[]
for channel,image in atlases.items():
    p=out/f'citadel_{channel}.png';image.save(p,optimize=True)
    uris.append('../textures/aegis_citadel_interiors/'+p.name)

report=json.loads((WORK/'build-report.json').read_text())
for asset in report:
    for lod in asset['lods']:
        file=WORK/'runtime'/lod['model'];data=file.read_bytes()
        length=struct.unpack_from('<I',data,12)[0]
        doc=json.loads(data[20:20+length]);binary=data[28+length:]
        image_views={im['bufferView'] for im in doc.get('images',[]) if 'bufferView' in im}
        result=bytearray();views=[];indices={}
        for i,view in enumerate(doc['bufferViews']):
            if i in image_views:continue
            while len(result)%4:result.append(0)
            start=view.get('byteOffset',0)
            indices[i]=len(views)
            views.append({**view,'byteOffset':len(result)})
            result.extend(binary[start:start+view['byteLength']])
        for accessor in doc.get('accessors',[]):
            if 'bufferView' in accessor:accessor['bufferView']=indices[accessor['bufferView']]
        doc['bufferViews']=views;doc['buffers'][0]['byteLength']=len(result)
        doc['images']=[{'uri':uri} for uri in uris]
        doc['samplers']=[{'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497}]
        doc['textures']=[{'sampler':0,'source':i} for i in range(3)]
        doc['extensionsUsed']=list(dict.fromkeys(doc.get('extensionsUsed',[])+['KHR_texture_transform']))
        for mat in doc['materials']:
            kind=mat['name'].replace('aegis_citadel_','')
            if kind not in transforms:continue
            transform=transforms[kind]
            def tex(index,**extra):
                return {'index':index,**extra,'extensions':{'KHR_texture_transform':transform}}
            pbr=mat['pbrMetallicRoughness']
            pbr['baseColorTexture']=tex(0)
            pbr['metallicRoughnessTexture']=tex(2)
            mat['normalTexture']=tex(1,scale=.30)
        raw=json.dumps(doc,separators=(',',':')).encode()
        raw+=b' '*((-len(raw))%4);result+=b'\0'*((-len(result))%4)
        file.write_bytes(struct.pack('<III',0x46546c67,2,28+len(raw)+len(result))+
            struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(result),0x004e4942)+result)
        lod['bytes']=file.stat().st_size;lod['sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
(WORK/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('Mesh MB:',round(sum(l['bytes'] for a in report for l in a['lods'])/1e6,2))
print('Shared runtime atlas MB:',round(sum(p.stat().st_size for p in out.glob('*.png'))/1e6,2))
