"""Offline fitted architecture for concave and multiple-frontage city parcels.

Shapely is an authoring dependency only. Native mesh data uses the same private
composite importer as the pilot. Exporting geometry never grants placement.
"""
import json
import math
import sys
import hashlib
from dutch_bastion import OUT, digest
sys.path.insert(0,str(OUT/'python'))
from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon, LineString, Point, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from dutch_city_ground import paving_height as height
from dutch_architecture import Mesh, MATERIALS, facade, window
from dutch_mesh_clipping import facade_envelope, clip_mesh, city_envelopes
from shapely import affinity


def polygons(geometry):
    if geometry.geom_type=='Polygon':
        if geometry.area>1e-9: yield geometry
    elif hasattr(geometry,'geoms'):
        for part in geometry.geoms: yield from polygons(part)


def slab(mesh,geometry,bottom,top,material):
    """Constrained triangles retain reentrant corners and interior openings."""
    for polygon in polygons(geometry):
        polygon=orient(polygon,sign=1)
        for triangle in constrained_delaunay_triangles(polygon).geoms:
            points=list(orient(triangle,sign=1).exterior.coords)[:-1]
            mesh.face([[x,y,top] for x,y in points],material)
            mesh.face([[x,y,bottom] for x,y in reversed(points)],material)
        for ring in (polygon.exterior,*polygon.interiors):
            points=list(ring.coords)
            for a,b in zip(points,points[1:]):
                mesh.face([[*a,bottom],[*b,bottom],[*b,top],[*a,top]],material)


def main_front(lot):
    # Remove collinear overlay vertices only; the micrometre tolerance is far
    # below the 1cm party-wall limit and does not flatten a winding frontage.
    polygon=orient(Polygon(lot['polygon']).simplify(1e-7,preserve_topology=True),sign=1)
    front=unary_union([LineString(p) for p in lot.get('frontages',[lot['polygon'][:2]])])
    edges=list(zip(list(polygon.exterior.coords),list(polygon.exterior.coords)[1:]))
    choices=[(math.dist(a,b),index,a,b) for index,(a,b) in enumerate(edges)
             if front.buffer(1e-5).covers(LineString([a,b])) and math.dist(a,b)>=3]
    if not choices:
        # A narrow bend can be an attached turret/corner wing. Its street shell
        # still follows the parcel exactly; it does not get a fictitious door.
        choices=[(math.dist(a,b),index,a,b) for index,(a,b) in enumerate(edges)]
    _,index,a,b=max(choices,key=lambda v:(v[0],-v[1]))
    return polygon,front,index,a,b


def terrain_samples(polygon,spacing=1.0):
    boundary=list(polygon.exterior.coords);points=list(boundary)
    for a,b in zip(boundary,boundary[1:]):
        count=max(1,math.ceil(math.dist(a,b)/spacing))
        points.extend((a[0]+(b[0]-a[0])*i/count,a[1]+(b[1]-a[1])*i/count) for i in range(count))
    lo_x,lo_y,hi_x,hi_y=polygon.bounds
    for x in range(math.floor(lo_x),math.ceil(hi_x)+1):
        for y in range(math.floor(lo_y),math.ceil(hi_y)+1):
            if polygon.covers(Point(x,y)): points.append((x,y))
    return [height(x,y) for x,y in points]


