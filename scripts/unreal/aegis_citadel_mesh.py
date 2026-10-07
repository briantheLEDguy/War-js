"""Bespoke carved masonry, Gothic tracery and route-owned floors in centimetres.

Complex architecture is assembled into textured authored meshes. Separate gate
leaves are real portcullises; structural collision never fills an open doorway.
"""
import math
from aegis_citadel_blueprint import route_clearance

MATERIALS = ['stone','limestone','flagstone','slate','gold','iron','blue','glass','window_dark','carved_stone','paving_inlay']
BLENDER_EXPORT_CONVENTION=dict(schemaVersion=1,positions='metres_y_x_z',normals='y_x_z',
    determinant=-1,triangleWinding='swap_second_and_third_at_blender_boundary',
    nativeSourceArraysPreserved=True)


def blender_export_point(p): return (p[1]/100,p[0]/100,p[2]/100)


def blender_export_normal(n): return (n[1],n[0],n[2])


def blender_export_indices(indices):
    if len(indices)%3:raise ValueError('Blender export requires complete source triangles')
    return [index for i in range(0,len(indices),3) for index in (indices[i],indices[i+2],indices[i+1])]


def placed_sentinel(placement):
    from aegis_citadel_statue import build_sentinel,LEGACY_NODE_SCALE
    mesh=build_sentinel(LEGACY_NODE_SCALE*placement['scale'])
    mesh.key='furnishing_'+placement['id']
    mesh.positions=[[round(p[j]+placement['point'][j],4) for j in range(3)] for p in mesh.positions]
    return mesh


def append_mesh(target,source):
    """Keep original corner normals and UV seams when joining authored sources."""
    start=len(target.positions)
    target.positions.extend([p[:] for p in source.positions])
    target.normals.extend([n[:] for n in source.normals]);target.uvs.extend([u[:] for u in source.uvs])
    target.indices.extend(i+start for i in source.indices)
    target.triangle_materials.extend(source.triangle_materials)


def commander_vault(mesh):
    # A continuous thick masonry vault closes the hall, beneath the replacement
    # upper rooms. Its lowest intrados clears the highest 7,210 cm gallery.
    x0,x1=26140,33290;ys=[-4210+i*8420/40 for i in range(41)]
    zs=[8140+730*(1-(abs(y)/4210)**1.6) for y in ys];top=9098
    for a,b,za,zb in zip(ys,ys[1:],zs,zs[1:]):
        mesh.face([[x0,a,za],[x0,b,zb],[x1,b,zb],[x1,a,za]],'stone')
        mesh.face([[x0,a,top],[x1,a,top],[x1,b,top],[x0,b,top]],'slate')
        for x,reverse in ((x0,True),(x1,False)):
            face=[[x,a,za],[x,b,zb],[x,b,top],[x,a,top]]
            mesh.face(list(reversed(face)) if reverse else face,'stone')
    for y,z in ((ys[0],zs[0]),(ys[-1],zs[-1])):
        face=[[x0,y,z],[x1,y,z],[x1,y,top],[x0,y,top]]
        mesh.face(face if y<0 else list(reversed(face)),'stone')
    for x in (26550,27820,28900,29900,31500,32920):
        for a,b,za,zb in zip(ys,ys[1:],zs,zs[1:]):
            mesh.rod([x,a,za-25],[x,b,zb-25],24,'limestone',8)
        mesh.ring(x,0,8820,35,105,'gold',24)
        for y in (-2100,2100):
            z=8140+730*(1-(abs(y)/4210)**1.6)
            mesh.rod([x,y,8240],[x,y,z-28],26,'limestone',8)
    for y in (-2600,0,2600):
        z=8140+730*(1-(abs(y)/4210)**1.6)
        mesh.rod([x0,y,z-22],[x1,y,z-22],19,'limestone',8)
    # An original ceremonial triptych frames the functional throne. Its center
    # starts above the measured 7,307.74 cm throne, with side piers well beyond
    # the signed rear stair and chamber lanes.
    arch(mesh,33245,0,7360,1220,1320,80,70,glass=True,lit=False)
    sun(mesh,33185,0,8020,340,True)
    for side in (-1,1):
        arch(mesh,33245,side*1650,6550,850,1980,80,65,glass=True,lit=False)
        banner(mesh,33180,side*1650,8430,500,1450,True)
        for y in (side*900,side*2380,side*3720):
            mesh.block([33210,y,7155],[140,160,2230],'limestone',10)
            for dy in (-40,40):mesh.rod([33135,y+dy,6110],[33135,y+dy,8240],17,'limestone',6)
CITY_TEXTURES='public/assets/textures/aegis_city/'
CITADEL_TEXTURES='public/assets/textures/aegis_citadel/'
UPPER_FACTOR=(14200-9000)/(22220-9000)
UV_PERIOD_CM={'stone':360,'limestone':360,'flagstone':480,'paving_inlay':480,'slate':1100,'iron':700}
ASHLAR=dict(baseColor=CITADEL_TEXTURES+'weathered_ashlar_albedo_v1.png',
    height=CITADEL_TEXTURES+'weathered_ashlar_height_v1.png',
    provenance=CITADEL_TEXTURES+'provenance.json',heightStrength=.75,heightDistanceCm=.45,
    texturePowerOfTwo='stretch_to_2048',roughness=.9,metallic=0)
MATERIAL_SPECS = {
    'stone': dict(ASHLAR,tint=[.45,.50,.57]),
    'limestone': dict(ASHLAR,tint=[.60,.66,.74]),
    'flagstone': dict(ASHLAR,baseColor=CITADEL_TEXTURES+'courtyard_limestone_albedo_v1.png',
        height=CITADEL_TEXTURES+'courtyard_limestone_height_v1.png',tint=[.68,.73,.80]),
    'slate': dict(baseColor=CITY_TEXTURES+'a40fe728cb768bfffcaf.png',
        normal=CITY_TEXTURES+'5005f7be83d08dfd1db6.png',orm=CITY_TEXTURES+'648ff647ce4bdaaec9ca.png',
        normalConvention='gltf_opengl_positive_y',tint=[.7,.8,1],roughness=.9,metallic=.12),
    'gold': dict(tint=[.61,.34,.075],roughness=.38,metallic=.8),
    'iron': dict(baseColor=CITY_TEXTURES+'2c15df4f7f5bd2e751c7.png',
        normal=CITY_TEXTURES+'6b89092569d158db6d91.png',orm=CITY_TEXTURES+'b0a09e676afb125acd05.png',
        normalConvention='gltf_opengl_positive_y',tint=[.6,.7,.8],roughness=.65,metallic=.9),
    'blue': dict(tint=[.0035,.012,.034],roughness=.92,metallic=0,specular=.25),
    'glass': dict(tint=[.11,.045,.009],roughness=.3,metallic=.18,emission=[10,3.1,.4]),
    'window_dark': dict(tint=[.025,.035,.048],roughness=.24,metallic=.25),
    'carved_stone':dict(tint=[.32,.37,.44],roughness=.86,metallic=0),
    'paving_inlay':dict(ASHLAR,baseColor=CITADEL_TEXTURES+'courtyard_limestone_albedo_v1.png',
        height=CITADEL_TEXTURES+'courtyard_limestone_height_v1.png',tint=[.40,.48,.58])}


