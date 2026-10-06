"""Reference-led Gothic precinct; Unreal centimetres, X uphill/north, Y east.

The route graph is independent of decoration. Raised projected crossings connect
only through authored stairs, and both stage cuts include every flank/gallery crossing.
"""
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/unreal/aegis-citadel'
REFERENCE = Path('C:/Users/bschm/Downloads/Bastion of Aegis_ Citadel War Board.png')
RECIPE_VERSION = 9
UPPER_BOUNDS=[[13500,-9600,2400],[34500,9600,24000]]
APPROACH_ENCLOSURE_BOUNDS=[
    dict(id='west_approach_wall_toe',bounds=[[13250,-7120,4190],[13350,-6810,4520]]),
    dict(id='east_approach_wall_toe',bounds=[[13250,6810,4190],[13350,7120,4520]])]
LIGHTING_FIXTURES_V1=[
    dict(actor='DirectionalLight_0',klass='DirectionalLight',label='Aegis workbench sun',
        component='DirectionalLightComponent',rotationDegrees=[-28,30,0],properties=dict(
            intensity=12500,temperature=5600,use_temperature=True,cast_shadows=True,
            atmosphere_sun_light=True,forward_shading_priority=1,light_source_angle=1.2)),
    dict(actor='DirectionalLight_1',klass='DirectionalLight',label='Crownward soft sky fill',
        component='DirectionalLightComponent',rotationDegrees=[-50,-140,0],properties=dict(
            intensity=2500,use_temperature=False,cast_shadows=False,atmosphere_sun_light=False,
            light_color=dict(kind='color',value=[158,187,226,255]))),
    dict(actor='SkyLight_0',klass='SkyLight',label='Aegis workbench sky',component='SkyLightComponent',
        properties=dict(intensity=1.4,real_time_capture=True,lower_hemisphere_is_black=False,
            lower_hemisphere_color=dict(kind='linear_color',value=[.065,.08,.115,1]),
            light_color=dict(kind='color',value=[215,228,247,255]),indirect_lighting_intensity=1.1)),
    dict(actor='ExponentialHeightFog_0',klass='ExponentialHeightFog',label='Crownward cold distance haze',
        component='ExponentialHeightFogComponent',properties=dict(fog_density=.003,fog_height_falloff=.15,
            start_distance=8000,fog_max_opacity=.22,enable_volumetric_fog=False,
            fog_inscattering_luminance=dict(kind='linear_color',value=[.10,.13,.18,1]))),
    dict(actor='PostProcessVolume_0',klass='PostProcessVolume',label='Aegis daylight exposure',
        component=None,properties=dict(
            override_auto_exposure_method=True,
            auto_exposure_method=dict(kind='enum',type='AutoExposureMethod',value='AEM_HISTOGRAM'),
            override_auto_exposure_apply_physical_camera_exposure=True,auto_exposure_apply_physical_camera_exposure=False,
            override_auto_exposure_bias=True,auto_exposure_bias=-.2,
            override_auto_exposure_min_brightness=True,auto_exposure_min_brightness=64,
            override_auto_exposure_max_brightness=True,auto_exposure_max_brightness=4096,
            override_histogram_log_min=True,histogram_log_min=1,
            override_histogram_log_max=True,histogram_log_max=14,
            override_auto_exposure_speed_up=True,auto_exposure_speed_up=3,
            override_auto_exposure_speed_down=True,auto_exposure_speed_down=1,
            override_color_saturation=True,color_saturation=dict(kind='vector4',value=[.92,.92,.92,1]),
            override_bloom_intensity=True,bloom_intensity=.18,
            override_lens_flare_intensity=True,lens_flare_intensity=0))]
from aegis_citadel_lighting import (FIXTURES,reference_fixture_requests,bind_fixture_edits,
    shadowed_practical_requests,CLOUD_IDENTITY,CLOUD_PROPERTIES,REVIEWED_CLOUD_MATERIAL)
LIGHTING_REQUESTS=reference_fixture_requests(LIGHTING_FIXTURES_V1)
LIGHTING_FIXTURES=[dict(id=identity[0],actor=identity[1],klass=identity[2],label=identity[3],
    component=identity[4],requiredTag=identity[6],**{k:v for k,v in request.items() if k!='id'})
    for identity,request in zip(FIXTURES,LIGHTING_REQUESTS)]



def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def castle_identity(state):
    return next((t.removeprefix('WarWorldObject_') for t in state['tags']
                 if t.startswith(('WarWorldObject_castle_', 'WarWorldObject_keep_',
                                  'WarWorldObject_gatehouse_'))), None)


def enclosure_identity(state):
    return next((t.removeprefix('WarWorldObject_') for t in state['tags']
                 if t.startswith(('WarWorldObject_aegis_battle_enclosure_',
                                  'WarWorldObject_aegis_city_north_wall_'))),None)


def intersects(a,b):
    return all(a[1][i]>b[0][i] and a[0][i]<b[1][i] for i in range(3))


def contains(outer,inner):
    return all(outer[0][i]<=inner[0][i] and inner[1][i]<=outer[1][i] for i in range(3))


def route_clearance(data,point,radius,height):
    """Conservative authored corridor reservation for solid support/prop placement."""
    spawn_routes=[dict(points=row['points'] if len(row['points'])>1 else row['points']*2,
                       width=row['widthCm']) for row in data.get('spawnApproaches',[])]
    for route in [*data['routes'],*spawn_routes]:
        for a,b in zip(route['points'],route['points'][1:]):
            dx,dy=b[0]-a[0],b[1]-a[1];length=dx*dx+dy*dy
            t=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/length)) if length else 0
            x,y,z=a[0]+dx*t,a[1]+dy*t,a[2]+(b[2]-a[2])*t
            if point[2]+height<=z-15 or point[2]>=z+207:continue
            if (point[0]-x)**2+(point[1]-y)**2<(route['width']/2+radius+10)**2:return False
    return True


def crossing_ledger(routes):
    """Enumerate projected centerline crossings and overlaps, including heights."""
    result={}
    def cross(a,b):return a[0]*b[1]-a[1]*b[0]
    def point(a,b,t):return [round(a[i]+(b[i]-a[i])*t,4) for i in range(3)]
    for i,left in enumerate(routes):
        for right in routes[i+1:]:
            for li,(a,b) in enumerate(zip(left['points'],left['points'][1:])):
                for ri,(c,d) in enumerate(zip(right['points'],right['points'][1:])):
                    u=[b[j]-a[j] for j in range(2)];v=[d[j]-c[j] for j in range(2)]
                    delta=[c[j]-a[j] for j in range(2)];den=cross(u,v)
                    if abs(den)>1e-6:
                        t,s=cross(delta,v)/den,cross(delta,u)/den
                        if not(-1e-7<=t<=1+1e-7 and -1e-7<=s<=1+1e-7):continue
                        lp,rp=point(a,b,t),point(c,d,s);positions=[lp,rp];kind='point'
                    else:
                        if abs(cross(delta,u))>1e-4:continue
                        axis=max(range(2),key=lambda j:abs(u[j]))
                        if abs(u[axis])<1e-7 or abs(v[axis])<1e-7:continue
                        lo=max(0,min((c[axis]-a[axis])/u[axis],(d[axis]-a[axis])/u[axis]))
                        hi=min(1,max((c[axis]-a[axis])/u[axis],(d[axis]-a[axis])/u[axis]))
                        if hi<lo-1e-7:continue
                        lps=[point(a,b,t) for t in (lo,hi)]
                        rps=[point(c,d,(p[axis]-c[axis])/v[axis]) for p in lps]
                        kind='shared_segment' if math.dist(lps[0][:2],lps[1][:2])>.01 else 'point'
                        positions=[lps,rps] if kind=='shared_segment' else [lps[0],rps[0]]
                    heights=([abs(positions[0][2]-positions[1][2])] if kind=='point' else
                             [abs(p[2]-q[2]) for p,q in zip(*positions)])
                    connects=max(heights)<=15
                    record=dict(kind=kind,routes=[left['id'],right['id']],positionsCm=positions,
                        connects=connects,reason='same_floor_walkable_junction' if connects else 'height_separated_no_connection')
                    key=digest(record)
                    if key not in result:result[key]=dict(id='crossing_'+key[:12],**record,segments=[[li,ri]])
                    else:result[key]['segments'].append([li,ri])
    return sorted(result.values(),key=lambda row:row['id'])