def house(lot,world_envelope=None):
    footprint,street,front_index,a,b=main_front(lot)
    if not footprint.is_valid or footprint.interiors: raise ValueError('Invalid house footprint')
    width=math.dist(a,b);dx,dy=(b[0]-a[0])/width,(b[1]-a[1])/width
    local=lambda p:((p[0]-a[0])*dx+(p[1]-a[1])*dy,-(p[0]-a[0])*dy+(p[1]-a[1])*dx)
    polygon=orient(Polygon([local(p) for p in list(footprint.exterior.coords)[:-1]]),sign=1)
    samples=terrain_samples(footprint)
    base=max(samples)+.06
    if lot['publicInterior'] and max(samples)-height(a[0]+(b[0]-a[0])*.25,a[1]+(b[1]-a[1])*.25)>.30:
        raise ValueError('Public room requires level entrance and floor')
    eave=lot['storeys']*3.;mesh=Mesh()
    bottom=min(samples)-base-1
    # A fitted stone basement carries level occupied floors above retained
    # terrain. Each closed entrance is set at its own ground elevation.
    core=polygon.buffer(-.25,join_style='mitre')
    # The foundation must end below the timber slab. Coincident top faces made
    # the foundation's stone material flicker through occupied room floors.
    slab(mesh,core if not core.is_empty else polygon,bottom,-.12,'limestone')
    # Slab edges terminate inside the masonry, never on its exposed wall plane.
    # Otherwise every storey's timber edge z-fights with the brick facade.
    floorplate=polygon.buffer(-.12,join_style='mitre')
    for floor in range(lot['storeys']): slab(mesh,floorplate,floor*3-.12,floor*3,'timber')
    # Roofs are clipped to the exact parcel and split on their ridge, rather
    # than spanning a concave court with an unconstrained triangle fan.
    bays=max(1,math.ceil(width/8));bay_width=width/bays
    def rise(x):
        if x<0 or x>width: return eave
        u=x%bay_width
        return eave+1.24*min(u,bay_width-u)
    min_x,min_y,max_x,max_y=polygon.bounds
    ridges=[i*bay_width/2 for i in range(bays*2+1)]
    divisions=sorted({min_x,max_x,*[x for x in ridges if min_x<x<max_x]})
    for left,right in zip(divisions,divisions[1:]):
        patch=polygon.intersection(box(left,min_y-1,right,max_y+1))
        for part in polygons(patch):
            for triangle in constrained_delaunay_triangles(part).geoms:
                points=list(orient(triangle,sign=1).exterior.coords)[:-1]
                mesh.face([[x,y,rise(x)] for x,y in points],'roof')
    points=list(polygon.exterior.coords)
    original=list(footprint.exterior.coords)
    exposed=unary_union([street,*[LineString(p) for p in lot.get('courtFrontages',[])]])
    # Every wall keeps its outside plane exactly on the shared parcel edge.
    # Roof infill reaches the pitched roof even along oblique corner walls.
    for index,(p,q) in enumerate(zip(points,points[1:])):
        length=math.dist(p,q);direction=((q[0]-p[0])/length,(q[1]-p[1])/length)
        exterior=exposed.buffer(1e-5).covers(LineString([original[index],original[index+1]]))
        if length>=3 and exterior:
            count=max(1,math.ceil(length/8));part=length/count
            for segment in range(count):
                offset=segment*part;wall=Mesh()
                t=(offset+part*.25)/length
                ga,gb=original[index],original[index+1]
                doorstep=height(ga[0]+(gb[0]-ga[0])*t,ga[1]+(gb[1]-ga[1])*t)+.06-base
                public=bool(lot['publicInterior']) and index==front_index and segment==0
                facade(wall,part,eave,lot['storeys'],public,lot['palette'],door_z=0 if public else doorstep,min_z=bottom)
                mesh.append(wall,[p[j]+direction[j]*offset for j in (0,1)],direction)
        else:
            strip=LineString([p,q]).buffer(.24,cap_style='flat').intersection(polygon)
            slab(mesh,strip,bottom,0,'limestone');slab(mesh,strip,0,eave,'brick')
            if exterior and length>.9:
                wall=Mesh()
                for floor in range(lot['storeys']): window(wall,length/2,floor*3+.7,min(.7,length*.6),1.6,depth=-.20)
                mesh.append(wall,p,direction)
        # Split exactly where the roof's height function changes slope.
        cuts=[0,1]
        if abs(q[0]-p[0])>1e-8:
            cuts += [(x-p[0])/(q[0]-p[0]) for x in ridges if 0<(x-p[0])/(q[0]-p[0])<1]
        for lo,hi in zip(sorted(cuts),sorted(cuts)[1:]):
            u=[p[j]+(q[j]-p[j])*lo for j in (0,1)];v=[p[j]+(q[j]-p[j])*hi for j in (0,1)]
            nx,ny=-direction[1]*.24,direction[0]*.24
            mesh.face([[*u,eave],[*v,eave],[*v,rise(v[0])],[*u,rise(u[0])]],'brick')
            mesh.face([[u[0]+nx,u[1]+ny,eave],[u[0]+nx,u[1]+ny,rise(u[0])],
                       [v[0]+nx,v[1]+ny,rise(v[0])],[v[0]+nx,v[1]+ny,eave]],'brick')
    # The primary street elevation uses the same original Dutch gable vocabulary.
    total_width=width;width=bay_width;peak=width*.62;gable=Mesh()
    if lot['gable']=='step':
        profile=[[0,eave]]
        for i in range(5): profile.extend([[width*i/10,eave+peak*(i+1)/5+.18],[width*(i+1)/10,eave+peak*(i+1)/5+.18]])
        profile.extend([[width-x,z] for x,z in reversed(profile[:-1])]);profile.append([width,eave])
    elif lot['gable']=='bell':
        left=[[width*t/2,eave+peak*(.5-.5*math.cos(math.pi*t))+.15] for t in [i/12 for i in range(13)]]
        profile=[[0,eave]]+left+[[width-x,z] for x,z in reversed(left[:-1])]+[[width,eave]]
    else: profile=[[0,eave],[width/2,eave+peak+.18],[width,eave]]
    gable.profile(profile,-.06,.25,'plaster' if lot['palette']==4 else 'brick')
    for p,q in zip(profile,profile[1:]):
        if math.dist(p,q)>1e-5: gable.profile([p,q,[q[0],q[1]+.1],[p[0],p[1]+.1]],-.12,.30,'limestone')
    if width>=3: window(gable,width/2,eave+.30,.75,1,depth=-.22)
    for bay in range(bays): mesh.append(gable,(bay*width,0),(1,0))
    centre=polygon.representative_point()
    chimney=box(centre.x-.3,centre.y-.3,centre.x+.3,centre.y+.3)
    if polygon.covers(chimney):
        slab(mesh,chimney,eave,eave+peak+1.1,'brick')
        slab(mesh,chimney.buffer(.06,join_style='mitre').intersection(polygon),eave+peak+1,eave+peak+1.18,'limestone')
    local_exposed=unary_union([LineString([local(p) for p in chain])
                              for chain in lot.get('frontages',[lot['polygon'][:2]])+lot.get('courtFrontages',[])])
    envelope=(facade_envelope(polygon,local_exposed) if world_envelope is None else
              affinity.affine_transform(world_envelope,[dx,dy,-dy,dx,-a[0]*dx-a[1]*dy,a[0]*dy-a[1]*dx]))
    mesh,clipped=clip_mesh(mesh,envelope)
    data=mesh.export(a,(dx,dy),base);door=width*.25
    # Preserve hard normals and UV seams while sharing identical triangle
    # corners. This reduces import memory without changing visible geometry.
    compact=dict(positions=[],normals=[],uvs=[],indices=[],triangleMaterials=data['triangleMaterials']);vertices={}
    for index in data['indices']:
        key=tuple(data['positions'][index]+data['normals'][index]+data['uvs'][index])
        if key not in vertices:
            vertices[key]=len(compact['positions'])
            for field in ('positions','normals','uvs'): compact[field].append(data[field][index])
        compact['indices'].append(vertices[key])
    data=compact
    return dict(id=lot['id'],actorId=lot['actorId'],position=[a[1]*100,a[0]*100,base*100],mesh=data,
                frame=[list(a),list(b)],
                materials=list(MATERIALS),palette=lot['palette'],publicInterior=lot['publicInterior'],
                entrance=[(a[1]+dy*door)*100,(a[0]+dx*door)*100,base*100],direction=[dx,-dy],
                width=total_width,depth=max_y,foundationRelief=max(samples)-min(samples),facadeBays=bays,
                clippedTriangles=clipped,
                triangles=len(data['indices'])//3,sourceSignature=digest(lot),
                acceptance=dict(native=False,visual=False,traversal=False))