def cross(a,b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


class Mesh:
    def __init__(self, key, collision=True, defer_flat_floors=False):
        self.key=key;self.collision=collision;self.positions=[];self.indices=[]
        self.normals=[];self.uvs=[];self.triangle_materials=[]
        self.defer_flat_floors=defer_flat_floors;self.flat_floors={}

    def remove_identical_faces(self):
        """Remove repeated oriented surfaces, retaining opposite solid-boundary faces."""
        seen={};remap={};indices=[];materials=[];removed=0
        for triangle,material in enumerate(self.triangle_materials):
            ids=self.indices[triangle*3:triangle*3+3]
            # No spatial epsilon may erase an authored seam or decorative relief.
            corners=tuple(sorted((tuple(self.positions[i]),tuple(self.normals[i]),tuple(self.uvs[i])) for i in ids))
            key=(material,corners)
            if key in seen:
                remap[triangle]=seen[key];removed+=1;continue
            remap[triangle]=len(materials);seen[key]=len(materials)
            indices.extend(ids);materials.append(material)
        self.indices=indices;self.triangle_materials=materials
        # Signed graded approach witnesses refer to triangle ordinals. Preserve
        # their exact surfaces after preceding support duplicates are removed.
        for binding in getattr(self,'surface_bindings',[]):
            binding['topTriangleIndices']=list(dict.fromkeys(remap[i] for i in binding['topTriangleIndices']))
        return dict(policy='exact_positions_normals_uvs_material_oriented_face_v1',
            removedTriangles=removed,retainedTriangles=len(materials),
            oppositeFacingSolidBoundariesPreserved=True,positionsNormalsAndUvsPreserved=True)

    def face(self, vertices, material='stone'):
        a,b,c=vertices[:3];normal=cross([b[i]-a[i] for i in range(3)],[c[i]-a[i] for i in range(3)])
        length=math.sqrt(sum(v*v for v in normal))
        if length < .001: return
        normal=[v/length for v in normal];axis=max(range(3),key=lambda i:abs(normal[i]))
        axes=[i for i in range(3) if i!=axis];start=len(self.positions)
        self.positions.extend([[round(v,4) for v in p] for p in vertices])
        scale=UV_PERIOD_CM.get(material,400)
        self.normals.extend([normal]*len(vertices));self.uvs.extend([[p[axes[0]]/scale,p[axes[1]]/scale] for p in vertices])
        for i in range(1,len(vertices)-1):
            self.indices.extend([start,start+i,start+i+1]);self.triangle_materials.append(MATERIALS.index(material))

    def block(self, center, size, material='stone', chamfer=4):
        # Octagonal plan and sloped arrises keep exposed masonry edges authored.
        x,y,z=center;hx,hy,hz=[s/2 for s in size];c=min(chamfer,hx*.2,hy*.2,hz*.2)
        if c<1e-6:
            bottom=[[x+u,y+v,z-hz] for u,v in ((-hx,-hy),(hx,-hy),(hx,hy),(-hx,hy))]
            top=[[p[0],p[1],z+hz] for p in bottom]
            self.face(list(reversed(bottom)),material);self.face(top,material)
            for i in range(4):self.face([bottom[i],bottom[(i+1)%4],top[(i+1)%4],top[i]],material)
            return
        ring=[[-hx+c,-hy],[hx-c,-hy],[hx,-hy+c],[hx,hy-c],
              [hx-c,hy],[-hx+c,hy],[-hx,hy-c],[-hx,-hy+c]]
        levels=[(-hz,c),(-hz+c,0),(hz-c,0),(hz,c)]
        rings=[[[x+u*(1-inset/max(hx,1)),y+v*(1-inset/max(hy,1)),z+w] for u,v in ring] for w,inset in levels]
        self.face(list(reversed(rings[0])),material);self.face(rings[-1],material)
        for a,b in zip(rings,rings[1:]):
            for i in range(8):
                j=(i+1)%8;self.face([a[i],a[j],b[j],b[i]],material)

    def rod(self, a, b, radius, material='limestone', sides=8):
        vector=[b[i]-a[i] for i in range(3)];length=math.sqrt(sum(v*v for v in vector))
        if length<.01: return
        direction=[v/length for v in vector];u=cross(direction,[0,0,1] if abs(direction[2])<.9 else [1,0,0])
        n=math.sqrt(sum(v*v for v in u));u=[v/n for v in u];v=cross(direction,u)
        rings=[[[p[j]+radius*(u[j]*math.cos(i*math.tau/sides)+v[j]*math.sin(i*math.tau/sides)) for j in range(3)]
                for i in range(sides)] for p in (a,b)]
        self.face(list(reversed(rings[0])),material);self.face(rings[1],material)
        for i in range(sides):
            j=(i+1)%sides;self.face([rings[0][i],rings[0][j],rings[1][j],rings[1][i]],material)

    def ring(self, x,y,z, inner,outer, material='limestone', segments=64, vertical=False):
        for i in range(segments):
            a,b=i*math.tau/segments,(i+1)*math.tau/segments
            points=[(inner,a),(outer,a),(outer,b),(inner,b)]
            if vertical:self.face([[x,y+r*math.cos(t),z+r*math.sin(t)] for r,t in reversed(points)],material)
            else:self.face([[x+r*math.cos(t),y+r*math.sin(t),z] for r,t in points],material)

    def export(self):
        return dict(id=self.key,positions=self.positions,indices=self.indices,normals=self.normals,
                    uvs=self.uvs,triangleMaterials=self.triangle_materials,materials=list(MATERIALS),collision=self.collision)

    def cohere_throne_gold_faces(self):
        """Share the intended plane of adjacent gold flute faces, never their shape."""
        faces=[self.indices[i:i+3] for i in range(0,len(self.indices),3)]
        parent=list(range(len(faces)));edges={};gold=MATERIALS.index('gold')
        def find(i):
            while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
            return i
        for j,ids in enumerate(faces):
            if self.triangle_materials[j]!=gold:continue
            for a,b in zip(ids,ids[1:]+ids[:1]):
                key=tuple(sorted((tuple(self.positions[a]),tuple(self.positions[b]))))
                for other in edges.get(key,[]):
                    n,m=self.normals[ids[0]],self.normals[faces[other][0]]
                    if sum(n[k]*m[k] for k in range(3))>1-1e-6:parent[find(j)]=find(other)
                edges.setdefault(key,[]).append(j)
        groups={}
        for j,ids in enumerate(faces):
            if self.triangle_materials[j]==gold:groups.setdefault(find(j),[]).append(j)
        changed=0;maximum_distance=0
        for group in groups.values():
            if len(group)<2:continue
            n=[sum(self.normals[faces[j][0]][k] for j in group) for k in range(3)]
            length=math.sqrt(sum(v*v for v in n));n=[v/length for v in n]
            ids={i for j in group for i in faces[j]};origin=self.positions[faces[group[0]][0]]
            distance=max(abs(sum((self.positions[i][k]-origin[k])*n[k] for k in range(3))) for i in ids)
            if (distance>.01 or any(sum(self.normals[i][k]*n[k] for k in range(3))<=1-1e-6 for i in ids)):
                continue
            axis=max(range(3),key=lambda k:abs(n[k]));axes=[k for k in range(3) if k!=axis]
            for i in ids:
                self.normals[i]=n[:];self.uvs[i]=[self.positions[i][k]/400 for k in axes]
            changed+=len(group);maximum_distance=max(maximum_distance,distance)
        return dict(kind='throne_gold_coplanar_face_coherence',triangles=changed,
                    minimumNormalDot=1-1e-6,maximumAllowedPlaneDistanceCm=.01,
                    maximumActualPlaneDistanceCm=maximum_distance,positionsAndIndicesPreserved=True)

    def reproject_stone_uvs(self):
        # Upper silhouette compression must not also compress the physical courses.
        seen=set()
        for offset,material in enumerate(self.triangle_materials):
            role=MATERIALS[material]
            if role not in ('stone','limestone','flagstone','paving_inlay'):continue
            for index in self.indices[offset*3:offset*3+3]:
                if index in seen:continue
                seen.add(index)
                axis=max(range(3),key=lambda j:abs(self.normals[index][j]))
                axes=[j for j in range(3) if j!=axis]
                self.uvs[index]=[self.positions[index][j]/UV_PERIOD_CM[role] for j in axes]

    def reshape_upper(self,cut,original_top,new_top):
        """Clip at the preserved clearance plane before changing upper height."""
        factor=(new_top-cut)/(original_top-cut)
        if abs(factor-1)<1e-9:return
        old=self.positions;positions=[p[:] for p in old]
        normals=[n[:] for n in self.normals];uvs=[u[:] for u in self.uvs]
        for i,p in enumerate(positions):
            if p[2]<=cut:continue
            p[2]=round(cut+(p[2]-cut)*factor,4)
            n=normals[i];n=[n[0],n[1],n[2]/factor];length=math.sqrt(sum(v*v for v in n))
            normals[i]=[v/length for v in n]
        indices=[];materials=[]
        upper_boundary={}
        def owned_upper_vertex(index):
            if old[index][2]!=cut:return index
            if index not in upper_boundary:
                n=self.normals[index];n=[n[0],n[1],n[2]/factor]
                length=math.sqrt(sum(v*v for v in n))
                upper_boundary[index]=len(positions)
                positions.append(old[index][:]);normals.append([v/length for v in n]);uvs.append(self.uvs[index][:])
            return upper_boundary[index]
        def clipped(poly,upper):
            result=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                inside_a=a[0][2]>=cut if upper else a[0][2]<=cut
                inside_b=b[0][2]>=cut if upper else b[0][2]<=cut
                if inside_a:result.append(a)
                if inside_a!=inside_b:
                    t=(cut-a[0][2])/(b[0][2]-a[0][2])
                    result.append(([a[0][j]+t*(b[0][j]-a[0][j]) for j in range(3)],
                                   [a[1][j]+t*(b[1][j]-a[1][j]) for j in range(2)]))
            unique=[]
            for item in result:
                if not unique or math.dist(item[0],unique[-1][0])>.0001:unique.append(item)
            if len(unique)>1 and math.dist(unique[0][0],unique[-1][0])<.0001:unique.pop()
            return unique
        for offset in range(0,len(self.indices),3):
            ids=self.indices[offset:offset+3];material=self.triangle_materials[offset//3]
            zs=[old[i][2] for i in ids]
            if not(min(zs)<cut<max(zs)):
                # A face touching the cutoff belongs to its upper half. Its
                # boundary normals need the same transform as its high corners,
                # without changing the normals of any retained lower face.
                if min(zs)>=cut and max(zs)>cut:ids=[owned_upper_vertex(i) for i in ids]
                indices.extend(ids);materials.append(material);continue
            poly=[(old[i],self.uvs[i]) for i in ids]
            for upper in (False,True):
                vertices=clipped(poly,upper)
                if len(vertices)<3:continue
                points=[[p[0],p[1],cut+(p[2]-cut)*factor if upper else p[2]] for p,_ in vertices]
                n=cross([points[1][j]-points[0][j] for j in range(3)],
                        [points[2][j]-points[0][j] for j in range(3)])
                length=math.sqrt(sum(v*v for v in n))
                if length<.001:continue
                n=[v/length for v in n];start=len(positions)
                positions.extend(points);normals.extend([n]*len(points));uvs.extend([u for _,u in vertices])
                for i in range(1,len(points)-1):
                    indices.extend([start,start+i,start+i+1]);materials.append(material)
        self.positions,self.normals,self.uvs=positions,normals,uvs
        self.indices,self.triangle_materials=indices,materials


def pointed_profile(width,height,steps=24):
    """Two-centre pointed Gothic opening; the bottom stays completely clear."""
    radius=width;spring=height-math.sqrt(3)*width/2
    left=[(width/2+radius*math.cos(math.pi-i*math.pi/(3*steps)),
           spring+radius*math.sin(math.pi-i*math.pi/(3*steps))) for i in range(steps+1)]
    return [(-width/2,0),*left,*[(-u,z) for u,z in reversed(left[:-1])],(width/2,0)]


def arch(mesh, x,y,z, width,height,depth=120,thickness=75, material='limestone', glass=False, lit=True):
    if glass and z>=9000 and width<1000:width*=.6
    inner=pointed_profile(width,height);outer=pointed_profile(width+thickness*2,height+thickness*1.7)
    # Keep the Gothic reveals extruded, with separate mortar-depth voussoirs.
    for i in range(len(inner)-1):
        a,b=inner[i],inner[i+1];c,d=outer[i],outer[i+1]
        for side in (-1,1):
            xx=x+side*depth/2
            vertices=[[xx,y+a[0],z+a[1]],[xx,y+b[0],z+b[1]],[xx,y+d[0],z+d[1]],[xx,y+c[0],z+c[1]]]
            mesh.face(list(reversed(vertices)) if side<0 else vertices,material)
        mesh.face([[x-depth/2,y+b[0],z+b[1]],[x+depth/2,y+b[0],z+b[1]],
                   [x+depth/2,y+a[0],z+a[1]],[x-depth/2,y+a[0],z+a[1]]],material)
        mesh.face([[x+depth/2,y+c[0],z+c[1]],[x+depth/2,y+d[0],z+d[1]],
                   [x-depth/2,y+d[0],z+d[1]],[x-depth/2,y+c[0],z+c[1]]],material)
    if glass:
        mesh.face([[x-depth*.25,y+u,z+v] for u,v in inner],'glass' if lit else 'window_dark')
        mesh.rod([x-depth*.53,y,z+20],[x-depth*.53,y,z+height-35],9,'gold')
        for level in (height*.3,height*.55):
            mesh.rod([x-depth*.53,y-width*.43,z+level],[x-depth*.53,y+width*.43,z+level],7,'gold')
        for offset in (-width*.2,width*.2):
            mesh.rod([x-depth*.54,y+offset,z+35],[x-depth*.54,y+offset,z+height*.84],6,'limestone')
        for side in (-1,1):
            mesh.rod([x-depth*.54,y,z+height*.64],[x-depth*.54,y+side*width*.33,z+height*.89],6,'limestone')


def blind_bay(mesh,x,y,z,width,height,relief_cm=30):
    """Shallow outward relief on a solid wall, with no floor or aperture edit."""
    if not 20<=relief_cm<=40:raise ValueError('Front blind relief exceeds its bounded envelope')
    profile=pointed_profile(width,height)
    mesh.face([[x-.5,y+u,z+v] for u,v in profile],'window_dark')
    arch(mesh,x-relief_cm/2,y,z,width,height,relief_cm,32)
    for sign in (-1,1):
        yy=y+sign*(width/2+52)
        mesh.block([x-relief_cm/2,yy,z+height*.39],[relief_cm,78,height*.78],'stone',3)
        mesh.block([x-relief_cm/2,yy,z+45],[relief_cm,120,90],'limestone',3)
        mesh.block([x-relief_cm/2,yy,z+height*.73],[relief_cm,108,55],'limestone',3)
    return dict(pointCm=[x,y,z],widthCm=width,heightCm=height,reliefCm=relief_cm,
                wallAndWalkingFloorsUnchanged=True)


def portal_roll_details(mesh):
    """Fine carved rolls remain outside the exact eighteen-metre portal cut."""
    start=len(mesh.positions)
    for width,height,radius,material in ((2240,3800,13,'limestone'),
            (2300,3920,10,'carved_stone'),(2370,4050,9,'gold')):
        profile=pointed_profile(width,height,32)
        for a,b in zip(profile,profile[1:]):
            mesh.rod([25406,a[0],6010+a[1]],[25406,b[0],6010+b[1]],radius,material,6)
    for sign in (-1,1):
        y=sign*1170
        for z,size in ((7600,[74,132,56]),(7680,[90,150,52]),(7750,[70,128,44])):
            mesh.block([25420,y,z],size,'limestone',4)
        for dy in (-45,0,45):
            mesh.rod([25376,y+dy,7610],[25376,y+dy,7760],7,'carved_stone',6)
    return dict(minimumInnerYCm=min(abs(p[1]) for p in mesh.positions[start:] if p[2]<8610),usableOpeningCm=[1800,2600],
                fineRollWidthsCm=[2240,2300,2370],boundedOutwardFacadeDecoration=True)


def wall_cut(mesh,x, y0,y1,z0,z1, openings, depth=120):
    """Rectangular cuts beneath carved arches; no bounding collision through portals."""
    levels=sorted({z0,z1,*[max(z0,min(z1,v)) for o in openings for v in (o['point'][2],o['point'][2]+o['height'])]})
    for a,b in zip(levels,levels[1:]):
        intervals=sorted((max(y0,o['point'][1]-o['width']/2),min(y1,o['point'][1]+o['width']/2))
                         for o in openings if o['point'][2] < b-.01 and o['point'][2]+o['height'] > a+.01
                         and o['point'][1]+o['width']/2>y0 and o['point'][1]-o['width']/2<y1)
        cursor=y0
        for left,right in intervals+[(y1,y1)]:
            if left>cursor:mesh.block([x,(cursor+left)/2,(a+b)/2],[depth,left-cursor,b-a],chamfer=3)
            cursor=max(cursor,right)


def side_arch(mesh,x,y,z,width,height,depth=70,thickness=40,glass=True,lit=True,outward_side=None):
    if glass and z>=9000 and width<1000:width*=.6
    if glass and outward_side not in (-1,1):raise ValueError('Glazed side bay requires its explicit outward side')
    if outward_side is None:outward_side=1
    if outward_side not in (-1,1):raise ValueError('Unknown side-bay orientation')
    local=Mesh('temporary_reveal');arch(local,0,0,0,width,height,depth,thickness,glass=glass,lit=lit)
    for i in range(0,len(local.indices),3):
        points=[local.positions[j] for j in local.indices[i:i+3]]
        if outward_side<0:points=list(reversed(points))
        mesh.face([[x+p[1],y-outward_side*p[0],z+p[2]] for p in points],MATERIALS[local.triangle_materials[i//3]])


def sun(mesh,x,y,z,radius,final_coordinates=False):
    horizontal=UPPER_FACTOR if not final_coordinates and z-radius*1.4>9000 else 1
    for r in (radius*.33,radius*.50,radius*.73):
        for i in range(48):
            a,b=i*math.tau/48,(i+1)*math.tau/48
            mesh.face([[x,y+rr*horizontal*math.cos(t),z+rr*math.sin(t)]
                       for rr,t in reversed([(r-8,a),(r+8,a),(r+8,b),(r-8,b)])],'gold')
    for i in range(16):
        t=i*math.tau/16;r1=radius*.62;r2=radius*(1.35 if i%4==0 else 1 if i%2==0 else .83)
        mesh.rod([x,y+math.cos(t)*r1*horizontal,z+math.sin(t)*r1],
                 [x,y+math.cos(t)*r2*horizontal,z+math.sin(t)*r2],8,'gold',6)


def banner(mesh,x,y,z,width=320,height=1900,final_coordinates=False):
    columns,rows=16,32
    def cloth_x(u,v):
        release=min(1,max(0,v)*5)
        return x-12-release*width*(.045*math.sin(u*math.pi*6)+.018*math.sin(u*math.pi)*math.sin(v*math.pi*2))
    def p(i,j):
        xx=cloth_x(i/columns,j/rows)
        u=(i/columns-.5)*width;v=-height*j/rows-height*.009*math.sin(i*math.pi/columns)*math.sin(j*math.pi/rows)
        if j>rows-6:v-=height*.16*(1-abs(u)/(width/2))*((j-rows+6)/6)
        return [xx,y+u,z+v]
    for j in range(rows):
        for i in range(columns):mesh.face([p(i,j),p(i+1,j),p(i+1,j+1),p(i,j+1)],'blue')
    for i in (0,columns):
        for j in range(rows):mesh.rod(p(i,j),p(i,j+1),6,'gold',6)
    emblem=Mesh('draped_standard_emblem',False)
    sun(emblem,x,y,z-height*.28,min(width*.34,height*.19),final_coordinates)
    for offset,material in enumerate(emblem.triangle_materials):
        vertices=[]
        for index in emblem.indices[offset*3:offset*3+3]:
            p=emblem.positions[index]
            u=(p[1]-y)/width+.5;v=(z-p[2])/height
            # Draping must retain the ray rods' depth. Flattening their cap
            # vertices onto cloth creates almost collinear opposite-facing skins.
            vertices.append([cloth_x(u,v)-7+(p[0]-x),p[1],p[2]])
        mesh.face(vertices,MATERIALS[material])
    if width>=1800:
        for sign in (-1,1):
            a=[cloth_x(.5+sign*.36,.6)-7,y+sign*width*.36,z-height*.6]
            b=[cloth_x(.5,.78)-7,y,z-height*.78]
            mesh.rod(a,b,8,'gold',6)
    mesh.rod([x,y-width*.6,z+20],[x,y+width*.6,z+20],20,'gold')


def upper_source_z(z):
    return z if z<=9000 else 9000+(z-9000)/UPPER_FACTOR


def final_banner(mesh,x,y,top,width,length):
    # Authored directly at its final proportion; do not flatten the pointed cloth.
    local=Mesh('final_standard',False);banner(local,x,y,top,width,length,True)
    for offset,material in enumerate(local.triangle_materials):
        vertices=[[p[0],p[1],upper_source_z(p[2])] for p in
                  [local.positions[i] for i in local.indices[offset*3:offset*3+3]]]
        mesh.face(vertices,MATERIALS[material])


def battlements(mesh,x0,x1,y,z,depth=190):
    mesh.block([(x0+x1)/2,y,z-55],[x1-x0,depth+55,95],'limestone',8)
    for x in range(int(x0)+75,int(x1)-40,210):
        mesh.block([x,y,z+100],[105,depth,210],'stone',8)
        mesh.block([x,y,z+212],[125,depth+20,28],'limestone',3)


def pinnacle(mesh,x,y,z,width=160,height=1100):
    mesh.block([x,y,z+height*.22],[width,width,height*.44],'limestone',5)
    for dx,dy in ((-1,-1),(-1,1),(1,-1),(1,1)):
        mesh.rod([x+dx*width*.42,y+dy*width*.42,z],
                 [x+dx*width*.42,y+dy*width*.42,z+height*.53],12,'limestone',6)
    corners=[[x+dx*width*.55,y+dy*width*.55,z+height*.44] for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))]
    tip=[x,y,z+height]
    for a,b in zip(corners,corners[1:]+corners[:1]):mesh.face([a,b,tip],'slate')
    mesh.rod(tip,[x,y,z+height+90],9,'gold',6)


def roof_courses(mesh,ring,tip):
    """Slate joints and iron arrises follow the existing supported roof planes."""
    for index,a in enumerate(ring):
        b=ring[(index+1)%len(ring)]
        mesh.rod(a,b,6,'iron',6)
        mesh.rod(a,tip,4,'iron',6)
        # The narrow seams sit on the roof; they do not bridge its silhouette.
        count=max(2,math.ceil((tip[2]-a[2])/180))
        for course in range(1,count):
            t=course/count
            left=[a[j]+(tip[j]-a[j])*t for j in range(3)]
            right=[b[j]+(tip[j]-b[j])*t for j in range(3)]
            mesh.rod(left,right,1.8,'iron',6)


def outer_crest_support(mesh):
    """Join the curtain above its existing aperture, backing the gate's sun crest."""
    wall_cut(mesh,14220,-1120,1120,6210,7350,[],260)
    # Short piers embed in the existing 6,510 cm wall crown. Nothing projects
    # into the original 1,840 by 1,800 cm pedestrian/convoy opening.
    for side in (-1,1):
        mesh.block([14220,side*1080,6105],[260,80,1170],'stone',3)
    mesh.block([14220,0,7365],[310,2300,65],'limestone',5)
    for side in (-1,1):
        mesh.block([14065,side*1045,6810],[70,90,1090],'limestone',4)
    # Shallow carved fields stay within the existing backing and side trims.
    for side in (-1,1):
        profile=pointed_profile(230,900)
        mesh.face([[14089.5,side*850+u,6240+v] for u,v in reversed(profile)],'window_dark')
        arch(mesh,14072.5,side*850,6240,230,900,35,32)
    return dict(boundsCm=[[14030,-1150,5520],[14375,1150,7397.5]],
        crestPlaneXCm=14075,backingFaceXCm=14090,
        preservedOpening=dict(pointCm=[14200,0,4210],widthCm=1840,heightCm=1800),
        joinsExistingCrown=True,nativeClearanceVerified=False)


def foundation_courses(mesh):
    """Bounded relief articulates the keep foundation below its occupied floors."""
    for side in (-1,1):
        y0,y1=side*2100,side*8910
        for z in (2720,3380,4050,4760,5630):
            mesh.block([25985,(y0+y1)/2,z],[45,abs(y1-y0),55],'limestone',4)
        for y in (side*2700,side*4300,side*5900,side*7500,side*8750):
            mesh.block([25983,y,4090],[50,115,3270],'stone',4)
        for z in (2720,3380,4050,4760,5630):
            mesh.block([29700,side*9108,z],[7240,40,55],'limestone',4)
    return dict(frontReliefCm=42,sideReliefCm=28,
        maximumZCm=5725,walkingFloorsUnchanged=True,
        grandStairHalfWidthReservationCm=2100,nativeClearanceVerified=False)


def tower(mesh,x,y,base,width=1000,height=3600,spire=2400,style='square'):
    final_tip = None
    if style!='battlement' and base+height>9000:
        original_tip=base+height+spire+220
        final_tip=min(14200,9000+(original_tip-9000)*UPPER_FACTOR)
        roof_rise=2100 if style in ('spire','lantern') else 1800
        final_eaves=max(9100,final_tip-roof_rise-120)
        if base>9000:base=upper_source_z(min(9000+(base-9000)*UPPER_FACTOR,final_eaves-650))
        height=upper_source_z(final_eaves)-base
        spire=roof_rise/UPPER_FACTOR
    mesh.block([x,y,base+height/2],[width,width,height],'stone',12)
    for level in (80,height*.66,height):
        mesh.block([x,y,base+level],[width+80,width+80,55],'limestone',15)
    for dx in (-width*.45,width*.45):
        for dy in (-width*.45,width*.45):
            mesh.block([x+dx,y+dy,base+height*.5],[110,110,height+160],'limestone',4)
    for i,yy in enumerate((-width*.24,width*.24)):
        for j,zz in enumerate((height*.23,height*.5,height*.76)):
            w=min(150,width*.15);h=min(950,height*.2)
            lit=(i+j+int(x/100))%4==0
            arch(mesh,x-width/2-7,y+yy,base+zz,w,h,55,30,glass=True,lit=lit)
            side_arch(mesh,x+yy,y-width/2-7,base+zz,w,h,55,30,True,lit,outward_side=-1)
    # Open castellated towers, square turrets and clustered narrow spires have
    # separate silhouettes; a repeated generic pyramid does not match the board.
    if style=='battlement':
        for side in (-1,1):
            battlements(mesh,x-width*.57,x+width*.57,y+side*width*.5,base+height,140)
            for xx in (x-width*.5,x+width*.5):
                mesh.block([xx,y+side*width*.5,base+height-100],[160,160,260],'limestone',8)
        mesh.block([x,y,base+height-50],[width,width,90],'flagstone',6)
        return
    if final_tip is not None:
        from aegis_citadel_spire_detail import source_spire
        final_bottom = 9000+(base+height+40-9000)*UPPER_FACTOR
        receipt = source_spire(mesh,x,y,final_bottom,final_tip,width+50)
        if not hasattr(mesh,'articulated_spire_details'):
            mesh.articulated_spire_details=[]
        mesh.articulated_spire_details.append(dict(centreCm=[x,y],style=style,**receipt))
        for dx in (-width*.52,width*.52):
            for dy in (-width*.52,width*.52):
                pinnacle(mesh,x+dx,y+dy,base+height,90,550 if style=='square' else 950)
        return
    sides=8 if style in ('spire','lantern') else 4
    phase=math.pi/8 if sides==8 else math.pi/4
    roofwidth=min(width*(.63 if sides==8 else .78),375)
    ring=[[x+roofwidth*math.cos(i*math.tau/sides+phase),y+roofwidth*math.sin(i*math.tau/sides+phase),base+height+40] for i in range(sides)]
    top=[x,y,base+height+spire]
    mesh.face(list(reversed(ring)),'slate')
    for i in range(sides):
        j=(i+1)%sides;mesh.face([ring[i],ring[j],top],'slate')
        if style in ('spire','lantern'):mesh.rod(ring[i],top,7,'gold',6)
    roof_courses(mesh,ring,top)
    mesh.rod(top,[x,y,top[2]+(120/UPPER_FACTOR if base+height>9000 else 220)],11,'gold')
    for dx in (-width*.52,width*.52):
        for dy in (-width*.52,width*.52):
            pinnacle(mesh,x+dx,y+dy,base+height,90,550 if style=='square' else 950)


def rail(mesh,a,b,height=145):
    for z in (height*.4,height):mesh.rod([a[0],a[1],a[2]+z],[b[0],b[1],b[2]+z],9,'iron')
    length=math.dist(a,b);n=max(1,math.ceil(length/95))
    for i in range(n+1):
        p=[a[j]+(b[j]-a[j])*i/n for j in range(3)]
        mesh.rod(p,[p[0],p[1],p[2]+height],7,'iron',6)


def clip_floor(poly,origin,direction,after=True):
    """Trim a landing at its neighboring flight plane, preserving its floor."""
    result=[]
    def signed(p):return ((p[0]-origin[0])*direction[0]+(p[1]-origin[1])*direction[1])*(1 if after else -1)
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da,db=signed(a),signed(b)
        if da>=-.00001:result.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);result.append([a[j]+(b[j]-a[j])*t for j in range(3)])
    unique=[]
    for p in result:
        if not unique or math.dist(p,unique[-1])>.001:unique.append(p)
    if len(unique)>1 and math.dist(unique[0],unique[-1])<.001:unique.pop()
    return unique


def floor_solid(mesh,top,depth=80):
    # Nearly collinear route turns can produce repeated clipping corners after
    # coordinate rounding. Weld only sub-millimetre polygon edges before faces.
    cleaned=[]
    for point in top:
        p=[round(v,4) for v in point]
        if not cleaned or math.dist(p,cleaned[-1])>=.01:cleaned.append(p)
    if len(cleaned)>1 and math.dist(cleaned[0],cleaned[-1])<.01:cleaned.pop()
    top=cleaned
    if len(top)<3:return
    if mesh.defer_flat_floors and all(p[2]==top[0][2] for p in top):
        mesh.flat_floors.setdefault((top[0][2],depth),[]).append([[p[0],p[1]] for p in top])
        return
    mesh.face(top,'flagstone');bottom=[[p[0],p[1],p[2]-depth] for p in top]
    mesh.face(list(reversed(bottom)),'stone')
    for a,b,c,d in zip(bottom,bottom[1:]+bottom[:1],top[1:]+top[:1],top):mesh.face([a,b,c,d],'limestone')


def polygon_area(poly):
    return sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1]))/2


