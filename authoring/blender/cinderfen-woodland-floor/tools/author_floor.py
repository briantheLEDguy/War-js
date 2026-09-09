"""Expand original wood surveys and botanical paths into retained closed meshes."""
import hashlib,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
ROOT=Path(__file__).resolve().parents[1]
DESIGN_PATH=ROOT/'source/design.json';D=json.loads(DESIGN_PATH.read_text())

def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def mul(a,s):return tuple(x*s for x in a)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def length(a):return math.sqrt(dot(a,a))
def unit(a):return mul(a,1/max(1e-10,length(a)))
def mix(a,b,t):return add(mul(a,1-t),mul(b,t))
def rounded(a):return [round(x,7) for x in a]

class Mesh:
    def __init__(self,name,materials):self.name=name;self.materials=materials;self.vertices=[];self.faces=[];self.uv=[];self.face_materials=[];self.grain=[]
    def vertex(self,p,grain=None):self.vertices.append(rounded(p));self.grain.append(rounded(grain if grain is not None else p));return len(self.vertices)-1
    def face(self,ids,uv,material=0):self.faces.append(ids);self.uv.append([rounded(c) for c in uv]);self.face_materials.append(material)
    def record(self):return {'name':self.name,'materials':self.materials,'vertices':self.vertices,'faces':self.faces,'corner_uv':self.uv,'face_materials':self.face_materials,'grain_coordinates':self.grain}