def upper_enclosure_edits(baseline):
    edits=[];preserved=[]
    if not baseline:return edits,preserved
    for package,rows in baseline['actors'].items():
        for row in rows:
            identity=enclosure_identity(row['state'])
            if not identity or 'bounds' not in row:continue
            evidence=dict(package=package,actor=row['actor'],identity=identity,bounds=row['bounds'],
                          category='old_north_curtain' if identity.startswith('aegis_city_north_wall_') else 'old_battle_enclosure',
                          stateHash=digest(row['state']))
            # Actual full-width movement contacts the two old front-wall toes
            # just below the main precinct mask. Replace only whole surveyed
            # enclosure modules contained in these narrow approach reservations.
            approach=next((mask for mask in APPROACH_ENCLOSURE_BOUNDS if contains(mask['bounds'],row['bounds'])),None)
            if approach:
                edits.append(dict(**evidence,mode='actor',editVolume=approach['id']));continue
            if not intersects(UPPER_BOUNDS,row['bounds']):
                preserved.append(evidence);continue
            if contains(UPPER_BOUNDS,row['bounds']):edits.append(dict(**evidence,mode='actor'))
            else:
                inside=[c['name'] for c in row['componentBounds'] if contains(UPPER_BOUNDS,c['bounds'])]
                clipped=[c['name'] for c in row['componentBounds'] if intersects(UPPER_BOUNDS,c['bounds'])
                         and not contains(UPPER_BOUNDS,c['bounds'])]
                # Boundary modules with no fully contained parts remain intact unless
                # actual route obstruction makes a source-triangle clip necessary.
                if inside:edits.append(dict(**evidence,mode='components',removeComponents=inside,
                                            clipRequired=clipped))
                else:preserved.append(dict(**evidence,boundaryIntersection=True))
    return edits,preserved


def enclosure_edit_bounds(edit_mask,edit):
    """Resolve only the fixed main mask or an exact whole-module toe reservation."""
    if edit.get('editVolume'):
        if edit_mask.get('approachEnclosureBounds')!=APPROACH_ENCLOSURE_BOUNDS:
            raise ValueError('Approach enclosure reservations changed from the bounded source recipe')
        mask=next((row for row in APPROACH_ENCLOSURE_BOUNDS if row['id']==edit['editVolume']),None)
        if not mask or edit.get('mode')!='actor' or not edit.get('identity','').startswith('aegis_battle_enclosure_front_'):
            raise ValueError('Only complete surveyed front-wall toes may use an approach reservation')
        bounds=mask['bounds']
    else:
        if edit_mask.get('upperBounds')!=UPPER_BOUNDS:raise ValueError('The main precinct mask changed')
        bounds=UPPER_BOUNDS
    if edit.get('mode')=='actor' and not contains(bounds,edit['bounds']):
        raise ValueError('Surveyed enclosure actor extends outside its exact edit volume')
    return [row[:] for row in bounds]


def lighting_fixture_edits(baseline):
    """Exact copied environmental identities; no other retained actors change."""
    if not baseline or 'actors' not in baseline:return []
    return bind_fixture_edits(baseline,LIGHTING_REQUESTS)


def cloud_material_file():
    engine=Path(os.environ.get('UNREAL_ENGINE_ROOT','C:/Program Files/Epic Games/UE_5.8')).resolve()
    content=(engine/'Engine/Content').resolve()
    file=(content/'EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst.uasset').resolve()
    file.relative_to(content)
    if not file.is_file():raise ValueError('Reviewed original Engine cloud material is unavailable')
    return file


def cloud_fixture(baseline):
    if not baseline:return None
    parent=REVIEWED_CLOUD_MATERIAL+'.m_SimpleVolumetricCloud_Inst'
    return dict(**CLOUD_IDENTITY,pointCm=[0,0,0],properties=CLOUD_PROPERTIES,
        material=dict(package=REVIEWED_CLOUD_MATERIAL,
            path=parent,sha256=sha(cloud_material_file())),
        materialInstance=dict(name='MI_Cloud',parent=parent,
            scalarParameters=dict(Layout_CloudGlobalScale=8,Cloud_GlobalCoverage=.25,
                Cloud_GlobalDensity=.008,StormClouds=.65),
            vectorParameters=dict(Cloud_AlbedoColor=[.65,.70,.78,.5],
                Storm_LightningColor=[0,0,0,0],Layout_CloudTypeMask=[0,0,1,0])))


def terrain_carve_edits(baseline):
    if not baseline:return []
    from aegis_citadel_terrain import HALL_CARVE_WORLD,MOUNTAIN_ACTOR_TRANSFORM,checked_native_terrain_source
    file=OUT/'b619391123d3/native-terrain-source-receipt.json'
    receipt=json.loads(file.read_text());package=receipt['sourcePackage'];actor=receipt['actor']
    source=next(r for r in baseline['actors'][package] if r['actor']==actor)
    if (digest(source['state'])!=receipt['sourceActorStateSha256'] or
            receipt['packagesBefore']!=receipt['packagesAfter'] or receipt['readOnly'] is not True
            or receipt['noPackagesSaved'] is not True or receipt['actorTransform']!=MOUNTAIN_ACTOR_TRANSFORM):
        raise ValueError('Actual retained mountain source state or transform changed')
    source_file=ROOT/receipt['sourceFile'];input_file=ROOT/receipt['inputFile']
    if sha(source_file)!=receipt['sourceSha256'] or sha(input_file)!=receipt['inputSha256']:
        raise ValueError('Committed terrain source export changed')
    checked_native_terrain_source(json.loads(source_file.read_text()),receipt['sourceMesh'])
    mesh_package=receipt['sourceMesh'].split('.')[0]
    if baseline['packageHashes'][mesh_package]!=receipt['packagesBefore'][mesh_package]:
        raise ValueError('Retained native mountain package changed after actual export')
    policy=baseline.get('terrainSourcePolicies',{}).get(receipt['sourceMesh'])
    if policy and (policy['package']!=package or policy['actor']!=actor
            or policy['sourceMeshSha256']!=baseline['packageHashes'][mesh_package]):
        raise ValueError('Original native terrain policy is bound to another actor or source package')
    survey_sha=sha(ROOT/baseline['file']) if policy else None
    return [dict(id=HALL_CARVE_WORLD['id'],package=package,actor=actor,klass=receipt['actorClass'],
        label=receipt['label'],component=receipt['component'],requiredTag=receipt['requiredTag'],
        sourceStateHash=receipt['sourceActorStateSha256'],sourceMesh=receipt['sourceMesh'],
        sourceMeshPackageSha256=baseline['packageHashes'][mesh_package],actorTransform=MOUNTAIN_ACTOR_TRANSFORM,
        worldVolumes=[HALL_CARVE_WORLD],localVolumeBounds=[[[960,-4260,5980],[8460,4260,24000]]],
        sourcePolicy=receipt['sourcePolicy'],sourceNativePolicy=policy['policy'] if policy else None,
        sourcePolicySurvey=dict(path=(OUT/'surveys'/(survey_sha+'.json')).relative_to(ROOT).as_posix(),
            sha256=survey_sha) if policy else None,
        sourceExportFile=receipt['sourceFile'],
        sourceExportSha256=receipt['sourceSha256'],inputFile=receipt['inputFile'],inputSha256=receipt['inputSha256'],
        sourceReceiptFile=file.relative_to(ROOT).as_posix(),sourceReceiptSha256=sha(file),
        method='convex_halfspace_difference_source_corner_barycentrics',
        outsideActorAndTriangleGeometryPreserved=True,nativeCollisionVerified=False)]



