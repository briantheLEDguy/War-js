"""Fresh private woodland actors retain the exact installed oak mesh, LODs and simple collision."""
import copy, math, struct
import unreal
from t1_woodland_clusters import woodland_layout


def add_woodland_canopies(assets, source, states, sources, height_cm):
    if source['id'] != 'sunmeadow_march' or not assets.folder.startswith('/Game/WorldRebuild/T1Redesign_Atmosphere_'):
        raise RuntimeError('Woodland study requires a fresh private Sunmeadow candidate')
    recipe = sources['SM_White_Oak_01']; mesh = unreal.load_asset(recipe['path'])
    if not isinstance(mesh, unreal.StaticMesh) or recipe['simpleCollisionCount'] < 1:
        raise RuntimeError('Woodland oak requires reviewed source collision')
    bounds = mesh.get_bounds(); ext = bounds.box_extent
    if [ext.x, ext.y, ext.z] != recipe['boundsExtent'] or mesh.get_num_lods() != recipe['lodCount']:
        raise RuntimeError('Woodland source bounds or LOD inventory changed')
    occupied = []; canopy_count = 0
    for label, state in states.items():
        if state['kind'] != 'mesh' or label.endswith(('_terrain', '_roads', '_water')): continue
        p = state['location']; s = state['scale']
        if 'WarT1PrivateInstalledNatureStudy' in state['tags']:
            canopy_count += 1; radius = 8
        else:
            obstacle = unreal.load_asset(state['mesh']).get_bounds().box_extent
            radius = math.hypot(obstacle.x*s[0], obstacle.y*s[1])/100+2
            if radius > 100: continue
            radius = max(.25, radius)
        occupied.append(dict(x=p[1]/100, z=p[0]/100, radius=radius))
    if not 200 <= canopy_count <= 490: raise RuntimeError('Woodland parent canopy inventory escapes its budget')
    placements = woodland_layout(source, lambda x,z:height_cm(x,z)/100, occupied, max(ext.x,ext.y)/(ext.z*2), min(190,490-canopy_count))
    if len(placements) < 100: raise RuntimeError('Woodland cannot fit a meaningful cluster without obstructing reserves')
    result = copy.deepcopy(states); f32 = lambda value:struct.unpack('<f',struct.pack('<f',value))[0]
    for row in placements:
        scale = row['heightMetres']*100/(ext.z*2); root = row['groundMetres']*100-(bounds.origin.z-ext.z)*scale
        if row['id'] in result: raise RuntimeError('Duplicate woodland actor identity')
        result[row['id']] = dict(kind='mesh', mesh=mesh.get_path_name(), materials=recipe['materials'][:], location=[row['z']*100,row['x']*100,root], rotation=[0,f32(row['yawDegrees']),0], scale=[scale]*3, tags=['WarT1PrivateInstalledNatureStudy','WarT1WoodlandCluster'], collision='BlockAll')
    return result, dict(placements=placements, installedMesh=mesh.get_path_name(), sourceGeometryAndLODsPreserved=True, simpleCollisionCount=recipe['simpleCollisionCount'], sourceCollisionRetained=True, collisionAccepted=False, authorityIntegrated=False, physicalDrivingAccepted=False, appearanceApproved=False, performanceAccepted=False)
