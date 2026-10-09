"""Rectangular world-space canopy mask; union blends forest soil without circular hard seams."""
import math,struct,zlib


def forest_floor_mask(bounds,trees,size=1024):
    if not isinstance(size,int) or isinstance(size,bool) or not 16<=size<=1024 or len(trees)>500 or not trees:
        raise ValueError('Invalid bounded forest mask inventory')
    if any(not math.isfinite(bounds[k]) for k in ('minX','maxX','minZ','maxZ')) or bounds['maxX']<=bounds['minX'] or bounds['maxZ']<=bounds['minZ']:
        raise ValueError('Invalid rectangular forest bounds')
    mask=bytearray(size*size);b=bounds
    for tree in trees:
        x,z,r=tree['x'],tree['z'],tree['radius']
        if any(not math.isfinite(v) for v in (x,z,r)) or not .5<=r<=100:raise ValueError('Invalid forest canopy influence')
        # The warped edge can extend beyond the unwarped canopy radius.
        extent=r+1.65
        ix0=max(0,math.floor((x-extent-b['minX'])/(b['maxX']-b['minX'])*size));ix1=min(size,math.ceil((x+extent-b['minX'])/(b['maxX']-b['minX'])*size))
        iy0=max(0,math.floor((b['maxZ']-z-extent)/(b['maxZ']-b['minZ'])*size));iy1=min(size,math.ceil((b['maxZ']-z+extent)/(b['maxZ']-b['minZ'])*size))
        for iy in range(iy0,iy1):
            zz=b['maxZ']-(iy+.5)/size*(b['maxZ']-b['minZ'])
            for ix in range(ix0,ix1):
                xx=b['minX']+(ix+.5)/size*(b['maxX']-b['minX']);warp=(math.sin(xx*.39+math.cos(zz*.27))+.5*math.cos(zz*.61-xx*.23))*1.1
                t=max(0,min(1,(r-math.hypot(xx-x,zz-z)-warp)/(r*.65)));w=round(t*t*(3-2*t)*255)
                index=iy*size+ix;mask[index]=max(mask[index],w)
    return bytes(mask)


def mask_png(mask,size):
    if len(mask)!=size*size:raise ValueError('Forest mask byte extent differs')
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    raw=b''.join(b'\0'+mask[i*size:(i+1)*size] for i in range(size))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,0,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b'')