def wing_ground_witness(file,baseline):
    from citadel_wing_support_evidence import checked_ground_summary
    if not file:
        raise ValueError('Native wing repairs require an explicit ground survey')
    path=Path(file).resolve()
    path.relative_to(OUT.resolve())
    report=json.loads(path.read_text())
    summary=checked_ground_summary(report)
    if (report.get('samplingVersion')!=2 or summary['samples']!=144
            or summary['samplesBelowCurrentEditFloor'] or summary['samplesAboveWingBase']
            or any(report['packageHashes'].get(p)!=h for p,h in baseline['packageHashes'].items())):
        raise ValueError('Wing ground survey is incomplete, outside the bounded foundation or for changed sources')
    return dict(file=path.relative_to(ROOT).as_posix(),sha256=sha(path),
        sourceRevision=report['revision'],samplingVersion=2,summary=summary,
        freshNativeReplayRequired=True,nativeFoundationApproved=False)


def plan(baseline=None, *, reference_hash=None, castle_removals=None,ground_survey=None):
    """Missing fresh native evidence leaves staging explicitly blocked."""
    lower = [[-11600, 0, 10], [-1000, 0, 10], [11900, -400, 4000], [13600, 0, 4210]]
    optional0, spawn0, spawn1 = [-7900, 3400, 10], [5800, -4800, 910], [-15800, 0, 10]
    if baseline:
        lower = baseline['battlefield']['objectives'][:4]
        optional0 = baseline['battlefield']['optional_objectives'][0]
        spawn0, spawn1 = baseline['battlefield']['team_spawns'][:2]
    nodes = {}
    routes = []

    def node(key, point, kind='junction'):
        nodes[key] = dict(id=key, point=point, kind=kind)

    def route(key, start, end, via=(), width=1200, kind='main', gate=None):
        points = [nodes[start]['point'], *via, nodes[end]['point']]
        routes.append(dict(id=key, start=start, end=end, points=points, width=width,
                           kind=kind, gate=gate, bidirectional=True))

    node('lower_breach', lower[3], 'retained')
    node('outer_gate', [14200, 0, 4210], 'gate')
    node('south_junction', [16500, 0, 4210])
    node('primary', [20800, -1000, 4210], 'primary')
    node('north_junction', [23700, 0, 4210])
    node('inner_gate', [26000, 0, 6010], 'gate')
    node('forehall', [27400, 0, 6010])
    node('commander', [30600, 0, 6010], 'commander')
    route('lower_main_gate', 'lower_breach', 'outer_gate', gate=0, width=1800)
    route('main_south', 'outer_gate', 'south_junction', width=1800)
    route('main_primary', 'south_junction', 'primary', [[19400,-1000,4210]], width=600)
    route('main_north', 'primary', 'north_junction', [[22200,-1000,4210],[23000,0,4210]], width=600)
    route('grand_stair', 'north_junction', 'inner_gate', width=1800, kind='stair', gate=1)
    route('grand_portal', 'inner_gate', 'forehall', width=1800, gate=1)
    route('commander_aisle', 'forehall', 'commander', width=1800)
    approach_corrections=[];flight_corrections=[]
    for side, sign in [('west', -1), ('east', 1)]:
        approach = [12000, -5100, 4046.39990234375] if sign < 0 else [11300, 5900, 3600.949951171875]
        if baseline:approach=baseline['approachTieIns'][side+'_approach']
        node(side+'_approach', approach, 'retained')
        node(side+'_outer_gate', [14200, sign*6500, 4210], 'gate')
        node(side+'_south', [16500, sign*5550, 4210])
        node(side+'_secondary', [20800, sign*5000, 4210], 'secondary')
        node(side+'_north', [23700, sign*5550, 4210])
        node(side+'_south_high', [16500, sign*5550, 5410], 'elevated')
        node(side+'_north_high', [23700, sign*5550, 5410], 'elevated')
        node(side+'_portal', [26000, sign*3100, 6010], 'gate')
        node(side+'_gallery_gate', [26000, sign*3500, 7210], 'gate')
        node(side+'_gallery', [30000, sign*3500, 7210], 'elevated')
        node(side+'_chamber', [30600, sign*5400, 6010], 'interior')
        ramp_y=approach[1]+(sign*6500-approach[1])*(12250-approach[0])/(14200-approach[0])
        previous_via=[[12250,approach[1],4205.5],[12700,sign*6200,4205.5],[13400,sign*6200,4205.5]]
        # A single graded fan retains the real lateral slope while it turns
        # through the measured 1260 cm aperture. A flat landing would roof its
        # own short incoming rise; a bridge would hit the retained 5410 cm coping.
        via=[[12200,approach[1],4173.7],[12400,sign*6200,4205.5],
             [13400,sign*6200,4205.5],[13900,sign*6500,4210]]
        route(side+'_approach', side+'_approach', side+'_outer_gate',via,width=1200,gate=0)
        approach_corrections.append(dict(route=side+'_approach',oldPointsCm=[approach,[12250,ramp_y,4205.5],[14200,sign*6500,4210]],
            newPointsCm=[approach,*via,[14200,sign*6500,4210]],widthCm=1200,
            previousReviewedPointsCm=[approach,*previous_via,[14200,sign*6500,4210]],
            gateAxisAlignmentCm=300,retainedEndpointThresholdLengthCm=20,
            retainedApertureCenterYCm=sign*6200,retainedApertureWidthCm=1260,
            retainedWallTopCm=5410.00004863739,apertureWalkingHeightCm=4205.5,
            floorPolicy='signed_world_x_piecewise_linear_full_width_fan',
            originalActorsPreserved=True,
            rationale='The unchanged endpoint follows the actual world-X grade into one continuously paved full-width fan. It crosses both retained walls inside their measured 1260 cm aperture at Y6200, then bends toward the unchanged gate after the final wall. Every lateral standing point follows the signed floor profile; no planar-height assumption, high bridge, wall removal or width waiver is used. The final 300 cm leg faces +X.'))
        route(side+'_south_main', 'south_junction', side+'_south', width=1200)
        route(side+'_main_objective', side+'_south', side+'_secondary', width=1200)
        route(side+'_main_north', side+'_secondary', side+'_north', width=1200)
        route(side+'_north_main', side+'_north', 'north_junction',
              [[23100,sign*2400,4210],[23100,0,4210]],width=1200)
        spoke_via=[[22200,2500,4210],[22200,-1000,4210]] if sign>0 else []
        route(side+'_primary_spoke', side+'_secondary', 'primary', spoke_via, width=600)
        route(side+'_outer_flank', side+'_outer_gate', side+'_north',
              [[16500, sign*6500, 4210], [23700, sign*6500, 4210]], width=600, kind='flank')
        south_via=[[19400,1800,4210],[19400,-1000,4210]] if sign>0 else []
        north_via=[[22200,-1000,4210],[22200,1800,4210]] if sign>0 else []
        route(side+'_south_diagonal', side+'_south', 'primary', south_via, width=600, kind='flank')
        route(side+'_north_diagonal', 'primary', side+'_north', north_via, width=600, kind='flank')
        # An actual switchback stair connects each raised inset platform.
        route(side+'_south_stair', side+'_south', side+'_south_high',
              [[14800,sign*5550,4210],[14800,sign*3500,4210],[15100, sign*3500, 4210],
               [16600, sign*3500, 4810],[17200,sign*3500,4810],[17200,sign*4900,4810],
               [16600,sign*4900,4810],[15400,sign*4900,5410],
               [14800,sign*4900,5410],[14800,sign*5550,5410]], width=600, kind='stair')
        route(side+'_north_stair', side+'_north', side+'_north_high',
              [[23700,sign*6100,4210],[25600,sign*6100,4210],[25600,sign*3500,4210],[25350, sign*3500, 4210],
               [23300, sign*3500, 4810],[22700,sign*3500,4810],[22700,sign*4900,4810],
               [23300,sign*4900,4810],[24500,sign*4900,5410],
               [25100,sign*4900,5410],[25100,sign*6100,5410],[23700,sign*6100,5410]], width=600, kind='stair')
        route(side+'_wall_balcony', side+'_south_high', side+'_north_high',
              [[16500, sign*6500, 5410], [23700, sign*6500, 5410]], width=600, kind='balcony')
        old_flight=[[24510,sign*5082.273,4210],[25400,sign*3100,6010]]
        run=math.dist(old_flight[0][:2],old_flight[1][:2])
        direction=[(old_flight[1][j]-old_flight[0][j])/run for j in range(2)]
        shifted=[[round(p[0]-direction[0]*350+250,4),round(p[1]-direction[1]*350,4),p[2]] for p in old_flight]
        toe=[round(24300-direction[0]*350+250,4),round(sign*5550-direction[1]*350,4),4210]
        landing=[old_flight[1][0]+250,old_flight[1][1],6010]
        route(side+'_ground_portal_stair', side+'_north', side+'_portal',
              [toe,*shifted,landing], width=600, kind='stair', gate=1)
        flight_corrections.append(dict(route=side+'_ground_portal_stair',oldFlightCm=old_flight,newFlightCm=shifted,
            finalStraightLandingCm=350,outwardShiftXCm=250,risingRunPreservedCm=run,riserCount=120,riserCm=15,widthCm=600,
            rationale='The existing diagonal flat approach becomes the first 350 cm of the flight; its last 350 cm becomes a level full-width landing before the axis turn.'))
        gallery_layout=[[24022,sign*5550,5410],[25600,sign*3500,7210]]
        gallery_run=math.dist(gallery_layout[0][:2],gallery_layout[1][:2])
        gallery_direction=[(gallery_layout[1][j]-gallery_layout[0][j])/gallery_run for j in range(2)]
        gallery_tangent_landing=[round(gallery_layout[0][j]-gallery_direction[j]*600,4) for j in range(2)]+[5410]
        gallery_shifted=[gallery_layout[0],[round(gallery_layout[1][0]-gallery_direction[0]*300,4),
                          round(gallery_layout[1][1]-gallery_direction[1]*300,4),7210]]
        route(side+'_gallery_stair', side+'_north_high', side+'_gallery_gate',
              [gallery_tangent_landing,*gallery_shifted,gallery_layout[1]], width=600, kind='stair', gate=1)
        route(side+'_gallery_aisle', side+'_gallery_gate', side+'_gallery', width=600, kind='balcony', gate=1)
        route(side+'_gallery_descent', side+'_gallery', 'commander',
              [[32600, sign*3500, 7210],[32600,sign*3100,7210], [32600, sign*1650, 6010],
               [32600,sign*1350,6010]], width=600, kind='stair')
        flight_corrections.extend([
            dict(route=side+'_south_stair',oldFlightCm=[[15400,sign*4100,4210],[16600,sign*4100,4810]],
                newFlightCm=[[15100,sign*3500,4210],[16600,sign*3500,4810]],widthCm=600,
                risingRunPreservedCm=None,riserCount=40,riserCm=15,
                rationale='The longer first flight keeps crossing headroom. Moving it 600 cm inward opens a full-width ground spawn approach between the two flights without moving their endpoints or the spawn.'),
            dict(route=side+'_north_stair',oldFlightCm=[[24500,sign*4100,4210],[23300,sign*4100,4810]],
                newFlightCm=[[25350,sign*3500,4210],[23300,sign*3500,4810]],widthCm=600,
                risingRunPreservedCm=None,riserCount=40,riserCm=15,
                rationale='The longer first flight retains crossing headroom. Moving it 600 cm inward opens the ground spawn approach while preserving the upper return flight and all stair endpoints.'),
            dict(route=side+'_gallery_stair',oldFlightCm=[[24022,sign*5236,5410],[25800,sign*3500,7210]],
                newFlightCm=gallery_shifted,widthCm=600,
                firstTangentLandingCm=600,firstTangentLandingPointCm=gallery_tangent_landing,
                finalDiagonalLandingCm=300,finalAxisLandingCm=400,riserCount=120,riserCm=15,
                rationale='A full-width 600 cm level run aligns with the rising flight before its first riser, keeping its inner treads out of the incoming flat lane. The entry stays outward of the north switchback. The final flight ends 400 cm before the doorway so the diagonal lane straightens before the wall reveal.'),
            dict(route=side+'_gallery_descent',oldFlightCm=[[32600,sign*3100,7210],[32600,sign*1650,6010]],
                newFlightCm=[[32600,sign*3100,7210],[32600,sign*1650,6010]],widthCm=600,
                risingRunPreservedCm=1450,finalStraightLandingCm=300,riserCount=80,riserCm=15,
                rationale='An unchanged real flight ends before the diagonal commander turn.')])
        route(side+'_chamber_access', 'commander', side+'_chamber', width=1000, kind='interior')
        route(side+'_hall_side_aisle', side+'_portal', 'forehall',
              [[27400, sign*3100, 6010]], width=600, kind='main', gate=1)
    gates = [dict(id='outer', index=0, leaves=[dict(point=[14200, y, 4210], width=w, height=1800 if y==0 else 900)
                 for y, w in [(0, 1800), (-6500, 1200), (6500, 1200)]]),
             dict(id='inner', index=1, leaves=[dict(point=[26000, y, z], width=w, height=2600 if y==0 else 1100)
                 for y, z, w in [(0, 6010, 1800), (-3100, 6010, 600), (3100, 6010, 600),
                                (-3500, 7210, 600), (3500, 7210, 600)]])]
    for leaf in gates[0]['leaves']:
        if leaf['point'][1]:
            leaf['approachClearance']=dict(incomingFlatLengthCm=300,outgoingFlatLengthCm=2300,
                maximumLeafHalfThicknessCm=55,pedestrianCapsuleRadiusCm=42,
                requiredCapsuleFloorMarginCm=3,localSweepHalfSpanCm=255,
                actualNativeStartClearanceRequired=True,fullWidthRouteTraversalRequired=True,
                rationale='The continuous paved fan ends with a measured 300 cm level +X landing. Its 255 cm sweep is derived as min(400, 300 - capsule radius 42 - floor margin 3), keeping both capsule endpoints on the landing. All lanes, complete opening height and closed/open phases remain mandatory.')
    coverage=[dict(id='inset_main_axis',source='top_down_inset',routes=['main_south','main_primary','main_north','grand_stair']),
              dict(id='inset_secondary_spokes',source='top_down_inset',routes=['west_primary_spoke','east_primary_spoke'])]
    for side in ('west','east'):
        coverage.extend([
            dict(id='inset_'+side+'_side_main',source='top_down_inset',routes=[side+s for s in
                 ('_south_main','_main_objective','_main_north','_north_main')]),
            dict(id='inset_'+side+'_diagonal_flanks',source='top_down_inset',routes=[side+'_south_diagonal',side+'_north_diagonal']),
            dict(id='inset_'+side+'_perimeter_flank',source='top_down_inset',routes=[side+'_outer_flank']),
            dict(id='inset_'+side+'_south_raised_corner',source='top_down_inset',routes=[side+'_south_stair',side+'_wall_balcony']),
            dict(id='inset_'+side+'_north_raised_corner',source='top_down_inset',routes=[side+'_north_stair',side+'_wall_balcony']),
            dict(id='perspective_'+side+'_hall_terrace',source='main_perspective_interpreted',routes=[side+'_ground_portal_stair']),
            dict(id='authored_'+side+'_keep_gallery',source='unshown_interior_authored',routes=[side+s for s in
                 ('_gallery_stair','_gallery_aisle','_gallery_descent')]),
            dict(id='authored_'+side+'_hall_services',source='unshown_interior_authored',routes=[side+'_chamber_access',side+'_hall_side_aisle'])])
    coverage.extend([
        dict(id='retained_lower_city_tie_ins',source='existing_native_endpoints',routes=['lower_main_gate','west_approach','east_approach']),
        dict(id='perspective_grand_gate',source='main_perspective_interpreted',routes=['grand_portal']),
        dict(id='authored_commander_aisle',source='unshown_interior_authored',routes=['commander_aisle'])])
    baseline_file = ROOT/'artifacts/unreal/dutch-bastion/baseline.json'
    if castle_removals is None:
        historic = json.loads(baseline_file.read_text())
        removals = [dict(actor=row['name'], identity=castle_identity(row['state']),
                         stateHash=digest(row['state'])) for row in historic['actors']['authored']
                    if castle_identity(row['state'])]
    else:removals=castle_removals
    if len(removals) != 2267:
        raise ValueError('Expected exactly the retained 2,267 castle module actors')
    enclosures,preserved_enclosures=upper_enclosure_edits(baseline) if baseline and 'actors' in baseline else ([],[])
    old_routes=[{**r,'points':next((c['oldPointsCm'] for c in approach_corrections if c['route']==r['id']),r['points'])} for r in routes]
    crossing_semantics=lambda ledger:{(tuple(r['routes']),r['kind'],r['connects']) for r in ledger}
    if crossing_semantics(crossing_ledger(old_routes))!=crossing_semantics(crossing_ledger(routes)):
        raise ValueError('Approach correction introduced an unintended route crossing')
    from aegis_citadel_surfaces import approach_profile
    surface_profiles=[approach_profile(r) for r in routes if r['id'] in ('west_approach','east_approach')]
    data = dict(schemaVersion=1, units='unreal_centimetres', zone='aegis_capital',
        reference=dict(file=REFERENCE.name, sha256=reference_hash or sha(REFERENCE),
                       insetPixels=[614, 746, 334, 270], north='uphill',
                       fidelity='hand-traced topology and bespoke architecture; unshown interiors are authored'),
        recipeVersion=RECIPE_VERSION,
        wingFoundationGroundSurvey=wing_ground_witness(ground_survey,baseline) if baseline else None,
        sourceRecipes={name:sha(Path(__file__).with_name(name)) for name in
                       ('aegis_citadel_blueprint.py','aegis_citadel_mesh.py','build-aegis-citadel.py',
                        'stage-aegis-citadel.py','citadel_stage_contract.py',
                        'aegis_citadel_crown.py','aegis_citadel_spire_detail.py','aegis_citadel_standard_detail.py','aegis_citadel_wing_hierarchy.py','aegis_citadel_wing_footings.py','citadel_wing_support_evidence.py','survey-citadel-wing-support.py','aegis_citadel_statue.py','aegis_citadel_supports.py',
                        'aegis_citadel_lighting.py','aegis_citadel_terrain.py',
                        'aegis_citadel_terrain_readback.py','aegis_citadel_terrain_render_readback.py','render-aegis-citadel-source.py',
                        'aegis_citadel_surfaces.py','citadel_route_surface_evidence.py',
                        'shared_city_authoring.py','shared_city_sources.py','citadel_spawn_surface.py')},
        nodes=list(nodes.values()), routes=routes, gates=gates,
        routeSurfaceProfiles=surface_profiles,
        routeSurfaceHeightField=dict(file='artifacts/unreal/dutch-bastion/city-ground.json',
            sha256=sha(ROOT/'artifacts/unreal/dutch-bastion/city-ground.json'),
            actualNativeSurveyRequired=True) if baseline and 'actors' in baseline else None,
        crossingLedger=crossing_ledger(routes),
        lightingTreatment=dict(schemaVersion=2,theme='warm low-angle stone / cool mountain sky / practical fire pools',
            fixtures=lighting_fixture_edits(baseline),exposureUnits='native_luminance',
            expectedExtendedEV100=False,existingAtmospherePreserved=False,
            retainedDutchStreetFillPreserved=False,otherRetainedActorsPreserved=True,nativeReviewed=False,
            cloudFixture=cloud_fixture(baseline) if baseline and 'actors' in baseline else None),
        terrainCarves=terrain_carve_edits(baseline) if baseline and 'actors' in baseline else [],
        diagnosticReviewViews=[dict(id='street_hero',eyeCm=[-4000,-21500,11000],targetCm=[24500,0,8400],focalLengthMm=40)],
        reviewViews=[
            dict(id='hero',eyeCm=[-4000,-21500,12000],targetCm=[24500,0,7500],focalLengthMm=30),
            dict(id='front',eyeCm=[-7500,0,6000],targetCm=[24500,0,8500],focalLengthMm=32),
            dict(id='top_down',eyeCm=[23000,0,42000],targetCm=[23000,0,4210],focalLengthMm=32,orthographicWidthCm=44000),
            dict(id='central_plaza',eyeCm=[17200,-5000,7600],targetCm=[20800,0,4700],focalLengthMm=28),
            dict(id='grand_gate',eyeCm=[22800,-1500,5410],targetCm=[26000,0,8300],focalLengthMm=24),
            dict(id='west_balcony',eyeCm=[15500,-6000,5800],targetCm=[23500,-6500,5600],focalLengthMm=28),
            dict(id='east_balcony',eyeCm=[15500,6000,5800],targetCm=[23500,6500,5600],focalLengthMm=28),
            dict(id='commander_hall',eyeCm=[27100,-1100,6510],targetCm=[31400,0,7300],focalLengthMm=24)],
        architecturalLights=[dict(id='hall_sconce_'+str(i),pointCm=[x,y,7800],intensityCd=24000,
            sourceWatts=3000,attenuationRadiusCm=3600,temperatureK=2900,sourceRadiusCm=30,
            mobility='movable',castShadows=i in (0,1,6,7))
            for i,(x,y) in enumerate((x,y) for x in (26500,28400,30500,32600) for y in (-1600,1600))]+[
            dict(id='portal_reveal_'+str(i),pointCm=[26300,y,7200],intensityCd=2500,
                 sourceWatts=450,attenuationRadiusCm=1800,temperatureK=2800,sourceRadiusCm=25,
                 mobility='movable',castShadows=True)
            for i,y in enumerate((-1150,1150))]+[
            dict(id='gate_fire_pool_'+str(i),pointCm=p,intensityCd=1800,sourceWatts=360,
                attenuationRadiusCm=2000,temperatureK=2800,sourceRadiusCm=35,
                mobility='movable',castShadows=i<2)
            for i,p in enumerate(([13480,-1550,4550],[13480,1550,4550],
                [24000,-2500,6250],[24000,2500,6250]))]+[
            dict(id='court_fire_pool_'+str(i),pointCm=p,intensityCd=1000,sourceWatts=240,
                attenuationRadiusCm=1400,temperatureK=2900,sourceRadiusCm=25,
                mobility='movable',castShadows=False)
            for i,p in enumerate(([18200,-3600,4370],[18200,3600,4370],
                [22000,-6500,4370],[22000,6500,4370]))],
        retainedHallFixturePads=[[x,y,6010] for x in (28200,29300) for y in (-3900,3900)],
        performanceFormations=[dict(stage=stage,id=identity,positions=positions,minimumCaptureGapCm=50,
            minimumSpacingCm=150 if stage==0 else 300,captureReservationRadiusCm=650,nativeFloorVerified=False,nativeTraversalVerified=False,
            camera=dict(eye=[-14625,-150,3500] if stage==0 else [20300,0,17000] if stage==1 else [26350,0,8100],
                target=[-14625,-150,10] if stage==0 else [20300,0,4210] if stage==1 else [29000,0,6300],horizontalFovDegrees=68,
                rationale='Signed functional crowd view; hall camera is below the real vault. Actual actor/body LOS remains mandatory.'))
            for stage,identity,positions in [
                (0,'lower_crowd',[[x,y,10] for x in range(-15450,-13799,150) for y in (-300,-150,0)]),
                (1,'courtyard_crowd',[[x,y,4210] for x in range(17600,19101,300) for y in (-2900,-2500,-2100)]+
                    [[x,y,4210] for x in range(21400,22901,300) for y in (2100,2500,2900)]),
                (2,'keep_crowd',[[x,y,6010] for x in range(27900,29401,300) for y in (-1500,-1200,-900)]+
                    [[x,y,6010] for x in range(30100,31601,300) for y in (900,1200,1500)])]],
        physicalCorrections=dict(nativeVerified=False,routeWaypointsChanged=True,
            approachWaypointCorrections=approach_corrections,flightLandingCorrections=flight_corrections,
            crossingSemanticsPreserved=True,
            northPlazaApproaches=[dict(route=side+'_north_main',
                oldPointsCm=[[23700,sign*5550,4210],[23700,0,4210]],
                newPointsCm=[[23700,sign*5550,4210],[23100,sign*2400,4210],[23100,0,4210],[23700,0,4210]],
                widthCm=1200,rationale='The full-width ground lane enters the grand stair toe along its axis; it does not intersect the low rising underside.')
                for side,sign in [('west',-1),('east',1)]],
            supportCaps=dict(separationBelowWalkingDeckCm=2,walkingHeightsUnchanged=True,
                hallFoundationTopCm=5788,hallFloorTopCm=6010),
            stairMasonry=dict(widthCm='routeWidth + 400',foundationBottomCm=2400,
                policy='continuous_solid_with_convex_vaulted_route_subtraction',signedLaneMarginCm=47,
                minimumStraightHeadroomCm=350,apexHeadroomCm=650,
                ownFlightExcluded=True,otherSegmentsOfSameRouteReserved=True,
                spawnPadsAndGroundApproachesReserved=True),
            outerTower=dict(oldCenterCm=[14800,7440,4210],newCenterCm=[14800,7820,4210],oldWidthCm=1100,newWidthCm=1000,mirrored=True),
            galleryRail=dict(oldAxisOffsetFraction=.49,newAxisOffsetCm='routeWidth/2 + 20',rodRadiusCm=9,minimumInnerMarginCm=11),
            raisedPortalNiche=dict(oldYCm=3850,newYCm=4430,mirrored=True),
            portalReveals=dict(additionalOpeningWidthCm=40,signedRouteAndGateWidthUnchanged=True),
            forehallPiers=dict(oldXCm=27700,newXCm=27820),
            northTerraceArcade=dict(oldColumnYCm=[6500,7100],newColumnYCm=[6700,7300],oldArchYCm=6800,newArchYCm=6950,mirrored=True),
            throne=dict(oldPointCm=[32400,0,6010],newPointCm=[32630,0,6010],oldScale=1.8,newScale=1.5,
                rationale='Grounded rear hall placement preserves the commander function and clears both gallery descent corridors.'),
            plazaSpokes='Raised round gold rods are replaced by flat engraved inlays 0.2 cm above the floor with vertical floor normals.',
            landingJoint='Flat landing faces are clipped at neighboring rising/descending flight planes, with outer corner floor unions; support clearance includes other segments of the same route.'),
        stairConstruction=[dict(route=r['id'],clearWidthCm=r['width'],flights=[dict(
            startCm=a,endCm=b,runCm=round(math.hypot(b[0]-a[0],b[1]-a[1]),4),
            riseCm=b[2]-a[2],riserCount=math.ceil(abs(b[2]-a[2])/15),
            riserCm=abs(b[2]-a[2])/math.ceil(abs(b[2]-a[2])/15),
            treadCm=math.hypot(b[0]-a[0],b[1]-a[1])/math.ceil(abs(b[2]-a[2])/15))
            for a,b in zip(r['points'],r['points'][1:]) if abs(b[2]-a[2])>.1]) for r in routes if r['kind']=='stair'],
        referenceCoverage=coverage,
        upperMassing=dict(preservedThroughZCm=9000,originalHighestZCm=22220,coreCompressionHighestZCm=14200,highestZCm=17200,
            adaptation='The existing core retains its 142 m compression. Its separate final-coordinate crown has substantial unequal attached belfries, a central octagonal lantern and clustered slate spires to 172 m, with hipped ridges and broken coping. Pointed draped standards and the broad 19 m ceremonial panel clear the full portal. Ground objectives, route widths and endpoints remain fixed; explicit physicalCorrections repair the measured stair, rail and doorway intrusions.'),
        interpretation=dict(
            insetLandmarksPx=dict(primary=[788,865],westSecondary=[675,865],eastSecondary=[899,865],
                                  raisedCorners=[[663,769],[900,769],[663,967],[900,967]]),
            compositionMapping=dict(measuredDrawing=False,visualApproval=False,
                referenceFrontHandTrace=dict(uncertaintyPx=5,portalWidthPx=39,portalHeightPx=68,
                    coreWidthPx=220,courtyardWidthPx=268,outerFortressWidthPx=500,
                    portalBaseToHighestSpirePx=math.hypot(307-289.5,733-947)),
                interpretedDimensionsCm=dict(coreFacadeWidth=9200,facadeIncludingWingsWidth=14400,
                    mainPortalWidth=1800,mainPortalHeight=2600,courtyardLength=11800,courtyardWidth=14400,
                    keepHighestPointZ=17200,hallFloorZ=6010,centralUpperLancetWidth=1240,
                    centralUpperLancetHeight=2670,centralUpperRevealDepth=420,
                    broadCeremonialStandardWidth=1900),
                hierarchyCm=dict(courtFloor=4210,raisedInsetPlatforms=5410,hallFloor=6010,
                    playableGalleryFloor=7210,lowerCurtainHighest=9365.8094,
                    flankingKeepWingCrown=11124.0545,centralBelfryEaves=13150,
                    attachedCrownTowerTips=[14880,15150,15480,15780,16150,16680,17200]),
                mapping='The 92 m core is compared with the hand-traced front core, not the 144 m combined wings. Reference pixels are perspective ratios with uncertainty; centimetre dimensions are authored gameplay scale. Main-view silhouette, tower hierarchy, supported court, tracery and material detail still require combined native review.'),
            scaleAssumption=dict(measuredDrawing=False,courtLengthCm=11800,courtWidthCm=14400,
                                 minimumRouteWidthCm=600,mainRouteWidthCm=1800,capsuleRadiusCm=42,
                                 capsuleHalfHeightCm=96,maxStairRiserCm=15,minimumStairTreadCm=18),
            crossingConnectivity='Every centerline crossing and shared segment is explicitly enumerated in crossingLedger. Same-floor entries connect; height-separated entries do not. Raised routes connect through physical stairs.',
            stageCuts='Every lower-to-court crossing uses outer gate 0; every court-to-hall or gallery crossing uses inner gate 1. Closed gates restrict all parallel approaches.',
            primaryMonument=dict(landmarkCenterCm=[20800,0,4210],captureStandingPointCm=nodes['primary']['point'],
                baseWidthCm=1000,minimumDetourClearWidthCm=600,mainApproachWidthOutsidePlazaCm=1800,
                adaptation='The monument remains at the pictured radial center. A clear standing point 10 m west and explicit plaza detours keep its collision out of the capture target and every physical route.'),
            fidelityLimit='Inset arrows indicate intended lanes, not surveyed wall coordinates. Main-perspective terraces and unseen interiors are explicitly distinguished from the hand-traced inset.'),
        objectives=lower+[nodes['west_secondary']['point'], nodes['east_secondary']['point'],
                          nodes['primary']['point'], nodes['commander']['point']],
        optionalObjectives=[optional0, [22000, -4600, 4210], [31000, 5200, 6010]],
        gameplayPads=[
            dict(id='west_gate_mechanism',binding='gate_mechanisms',index=0,objectiveIndex=4,
                 footprintCentreFloorCm=[20100,-3900,4210],maximumFootprintRadiusCm=340,
                 maximumHeightCm=400,captureClearRadiusCm=650,minimumCaptureGapCm=50),
            dict(id='east_gate_mechanism',binding='gate_mechanisms',index=1,objectiveIndex=5,
                 footprintCentreFloorCm=[20100,3900,4210],maximumFootprintRadiusCm=340,
                 maximumHeightCm=400,captureClearRadiusCm=650,minimumCaptureGapCm=50),
            dict(id='lower_ammunition',binding='war_effort_props',index=0,preserveTransform=True),
            dict(id='courtyard_workshop',binding='war_effort_props',index=1,optionalIndex=1,
                 footprintCentreFloorCm=[22000,-4200,4210],maximumFootprintRadiusCm=165,
                 maximumHeightCm=180,minimumTargetGapCm=100),
            dict(id='hall_rally_brazier',binding='war_effort_props',index=2,optionalIndex=2,
                 footprintCentreFloorCm=[31400,5200,6010],maximumFootprintRadiusCm=85,
                 maximumHeightCm=230,minimumTargetGapCm=100)],
        teamSpawns=[spawn0, spawn1, [23000, 4500, 4210], [15300, -4500, 4210],
                    [31800, 1700, 6010], [27400, 0, 6010]],
        spawnApproaches=[
            dict(index=0,points=[spawn0],widthCm=600,preserveLowerCity=True,groundGradient=[.5,0]),
            dict(index=1,points=[spawn1],widthCm=600,preserveLowerCity=True,groundGradient=[0,0]),
            dict(index=2,points=[[23000,4500,4210],[23700,4500,4210],[23700,5550,4210]],
                 widthCm=600,joinsRoute='east_main_north',groundGradient=[0,0]),
            dict(index=3,points=[[15300,-4500,4210],[14800,-4500,4210],[14800,-3500,4210]],
                 widthCm=600,joinsRoute='west_south_stair',groundGradient=[0,0]),
            dict(index=4,points=[[31800,1700,6010],[30600,1700,6010]],
                 widthCm=600,joinsRoute='east_chamber_access',groundGradient=[0,0]),
            dict(index=5,points=[[27400,0,6010]],widthCm=600,joinsRoute='commander_aisle',groundGradient=[0,0])],
        editMask=dict(removeActors=removals, preservedLowerCity=True,
                      upperBounds=UPPER_BOUNDS,upperEnclosureEdits=enclosures,
                      approachEnclosureBounds=APPROACH_ENCLOSURE_BOUNDS,
                      retainedEnclosureEvidence=preserved_enclosures,
                      approachTieIns=['lower_breach', 'west_approach', 'east_approach']),
        rooms=[dict(id='forehall', bounds=[[26000,-4300,6010],[28900,4300,10100]], function='gathering_and_defense'),
               dict(id='throne_hall', bounds=[[28900,-4300,6010],[33400,4300,11500]], function='commander'),
               dict(id='west_archive', bounds=[[28800,-6800,6010],[33000,-4300,8800]], function='archives_and_war_table'),
               dict(id='east_treasury', bounds=[[28800,4300,6010],[33000,6800,8800]], function='treasury_and_reliquary')],
        baseline={k:v for k,v in baseline.items() if k!='actors'} if baseline else None,
        acceptance=dict(geometry=False, traversal=False, visual=False,
                                          eighteenPerRealm=False, published=False))
    data['architecturalLights']=shadowed_practical_requests(data['architecturalLights'])
    data['signature'] = digest({k:v for k,v in data.items() if k not in ('signature','acceptance')})
    data['revision'] = data['signature'][:12]
    validate(data)
    return data


