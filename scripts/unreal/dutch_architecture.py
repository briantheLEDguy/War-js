"""Authored Dutch masonry, gables and shopfronts fitted to exact party-wall lots.

Produces textured architectural mesh data for the existing native composite
mesh importer. No engine primitive or substitute building assets are used.
"""
import json
import math
from dutch_bastion import OUT, digest, lerp, validate
from capital_geography import height

MATERIALS = ('brick', 'limestone', 'roof', 'timber', 'glass', 'iron', 'paving', 'plaster')


class Mesh:
    def __init__(self):
        self.positions=[]; self.indices=[]; self.normals=[]; self.uvs=[]; self.slots=[]

    def face(self, points, material, uv=None):
        if len(points)>4: raise ValueError('Triangulate authored profiles before export')
        for k in range(1,len(points)-1):
            pts=[points[0],points[k],points[k+1]]
            u=[pts[1][i]-pts[0][i] for i in range(3)]
            v=[pts[2][i]-pts[0][i] for i in range(3)]
            n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            length=math.sqrt(sum(c*c for c in n))
            if length<1e-9: continue
            n=[c/length for c in n]
            start=len(self.positions)
            self.positions.extend(pts); self.normals.extend([n]*3)
            if uv:
                self.uvs.extend([uv[0],uv[k],uv[k+1]])
            elif abs(n[2])<.01:
                # Keep masonry courses horizontal on every wall orientation.
                self.uvs.extend([[(p[0]*-n[1]+p[1]*n[0])/1.6,-p[2]/1.6] for p in pts])
            else:
                axes=sorted(range(3),key=lambda i:abs(n[i]))[:2]
                self.uvs.extend([[p[axes[0]]/1.6,-p[axes[1]]/1.6] for p in pts])
            self.indices.extend(range(start,start+3)); self.slots.append(MATERIALS.index(material))

    def prism(self, polygon, bottom, top, material):
        # Convex architectural profiles only; exterior and interior faces retain
        # their own normals so rooms are closed without two-sided materials.
        lo=[[x,y,bottom] for x,y in polygon]; hi=[[x,y,top] for x,y in polygon]
        for i in range(1,len(polygon)-1):
            self.face([hi[0],hi[i],hi[i+1]],material)
            self.face([lo[0],lo[i+1],lo[i]],material)
        for i in range(len(polygon)):
            j=(i+1)%len(polygon)
            self.face([lo[i],lo[j],hi[j],hi[i]],material)

    def box(self,x0,x1,y0,y1,z0,z1,material):
        if min(x1-x0,y1-y0,z1-z0)<=1e-6: return
        self.prism([[x0,y0],[x1,y0],[x1,y1],[x0,y1]],z0,z1,material)

    def append(self,other,origin,direction):
        dx,dy=direction;offset=len(self.positions)
        self.positions.extend([[origin[0]+dx*x-dy*y,origin[1]+dy*x+dx*y,z] for x,y,z in other.positions])
        self.normals.extend([[dx*x-dy*y,dy*x+dx*y,z] for x,y,z in other.normals])
        self.indices.extend(i+offset for i in other.indices);self.uvs.extend(other.uvs);self.slots.extend(other.slots)

    def profile(self, points, front, back, material):
        # Profile is an x/z polygon. Fan origin at its bottom centre keeps
        # stepped and bell-gable triangles inside the visible silhouette.
        centre=[(points[0][0]+points[-1][0])/2,min(z for x,z in points)]
        for a,b in zip(points,points[1:]+points[:1]):
            self.face([[centre[0],front,centre[1]],[b[0],front,b[1]],[a[0],front,a[1]]],material)
            self.face([[centre[0],back,centre[1]],[a[0],back,a[1]],[b[0],back,b[1]]],material)
            self.face([[a[0],front,a[1]],[a[0],back,a[1]],[b[0],back,b[1]],[b[0],front,b[1]]],material)

    def export(self, a, direction, base):
        dx,dy=direction
        # Campaign x/z -> Unreal Y/X. The reflection already changes the
        # counterclockwise authoring faces to Unreal's clockwise front faces.
        result=dict(positions=[],normals=[],uvs=self.uvs,indices=[],triangleMaterials=self.slots)
        for x,y,z in self.positions:
            gx=a[0]+dx*x-dy*y; gy=a[1]+dy*x+dx*y
            result['positions'].append([round((gy-a[1])*100,5),round((gx-a[0])*100,5),round(z*100,5)])
        for x,y,z in self.normals: result['normals'].append([dy*x+dx*y,dx*x-dy*y,z])
        result['indices']=list(self.indices)
        return result


