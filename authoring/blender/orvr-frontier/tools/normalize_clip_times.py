"""Normalize exported NLA timelines without touching geometry or motion values.

Blender retains the source strip start in its glTF sampler times by default.
Independent runtime actions must start at zero; their original keyed intervals
and output transforms remain unchanged. This pass records exact provenance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]


def digest(data):return hashlib.sha256(data).hexdigest()


def normalize(data):
    if struct.unpack_from('<III',data)!=(0x46546c67,2,len(data)):raise ValueError('Invalid GLB header')
    json_length,kind=struct.unpack_from('<II',data,12)
    if kind!=0x4e4f534a:raise ValueError('Expected JSON chunk')
    document=json.loads(data[20:20+json_length])
    binary_start=20+json_length
    size,kind=struct.unpack_from('<II',data,binary_start)
    if kind!=0x004e4942:raise ValueError('Expected binary chunk')
    binary=bytearray(data[binary_start+8:binary_start+8+size])
    offsets={};clips=[]
    for clip in document.get('animations',[]):
        inputs=set(sampler['input'] for sampler in clip['samplers'])
        values={}
        for index in inputs:
            accessor=document['accessors'][index];view=document['bufferViews'][accessor['bufferView']]
            if accessor['componentType']!=5126 or accessor['type']!='SCALAR' or 'sparse' in accessor:raise ValueError('Expected dense float sampler input')
            start=view.get('byteOffset',0)+accessor.get('byteOffset',0);stride=view.get('byteStride',4)
            values[index]=[struct.unpack_from('<f',binary,start+i*stride)[0] for i in range(accessor['count'])]
        offset=min(min(row) for row in values.values())
        clips.append({'name':clip['name'],'original_start_seconds':offset,'duration_seconds':max(max(row) for row in values.values())-offset})
        for index in inputs:
            if index in offsets and abs(offsets[index]-offset)>1e-7:raise ValueError('Shared input with incompatible action starts')
            offsets[index]=offset
    output_accessors={sampler['output'] for clip in document.get('animations',[]) for sampler in clip['samplers']}
    if output_accessors.intersection(offsets):raise ValueError('Input accessor also used for motion output')
    for index,offset in offsets.items():
        accessor=document['accessors'][index];view=document['bufferViews'][accessor['bufferView']]
        start=view.get('byteOffset',0)+accessor.get('byteOffset',0);stride=view.get('byteStride',4);values=[]
        for i in range(accessor['count']):
            value=struct.unpack_from('<f',binary,start+i*stride)[0]-offset
            if value<0 and value>-1e-6:value=0
            struct.pack_into('<f',binary,start+i*stride,value);values.append(value)
        accessor['min']=[min(values)];accessor['max']=[max(values)]
    encoded=json.dumps(document,separators=(',',':')).encode();encoded+=b' '*(-len(encoded)%4)
    output=struct.pack('<III',0x46546c67,2,12+8+len(encoded)+8+len(binary))
    output+=struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(binary),0x004e4942)+binary
    return output,clips


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--assets');args=parser.parse_args()
    source=json.loads((ROOT/'source/frontier_collection.json').read_text())
    for asset in args.assets.split(',') if args.assets else source['assets']:
        report_path=ROOT/'review'/f'{asset}_build.json';report=json.loads(report_path.read_text())
        for lod in report['lods']:
            path=ROOT/lod['path'].replace('\\','/');original=path.read_bytes()
            if digest(original)!=lod['sha256']:raise ValueError(f'{path.name}: build hash differs before timing normalization')
            output,clips=normalize(original);path.write_bytes(output)
            lod['timeline_normalization']={'tool':'tools/normalize_clip_times.py','tool_sha256':digest(Path(__file__).read_bytes()),
                'input_glb_sha256':digest(original),'output_glb_sha256':digest(output),'clips':clips}
            lod['sha256']=digest(output);lod['bytes']=len(output)
        report_path.write_text(json.dumps(report,indent=2)+'\n')
        print(f'NORMALIZED_CLIPS {asset}',flush=True)


if __name__=='__main__':main()