def validate(data):
    if data.get('signature') != digest({k:v for k,v in data.items() if k not in ('signature','revision','acceptance')}):
        raise ValueError('Reviewed topology or blueprint identity changed')
    if data['units'] != 'unreal_centimetres' or len(data['objectives']) != 8 or len(data['optionalObjectives']) != 3 or len(data['teamSpawns']) != 6:
        raise ValueError('Incorrect native battlefield interface')
    nodes = {n['id']:n for n in data['nodes']}
    if len(nodes) != len(data['nodes']) or len({r['id'] for r in data['routes']}) != len(data['routes']):
        raise ValueError('Duplicate graph identity')
    for route in data['routes']:
        if route['points'][0] != nodes[route['start']]['point'] or route['points'][-1] != nodes[route['end']]['point']:
            raise ValueError('Route endpoints disagree with topology')
        if route['width'] < 600 or route['gate'] not in (None,0,1):
            raise ValueError('Unapproved corridor or stage gate')
    approaches=data.get('spawnApproaches',[])
    if (data.get('recipeVersion',0)>=5 or approaches) and (len(approaches)!=len(data['teamSpawns']) or
            {row.get('index') for row in approaches}!=set(range(len(data['teamSpawns'])))):
        raise ValueError('Every retained spawn needs one explicit ground pad and approach')
    route_by_id={row['id']:row for row in data['routes']}
    from citadel_spawn_surface import gradient,validate_retained_surfaces
    for row in approaches:
        gradient(row,data.get('recipeVersion',0))
        index=row['index'];points=row['points'];width=row['widthCm']
        if (type(index) is not int or not points or points[0]!=data['teamSpawns'][index] or
                type(width) not in (int,float) or not math.isfinite(width) or width<600 or
                any(len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p)
                    for p in points)):
            raise ValueError('Spawn pad differs from its anchor or has invalid clearance')
        if index<2:
            if row.get('preserveLowerCity') is not True or len(points)!=1:
                raise ValueError('Lower-city spawn authoring must preserve the surveyed scene')
            continue
        route=route_by_id.get(row.get('joinsRoute'))
        if not route or width>route['width'] or any(p[2]!=points[0][2] for p in points):
            raise ValueError('Upper spawn approach needs a full-width ground route connection')
        end=points[-1];connected=end in route['points']
        for a,b in zip(route['points'],route['points'][1:]):
            delta=[b[j]-a[j] for j in range(3)];length2=sum(v*v for v in delta)
            if length2<.0001:continue
            t=sum((end[j]-a[j])*delta[j] for j in range(3))/length2
            if 0<=t<=1 and math.dist(end,[a[j]+delta[j]*t for j in range(3)])<.01:
                connected=True
        if not connected:
            raise ValueError('Spawn approach does not meet its declared playable route')
    if data.get('recipeVersion',0)>=6 and (data.get('baseline') or {}).get('packageHashes'):
        validate_retained_surfaces(data['baseline'],approaches)
    if [g['index'] for g in data['gates']] != [0,1] or [len(g['leaves']) for g in data['gates']] != [3,5]:
        raise ValueError('A flank or gallery stage crossing is missing its physical gate')
    if len(data['editMask']['removeActors']) != 2267:
        raise ValueError('Unbounded citadel replacement')
    if data.get('recipeVersion',0)>=6 and data['editMask'].get('approachEnclosureBounds')!=APPROACH_ENCLOSURE_BOUNDS:
        raise ValueError('Approach enclosure masks differ from the fixed source reservations')
    for edit in data['editMask']['upperEnclosureEdits']:enclosure_edit_bounds(data['editMask'],edit)
    pads=data['gameplayPads']
    if {(p['binding'],p['index']) for p in pads}!={('gate_mechanisms',0),('gate_mechanisms',1),
            ('war_effort_props',0),('war_effort_props',1),('war_effort_props',2)}:
        raise ValueError('Every gameplay prop needs a signed pad or retained transform')
    for pad in pads:
        if pad.get('preserveTransform'):
            if (pad['binding'],pad['index'])!=('war_effort_props',0):
                raise ValueError('Only lower-city ammunition retains its surveyed transform')
            continue
        point=pad['footprintCentreFloorCm'];radius=pad['maximumFootprintRadiusCm']
        if not route_clearance(data,point,radius,pad['maximumHeightCm']):
            raise ValueError('Gameplay pad intersects a reserved route: '+pad['id'])
        if pad['binding']=='gate_mechanisms':
            anchor=data['objectives'][pad['objectiveIndex']]
            minimum=radius+pad['captureClearRadiusCm']+pad['minimumCaptureGapCm']
        else:
            anchor=data['optionalObjectives'][pad['optionalIndex']]
            minimum=radius+pad['minimumTargetGapCm']
        if math.dist(point[:2],anchor[:2])<minimum:
            raise ValueError('Gameplay prop obstructs its playable capture target: '+pad['id'])
    covered=set()
    for group in data['referenceCoverage']:
        if not group['routes'] or any(key not in {r['id'] for r in data['routes']} for key in group['routes']):
            raise ValueError('Unaccounted reference route group')
        covered.update(group['routes'])
    if covered!={r['id'] for r in data['routes']}:
        raise ValueError('A route lacks reference or authored-extension provenance')


