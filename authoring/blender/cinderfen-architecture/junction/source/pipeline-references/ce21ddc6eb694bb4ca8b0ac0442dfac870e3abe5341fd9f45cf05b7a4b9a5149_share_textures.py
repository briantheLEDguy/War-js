"""Deduplicate exact exported PBR pixels; preserve every mesh and animation accessor."""
import hashlib
import json
from pathlib import Path
import struct
ROOT=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()


def pack(file):
    data=file.read_bytes();length=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+length]);binary=data[28+length:]
    image_views=set();textures={}
    for image in doc.get('images',[]):
        if 'bufferView' in image:
            index=image.pop('bufferView');image_views.add(index);view=doc['bufferViews'][index]
            pixels=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
            filename=sha(pixels)+'.png';target=ROOT/'textures/cinderfen_architecture'/filename;target.write_bytes(pixels)
            image['uri']='../textures/cinderfen_architecture/'+filename
        target=(file.parent/image['uri']).resolve();textures[image['uri']]=sha(target.read_bytes())
    if not image_views:return None,textures
    result=bytearray();views=[];indices={}
    for index,view in enumerate(doc['bufferViews']):
        if index in image_views:continue
        result.extend(b'\0'*((-len(result))%4));offset=view.get('byteOffset',0)
        indices[index]=len(views);views.append({**view,'byteOffset':len(result)});result.extend(binary[offset:offset+view['byteLength']])
    for accessor in doc.get('accessors',[]):
        if 'bufferView' in accessor:accessor['bufferView']=indices[accessor['bufferView']]
        if 'sparse' in accessor:raise RuntimeError('Sparse accessors require explicit repacking support')
    doc['bufferViews']=views;doc['buffers'][0]['byteLength']=len(result)
    encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);result.extend(b'\0'*((-len(result))%4))
    output=struct.pack('<III',0x46546c67,2,28+len(encoded)+len(result))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(result),0x004e4942)+result
    file.write_bytes(output)
    return {'tool':'tools/share_textures.py','tool_sha256':sha(Path(__file__).read_bytes()),'input_glb_sha256':sha(data),'output_glb_sha256':sha(output),'embedded_bytes':len(data),'externalized_bytes':len(output)},textures


if __name__=='__main__':
    (ROOT/'textures/cinderfen_architecture').mkdir(exist_ok=True)
    for report_path in sorted((ROOT/'review').glob('*_build.json')):
        report=json.loads(report_path.read_text())
        for lod in report['lods']:
            file=ROOT/'runtime'/lod['model'];packing,textures=pack(file)
            if packing:lod['texture_packing']=packing
            lod['external_textures']=textures;lod['bytes']=file.stat().st_size;lod['sha256']=sha(file.read_bytes())
        report_path.write_text(json.dumps(report,indent=2)+'\n')
    print('Shared textures:',len(list((ROOT/'textures/cinderfen_architecture').glob('*.png'))))