def interpolate(points,steps,closed=False):
    result=[];count=len(points) if closed else len(points)-1
    for i in range(count):
        get=lambda k:points[k%len(points)] if closed else points[max(0,min(k,len(points)-1))]
        a,b,c,d=get(i-1),get(i),get(i+1),get(i+2)
        for j in range(steps):
            t=j/steps
            result.append(tuple(.5*(2*b[k]+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in range(len(b))))
    if not closed:result.append(tuple(points[-1]))
    return result

def frame(path,index):
    tangent=unit(sub(path[min(index+1,len(path)-1)][:3],path[max(0,index-1)][:3]))
    guide=(0,0,1) if abs(tangent[2])<.9 else (0,1,0)
    side=unit(cross(guide,tangent));normal=unit(cross(tangent,side))
    return tangent,side,normal

def woody_limb(control,lod,index):
    mesh=Mesh('surveyed_broken_alder_limb_'+str(index),['fallen_bark','broken_heartwood','pale_fracture'])
    path=interpolate(control,[5,3,1][lod]);section=interpolate(D['limbSection'],[4,2,1][lod],True)
    if lod==2:section=section[::2]
    rings=[];run=0;frames=[]
    for row,p in enumerate(path):
        tangent,side,normal=frame(path,row);frames.append((tangent,side,normal));ids=[]
        if row:run+=length(sub(p[:3],path[row-1][:3]))
        for j,(x,y) in enumerate(section):
            # Narrow physical bark ridges preserve a broken, asymmetric contour.
            relief=1+(.018 if lod==0 else .009)*math.sin(j*2.31+row*.29+index)*(.35+.65*math.sin(row*.43+j*.17)**2)
            bare_arc=.12<(j/len(section)+index*.13)%1<.39
            if bare_arc and row>=len(path)-2:relief*=.93
            centre=p[:3];break_offset=0
            if row in (0,len(path)-1):
                value=D['brokenEndOffsets'][int(j*len(D['brokenEndOffsets'])/len(section))]
                break_offset=value*(1 if row else -1)*(1 if index==0 else .55)
            point=add(add(centre,mul(tangent,break_offset)),add(mul(side,x*p[3]*relief),mul(normal,y*p[3]*relief*.83)))
            ids.append(mesh.vertex(point,(x*p[3]*relief,y*p[3]*relief*.83,run+break_offset)))
        rings.append((ids,run))
    n=len(section)
    for row in range(len(rings)-1):
        a,va=rings[row];b,vb=rings[row+1]
        for j in range(n):
            k=(j+1)%n;bare_arc=.12<(j/n+index*.13)%1<.39
            mesh.face([a[j],a[k],b[k],b[j]],[(j/n,va),(j/n+1/n,va),(j/n+1/n,vb),(j/n,vb)],1 if bare_arc and row==len(rings)-2 else 0)
    for endpoint in (0,len(path)-1):
        p=path[endpoint];tangent,side,normal=frames[endpoint];outer=rings[endpoint][0]
        reverse=endpoint==0;sign=-1 if reverse else 1;scale=.94;inner=[]
        for j,(x,y) in enumerate(section):
            tear=D['brokenEndOffsets'][int(j*len(D['brokenEndOffsets'])/n)]
            depth=tear*.38*sign*(1 if index==0 else .55)
            position=add(add(p[:3],mul(tangent,depth)),add(mul(side,x*p[3]*scale),mul(normal,y*p[3]*scale*.83)))
            inner.append(mesh.vertex(position,(x*p[3]*scale,y*p[3]*scale*.83,rings[endpoint][1]+depth)))
        for j in range(n):
            k=(j+1)%n;ids=[outer[j],outer[k],inner[k],inner[j]]
            coords=[(.5+section[j][0]*.45,.5+section[j][1]*.45),(.5+section[k][0]*.45,.5+section[k][1]*.45),(.5+section[k][0]*scale*.45,.5+section[k][1]*scale*.45),(.5+section[j][0]*scale*.45,.5+section[j][1]*scale*.45)]
            if reverse:ids.reverse();coords.reverse()
            arc=(j/n+index*.13)%1;mesh.face(ids,coords,2 if .20<arc<.25 else 1 if .12<arc<.39 else 0)
        # The broken surface follows a non-radial measured height survey. The
        # constrained triangulation retains the entire irregular boundary and
        # avoids a spoke fan or a perfectly flat saw-cut disk.
        survey=D['heartwoodBreakSurvey'] if lod==0 else D['heartwoodBreakSurvey'][::2] if lod==1 else D['heartwoodBreakSurvey'][::4]
        coordinates=[Vector((x*scale,y*scale)) for x,y in section]+[Vector(row[:2]) for row in survey]
        verts,edges,faces,originals,_,_=delaunay_2d_cdt(coordinates,[],[list(range(n))],1,1e-8,True)
        mapping=[]
        for i,point in enumerate(verts):
            original=originals[i][0] if originals[i] else None
            if original is not None and original<n:mapping.append(inner[original]);continue
            if original is not None:height=survey[original-n][2]
            else:height=.02*math.sin(point.x*13)-.04
            depth=height*p[3]*sign
            position=add(add(p[:3],mul(tangent,depth)),add(mul(side,point.x*p[3]),mul(normal,point.y*p[3]*.83)))
            mapping.append(mesh.vertex(position,(point.x*p[3],point.y*p[3]*.83,rings[endpoint][1]+depth)))
        for face in faces:
            ids=[mapping[i] for i in face];coords=[(.5+verts[i].x*.45,.5+verts[i].y*.45) for i in face]
            if reverse:ids.reverse();coords.reverse()
            mesh.face(ids,coords,1)
    correction=D['limbLodGroundCorrectionsM'][lod]
    if correction:
        for vertex in mesh.vertices:vertex[2]=round(vertex[2]+correction,7)
    return mesh

STEM_SECTION=[(.98,.03),(.48,.81),(-.43,.86),(-1.03,-.04),(-.51,-.78),(.51,-.88)]
def stem(mesh,control,lod):
    path=interpolate(control,[3,2,1][lod]);section=STEM_SECTION if lod<2 else STEM_SECTION[::2];rings=[]
    for row,p in enumerate(path):
        tangent,side,normal=frame(path,row)
        rings.append([mesh.vertex(add(p[:3],add(mul(side,x*p[3]),mul(normal,y*p[3])))) for x,y in section])
    n=len(section)
    for row in range(len(rings)-1):
        for j in range(n):
            k=(j+1)%n;mesh.face([rings[row][j],rings[row][k],rings[row+1][k],rings[row+1][j]],[(j/n,row/len(rings)),((j+1)/n,row/len(rings)),((j+1)/n,(row+1)/len(rings)),(j/n,(row+1)/len(rings))])
    for row,reverse in ((0,True),(len(rings)-1,False)):
        ids=list(rings[row]);coords=[(.5+x*.45,.5+y*.45) for x,y in section]
        if reverse:ids.reverse();coords.reverse()
        mesh.face(ids,coords)

def thick_leaf(mesh,base,axis,normal,size,width,lod,outline,phase,bend=.09):
    axis=unit(axis);normal=unit(sub(normal,mul(axis,dot(normal,axis))));side=unit(cross(normal,axis))
    profile=outline if lod==0 else outline[::2]+([outline[-1]] if outline[::2][-1]!=outline[-1] else []) if lod==1 else [outline[0],outline[len(outline)//3],outline[2*len(outline)//3],outline[-1]]
    rows=[];tile=phase%4
    def uv(t,w):return ((tile+.5+w*.46)/4,t)
    for row,(t,w) in enumerate(profile):
        centre=add(base,add(mul(axis,t*size),mul(normal,size*(bend*math.sin(t*math.pi)-.10*t*t))))
        ids=[]
        for under in (False,True):
            for across in (-1,0,1):
                asymmetry=1+.06*math.sin(phase+row*.87+across)
                fold=width*.15*(1-abs(across))*math.sin(t*math.pi)
                point=add(centre,add(mul(side,across*w*width*.5*asymmetry),mul(normal,fold+(-.00035 if under else .00035))))
                ids.append(mesh.vertex(point))
        rows.append((ids,t,w))
    for row in range(len(rows)-1):
        a,t,w=rows[row];b,u,v=rows[row+1]
        for under in (0,3):
            for col in (0,1):
                ids=[a[col+under],a[col+1+under],b[col+1+under],b[col+under]];coords=[uv(t,(col-1)*w),uv(t,col*w),uv(u,col*v),uv(u,(col-1)*v)]
                if under:ids.reverse();coords.reverse()
                mesh.face(ids,coords)
        for col in (0,2):
            atex=uv(t,(col-1)*w);btex=uv(u,(col-1)*v)
            mesh.face([a[col],b[col],b[col+3],a[col+3]],[atex,btex,(btex[0]+.0002,btex[1]),(atex[0]+.0002,atex[1])])
    for ids,t,w in (rows[0],rows[-1]):
        mesh.face([ids[0],ids[1],ids[2],ids[5],ids[4],ids[3]],[uv(t,-w),uv(t,0),uv(t,w),uv(t+.0002,w),uv(t+.0002,0),uv(t+.0002,-w)])

def plants(lod):
    rachis=Mesh('arched_green_fern_rachises',['fern_stem']);pinnules=Mesh('separate_folded_fern_pinnules',['fern_leaf']);sedge=Mesh('broad_shade_wood_sedge_blades',['wood_sedge'])
    for i,control in enumerate(D['fernRachises']):
        if lod==2 and i in (2,5):continue
        stem(rachis,control,lod);path=interpolate(control,7);pairs=[13,9,5][lod]
        for j in range(pairs):
            t=.16+j*.76/(pairs-1);index=min(len(path)-2,int(t*(len(path)-1)));f=t*(len(path)-1)-index;base=mix(path[index][:3],path[index+1][:3],f)
            tangent=unit(sub(path[index+1][:3],path[index][:3]));side=unit(cross((0,0,1),tangent))
            for sign in (-1,1):
                origin=add(base,mul(tangent,(.003 if sign==1 else -.004)))
                direction=unit(add(mul(side,sign),mul(tangent,.48)))
                normal=unit((.14*math.sin(i*1.7+j),.16*math.cos(i+j*.6),1))
                size=(.157+.015*math.sin(i*1.4))*(math.sin(t*math.pi)**.7)*(1+.08*math.sin(j+i*2+sign))
                thick_leaf(pinnules,origin,direction,normal,size,size*.30,lod,D['pinnuleOutline'],i*31+j*2+sign,.075)
    for tuft,(x,y,h,phase) in enumerate(D['woodSedgeTufts']):
        count=[15,10,6][lod]
        for j in range(count):
            angle=phase+j*2.399;size=h*(1.55+.21*math.sin(j*1.9+tuft));axis=(math.cos(angle)*.68,math.sin(angle)*.68,.74+.14*math.sin(j))
            base=(x+.022*math.cos(j),y+.024*math.sin(j),-.018)
            normal=(math.cos(angle)*.34,math.sin(angle)*.34,.84)
            thick_leaf(sedge,base,axis,normal,size,.034+.008*((j+tuft)%3),lod,D['woodSedgeOutline'],tuft*17+j,.21)
    return [rachis,pinnules,sedge]

def main():
    assets={
        'frontier_cinderfen_fallen_alder_limb':{'name':'Cinderfen fallen alder limb','contract':{'kind':'fallen_wood','plantedDatum':0,'placement':'Damp woodland floor; align long limb across open soil pockets, keep away from narrow travel lines.','colliders':[],'walkableSurfaces':[],'cameraSolid':False},'lods':[]},
        'frontier_cinderfen_fern_wood_sedge':{'name':'Cinderfen shade fern and wood sedge','contract':{'kind':'shade_foliage','plantedDatum':0,'placement':'Damp shaded woodland soil beneath alder crowns; unsuitable for open geothermal mud or deep water.','colliders':[],'walkableSurfaces':[],'cameraSolid':False},'lods':[]}}
    for lod in range(3):
        assets['frontier_cinderfen_fallen_alder_limb']['lods'].append({'level':lod,'objects':[woody_limb(p,lod,i).record() for i,p in enumerate(D['limbPaths'])]})
        assets['frontier_cinderfen_fern_wood_sedge']['lods'].append({'level':lod,'objects':[m.record() for m in plants(lod)]})
    result={'schemaVersion':1,'design':'source/design.json','designSha256':hashlib.sha256(DESIGN_PATH.read_bytes()).hexdigest(),'authoringUpAxis':'+Z','units':'metres','assets':assets}
    out=ROOT/'source/floor.json';out.write_text(json.dumps(result,separators=(',',':'))+'\n')
    for key,asset in assets.items():print(key,[(lod['level'],sum(sum(len(face)-2 for face in obj['faces']) for obj in lod['objects'])) for lod in asset['lods']])
if __name__=='__main__':main()