def window(m,x,z,w=1.05,h=1.7,depth=0,shutters=False):
    m.box(x-w/2,x+w/2,depth+.10,depth+.14,z,z+h,'glass')
    for left in (x-w/2-.09,x+w/2):
        m.box(left,left+.09,depth-.10,depth+.15,z-.08,z+h+.08,'limestone')
    for level in (z-.1,z+h): m.box(x-w/2-.15,x+w/2+.15,depth-.17,depth+.1,level,level+.1,'limestone')
    m.box(x-.025,x+.025,depth+.04,depth+.1,z,z+h,'timber')
    for level in (z+h*.36,z+h*.72): m.box(x-w/2,x+w/2,depth+.04,depth+.1,level,level+.04,'timber')
    if shutters:
        for sign in (-1,1):
            c=x+sign*(w/2+.28)
            m.box(c-.16,c+.16,depth-.09,depth-.025,z,z+h,'timber')
            for level in (z+.2,z+h-.25): m.box(c-.18,c+.18,depth-.11,depth-.08,level,level+.06,'iron')


def facade(m,w,eave,storeys,public,palette,door_z=0,min_z=0,door_enabled=True):
    material='plaster' if palette==4 else 'brick'
    door=w*.25; door_w=1.4
    windows=[w*.68] if w<5.3 else [w*.27,w*.73]
    holes=[]
    for floor in range(storeys):
        if floor==0:
            if door_enabled: holes.append((door-door_w/2,door+door_w/2,door_z,door_z+2.45,'door'))
            holes.append((w*.70-.65,w*.70+.65,.65,2.45,'window'))
        else:
            for x in windows: holes.append((x-.525,x+.525,floor*3.0+.65,floor*3.0+2.35,'window'))
    # Exact rectangular subtraction leaves real openings and reveals. It does
    # not conceal a solid collision wall behind a decorative doorway.
    xs=sorted({0,w,*[v for h in holes for v in h[:2]]})
    zs=sorted({min_z,0,eave,*[v for h in holes for v in h[2:4]]})
    for x0,x1 in zip(xs,xs[1:]):
        for z0,z1 in zip(zs,zs[1:]):
            cx,cz=(x0+x1)/2,(z0+z1)/2
            if any(a<cx<b and c<cz<d for a,b,c,d,kind in holes): continue
            m.box(x0,x1,0,.24,z0,z1,'limestone' if z1<=0 else material)
    for x0,x1,z0,z1,kind in holes:
        if kind=='window': window(m,(x0+x1)/2,z0,x1-x0,z1-z0,shutters=palette%2==0 and z0>3)
        else:
            if not public:
                for i in range(7):
                    m.box(x0+i*.2+.006,x0+(i+1)*.2-.006,.12,.19,z0+.015,z0+2.44,'timber')
                for z in (z0+.4,z0+1.8): m.box(x0,x1,.07,.12,z,z+.06,'iron')
            for x in (x0-.13,x1): m.box(x,x+.13,-.12,.27,z0,z0+2.60,'limestone')
            m.box(x0-.13,x1+.13,-.13,.28,z0+2.45,z0+2.62,'limestone')
            # Recessed threshold stays flush with the ground floor.
            m.box(x0-.04,x1+.04,-.25,.3,z0-.06,z0+.01,'limestone')
    # The plinth stops at the doorway; a continuous band would create a
    # shin-high collision barrier across an otherwise open public entrance.
    m.box(0,door-door_w/2,-.09,.29,.3,.44,'limestone')
    m.box(door+door_w/2,w,-.09,.29,.3,.44,'limestone')
    m.box(0,w,-.09,.29,eave-.14,eave,'limestone')
    for floor in range(1,storeys): m.box(0,w,-.045,.27,floor*3-.12,floor*3-.04,'limestone')
    return door