def compile_architecture():
    plan=json.loads((OUT/'city-plan.json').read_text());rows=[];pending=[]
    envelopes=city_envelopes([lot for block in plan['blocks'] for lot in block['lots']])
    directory=OUT/'city-geometry';directory.mkdir(exist_ok=True)
    for block in plan['blocks']:
        for lot in block['lots']:
            try:
                row=house(lot,envelopes[lot['id']]);row['block']=block['id'];row['district']=block['district']
                data=json.dumps(row.pop('mesh'),separators=(',',':')).encode()
                sha=hashlib.sha256(data).hexdigest();file=directory/(sha+'.json')
                if file.exists() and hashlib.sha256(file.read_bytes()).hexdigest()!=sha: raise RuntimeError('Edited immutable geometry')
                if not file.exists(): file.write_bytes(data)
                row['meshFile']=file.relative_to(OUT).as_posix();row['meshSha256']=sha;rows.append(row)
            except ValueError as error: pending.append(dict(id=lot['id'],block=block['id'],reason=str(error)))
    result=dict(schemaVersion=1,planSignature=digest(plan),houses=rows,pending=pending,geometrySignature=digest(rows),
                acceptance=dict(native=False,visual=False,traversal=False,live=False))
    (OUT/'city-architecture.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(authoredHouses=len(rows),pendingParcels=len(pending),triangles=sum(r['triangles'] for r in rows))))


if __name__=='__main__': compile_architecture()
