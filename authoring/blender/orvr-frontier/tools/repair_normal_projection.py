"""Reject backward bake projections on thin authored surfaces.

A selected-to-active ray can hit an inner shell, yielding a tangent-space normal
behind the evaluated runtime surface. Those texels cannot represent that surface
and cause black patches. Retain all forward high-source detail; use the actual
evaluated mesh normal (neutral tangent normal) only for backward projections.
No topology, UV, color, roughness, metallic, AO or surface positions are changed.
Original maps, exact corrected texel counts and before/after GLB hashes are kept.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]


def digest(data): return hashlib.sha256(data).hexdigest()


def unpack(data):
    magic,version,length=struct.unpack_from('<III',data)
    if magic!=0x46546c67 or version!=2 or length!=len(data): raise ValueError('Invalid GLB header')
    cursor=12; document=None; binary=None
    while cursor<len(data):
        size,kind=struct.unpack_from('<II',data,cursor); cursor+=8
        chunk=data[cursor:cursor+size]; cursor+=size
        if kind==0x4e4f534a: document=json.loads(chunk)
        elif kind==0x004e4942: binary=chunk
        else: raise ValueError('Unsupported extra GLB chunk')
    if document is None or binary is None or len(document.get('buffers',[]))!=1: raise ValueError('One self-contained binary buffer is required')
    return document,binary


def pack(document,binary,replacements):
    chunks=[]; cursor=0
    for index,view in enumerate(document['bufferViews']):
        original=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
        payload=replacements.get(index,original)
        padding=(-cursor)%4
        if padding: chunks.append(b'\0'*padding); cursor+=padding
        view['byteOffset']=cursor; view['byteLength']=len(payload)
        chunks.append(payload); cursor+=len(payload)
    document['buffers'][0]['byteLength']=cursor
    binary_out=b''.join(chunks); binary_out+=b'\0'*((-len(binary_out))%4)
    json_out=json.dumps(document,separators=(',',':'),ensure_ascii=False).encode('utf-8'); json_out+=b' '*((-len(json_out))%4)
    return struct.pack('<III',0x46546c67,2,28+len(json_out)+len(binary_out))+struct.pack('<II',len(json_out),0x4e4f534a)+json_out+struct.pack('<II',len(binary_out),0x004e4942)+binary_out


def repair(asset_id,level,build):
    row=next(lod for lod in build['lods'] if lod['level']==level)
    filepath=ROOT/row['path'].replace('\\','/')
    original=filepath.read_bytes(); original_hash=digest(original); tool_hash=digest(Path(__file__).read_bytes())
    old=row.get('normal_projection_repair')
    if old and old['output_glb_sha256']==original_hash: return old
    tangent=row.get('degenerate_tangent_repair')
    if old and tangent and tangent['input_glb_sha256']==old['output_glb_sha256'] and tangent['output_glb_sha256']==original_hash: return old
    if original_hash!=row['sha256']: raise ValueError(f'Unexpected source GLB hash: {filepath.name}')
    document,binary=unpack(original); replacements={}; maps=[]
    indices={document['textures'][material['normalTexture']['index']]['source'] for material in document.get('materials',[]) if 'normalTexture' in material}
    for index in sorted(indices):
        definition=document['images'][index]; view=document['bufferViews'][definition['bufferView']]
        payload=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
        image=Image.open(io.BytesIO(payload)).convert('RGBA')
        mask=image.getchannel('B').point([255]*126+[0]*130)
        mask=ImageChops.multiply(mask,image.getchannel('A'))
        count=mask.histogram()[255]
        if not definition.get('name','').startswith(f'{asset_id}_lod{level}_') or not definition['name'].endswith('_normal'): raise ValueError('Unexpected normal map name')
        corrected=Image.composite(Image.new('RGBA',image.size,(128,128,255,255)),image,mask)
        output=io.BytesIO(); corrected.save(output,format='PNG',optimize=True); corrected_bytes=output.getvalue()
        map_path=ROOT/'textures'/'baked'/f"{definition['name']}.png"
        original_path=ROOT/'textures'/'baked'/f"{definition['name']}_projection_original.png"
        if original_path.exists() and digest(original_path.read_bytes())!=digest(payload):
            original_path=original_path.with_name(f"{definition['name']}_projection_original_{digest(payload)}.png")
        if not original_path.exists(): original_path.write_bytes(payload)
        if digest(original_path.read_bytes())!=digest(payload): raise ValueError('Original normal-map retention hash mismatch')
        if count:
            replacements[definition['bufferView']]=corrected_bytes
            map_path.write_bytes(corrected_bytes)
        maps.append({'image':definition['name'],'corrected_texels':count,'total_texels':image.width*image.height,'input_image_sha256':digest(payload),
                     'output_image_sha256':digest(corrected_bytes if count else payload),'original_map':str(original_path.relative_to(ROOT)).replace('\\','/')})
    result=pack(document,binary,replacements) if replacements else original
    filepath.write_bytes(result)
    record={'asset_id':asset_id,'level':level,'method':'backward_ray_projection_to_evaluated_mesh_normal','blue_channel_threshold':126,
            'tool_sha256':tool_hash,'input_glb_sha256':original_hash,'output_glb_sha256':digest(result),'maps':maps,
            'note':'Only invalid backward normal projections are reset to the evaluated mesh normal; original maps and all other material channels are retained.'}
    row['sha256']=digest(result); row['bytes']=len(result); row['normal_projection_repair']=record
    return record


def main():
    source=json.loads((ROOT/'source'/'frontier_collection.json').read_text())
    parser=argparse.ArgumentParser(); parser.add_argument('--assets',default=','.join(source['assets'])); args=parser.parse_args()
    output=ROOT/'review'/'normal_projection_repairs.json'
    previous=json.loads(output.read_text()) if output.exists() else {}
    retained=previous.get('records',[]); history=previous.get('history',[])
    records={(row['asset_id'],row['level']):row for row in retained}
    for asset_id in args.assets.split(','):
        path=ROOT/'review'/f'{asset_id}_build.json'; build=json.loads(path.read_text())
        if len(build['lods'])!=3: raise ValueError(f'Complete exports required: {asset_id}')
        for level in (0,1,2):
            row=next(lod for lod in build['lods'] if lod['level']==level)
            if row.get('lod_refinement'):
                print(f'{asset_id} LOD{level}: direct evaluated-material bake needs no projection repair')
                continue
            record=repair(asset_id,level,build)
            old=records.get((asset_id,level))
            if old and old!=record and old not in history: history.append(old)
            records[(asset_id,level)]=record
            print(f"{asset_id} LOD{level}: corrected {sum(row['corrected_texels'] for row in record['maps'])} backward normal texels")
        path.write_text(json.dumps(build,indent=2)+'\n')
    output.write_text(json.dumps({'records':[records[key] for key in sorted(records)],'history':history,'visual_approval':False},indent=2)+'\n')


if __name__=='__main__': main()
