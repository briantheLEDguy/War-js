"""Preserve authored furniture surfaces and place dressing outside signed play lanes."""
import hashlib
import json
import math
import struct
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRESSING_GROUPS = ('forehall', 'throne_hall', 'west_archive', 'east_treasury', 'west_terrace', 'east_terrace')


@lru_cache(maxsize=1)
def reviewed_catalog():
    return json.loads((ROOT/'public/assets/models/asset-index.json').read_text())['staticProps']


def source_document(source):
    raw = source.read_bytes()
    if len(raw) < 28 or struct.unpack_from('<III', raw) != (0x46546c67, 2, len(raw)):
        raise ValueError('Invalid furnishing source GLB')
    size, kind = struct.unpack_from('<II', raw, 12)
    if kind != 0x4e4f534a: raise ValueError('Missing furnishing source JSON')
    return json.loads(raw[20:20+size])


def authored_material(source, document, material):
    """Bake the common glTF atlas transform into UVs; retain each PBR factor."""
    pbr = material.get('pbrMetallicRoughness', {})
    spec = dict(tint=pbr.get('baseColorFactor', [1, 1, 1, 1])[:3],
                roughness=pbr.get('roughnessFactor', 1), metallic=pbr.get('metallicFactor', 1),
                twoSided=material.get('doubleSided', False))
    transform = None
    for key, entry in [('baseColor', pbr.get('baseColorTexture')),
                       ('normal', material.get('normalTexture')),
                       ('orm', pbr.get('metallicRoughnessTexture'))]:
        if entry is None: continue
        current = entry.get('extensions', {}).get('KHR_texture_transform', {})
        if entry.get('texCoord', 0) != 0 or current.get('texCoord', 0) != 0 or current.get('rotation', 0) != 0:
            raise ValueError('Unsupported furnishing UV channel or rotated atlas')
        current = dict(offset=current.get('offset', [0, 0]), scale=current.get('scale', [1, 1]))
        if transform is not None and transform != current:
            raise ValueError('Furnishing textures require different UV mappings')
        transform = current
        image = document['images'][document['textures'][entry['index']]['source']]
        if 'uri' not in image: raise ValueError('Furnishing textures must use reviewed repository sources')
        file = (source.parent / image['uri']).resolve()
        file.relative_to((ROOT / 'public/assets').resolve())
        if not file.is_file(): raise ValueError('Missing original furnishing texture')
        spec[key] = file.relative_to(ROOT).as_posix()
        if key == 'normal':
            spec['normalStrength'] = entry.get('scale', 1)
            spec['normalConvention'] = 'gltf_opengl_positive_y'
    if 'emissiveFactor' in material and any(material['emissiveFactor']):
        spec['emission'] = material['emissiveFactor']
    mode=material.get('alphaMode', 'OPAQUE')
    if mode not in ('OPAQUE','MASK','BLEND'): raise ValueError('Unknown source alpha mode')
    if mode != 'OPAQUE':
        spec.update(alphaMode=mode,opacity=pbr.get('baseColorFactor',[1,1,1,1])[3])
        if mode == 'MASK': spec['alphaCutoff']=material.get('alphaCutoff',.5)
    role = 'furniture_' + hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:12]
    return role, spec, transform or dict(offset=[0, 0], scale=[1, 1])


def transform_vector(point, yaw_degrees):
    angle = math.radians(yaw_degrees)
    c, s = math.cos(angle), math.sin(angle)
    return [c*point[0]-s*point[1], s*point[0]+c*point[1], point[2]]


