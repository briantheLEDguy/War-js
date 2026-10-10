"""Offline source-derived small terrain folds; route grading and native qualification remain separate."""
import copy
import math

def _finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)

def _surface(surface, edge=False):
    if not isinstance(surface, dict) or not isinstance(surface.get('bounds'), dict):
        raise ValueError('Ground detail requires bounded terrain rasters')
    b=surface['bounds'];nx,nz=surface.get('segmentsX'),surface.get('segmentsZ')
    if (any(not _finite(b.get(k)) or abs(b[k])>10000 for k in ('minX','maxX','minZ','maxZ'))
            or b['minX']>=b['maxX'] or b['minZ']>=b['maxZ']
            or any(isinstance(v,bool) or not isinstance(v,int) or not 1<=v<=512 for v in (nx,nz))
            or not isinstance(surface.get('samples'),list) or len(surface['samples'])!=(nx+1)*(nz+1)
            or any(not _finite(v) or not -100<=v<=350 for v in surface['samples'])):
        raise ValueError('Invalid bounded ground-detail samples')
    if edge and (not _finite(surface.get('edgeFade')) or not 1<=surface['edgeFade']<=min(b['maxX']-b['minX'],b['maxZ']-b['minZ'])/2):
        raise ValueError('Ground detail needs a bounded seam fade')
    return b,nx,nz

def modulate_surface(base, detail, layers, sampling_bounds=None):
    """Return an immutable raster derivative; exact boundary samples and sampling topology are retained."""
    b,nx,nz=_surface(base,True);_,dx,dz=_surface(detail)
    cell=max((b['maxX']-b['minX'])/nx,(b['maxZ']-b['minZ'])/nz)
    active=b if sampling_bounds is None else sampling_bounds
    if (not isinstance(active,dict) or any(not _finite(active.get(k)) for k in ('minX','maxX','minZ','maxZ'))
            or not b['minX']<=active['minX']<active['maxX']<=b['maxX']
            or not b['minZ']<=active['minZ']<active['maxZ']<=b['maxZ']):
        raise ValueError('Invalid contained terrain sampling boundary')
    # The source raster can extend beyond the rendered mesh. Preserve the raw
    # interpolation support near its boundary before fading in the new folds.
    protected_band=0 if sampling_bounds is None else 2*cell
    if min(active['maxX']-active['minX'],active['maxZ']-active['minZ'])<=2*protected_band:
        raise ValueError('Sampling footprint is too small for protected seam support')
    if not isinstance(layers,list) or not 1<=len(layers)<=4:
        raise ValueError('Ground detail requires one to four explicit layers')
    ids=set();prepared=[]
    for layer in layers:
        keys=('wavelengthMetres','amplitudeMetres','angleRadians','offsetX','offsetZ')
        if (not isinstance(layer,dict) or not isinstance(layer.get('id'),str) or not layer['id'] or layer['id'] in ids
                or any(not _finite(layer.get(k)) for k in keys)
                or not max(16,cell*4)<=layer['wavelengthMetres']<=256 or not 0<=layer['amplitudeMetres']<=4
                or abs(layer['angleRadians'])>math.tau or max(abs(layer['offsetX']),abs(layer['offsetZ']))>10000):
            raise ValueError('Invalid bounded ground-detail layer')
        ids.add(layer['id']);prepared.append((layer,math.cos(layer['angleRadians']),math.sin(layer['angleRadians'])))
    if sum(p['amplitudeMetres'] for p in layers)>4:
        raise ValueError('Ground-detail amplitude budget exceeded')
    values=detail['samples'];low,high=min(values),max(values);span=high-low
    if span<1e-6:
        raise ValueError('Source relief must contain variation')
    mean=math.fsum(values)/len(values)

    def sample(u,v):
        # Reflection keeps tile edges continuous without clamping broad regions flat.
        u=1-abs(u%2-1);v=1-abs(v%2-1);fx,fz=u*dx,v*dz
        ix,iz=min(dx-1,int(fx)),min(dz-1,int(fz));a,c=fx-ix,fz-iz
        at=lambda x,z:values[(iz+z)*(dx+1)+ix+x]
        return ((at(0,0)*(1-a)+at(1,0)*a)*(1-c)+(at(0,1)*(1-a)+at(1,1)*a)*c-mean)/span

    result=copy.deepcopy(base);changed=[];maximum=0
    for iz in range(nz+1):
        z=b['minZ']+(b['maxZ']-b['minZ'])*iz/nz
        for ix in range(nx+1):
            index=iz*(nx+1)+ix
            if ix in (0,nx) or iz in (0,nz):
                continue
            x=b['minX']+(b['maxX']-b['minX'])*ix/nx
            distance=min(x-active['minX'],active['maxX']-x,z-active['minZ'],active['maxZ']-z)-protected_band
            if distance<=0:
                continue
            t=min(1,distance/base['edgeFade']);fade=t*t*(3-2*t)
            delta=math.fsum(p['amplitudeMetres']*sample((x*c+z*s+p['offsetX'])/p['wavelengthMetres'],(-x*s+z*c+p['offsetZ'])/p['wavelengthMetres']) for p,c,s in prepared)*fade
            height=base['samples'][index]+delta
            if not -100<=height<=350:
                raise ValueError('Ground detail exceeds admitted terrain heights')
            maximum=max(maximum,abs(delta))
            if delta:
                result['samples'][index]=height;changed.append(index)
    return result,dict(changedVertices=len(changed),maximumDeltaMetres=maximum,boundarySamplesPreserved=True,
                       samplingTopologyPreserved=True,protectedSamplingBounds=copy.deepcopy(active),
                       protectedSamplingBorderMetres=protected_band,requiresRouteGrading=True,sourceOnly=True,
                       nativeIntegrated=False,walkingAccepted=False,appearanceApproved=False)