def house(lot):
    a,b,c,d=lot['polygon']; w=math.dist(a,b)
    dx,dy=(b[0]-a[0])/w,(b[1]-a[1])/w
    local=lambda p:[(p[0]-a[0])*dx+(p[1]-a[1])*dy,-(p[0]-a[0])*dy+(p[1]-a[1])*dx]
    back_right,back_left=local(c),local(d)
    polygon=[[0,0],[w,0],back_right,back_left]
    if min(back_right[1],back_left[1])<3: raise ValueError('Lot too shallow')
    base=height((a[0]+b[0])/2,(a[1]+b[1])/2)+.06
    eave=lot['storeys']*3.; m=Mesh()
    m.prism(polygon,-1.5,0,'limestone')
    # Opaque party walls reach the taller neighbour's eave. All walls are inset
    # into their own parcel; their outside planes share the same boundary.
    for p,q in ((polygon[1],polygon[2]),(polygon[3],polygon[0])):
        length=math.dist(p,q); nx,ny=-(q[1]-p[1])/length*.24,(q[0]-p[0])/length*.24
        m.prism([p,q,[q[0]+nx,q[1]+ny],[p[0]+nx,p[1]+ny]],0,eave,'brick')
    door=facade(m,w,eave,lot['storeys'],lot['publicInterior'],lot['palette'])
    rear_width=math.dist(back_right,back_left)
    rear_direction=[(back_left[i]-back_right[i])/rear_width for i in range(2)]
    rear=Mesh()
    if rear_width>=3.6:
        facade(rear,rear_width,eave,lot['storeys'],False,lot['palette'])
    else:
        rear.box(0,rear_width,0,.24,0,eave,'brick')
    m.append(rear,back_right,rear_direction)
    for f in range(lot['storeys']): m.prism(polygon,3*f-.12,3*f,'timber')
    ridge=w*.62
    front_mid=[w/2,0,eave+ridge]; rear_mid=[(back_left[0]+back_right[0])/2,(back_left[1]+back_right[1])/2,eave+ridge]
    # Roof footprints terminate at shared parcel boundaries, without eaves
    # extending sideways into an adjacent roof or its room volume.
    for p,q,reverse in ((polygon[0],polygon[3],False),(polygon[1],polygon[2],True)):
        pts=[[p[0],p[1],eave],front_mid,rear_mid,[q[0],q[1],eave]]
        if reverse: pts.reverse()
        m.face(pts,'roof')
    m.face([[back_left[0],back_left[1],eave],rear_mid,[back_right[0],back_right[1],eave]],'brick')
    if lot['gable']=='step':
        steps=5; points=[[0,eave]]
        for i in range(steps):
            x=w/2*i/steps; z=eave+ridge*(i+1)/steps+.18
            points.extend([[x,z],[w/2*(i+1)/steps,z]])
        points.extend([[w-x,z] for x,z in reversed(points[:-1])]);points.append([w,eave])
    elif lot['gable']=='bell':
        left=[[w/2*t,eave+ridge*(.5-.5*math.cos(math.pi*t))+.15] for t in [i/12 for i in range(13)]]
        points=[[0,eave]]+left+[[w-x,z] for x,z in reversed(left[:-1])]+[[w,eave]]
    else: points=[[0,eave],[w/2,eave+ridge+.18],[w,eave]]
    m.profile(points,-.06,.25,'plaster' if lot['palette']==4 else 'brick')
    # A stone cap follows every tread/curve rather than bridging across it.
    for p,q in zip(points,points[1:]):
        if math.dist(p,q)<1e-5: continue
        m.profile([p,q,[q[0],q[1]+.1],[p[0],p[1]+.1]],-.12,.30,'limestone')
    window(m,w/2,eave+.30,.75,1.0,depth=-.22)
    chimney_x=w*.68; chimney_y=min(back_right[1],back_left[1])*.68
    m.box(chimney_x-.28,chimney_x+.28,chimney_y-.3,chimney_y+.3,eave+ridge*.45,eave+ridge+1.1,'brick')
    m.box(chimney_x-.34,chimney_x+.34,chimney_y-.36,chimney_y+.36,eave+ridge+1.0,eave+ridge+1.18,'limestone')
    if lot['publicInterior']:
        # Authored shopfront canopy and hanging iron sign; route clearance
        # remains below the canopy and outside its short wall brackets.
        m.face([[w*.46,-1.0,2.65],[w-.2,-1.0,2.65],[w-.2,-.1,2.95],[w*.46,-.1,2.95]],'timber')
        m.box(w*.45,w*.45+.045,-.8,.08,3.05,3.1,'iron')
        m.box(w*.45-.025,w*.45+.065,-.77,-.3,2.6,3.02,'timber')
    mesh=m.export(a,(dx,dy),base)
    return dict(id=lot['id'],actorId=lot['actorId'],position=[a[1]*100,a[0]*100,base*100],mesh=mesh,
        materials=list(MATERIALS),palette=lot['palette'],publicInterior=lot['publicInterior'],
        entrance=[(a[1]+dy*door)*100,(a[0]+dx*door)*100,base*100],
        direction=[dx,-dy],width=w,depth=min(back_right[1],back_left[1]),
        triangles=len(mesh['indices'])//3,sourceSignature=digest(lot))


def main():
    plan=json.loads((OUT/'pilot-plan.json').read_text());validate(plan)
    rows=[house(lot) for b in plan['blocks'] for lot in b['lots']]
    result=dict(schemaVersion=1,planSignature=plan['signature'],houses=rows,geometrySignature=digest(rows))
    (OUT/'architecture.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(f"Authored {len(rows)} houses / {sum(r['triangles'] for r in rows)} triangles")


if __name__=='__main__': main()