def repair_collapsed_uvs(mesh):
    """Disambiguate collapsed seam UVs without changing geometry or normals.

    MikkTSpace cannot derive a tangent plane from a line. Give only that face
    separate corners and a perpendicular UV span bounded to a quarter texel.
    Healthy faces retain their exact original corner attributes.
    """
    from aegis_citadel_mesh import MATERIALS, MATERIAL_SPECS
    def f32(v): return struct.unpack('<f', struct.pack('<f', v))[0]
    repaired=[]
    for ordinal in range(len(mesh.indices)//3):
        ids=mesh.indices[ordinal*3:ordinal*3+3]
        uv=[[f32(v) for v in mesh.uvs[i]] for i in ids]
        du=[uv[1][i]-uv[0][i] for i in range(2)];dv=[uv[2][i]-uv[0][i] for i in range(2)]
        determinant=f32(f32(du[0]*dv[1])-f32(du[1]*dv[0]))
        if determinant != 0: continue
        role=MATERIALS[mesh.triangle_materials[ordinal]];spec=MATERIAL_SPECS[role]
        sizes=[]
        for key in ('baseColor','normal','orm'):
            if key not in spec:continue
            with (ROOT/spec[key]).open('rb') as source: header=source.read(24)
            if header[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Seam repair requires measurable PNG textures')
            sizes.extend(struct.unpack('>II',header[16:24]))
        limit=1/(4*max(sizes,default=4096))
        a,b=max(((a,b) for a in range(3) for b in range(a+1,3)),
                key=lambda pair:math.dist(uv[pair[0]],uv[pair[1]]))
        c=3-a-b
        p=[mesh.positions[i] for i in ids]
        edge=[p[b][i]-p[a][i] for i in range(3)]
        other=[p[c][i]-p[a][i] for i in range(3)]
        length=math.sqrt(sum(v*v for v in edge))
        if length==0:raise ValueError('Collapsed furnishing geometry cannot be UV repaired')
        perpendicular=[other[i]-edge[i]*sum(other[j]*edge[j] for j in range(3))/(length*length) for i in range(3)]
        if math.sqrt(sum(v*v for v in perpendicular))<=1e-6:
            raise ValueError('Degenerate furnishing face cannot be UV repaired')
        delta=[uv[b][i]-uv[a][i] for i in range(2)];span=math.hypot(*delta)
        changed=[u[:] for u in uv]
        if span:
            changed[c]=[uv[c][0]-delta[1]/span*limit,uv[c][1]+delta[0]/span*limit]
        else:
            changed[b][0]+=limit;changed[c][1]+=limit
        start=len(mesh.positions)
        for original,new_uv in zip(ids,changed):
            mesh.positions.append(mesh.positions[original][:]);mesh.normals.append(mesh.normals[original][:])
            mesh.uvs.append(new_uv)
        mesh.indices[ordinal*3:ordinal*3+3]=range(start,start+3)
        repaired.append(dict(triangle=ordinal,originalUVs=[mesh.uvs[i][:] for i in ids],
            repairedUVs=changed,maximumAxisDelta=limit,quarterTexelLimit=limit,materialRole=role))
    return dict(policy='collapsed_float32_uv_determinant_quarter_texel_v1',faces=repaired,
        originalGeometryPreserved=True,originalNormalsPreserved=True,healthyUVsPreserved=True)


def source_furnishing(placement):
    from world_static import read_glb
    from aegis_citadel_mesh import Mesh, MATERIALS, MATERIAL_SPECS
    source = ROOT / placement['source']
    reviewed=reviewed_catalog().get(source.stem.removeprefix('prop_'),{})
    if (reviewed.get('approvalState')!='approved' or reviewed.get('runtimeReady') is not True
            or reviewed.get('model')!=source.name
            or reviewed.get('modelSha256')!=hashlib.sha256(source.read_bytes()).hexdigest()):
        raise ValueError('Furnishing does not match its reviewed repository binding: '+source.name)
    document = source_document(source)
    native = read_glb(source)
    definitions = [document['materials'][p['material']] for node in document['nodes']
                   for p in document['meshes'][node['mesh']]['primitives']]
    if len(definitions) != len(native['parts']): raise ValueError('Furnishing material sections changed')
    vertices = [p for part in native['parts'] for p in part['positions']]
    minimum = [min(p[i] for p in vertices) for i in range(3)]
    maximum = [max(p[i] for p in vertices) for i in range(3)]
    center = [(minimum[i]+maximum[i])/2 for i in range(2)] if placement.get('centerPlan') else [0, 0]
    scale = placement['scale']
    if not math.isfinite(scale) or scale <= 0: raise ValueError('Invalid furnishing scale')
    yaw = placement.get('yawDegrees', -90)
    mesh = Mesh('furnishing_'+placement['id'])
    sections = []
    for part, material in zip(native['parts'], definitions):
        role, spec, uv_transform = authored_material(source, document, material)
        if role not in MATERIAL_SPECS:
            MATERIAL_SPECS[role] = spec; MATERIALS.append(role)
        elif MATERIAL_SPECS[role] != spec: raise ValueError('Furnishing material hash collision')
        start = len(mesh.positions)
        for p, normal, uv in zip(part['positions'], part['normals'], part['uvs']):
            local = transform_vector([p[0]-center[0], p[1]-center[1], p[2]-minimum[2]], yaw)
            mesh.positions.append([local[i]*scale+placement['point'][i] for i in range(3)])
            mesh.normals.append(transform_vector(normal, yaw))
            mesh.uvs.append([uv_transform['offset'][i]+uv[i]*uv_transform['scale'][i] for i in range(2)])
        # world_static emits native CW faces. The citadel's signed source arrays
        # use CCW; staging applies the single native winding conversion later.
        for i in range(0, len(part['indices']), 3):
            a, b, c = part['indices'][i:i+3]
            mesh.indices.extend([start+a, start+c, start+b]);mesh.triangle_materials.append(MATERIALS.index(role))
        sections.append(dict(sourceMaterial=material.get('name', ''), role=role, uvTransform=uv_transform))
    seam_repair=repair_collapsed_uvs(mesh)
    bounds = [[min(p[i] for p in mesh.positions) for i in range(3)],
              [max(p[i] for p in mesh.positions) for i in range(3)]]
    return mesh, dict(kind='authored_furniture_pbr_uv_normals_v1', sourceSha256=native['sourceSha256'],
        yawDegrees=yaw, scale=scale, boundsCm=bounds, materialSections=sections,
        originalNormalsPreserved=True, originalAtlasTransformsBaked=True, groundFromActualVertices=True,
        collapsedSeamUVRepair=seam_repair)


def dressing_requests():
    """Room functions and desired positions; actual bounds are checked before export."""
    rows = []
    def add(group, kind, point, yaw=-90, scale=1):
        rows.append(dict(id=group+'_'+kind+'_'+str(sum(r['group']==group for r in rows)), group=group,
            source='public/assets/models/prop_aegis_'+kind+'.glb', point=point,
            scale=scale, yawDegrees=yaw, centerPlan=True))
    for side in (-1, 1):
        group='forehall'
        for x,y in ((26700,2400),(28250,3000)): add(group,'citadel_feast_table',[x,side*y,6010],0,.85)
        add(group,'citadel_provision_rack',[27150,side*3870,6010],180 if side<0 else 0,.8)
        add(group,'barrel_cluster',[26650,side*3600,6010],0,.85)
        add(group,'crate_stack',[28480,side*3520,6010],0,.7)
        for x in (29550, 31300): add('throne_hall','civic_bench',[x,side*3420,6010],0 if side<0 else 180,.8)
    for x in (29600, 30600):
        add('west_archive','citadel_counting_desk',[x,-6270,6010],0,.8)
    add('west_archive','citadel_archive',[31000,-6470,6010],0,.6)
    add('west_archive','citadel_provision_rack',[29150,-6500,6010],0,.65)
    for x in (29350, 30700): add('east_treasury','citadel_counting_desk',[x,6190,6010],180,.8)
    for x in (29500, 30700, 32400): add('east_treasury','crate_stack',[x,6500,6010],0,.7)
    add('east_treasury','barrel_cluster',[30100,6470,6010],0,.85)
    for sign, group in [(-1,'west_terrace'),(1,'east_terrace')]:
        for x,y in ((19000,4150),(20300,3500)): add(group,'civic_bench',[x,sign*y,4210],0 if sign<0 else 180,.85)
        add(group,'barrel_cluster',[19700,sign*3950,4210],0,.85)
        add(group,'crate_stack',[20300,sign*4000,4210],0,.7)
    # Furnish the gathering bays, leaving the commander aisle, chamber access,
    # gallery descent and the measured spawn exits outside the actual bounds.
    for sign in (-1,1):
        for x in (26700,28250,28600):
            add('forehall','citadel_feast_table',[x,sign*1500,6010],0,.85)
        for x,y in ((29300,2850),(29700,2850),(31550,3500)):
            add('throne_hall','citadel_feast_table',[x,sign*y,6010],0,.85)
        for x,y in ((29000,3800),(31900,3900)):
            add('throne_hall','barrel_cluster',[x,sign*y,6010],0,.85)

    # Measured facade/stair clearance repairs preserve each furnishing identity.
    repaired_points = {
        'forehall_citadel_feast_table_0': [26850, -2400, 6010],
        'forehall_citadel_feast_table_5': [26850, 2400, 6010],
        'throne_hall_civic_bench_3': [31250, 3420, 6010],
        'east_treasury_crate_stack_4': [32100, 6500, 6010],
        'west_terrace_civic_bench_1': [20300, -3450, 4210],
        'west_terrace_barrel_cluster_2': [19600, -3950, 4210],
        'west_terrace_crate_stack_3': [20350, -4300, 4210],
        'east_terrace_civic_bench_1': [20300, 3450, 4210],
        'east_terrace_barrel_cluster_2': [19600, 3950, 4210],
        'east_terrace_crate_stack_3': [20500, 4150, 4210],
        'forehall_citadel_feast_table_10': [26650, -1350, 6010],
        'throne_hall_barrel_cluster_8': [31900, -3850, 6010],
        'forehall_citadel_feast_table_13': [26650, 1350, 6010],
        'throne_hall_citadel_feast_table_11': [31900, 3500, 6010],
        'throne_hall_barrel_cluster_13': [31900, 3850, 6010],
    }
    for row in rows:
        if row['id'] in repaired_points: row['point'] = repaired_points[row['id']]
    return rows


def checked_dressing(blueprint, existing, architecture):
    from aegis_citadel_blueprint import route_clearance
    from aegis_citadel_mesh import Mesh, append_mesh
    from aegis_citadel_furnishing_density import ArchitectureClearance, route_witness, overlaps
    from citadel_review_world import residents
    requests=dressing_requests()
    prepared=[source_furnishing(request) for request in requests]
    checker=ArchitectureClearance(architecture,[receipt['boundsCm'] for _,receipt in prepared])
    groups = {key:Mesh('dressing_'+key) for key in DRESSING_GROUPS}
    occupied = [row['boundsCm'] for row in existing]
    ledger = []
    for request,(mesh,receipt) in zip(requests,prepared):
        bounds = receipt['boundsCm']
        point=[(bounds[0][i]+bounds[1][i])/2 for i in range(2)]+[bounds[0][2]]
        radius=math.hypot((bounds[1][0]-bounds[0][0])/2,(bounds[1][1]-bounds[0][1])/2)
        if not route_clearance(blueprint,point,radius,bounds[1][2]-bounds[0][2]):
            raise ValueError('Dressing enters a signed route: '+request['id'])
        if any(all(bounds[1][i]+15>b[0][i] and bounds[0][i]-15<b[1][i] for i in range(3)) for b in occupied):
            raise ValueError('Dressing overlaps another furnishing: '+request['id'])
        for objective in blueprint['objectives']+blueprint['optionalObjectives']:
            p=objective.get('point') if isinstance(objective,dict) else objective
            if p and abs(p[2]-point[2])<210 and math.dist(p[:2],point[:2])<650+radius:
                raise ValueError('Dressing enters an objective reservation: '+request['id'])
        room=next((r for r in blueprint.get('rooms',[]) if r['id']==request['group']),None)
        if room and not all(room['bounds'][0][i]<=bounds[0][i] and bounds[1][i]<=room['bounds'][1][i] for i in range(3)):
            raise ValueError('Dressing leaves signed room: '+request['id'])
        route=route_witness(blueprint,bounds)
        for pad in blueprint.get('gameplayPads',[]):
            if pad.get('preserveTransform'): continue
            p=pad['footprintCentreFloorCm']
            if bounds[0][2]<p[2]+pad['maximumHeightCm'] and bounds[1][2]>p[2] and math.dist(p[:2],point[:2])<pad['maximumFootprintRadiusCm']+radius+15:
                raise ValueError('Dressing enters gameplay/service pad: '+request['id'])
        for gate in blueprint.get('gates',[]):
            for leaf in gate['leaves']:
                x,y,z=leaf['point'];width=leaf['width'];height=leaf['height']
                if overlaps(bounds,[[x-255,y-width/2,z],[x+255,y+width/2,z+height]],15):
                    raise ValueError('Dressing enters gate reservation: '+request['id'])
        for resident in residents():
            x,y,z=resident['pointCm'];r=resident['clearanceRadiusCm']
            if overlaps(bounds,[[x-r,y-r,z],[x+r,y+r,z+resident['heightCm']]],15):
                raise ValueError('Dressing enters resident reservation: '+request['id'])
        geometry=checker.check(request['id'],bounds)
        occupied.append(bounds);append_mesh(groups[request['group']],mesh)
        ledger.append({**request,**receipt, 'signedRouteClear':True,'otherFurnishingsClear':True,
                       'routeClearance':route,'architectureClearance':geometry,'nativeClearanceVerified':False})
    return list(groups.values()),ledger