def svg(data):
    """Hand-traced architectural sheet; all drawn routes are generated from the ledger."""
    def xy(p): return 670+p[1]*.033, 940-(p[0]-11000)*.033
    content = ['<svg xmlns="http://www.w3.org/2000/svg" width="1340" height="1250" viewBox="0 0 1340 1250">',
               '<rect width="1340" height="1250" fill="#151e28"/>',
               '<style>text{font-family:Segoe UI,sans-serif;fill:#e6dbbf} .label{font-size:11px}</style>',
               '<text x="42" y="45" font-size="28">Bastion of Aegis — reference citadel</text>',
               '<text x="42" y="72" font-size="14">X uphill / Y east · centimetres · three gate leaves outside, five at the hall · 18 per realm</text>']
    for room in data['rooms']:
        a,b=room['bounds'];x,y=xy([b[0],a[1],0]);w=(b[1]-a[1])*.033;h=(b[0]-a[0])*.033
        content.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#344553" stroke="#bd9c66"/>')
        content.append(f'<text x="{x+8}" y="{y+20}" class="label">{html.escape(room["id"])}</text>')
    x,y=xy([26000,-7200,0]);content.append(f'<rect x="{x}" y="{y}" width="475.2" height="389.4" fill="#22303b" stroke="#a98a54" stroke-width="6"/>')
    cx,cy=xy([20800,0,0])
    for radius in (900,1900,3000):
        content.append(f'<circle cx="{cx}" cy="{cy}" r="{radius*.033}" fill="none" stroke="#71828d" stroke-width="2"/>')
    colors={'main':'#e7c17d','flank':'#c39456','stair':'#83b4ca','balcony':'#91aac0','interior':'#baa3cf'}
    for r in data['routes']:
        points=' '.join(f'{x:.2f},{y:.2f}' for x,y in map(xy,r['points']))
        dash=' stroke-dasharray="6 4"' if r['kind']=='flank' else ''
        content.append(f'<polyline points="{points}" fill="none" stroke="{colors[r["kind"]]}" stroke-width="{3 if r["kind"]=="main" else 2}"{dash}><title>{html.escape(r["id"])}; width {r["width"]} cm; gate {r["gate"]}</title></polyline>')
    for n in data['nodes']:
        x,y=xy(n['point']);radius=9 if n['kind'] in ('primary','secondary') else 4
        content.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="#151e28" stroke="#f0c37b" stroke-width="2"/><text x="{x+8}" y="{y-6}" class="label">{html.escape(n["id"])}</text>')
    for row in data.get('spawnApproaches',[]):
        if row['index']<2:continue
        x,y=xy(row['points'][0]);half=row['widthCm']*.033/2
        points=' '.join(f'{xx:.2f},{yy:.2f}' for xx,yy in map(xy,row['points']))
        content.append(f'<polyline points="{points}" fill="none" stroke="#77c8bc" stroke-width="2"/>')
        content.append(f'<rect x="{x-half}" y="{y-half}" width="{half*2}" height="{half*2}" fill="none" stroke="#77c8bc"><title>Retained spawn {row["index"]}: full-width ground pad and route exit</title></rect>')
    for pad in data['gameplayPads']:
        if pad.get('preserveTransform'):continue
        x,y=xy(pad['footprintCentreFloorCm']);r=pad['maximumFootprintRadiusCm']*.033
        content.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#305244" stroke="#9fc8a1"><title>{html.escape(pad["id"])}: signed maximum footprint; actual native bounds required</title></circle>')
    for g in data['gates']:
        for leaf in g['leaves']:
            x,y=xy(leaf['point']);w=leaf['width']*.033
            content.append(f'<line x1="{x-w/2}" x2="{x+w/2}" y1="{y}" y2="{y}" stroke="#dc7169" stroke-width="8"><title>{g["id"]} physical gate, floor {leaf["point"][2]} cm</title></line>')
    content.extend(['<text x="42" y="1010" font-size="16">Gold: main routes · dashed: flank routes · blue: stairs and raised balconies · purple: interior access</text>',
                    '<text x="42" y="1040" font-size="14">Floor: court 4210 cm · raised platforms 5410 cm · hall 6010 cm · interior galleries 7210 cm</text>',
                    '<text x="42" y="1070" font-size="14">Every raised platform has physical stair access. Reference proportions interpreted for playable scale; native evidence pending.</text>',
                    '<text x="42" y="1120" font-size="14">Authored core 92 m / wings 144 m / court 118 × 144 m / highest point 172 m / hall floor 60.1 m.</text>',
                    '<text x="42" y="1150" font-size="14">Front inset hand trace (±5 px): core 220 / portal 39 / court 268 / outer extent 500 / skyline rise 214.7 px.</text>',
                    '<text x="42" y="1180" font-size="14">Central upper lancet 12.4 × 26.7 m, 4.2 m reveal; main gate 18 × 26 m. Scale and visual approval remain pending.</text>', '</svg>'])
    return '\n'.join(content)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--wing-ground-survey',type=Path)
    args=parser.parse_args();baseline=json.loads(args.baseline.read_text()) if args.baseline else None
    data=plan(baseline,ground_survey=args.wing_ground_survey);directory=OUT/data['revision'];directory.mkdir(parents=True,exist_ok=True)
    (directory/'blueprint.json').write_text(json.dumps(data,indent=2)+'\n')
    (directory/'architectural-sheet.svg').write_text(svg(data))
    (OUT/'current.json').write_text(json.dumps(dict(revision=data['revision'],directory=str(directory)),indent=2)+'\n')
    print(f'{directory}: {len(data["nodes"])} nodes, {len(data["routes"])} routes, 2267 bounded removals')


if __name__=='__main__': main()
