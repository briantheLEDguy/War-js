"""Clip finished architectural triangles, retaining normals and texture coordinates."""
import math
from shapely import constrained_delaunay_triangles, set_precision
from shapely.geometry import Polygon, LineString, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.strtree import STRtree


def polygon_parts(geometry):
    if geometry.geom_type=='Polygon':
        if geometry.area>1e-12: yield geometry
    elif hasattr(geometry,'geoms'):
        for part in geometry.geoms: yield from polygon_parts(part)


def facade_envelope(polygon, exposed, projection=.30):
    """Offset only exposed walls; party-wall planes never move into a neighbour.

    Each offset edge meets the adjoining wall's infinite plane. This mitres
    stone bands at oblique joins instead of using rectangular mesh bounds.
    """
    points=list(orient(polygon,sign=1).exterior.coords)[:-1]
    lines=[]
    for a,b in zip(points,points[1:]+points[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        offset=projection if exposed.buffer(1e-5).covers(LineString([a,b])) else 0
        lines.append(((a[0]+dy/length*offset,a[1]-dx/length*offset),(dx,dy)))
    vertices=[]
    for i,(q,v) in enumerate(lines):
        p,u=lines[i-1];cross=u[0]*v[1]-u[1]*v[0]
        if abs(cross)<1e-10:
            vertices.append(q);continue
        t=((q[0]-p[0])*v[1]-(q[1]-p[1])*v[0])/cross
        vertices.append((p[0]+t*u[0],p[1]+t*u[1]))
    result=Polygon(vertices)
    if not result.is_valid: result=result.buffer(0)
    # The shell itself must never be trimmed away by an acute offset join.
    return unary_union([polygon,result.intersection(polygon.buffer(projection,join_style='mitre',mitre_limit=2))])


def clip_triangle(vertices, boundary):
    """Sutherland-Hodgman in XY; interpolate all remaining vertex attributes."""
    result=vertices
    coords=list(orient(boundary,sign=1).exterior.coords)
    for a,b in zip(coords,coords[1:]):
        def side(p): return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
        source=result;result=[]
        if not source: break
        for p,q in zip(source,source[1:]+source[:1]):
            dp,dq=side(p),side(q);inside_p,inside_q=dp>=-1e-9,dq>=-1e-9
            if inside_p: result.append(p)
            if inside_p!=inside_q:
                t=dp/(dp-dq)
                result.append([p[i]+t*(q[i]-p[i]) for i in range(len(p))])
    return result


def city_envelopes(lots):
    """Reserve opaque cores first, then allocate small exterior trim overlaps.

    A stable identity breaks ties at a concave corner; adjacent houses cannot
    both own the same projecting stone band. No core or party wall is removed.
    """
    lots=sorted(lots,key=lambda r:r['id'])
    cores=[set_precision(Polygon(row['polygon']),1e-7) for row in lots]
    core_tree=STRtree(cores);raw=[]
    for row,core in zip(lots,cores):
        exposed=unary_union([LineString(p) for p in row.get('frontages',[row['polygon'][:2]])+row.get('courtFrontages',[])])
        raw.append(unary_union(list(polygon_parts(set_precision(facade_envelope(core,exposed),1e-7)))))
    tree=STRtree(raw);owned=[]
    for i,envelope in enumerate(raw):
        exclusions=[cores[j] for j in core_tree.query(envelope,predicate='intersects') if j!=i]
        exclusions.extend(owned[j] for j in tree.query(envelope,predicate='intersects') if j<i)
        clipped=envelope.difference(unary_union(exclusions),grid_size=1e-7)
        if cores[i].difference(clipped).area>1e-5: raise ValueError('Trim ownership removed a building core')
        owned.append(unary_union(list(polygon_parts(clipped))))
    return {row['id']:geometry for row,geometry in zip(lots,owned)}


def clip_mesh(mesh, envelope):
    """Works for horizontal, sloped and vertical faces, including concave lots."""
    from dutch_architecture import Mesh, MATERIALS
    cells=list(constrained_delaunay_triangles(envelope).geoms);tree=STRtree(cells)
    result=Mesh();changed=0;tolerant=envelope.buffer(1e-8)
    for offset in range(0,len(mesh.indices),3):
        indices=mesh.indices[offset:offset+3]
        points=[mesh.positions[i] for i in indices]
        uv=[mesh.uvs[i] for i in indices];material=MATERIALS[mesh.slots[offset//3]]
        projected=Polygon([p[:2] for p in points])
        if projected.area<1e-12:
            projected=LineString([p[:2] for p in points]).convex_hull
        if tolerant.covers(projected):
            result.face(points,material,uv);continue
        changed+=1;seen=set()
        for index in tree.query(projected):
            clipped=clip_triangle([p+t for p,t in zip(points,uv)],cells[index])
            for j in range(1,len(clipped)-1):
                triangle=[clipped[0],clipped[j],clipped[j+1]]
                key=tuple(sorted(tuple(round(x,8) for x in p[:3]) for p in triangle))
                if key in seen: continue
                seen.add(key)
                result.face([p[:3] for p in triangle],material,[p[3:] for p in triangle])
    return result,changed


def clip_legacy_roads(source, retained):
    """Keep the source road winding, UVs and authored upward normals."""
    from dutch_architecture import Mesh
    if any(n!=[0,0,1] for n in source['normals']):
        raise ValueError('Review changed source road normals before clipping')
    mesh=Mesh()
    for i in range(0,len(source['indices']),3):
        indices=source['indices'][i:i+3]
        mesh.face([[source['positions'][j][1]/100,source['positions'][j][0]/100,source['positions'][j][2]/100] for j in indices],
                  'paving',[source['uvs'][j] for j in indices])
    mesh,_=clip_mesh(mesh,retained)
    result=mesh.export((0,0),(1,0),0)
    result['normals']=[[0,0,1] for _ in result['positions']]
    result['triangleMaterials']=[0]*len(result['triangleMaterials'])
    return result


def retained_road_region(surface_domain, houses, interiors, decks):
    # Decks remain necessary collision geometry even where their visual bridge
    # is supplied by another actor. Room exclusions always take precedence.
    replaced=surface_domain.intersection(box(-150,-150,150,150)).difference(decks)
    return box(-1000,-1000,1000,1000).difference(replaced.union(houses).union(interiors))
