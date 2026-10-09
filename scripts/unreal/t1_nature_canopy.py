"""Private nature-canopy root/scale contract; replacement geometry needs fresh traversal acceptance."""
import math
MAPPING={'frontier_sunmeadow_oak_hedgerow_lod0':'SM_White_Oak_01','frontier_sunmeadow_oak_pasture_lod0':'SM_White_Oak_02','frontier_sunmeadow_hawthorn_lod0':'SM_White_Oak_Young_01'}


def canopy_transform(source_bounds,target_bounds,scale,location,rotation):
    vectors=[*source_bounds,*target_bounds,scale,location,rotation]
    if any(len(v)!=3 or any(isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n) for n in v) for v in vectors):raise ValueError('Invalid canopy transform inputs')
    if any(v<=0 for v in source_bounds[1]+target_bounds[1]+scale) or abs(rotation[0])>1e-6 or abs(rotation[2])>1e-6:raise ValueError('Canopy replacement requires upright positive bounds')
    value=source_bounds[1][2]/target_bounds[1][2]*scale[2]
    if not .1<=value<=4:raise ValueError('Canopy replacement exceeds bounded scale')
    bottom=location[2]+(source_bounds[0][2]-source_bounds[1][2])*scale[2]
    root=bottom-(target_bounds[0][2]-target_bounds[1][2])*value
    if any(abs(n)>300000 for n in [*location[:2],root]):raise ValueError('Canopy replacement leaves bounded native coordinates')
    return dict(scale=[value]*3,location=[location[0],location[1],root],retainedHeightCm=source_bounds[1][2]*2*scale[2],retainedBottomCm=bottom)
