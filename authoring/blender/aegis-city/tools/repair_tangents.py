"""Provide an orthogonal tangent at bevel vertices whose projected UVs collapse.

The normal remains authoritative. Only undefined zero tangents are repaired;
valid authored tangents and handedness remain unchanged.
"""
import json
import struct
import math
import hashlib
import sys
from pathlib import Path
WORK=Path(__file__).resolve().parents[1]
report=json.loads((WORK/'build-report.json').read_text())
requested = next((set(arg.split('=', 1)[1].split(',')) for arg in sys.argv if arg.startswith('--assets=')), set())
for asset in report:
    if requested and asset['kind'] not in requested: continue
    for lod in asset['lods']:
        file=WORK/'runtime'/lod['model'];data=bytearray(file.read_bytes())
        n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n]);binary=28+n
        repaired=0
        def offset(accessor,i):
            a=doc['accessors'][accessor];v=doc['bufferViews'][a['bufferView']]
            return binary+v.get('byteOffset',0)+a.get('byteOffset',0)+i*v.get('byteStride',16 if a['type']=='VEC4' else 12)
        for mesh in doc.get('meshes',[]):
            for primitive in mesh['primitives']:
                attrs=primitive['attributes']
                if 'TANGENT' not in attrs:continue
                for i in range(doc['accessors'][attrs['TANGENT']]['count']):
                    at=offset(attrs['TANGENT'],i);x,y,z,w=struct.unpack_from('<4f',data,at)
                    if x*x+y*y+z*z>.01:continue
                    nx,ny,nz=struct.unpack_from('<3f',data,offset(attrs['NORMAL'],i))
                    tx,ty,tz=(0,nz,-ny) if abs(nx)<.9 else (-nz,0,nx)
                    length=math.sqrt(tx*tx+ty*ty+tz*tz)
                    struct.pack_into('<4f',data,at,tx/length,ty/length,tz/length,1 if w>=0 else -1)
                    repaired+=1
        file.write_bytes(data);lod['sha256']=hashlib.sha256(data).hexdigest();lod['repairedDegenerateTangents']=repaired
(WORK/'build-report.json').write_text(json.dumps(report,indent=2))