def clean_floor_polygon(poly,minimum_edge_cm=1e-7):
    result=[]
    for p in poly:
        if not result or math.dist(p,result[-1])>minimum_edge_cm:result.append(p[:])
    if len(result)>1 and math.dist(result[0],result[-1])<=minimum_edge_cm:result.pop()
    changed=True
    while changed and len(result)>3:
        changed=False
        for j,b in enumerate(result):
            a,c=result[j-1],result[(j+1)%len(result)]
            if abs((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))<1e-7:
                result.pop(j);changed=True;break
    if len(result)<3 or abs(polygon_area(result))<1e-7:return []
    if polygon_area(result)<0:result.reverse()
    return result


def clip_floor_half_plane(poly,a,b,inside=True):
    result=[];sign=1 if inside else -1
    def side(p):return sign*((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
    for p,q in zip(poly,poly[1:]+poly[:1]):
        dp,dq=side(p),side(q)
        if dp>=0:result.append(p)
        if (dp>=0)!=(dq>=0):
            t=dp/(dp-dq);result.append([p[j]+(q[j]-p[j])*t for j in range(2)])
    return clean_floor_polygon(result)


def subtract_floor_polygon(poly,cutter):
    intersection=poly
    for a,b in zip(cutter,cutter[1:]+cutter[:1]):
        intersection=clip_floor_half_plane(intersection,a,b)
        if not intersection:return [poly]
    result=[];remaining=poly
    for a,b in zip(cutter,cutter[1:]+cutter[:1]):
        outside=clip_floor_half_plane(remaining,a,b,False)
        if outside:result.append(outside)
        remaining=clip_floor_half_plane(remaining,a,b)
        if not remaining:break
    return result


def union_floor_polygons(polygons):
    """Partition the exact original union; no convex hull or corridor expansion."""
    occupied=[];fragments=[]
    def bounds(p):return min(q[0] for q in p),min(q[1] for q in p),max(q[0] for q in p),max(q[1] for q in p)
    for raw in polygons:
        poly=clean_floor_polygon(raw)
        if not poly:continue
        box=bounds(poly);pieces=[poly]
        for cutter,other in occupied:
            if min(box[2],other[2])<=max(box[0],other[0]) or min(box[3],other[3])<=max(box[1],other[1]):continue
            pieces=[p for fragment in pieces for p in subtract_floor_polygon(fragment,cutter)]
            if not pieces:break
        fragments.extend(pieces);occupied.append((poly,box))
    return fragments


def floor_union_boundary(fragments):
    """Split shared fragment edges, then cancel only opposite internal segments."""
    vertices={tuple(p) for fragment in fragments for p in fragment};segments={}
    def key(p):return tuple(round(v,4) for v in p)
    for poly in fragments:
        for a,b in zip(poly,poly[1:]+poly[:1]):
            dx,dy=b[0]-a[0],b[1]-a[1];length2=dx*dx+dy*dy
            if length2<1e-12:continue
            length=math.sqrt(length2);cuts=[0.,1.]
            for p in vertices:
                if not(min(a[0],b[0])-1e-6<=p[0]<=max(a[0],b[0])+1e-6
                       and min(a[1],b[1])-1e-6<=p[1]<=max(a[1],b[1])+1e-6):continue
                if abs(dx*(p[1]-a[1])-dy*(p[0]-a[0]))>length*1e-6:continue
                t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length2
                if 1e-9<t<1-1e-9:cuts.append(t)
            cuts=sorted(set(cuts))
            for lo,hi in zip(cuts,cuts[1:]):
                p=key([a[0]+dx*lo,a[1]+dy*lo]);q=key([a[0]+dx*hi,a[1]+dy*hi])
                if math.dist(p,q)<.01:continue
                reverse=(q,p)
                if segments.get(reverse,0):
                    segments[reverse]-=1
                else:segments[(p,q)]=segments.get((p,q),0)+1
    if any(count>1 for count in segments.values()):raise ValueError('Landing union has a repeated exterior edge')
    return [edge for edge,count in segments.items() if count]


def emit_united_flat_floors(mesh):
    contributions=0;pieces=0;edges=0;areas=[]
    by_height={}
    for (z,depth),polygons in mesh.flat_floors.items():by_height.setdefault(z,{})[depth]=polygons
    for z,depths in sorted(by_height.items()):
        covered=[]
        before=union_floor_polygons([p for rows in depths.values() for p in rows])
        for depth,polygons in sorted(depths.items(),reverse=True):
            fragments=union_floor_polygons(polygons)
            # A deep hall slab and a thin stair landing can share the same
            # floor. Retain the original deeper solid on overlaps and emit its
            # visible top once; rooms keep their original depth and footprint.
            for cutter in covered:
                fragments=[p for fragment in fragments for p in subtract_floor_polygon(fragment,cutter)]
            # Repeated clipping can recreate submillimetre duplicate corners.
            fragments=[clean_floor_polygon([[round(v,4) for v in p] for p in poly],.01) for poly in fragments]
            fragments=[p for p in fragments if p];boundary=floor_union_boundary(fragments)
            covered.extend(fragments)
            contributions+=len(polygons);pieces+=len(fragments);edges+=len(boundary)
            for poly in fragments:
                mesh.face([[p[0],p[1],z] for p in poly],'flagstone')
                mesh.face([[p[0],p[1],z-depth] for p in reversed(poly)],'stone')
            for a,b in boundary:
                mesh.face([[a[0],a[1],z-depth],[b[0],b[1],z-depth],
                           [b[0],b[1],z],[a[0],a[1],z]],'limestone')
        areas.append(dict(heightCm=z,originalUnionAreaCm2=sum(polygon_area(p) for p in before),
                          emittedTopAreaCm2=sum(polygon_area(p) for p in covered)))
    mesh.flat_floors={}
    return dict(originalContributions=contributions,nonoverlappingPieces=pieces,exteriorSegments=edges,
                postClipDuplicateCornerDistanceCm=.01,overlapDepthPolicy='retain_deepest_original_slab',sameHeightAreas=areas)


def path_floor(mesh, points,width, stairs=False, rails=False, rail_breaks=(),endpoint_landing=False):
    """Real treads and joined landings: at most 15 cm rise, at least 18 cm run."""
    if endpoint_landing:
        a,b=points[:2];run=math.dist(a[:2],b[:2])
        if run>.01:
            dx,dy=(b[0]-a[0])/run,(b[1]-a[1])/run
            # A 20 cm threshold joins the retained paving at its exact floor;
            # collision then has a real surface under the endpoint, rather than
            # relying on two independently quantized triangle boundary planes.
            floor_solid(mesh,[[a[0]+dx*t-dy*s,a[1]+dy*t+dx*s,a[2]]
                for t,s in ((-10,-width/2),(10,-width/2),(10,width/2),(-10,width/2))])
    for segment,(a,b) in enumerate(zip(points,points[1:])):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        if length<.01:
            if abs(b[2]-a[2])>.01:raise ValueError('Vertical route without a physical stair run')
            continue
        nx,ny=-dy/length,dx/length;rise=b[2]-a[2]
        count=max(1,math.ceil(abs(rise)/15)) if stairs and abs(rise)>.1 else max(1,math.ceil(length/300))
        if stairs and abs(rise)>.1 and length/count<18:
            raise ValueError('Stair run cannot satisfy real capsule clearance')
        for i in range(count):
            u,v=i/count,(i+1)/count;z=a[2]+rise*(v if rise>0 else u) if stairs else a[2]+rise*u
            endz=z if stairs else a[2]+rise*v
            p=[a[0]+dx*u,a[1]+dy*u,z];q=[a[0]+dx*v,a[1]+dy*v,endz]
            top=[[p[0]+nx*width/2,p[1]+ny*width/2,p[2]],
                 [p[0]-nx*width/2,p[1]-ny*width/2,p[2]],
                 [q[0]-nx*width/2,q[1]-ny*width/2,q[2]],
                 [q[0]+nx*width/2,q[1]+ny*width/2,q[2]]]
            if abs(rise)<.1:
                if segment and points[segment-1][2]<a[2]-15:
                    previous=points[segment-1];direction=[a[0]-previous[0],a[1]-previous[1]]
                    if abs(direction[0]*dy-direction[1]*dx)>math.hypot(*direction)*length*1e-5:
                        top=clip_floor(top,a,direction)
                if segment+2<len(points) and points[segment+2][2]<b[2]-15:
                    following=points[segment+2];direction=[following[0]-b[0],following[1]-b[1]]
                    if abs(direction[0]*dy-direction[1]*dx)>math.hypot(*direction)*length*1e-5:
                        top=clip_floor(top,b,direction,False)
            floor_solid(mesh,top)
        if rails:
            # Open the inside of each turn/landing. A continuous rail around a
            # polyline elbow would otherwise cross the incoming playable floor.
            trim=(width/2+70)/length
            intervals=[(0,min(1,trim)),(max(0,1-trim),1)]
            for crossing,other_width in rail_breaks:
                candidates=crossing if isinstance(crossing[0],list) else [crossing]
                projected=[]
                for p in candidates:
                    t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(length*length)
                    if abs((p[0]-a[0])*nx+(p[1]-a[1])*ny)<1 and abs(p[2]-a[2])<16:projected.append(t)
                if not projected:continue
                margin=(other_width/2+70)/length
                lo,hi=max(0,min(projected)-margin),min(1,max(projected)+margin)
                if hi>lo:intervals.append((lo,hi))
            spans=[];cursor=0
            for lo,hi in sorted(intervals)+[(1,1)]:
                if lo>cursor:spans.append((cursor,lo))
                cursor=max(cursor,hi)
            for sign in (-1,1):
                for lo,hi in spans:
                    offset=width/2+20
                    rail(mesh,[a[0]+dx*lo+nx*offset*sign,a[1]+dy*lo+ny*offset*sign,a[2]],
                              [a[0]+dx*hi+nx*offset*sign,a[1]+dy*hi+ny*offset*sign,a[2]])
    for previous,junction,following in zip(points,points[1:],points[2:]):
        before=[junction[j]-previous[j] for j in range(2)];after=[following[j]-junction[j] for j in range(2)]
        lb,la=math.hypot(*before),math.hypot(*after)
        if min(lb,la)<.01:continue
        nb,na=[-before[1]/lb,before[0]/lb],[-after[1]/la,after[0]/la]
        for sign in (-1,1):
            top=[junction[:],[junction[0]+nb[0]*width/2*sign,junction[1]+nb[1]*width/2*sign,junction[2]],
                 [junction[0]+na[0]*width/2*sign,junction[1]+na[1]*width/2*sign,junction[2]]]
            angled=abs(before[0]*after[1]-before[1]*after[0])>lb*la*1e-5
            if angled and previous[2]<junction[2]-15:top=clip_floor(top,junction,before)
            if angled and following[2]<junction[2]-15:top=clip_floor(top,junction,after,False)
            if len(top)<3:continue
            if cross([top[1][j]-top[0][j] for j in range(3)],[top[2][j]-top[0][j] for j in range(3)])[2]<0:top.reverse()
            floor_solid(mesh,top)


def architecture(blueprint):
    from aegis_citadel_wing_hierarchy import wing_hierarchy
    from aegis_citadel_wing_footings import build_wing_footings
    from aegis_citadel_supports import reservations,prism,emit_support
    from aegis_citadel_crown import build_keep_crown
    from aegis_citadel_standard_detail import build_central_standard
    from aegis_citadel_surfaces import emit_surface
    meshes=[]
    court=Mesh('court_and_foundations');meshes.append(court)
    # Native walking hit the 10 cm upper edge chamfer at the retained-road seam.
    # Keep the signed 4210 cm deck and square structural edge; decorative masonry
    # bands below the walking surface still carry their carved bevels.
    court.block([20100,0,3305],[11800,14400,1810],'stone',0)
    # Banded stonework foundations remain detailed at approach level.
    for x in (14200,26000):
        for level in range(6):
            for y in range(-7200,7200,300):court.block([x,y+150,2600+level*250],[200,298,248],'stone',7)
    for radius in (750,1450,2350,2900):
        court.ring(20800,0,4210.4,radius-50,radius+50,'paving_inlay',128)
        court.ring(20800,0,4210.5,radius-53,radius-48,'gold',128)
    for i in range(16):
        a,b=(i+.08)*math.tau/16,(i+.38)*math.tau/16
        for inner,outer in ((825,1375),(1525,2275),(2425,2825)):
            court.face([[20800+r*math.cos(t),r*math.sin(t),4210.3]
                        for r,t in ((inner,a),(outer,a),(outer,b),(inner,b))],'paving_inlay')
    for i in range(16):
        t=i*math.tau/16;dx,dy=math.cos(t),math.sin(t)
        court.face([[20800+950*dx-6*dy,950*dy+6*dx,4210.2],
                    [20800+950*dx+6*dy,950*dy-6*dx,4210.2],
                    [20800+3000*dx+6*dy,3000*dy-6*dx,4210.2],
                    [20800+3000*dx-6*dy,3000*dy+6*dx,4210.2]],'gold')
    for x in range(14600,26000,400):
        for y in (-6800,6800):court.block([x,y,4212],[360,65,8],'limestone',1)
    for side in (-1,1):
        for x in (16500,23700):
            # The switchback's upper flight runs along Y4900. A recessed inner
            # deck edge keeps its headroom clear rather than roofing over it.
            court.block([x,side*6277.5,5348],[2200,2005,120],'limestone',12)
    paths=Mesh('stairs_and_balconies',defer_flat_floors=True);meshes.append(paths)
    reserved=reservations(blueprint);support_rows=[]
    surface_profiles={p['routeId']:p for p in blueprint.get('routeSurfaceProfiles',[])}
    paths.surface_bindings=[]
    route_widths={r['id']:r['width'] for r in blueprint['routes']}
    for r in blueprint['routes']:
        if r['kind'] in ('stair','balcony') or 'approach' in r['id']:
            breaks=[]
            if r['kind']=='balcony':
                for crossing in blueprint['crossingLedger']:
                    if crossing['connects'] and r['id'] in crossing['routes']:
                        index=crossing['routes'].index(r['id']);other=crossing['routes'][1-index]
                        breaks.append((crossing['positionsCm'][index],route_widths[other]))
            if r['id'] in surface_profiles:
                paths.surface_bindings.append(emit_surface(paths,r,surface_profiles[r['id']]))
            else:
                path_floor(paths,r['points'],3600 if r['id']=='grand_stair' else r['width'],r['kind']=='stair',r['kind']=='balcony',breaks,
                           endpoint_landing=r['id'].endswith('_approach'))
        if r['id']=='grand_stair':
            a,b=r['points'];w=1800;base=a[2]-80
            for sign in (-1,1):
                paths.face([[a[0],sign*w,base],[b[0],sign*w,base],
                            [b[0],sign*w,b[2]-80]],'stone')
            paths.face([[a[0],-w,base],[a[0],w,base],
                        [b[0],w,b[2]-80],[b[0],-w,b[2]-80]],'stone')
            paths.face([[b[0],-w,base],[b[0],w,base],
                        [b[0],w,b[2]-80],[b[0],-w,b[2]-80]],'stone')
        elif r['kind']=='stair' or r['id'].endswith('_approach') and r['id'] not in surface_profiles:
            for segment,(a,b) in enumerate(zip(r['points'],r['points'][1:])):
                if math.dist(a[:2],b[:2])<.01:continue
                support_rows.append(dict(route=r['id'],segment=segment,
                    **emit_support(paths,prism(a,b,r['width']+400,2400),reserved,(r['id'],segment))))
    for x in (16500,23700):
        for sign in (-1,1):
            for xx in (x-1100,x+1100):
                paths.block([xx,sign*7000,3875],[220,220,2950],'limestone',8)
                paths.block([xx,sign*7000,4210],[300,220,160],'limestone',8)
            side_arch(paths,x,sign*7000,4210,2040,2200,150,65,False)
    # Outward arcaded buttresses carry the raised routes. They remain outside
    # every reserved lane, with braces above ground-headroom and below the deck.
    for side in (-1,1):
        # A broad masonry terrace carries each playable raised side route. Its
        # inward face stays outside the lower flank lane rather than sealing it.
        # Supporting terrace caps sit below the route deck. Coplanar duplicate
        # tops produce shadow/Z-fighting artifacts despite valid outward normals.
        paths.block([20100,side*6980,5328],[9400,1600,160],'flagstone',12)
        # Thick terraces are carved by real vaulted passages wherever the lower
        # flank or another stair crosses them. The deck remains independently
        # authored at its exact existing height.
        a,b=[15400,side*6500,5410],[24800,side*6500,5410]
        support_rows.append(dict(route=side,terrace=True,
            **emit_support(paths,prism(a,b,1600,2400,-84),reserved)))
        paths.block([20100,side*7170,3865],[9400,280,2930],'stone',12)
        for x in range(15800,24800,700):
            side_arch(paths,x,side*7350,2810,500,1750,150,75,False)
            paths.block([x-340,side*7330,3865],[130,220,2930],'limestone',8)
        for x in (18200,20600,22600):
            p=[x,side*7100,2400]
            if route_clearance(blueprint,p,90,2930):
                paths.block([x,side*7100,3865],[180,180,2930],'limestone',10)
                paths.rod([x,side*7100,4860],[x,side*6500,5325],65,'limestone')
                side_arch(paths,x,side*7170,2700,650,1700,90,55,False)
        for x in (24400,25100):
            t=(x-23700)/2300;y=side*(5550-2050*t);floor=5410+1800*t
            for shift in (650,850,1050):
                xx=x+shift*.666;yy=y+side*shift*.746;p=[xx,yy,2400]
                if not route_clearance(blueprint,p,100,floor-2480):continue
                paths.block([xx,yy,(2400+floor-80)/2],[200,200,floor-2480],'limestone',10)
                paths.rod([xx,yy,floor-410],[x,y,floor-85],75,'limestone')
                break
    # Raised entrance terraces/galleries have explicit floors with fall protection.
    paths.block([26450,0,5928],[900,8600,160],'flagstone',8)
    for side in (-1,1):
        paths.block([29450,side*3500,7128],[6900,800,160],'flagstone',8)
        rail(paths,[26500,side*3050,7210],[32200,side*3050,7210])
    curtain=Mesh('curtain_gatehouses');meshes.append(curtain)
    front_openings=[{**leaf,'width':leaf['width']+40,'height':1800 if leaf['point'][1]==0 else leaf['height']} for leaf in blueprint['gates'][0]['leaves']]
    wall_cut(curtain,14200,-7500,7500,4210,5410,front_openings,240)
    wall_cut(curtain,14200,-1800,1800,5410,6510,front_openings,240)
    for side in (-1,1):
        curtain.block([20100,side*7400,4155],[11800,260,3510],chamfer=15)
        for x in range(14300,25900,250):
            curtain.block([x,side*7400,6050],[125,280,220],'limestone',12)
        tower(curtain,14800,side*7820,4210,1000,3600,1900,'square')
        tower(curtain,25100,side*7440,4210,1100,3600,1900,'battlement')
        for x in (17800,21400):tower(curtain,x,side*7450,4210,800,2800 if x==17800 else 3300,1800,'battlement' if x==17800 else 'square')
        tower(curtain,14200,side*1550,4210,1200,3900 if side<0 else 3400,1600,'battlement')
        for x in (16600,20100,23500):
            curtain.block([x,side*7550,4430],[320,500,3900],'limestone',12)
            side_arch(curtain,x,side*7690,4400,300,1650,60,65,True,outward_side=side)
        for x in range(15400,24700,1100):
            side_arch(curtain,x,side*7600,2750,680,1700,120,80,False)
            side_arch(curtain,x,side*7600,4790,260,900,90,55,True,(x//1100)%4==0,outward_side=side)
        for x in (16500,23700):
            for offset in (-600,600):
                side_arch(court,x+offset,side*7210,2680,520,1370,90,65,False)
    for y in range(-7000,7100,250):
        if any(abs(y-l['point'][1])<l['width']/2+70 for l in blueprint['gates'][0]['leaves']):continue
        curtain.block([14200,y,5550],[300,130,220],'limestone',12)
    arch(curtain,14100,0,4210,1840,1800,200,130)
    # The reference curtain is inhabited masonry, with a shallow arcade rhythm.
    # Every bay is between the main and side apertures; its foundation detail is
    # below walking height and its upper relief projects only toward the street.
    curtain.front_blind_bays=[]
    for sign in (-1,1):
        for y in (2500,3550,4600,5350):
            curtain.front_blind_bays.append(blind_bay(curtain,14080,sign*y,4335,500,940,30))
            curtain.front_blind_bays.append(blind_bay(curtain,14093,sign*y,2620,620,1280,28))
        for z in (4080,5320):
            curtain.block([14063,sign*3950,z],[34,3550,40],'limestone',3)
    # Reference's long navy standards and front gate sun sigil.
    for side in (-1,1):
        banner(curtain,13530,side*1550,7860,740,3400)
        banner(curtain,14210,side*7440,7480,600,3000)
    curtain.outer_crest_support=outer_crest_support(curtain)
    sun(curtain,14075,0,6790,330)
    hall=Mesh('fortress_keep_shell');meshes.append(hall)
    # A broad, flat-crowned fortress replaces the cathedral's dominant house roof.
    # Foundation fills only below the hall floor; functional rooms remain hollow.
    hall.block([29700,0,4094],[7400,18200,3388],'stone',12)
    hall.foundation_course_details=foundation_courses(hall)
    floor_solid(paths,[[26000,-4300,6010],[33400,-4300,6010],[33400,4300,6010],[26000,4300,6010]],220)
    hall_openings=[{**leaf,'width':leaf['width']+40,'height':2600 if leaf['width']==1800 else leaf['height']}
                   for leaf in blueprint['gates'][1]['leaves']]
    wall_cut(hall,26000,-4600,4600,6010,14400,hall_openings,280)
    for side in (-1,1):
        wall_cut(hall,26000,side*5950-1350,side*5950+1350,6010,11200,hall_openings,280)
    for leaf in blueprint['gates'][1]['leaves']:
        x,y,z=leaf['point'];arch(hall,x-40,y,z,leaf['width']+40,2600 if leaf['width']==1800 else leaf['height'],160,100)
    for side in (-1,1):
        for x0,x1 in ((26000,29400),(31400,33400)):
            hall.block([(x0+x1)/2,side*4300,10205],[x1-x0,180,8390],chamfer=12)
        hall.block([30400,side*4300,11555],[2000,180,5690],chamfer=12)
    hall.block([33400,0,10205],[220,8600,8390],chamfer=12)
    # The replacement crown and vaulted ceiling provide the roof. Retaining the
    # previous solid roof here would fill its real upper lancet chambers.
    facade=Mesh('gothic_facade_and_spires');meshes.append(facade)
    for y in range(-4300,4301,550):
        # Bundled Gothic shafts and deeply projecting buttresses give the facade
        # vertical structure at the reference's monumental scale.
        if abs(y)<1200:continue
        base=10000 if 2600<abs(y)<4100 else 6010
        facade.block([25790,y,(base+14410)/2],[380,150,14410-base],'stone',8)
        for dy in ((-55,0,55) if abs(y)<=1750 or abs(y)>=3900 else (0,)):
            facade.rod([25588,y+dy,base+130],[25588,y+dy,14450],17,'limestone',6)
        pinnacle(facade,25760,y,14400,170,1500 if abs(y)>3000 else 2050)
        for z in (9500,12350):
            facade.block([25590,y,z],[100,240,80],'limestone',6)
    facade.wing_hierarchy=[]
    for side in (-1,1):
        # Retained galleries and rooms pass through five exact openings. Their
        # neighboring mass is a deep curtain terrace, not a freestanding ribbon.
        facade.block([25200,side*6800,5930],[2000,1200,160],'limestone',6)
        facade.block([25100,side*7300,4135],[1600,240,3470],'stone',8)
        for y in (side*6700,side*7300):
            facade.block([25000,y,5050],[180,180,1680],'limestone',6)
            facade.block([25000,y,5870],[280,280,90],'limestone',6)
        arch(facade,24920,side*6950,4210,720,1700,160,70)
        for tier,(x0,x1,yy,width,base,top) in enumerate((
            (27000,34400,8000,2200,6010,9700),
            (28100,34200,7800,1400,9700,11900),
            (29300,33600,6600,1500,11900,13700))):
            yy*=side;outside=yy+side*width*.5
            hierarchy=wing_hierarchy(x0,x1,base,top,UPPER_FACTOR)
            hierarchy.update(side=side,tier=tier,integrated=True)
            facade.wing_hierarchy.append(hierarchy)
            facade.block([(x0+x1)/2,yy,(base+top)/2],[x1-x0,width,top-base],'stone',10)
            facade.block([(x0+x1)/2,yy,top+35],[x1-x0+100,width+100,70],'flagstone',8)
            cornice=hierarchy['cornice']
            facade.block([(x0+x1)/2,yy,cornice['sourceCenterZCm']],
                [x1-x0,width+2*cornice['outwardProjectionCm'],cornice['sourceDepthCm']],
                'limestone',6)
            battlements(facade,x0,x1,outside,top+140,170)
            for bay,x in enumerate(hierarchy['bayPositionsCm']):
                side_arch(facade,x,outside+side*80,base+350,240,hierarchy['windowHeightCm'],140,65,True,(x//560+tier)%4==0,outward_side=side)
                # Select attached upper piers; all existing lancet bays stay clear.
                strengthen=tier>=1 and bay in hierarchy['pinnacleBayIndices']
                facade.block([x-280,outside,(base+top)/2],
                    [160 if strengthen else 130,470 if strengthen else 380,top-base+100],'stone',8)
                if bay in hierarchy['rodBayIndices'] or strengthen:
                    offset,radius=(260,22) if strengthen else (215,16)
                    for dx in (-45,45):facade.rod([x-280+dx,outside+side*offset,base+120],[x-280+dx,outside+side*offset,top+170],radius,'limestone',6)
                if bay in hierarchy['pinnacleBayIndices']:
                    # Convert the full 700 cm height, including its existing finial.
                    height=700/UPPER_FACTOR-90 if strengthen else 850+tier*150
                    pinnacle(facade,x-280,outside,top+210,130,height)
            for y in range(int(yy-width/2)+230,int(yy+width/2)-120,420):
                arch(facade,x0-120,y,base+420,240,min(1500,top-base-500),180,60,glass=True,lit=(y//420)%4==0)
            tower(facade,x0+450,outside,base,850-tier*90,top-base+850,1100+tier*650,
                  'battlement' if tier==0 else 'square' if tier==1 else 'spire')
            tower(facade,x1-500,outside,base,720-tier*80,top-base+600,1500+tier*350,'square')
            final_top=top-200 if top-200<=9000 else 9000+(top-200-9000)*UPPER_FACTOR
            final_banner(facade,x0-200,yy,final_top,420,2200 if tier==0 else 1800)
        for y in (side*5100,side*6250,side*7100):
            for z in (6900,9100):arch(facade,25805,y,z,250,1300,150,65,glass=True,lit=abs(y)==6250)
            facade.block([25795,y-350,8570],[290,130,5260],'stone',6)
            pinnacle(facade,25950,y-350,11200,150,1300)
        # The central body stays rectangular and broad. Taller clustered spires
        # rise behind it, matching the reference's broad vertical keep silhouette.
        for x in range(26800,33200,550):
            side_arch(facade,x,side*4435,10400,240,2500,170,70,True,(x//550)%5==0,outward_side=side)
            base=9000 if 29400<x-270<31500 else 6180
            facade.block([x-270,side*4540,(base+14480)/2],[150,410,14480-base],'stone',8)
            for dx in (-45,45):facade.rod([x-270+dx,side*4770,base],[x-270+dx,side*4770,14480],16,'limestone',6)
            pinnacle(facade,x-270,side*4540,14400,150,1400 if x<30000 else 1150)
        battlements(facade,26100,33300,side*4360,14400,190)
        for x in (27400,29600,31900):
            facade.rod([x,side*5520,10100],[x,side*4300,13850],115,'stone')
            facade.rod([x,side*5520,9660],[x,side*4300,13100],60,'limestone')
    battlements(facade,25400,26600,-4500,14500,190)
    battlements(facade,25400,26600,4500,14500,190)
    for y in range(-4400,4400,210):
        if abs(y)<=950:continue
        facade.block([25810,y,14500],[280,110,210],'stone',6)
    # Broad portals, nested archivolts, statue niches and gold-blue wall standards.
    for order in range(5):
        arch(facade,25720-order*55,0,6010,1840+order*180,2810+order*235,130,85)
    facade.fine_portal_details=portal_roll_details(facade)
    for side in (-1,1):
        for y in (side*1600,side*4430):
            arch(facade,25520,y,7560,480,1900,240,80)
            facade.block([25510,y,7520],[490,700,110],'limestone',12)
            pinnacle(facade,25520,y,9580,220,1600)
        final_banner(facade,25470,side*2500,10690,570,3250)
        final_banner(facade,25460,side*6050,9840,510,2550)
    # The supported central standard is appended in final space after compression.
    for side in (-1,1):
        for y in (side*1190,side*1470):
            arch(facade,25590,y,upper_source_z(9250),300,1400/UPPER_FACTOR,140,65,glass=True,lit=False)
    for y in (-3950,-3300,-1500,1500,3300,3950):
        for z in (10950,12600):arch(facade,25720,y,z,230,1250,190,55,glass=True,lit=z==12600 and abs(y)==1500)
    for y in (-3400,-2100,-800,800,2100,3400):
        arch(facade,26640,y,14500,260,1850,160,70,glass=True,lit=abs(y)==800)
    # Corner castellated keeps, narrow belfries and soaring clustered lancet
    # towers vary both width and height rather than repeating pyramid turrets.
    for y,height,style in ((-7200,4900,'battlement'),(7200,4400,'battlement'),
                           (-4550,8900,'spire'),(4550,8500,'spire'),
                           (-2050,6600,'square'),(2050,7000,'square')):
        tower(facade,26300,y,6010,1050 if abs(y)>3000 else 780,height,3300 if style=='spire' else 1800,style)
    # The six-tower replacement is appended in final coordinates below. All
    # old central crown blocks, glass-filled belfries and detached roof needles
    # are retired, while the flanking keep wings remain individually authored.
    for x in (28300,31900):
        for side in (-1,1):tower(facade,x,side*4900,6010,780,8400,2000,'battlement' if x==31900 else 'spire')
    for side in (-1,1):
        tower(facade,22400,side*7800,4210,1150,4600 if side<0 else 3900,1600,'battlement')
        tower(facade,28600,side*8900,6010,1000,5400,1900,'square')
    interior=Mesh('ribbed_interiors');meshes.append(interior)
    for x in (27820,28900,29900,31500):
        for side in (-1,1):
            # Bundled supports remain outside the central and side reservations.
            interior.block([x,side*2200,7125],[120,120,2230],'limestone',12)
            interior.block([x,side*2200,8265],[240,240,110],'limestone',10)
            for dy in (-35,35):interior.rod([x-62,side*2200+dy,6030],[x-62,side*2200+dy,8210],14,'limestone',6)
    for x in (27200,28600,30000,31600):
        for side in (-1,1):
            arch(interior,x-50,side*4170,7850,170,900,60,30,glass=True)
    for room in blueprint['rooms'][2:]:
        a,b=room['bounds'];cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2
        floor_solid(paths,[[a[0],a[1],6010],[b[0],a[1],6010],[b[0],b[1],6010],[a[0],b[1],6010]],200)
        outside=b[1] if cy>0 else a[1]
        interior.block([cx,outside,7360],[b[0]-a[0],120,2700],chamfer=10)
        for x in (a[0],b[0]):interior.block([x,cy,7360],[120,b[1]-a[1],2700],chamfer=10)
        interior.block([cx,cy,8720],[b[0]-a[0]+150,b[1]-a[1]+150,140],'stone',12)
        for x in range(a[0]+400,b[0]-200,800):arch(interior,x,cy,7510,b[1]-a[1]-200,1100,80,45)
        for x in range(a[0]+450,b[0]-300,650):
            side_arch(facade,x,outside+(75 if cy>0 else -75),6650,220,1450,100,50,True,outward_side=1 if cy>0 else -1)
            facade.block([x-330,outside,7490],[90,250,3000],'limestone',5)
        for side_y in (a[1]-80,b[1]+80):
            facade.face([[a[0]-80,side_y,8890],[b[0]+80,side_y,8890],
                         [b[0]+80,cy,10600],[a[0]-80,cy,10600]],'slate')
        for x in (a[0]-80,b[0]+80):
            facade.face([[x,a[1]-80,8890],[x,b[1]+80,8890],[x,cy,10600]],'stone')
        tower(facade,b[0]-350,outside,6010,750,3700,1900)
    footings,footing_contract=build_wing_footings(blueprint)
    footings.wing_foundation_repairs=footing_contract
    meshes.append(footings)
    # Decorative plinths sit away from the 6.5 m objective capture rings.
    dressing=Mesh('sculpture_plinths');meshes.append(dressing)
    placements=[]
    for key,p,scale in [('court_oath',[20800,0,4710],1.97),
                         ('west_guard',[24800,-2500,5860],2.8),('east_guard',[24800,2500,5860],2.8),
                         ('west_terrace_guard',[25000,-6800,6010],2.5),('east_terrace_guard',[25000,6800,6010],2.5),
                         ('throne',[32630,0,6010],.55),('war_table',[29400,-5700,6010],.85),
                         ('archive',[32000,-6350,6010],1.3),('treasury',[32200,6150,6010],1.4),
                         ('reliquary',[31500,6100,6010],1.3),('arms_rack',[27700,-3900,6010],.8)]:
        kind='oath_statue' if 'guard' in key or key=='court_oath' else key
        if key=='court_oath':
            for tier in range(3):dressing.block([p[0],p[1],4260+tier*100],[1000-tier*20,1000-tier*20,100],'limestone',15)
            dressing.block([p[0],p[1],4590],[600,600,200],'carved_stone',18)
            dressing.block([p[0],p[1],4690],[780,780,40],'limestone',12)
            for sign in (-1,1):
                arch(dressing,p[0]+sign*305,p[1],4490,290,180,45,24,material='carved_stone')
        elif key in ('west_guard','east_guard'):
            dressing.block([p[0],p[1],5035],[700,700,1650],'limestone',18)
            arch(dressing,p[0]-360,p[1],4470,370,1050,90,55)
            dressing.block([p[0],p[1],5815],[850,850,90],'limestone',10)
        placements.append(dict(id=key,source='public/assets/models/prop_aegis_citadel_'+kind+'.glb',point=p,scale=scale,
            **(dict(yawDegrees=180) if key=='throne' else {})))
    for index,(x,y,z) in enumerate([(18200,-3600,4210),(18200,3600,4210),(22000,-6500,4210),(22000,6500,4210),
        (23600,-1300,4210),(23600,1300,4210),(26400,-1250,6010),(26400,1250,6010),
        (27950,-3450,6010),(27800,3900,6010),(30200,-3900,6010),(30200,3900,6010)]):
        candidates=sorted((dx*dx+dy*dy,x+dx,y+dy) for dx in range(-800,801,100) for dy in range(-800,801,100))
        for _,xx,yy in candidates:
            if z==6010 and not(26150<=xx<=33000 and abs(yy)<=4080):continue
            if z==4210 and not(14500<=xx<=25200 and abs(yy)<=7100):continue
            if route_clearance(blueprint,[xx,yy,z],75,190):
                x,y=xx,yy;break
        else:raise ValueError('No clear authored brazier placement')
        placements.append(dict(id='brazier_'+str(index),source='public/assets/models/prop_riftspire_war_brazier.glb',point=[x,y,z],scale=.45))
    gate_meshes=[]
    for gate in blueprint['gates']:
        for index,leaf in enumerate(gate['leaves']):
            gate_mesh=Mesh('gate_'+gate['id']+'_'+str(index));width,height=leaf['width'],leaf['height']
            # Local leaf geometry is placed by the compound authoritative gate actor.
            for y in range(int(-width/2)+20,int(width/2),60):
                gate_mesh.block([0,y,height/2],[70,24,height],'iron',4)
                gate_mesh.rod([-42,y,height],[42,y,height],12,'gold')
            for z in range(100,int(height),140):gate_mesh.block([0,0,z],[80,width,30],'iron',4)
            gate_mesh.block([0,0,height-20],[110,width+60,60],'gold',8)
            gate_meshes.append(gate_mesh)
    paths.floor_union_receipt=emit_united_flat_floors(paths)
    massing=blueprint['upperMassing']
    for mesh in meshes:
        mesh.reshape_upper(massing['preservedThroughZCm'],massing['originalHighestZCm'],massing['coreCompressionHighestZCm'])
        mesh.reproject_stone_uvs()
    crown,crown_contract=build_keep_crown()
    append_mesh(facade,crown);facade.crown_replacement=crown_contract
    support,standard,standard_contract=build_central_standard()
    append_mesh(facade,support);append_mesh(facade,standard)
    facade.central_standard_replacement=standard_contract
    commander_vault(interior)
    paths.structural_supports=dict(policy='solid_masonry_with_exact_vaulted_route_subtraction',
        signedLaneMarginCm=47,minimumStraightHeadroomCm=350,deckSeparationCm=2,rows=support_rows)
    for mesh in meshes:mesh.surface_duplicate_repair=mesh.remove_identical_faces()
    return meshes,gate_meshes,placements
