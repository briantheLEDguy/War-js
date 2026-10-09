"""Bounded selection/dependency contract for private installed nature-kit inspection."""
import math
NATURE_ROOT='/Game/Medieval_Environment/Real_Landscape'
PACKAGE_ROOT='/Game/Medieval_Environment/'
NAMES=('SM_White_Oak_01','SM_White_Oak_02','SM_White_Oak_Young_01','SM_White_Oak_Sapling_01','SM_White_Oak_Sapling_02','SM_White_Oak_Seed_01','SM_White_Oak_Seed_02','SM_Fern_01','SM_Grass_01','SM_Grass_Long_01','SM_Small_Rock_01','SM_Small_Rock_03','SM_Small_Rock_05','SM_Dead_Branch_01','SM_Dead_Leaf_01')


def select_nature_meshes(receipt):
    if receipt.get('kit')!=NATURE_ROOT:raise ValueError('Unexpected installed nature kit')
    selected=[]
    for name in NAMES:
        rows=[r for r in receipt['meshes'] if r['path'].startswith(NATURE_ROOT+'/') and r['path'].rsplit('.',1)[-1]==name]
        if len(rows)!=1:raise ValueError('Missing or ambiguous nature mesh: '+name)
        row=rows[0]
        if not isinstance(row['lodCount'],int) or not 1<=row['lodCount']<=8 or len(row['lodVertices'])!=row['lodCount'] or any(not isinstance(v,int) or v<1 for v in row['lodVertices']):raise ValueError('Invalid nature LOD inventory')
        if len(row['boundsOrigin'])!=3 or len(row['boundsExtent'])!=3 or any(not math.isfinite(v) for v in row['boundsOrigin']+row['boundsExtent']) or any(not 0<v<=10000 for v in row['boundsExtent']):raise ValueError('Invalid nature bounds')
        if not row['materials'] or any(not m or not m.startswith(PACKAGE_ROOT) for m in row['materials']):raise ValueError('Unreviewed nature material binding')
        selected.append(row)
    return selected


def nature_dependencies(roots,lookup):
    pending=list(roots);packages=set()
    while pending:
        package=pending.pop()
        if package.startswith(('/Engine/','/Script/')):continue
        if not package.startswith(PACKAGE_ROOT) or any(part in ('','..','.') for part in package.split('/')[1:]) or '.' in package:raise ValueError('Unreviewed nature dependency: '+package)
        if package in packages:continue
        packages.add(package)
        if len(packages)>2048:raise ValueError('Nature dependency inventory exceeds bounded inspection')
        pending.extend(lookup(package))
    return sorted(packages)
