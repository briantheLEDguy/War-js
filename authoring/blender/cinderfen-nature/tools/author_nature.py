"""Original botanical paths/blade outlines and basalt cleavage cages.

This writer retains expanded vertices, faces and corner UVs for every LOD.
Repeated organs grow from named attachment points; no primitive mesh operators
or imported tree/rock geometry participate in the source.
"""
import json, math, random, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def mul(a,b):return tuple(x*b for x in a)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def length(a):return math.sqrt(dot(a,a))
def unit(a):return mul(a,1/max(length(a),1e-9))
def mix(a,b,t):return add(mul(a,1-t),mul(b,t))
def rounded(v):return [round(x,7) for x in v]

# An asymmetric, ridged alder section; lobes remain visible at the root flare.
SECTION=[(1.02,.02),(.79,.64),(.16,1.04),(-.58,.79),(-1.03,.19),(-.83,-.53),(-.14,-.97),(.66,-.76)]
CULM_SECTION=[(.97,.08),(.40,.87),(-.51,.78),(-1.01,-.12),(-.42,-.91),(.56,-.73)]
# Along-stem profiles are art-directed rather than conical generated proxies.
ALDER_BLADE=[(0,.018),(.08,.27),(.19,.68),(.29,.81),(.40,.94),(.50,.92),(.61,1),(.72,.90),(.82,.73),(.91,.52),(1,.10)]
REED_BLADE=[(0,.06),(.10,.53),(.25,.93),(.42,1),(.60,.82),(.77,.56),(.90,.25),(1,.012)]
SEDGE_BLADE=[(0,.50),(.13,.84),(.29,1),(.48,.85),(.66,.60),(.81,.35),(.93,.14),(1,.008)]

TRUNK=[(-.08,.02,-.24,.83),(.04,-.06,.25,.65),(.17,.04,1.25,.48),(.11,.17,2.55,.40),(.32,.07,3.82,.32),(.08,.16,5.04,.255),(.27,.10,6.17,.20),(.47,.28,7.37,.139),(.24,.49,8.52,.08),(.51,.44,9.45,.035),(.70,.61,10.14,.008)]
LIMBS=[
 [[.15,.10,2.90,.22],[-.53,.13,3.52,.19],[-1.34,.12,4.08,.12],[-2.13,.37,4.60,.058],[-2.90,.30,5.34,.018]],
 [[.24,.09,3.77,.205],[.98,-.39,4.35,.158],[1.68,-.70,4.84,.098],[2.35,-.74,5.48,.050],[2.79,-1.07,6.30,.012]],
 [[.16,.12,4.42,.19],[-.36,1.04,4.95,.14],[-.72,1.82,5.57,.083],[-.95,2.48,6.40,.033],[-.68,2.85,7.21,.009]],
 [[.10,.16,5.03,.174],[-.72,-.51,5.79,.13],[-1.33,-.92,6.48,.080],[-1.92,-1.07,7.32,.032],[-2.24,-.97,8.03,.009]],
 [[.22,.12,5.68,.17],[.72,.79,6.15,.122],[1.48,1.38,6.89,.068],[2.06,1.65,7.75,.027],[2.20,1.88,8.42,.008]],
 [[.29,.13,6.31,.15],[.73,-.57,6.96,.102],[1.09,-1.20,7.74,.060],[1.48,-1.50,8.57,.026],[1.21,-1.66,9.17,.007]],
 [[.39,.24,6.96,.121],[-.15,.64,7.66,.092],[-.59,.93,8.42,.055],[-1.00,1.07,9.11,.018],[-1.15,.95,9.60,.006]],
 [[.43,.34,7.74,.097],[1.01,.41,8.41,.068],[1.46,.19,9.14,.029],[1.62,.38,9.71,.007]],
 [[.22,.47,8.45,.066],[-.29,.27,9.03,.044],[-.57,.13,9.73,.021],[-.42,-.02,10.35,.006]],
 [[.15,.13,2.00,.148],[-.21,-.56,2.34,.105],[-.78,-.93,2.69,.062],[-1.20,-1.07,2.83,.046]],
]
ROOT_PATHS=[[[0,0,.38,.31],[-.72,.12,.17,.24],[-1.34,.28,.02,.135],[-1.94,.49,-.12,.025]],[[.10,0,.32,.31],[.79,-.32,.13,.23],[1.41,-.75,-.03,.108],[1.81,-.89,-.16,.018]],[[0,.05,.38,.27],[.14,1.01,.16,.205],[.43,1.52,-.03,.086],[.63,1.92,-.16,.015]],[[.06,-.02,.32,.31],[-.32,-.78,.12,.22],[-.62,-1.43,-.02,.089],[-.95,-1.79,-.15,.017]],[[0,0,.28,.22],[.91,.72,.12,.15],[1.30,1.04,-.12,.015]]]

class Mesh:
    def __init__(self,name,material,smooth=True):self.name=name;self.material=material;self.vertices=[];self.faces=[];self.uv=[];self.smooth=smooth
    def vertex(self,p):self.vertices.append(rounded(p));return len(self.vertices)-1
    def face(self,indices,uv):self.faces.append(indices);self.uv.append([rounded(p) for p in uv])
    def record(self):return {'name':self.name,'material':self.material,'smooth':self.smooth,'vertices':self.vertices,'faces':self.faces,'corner_uv':self.uv}

def catmull(points,steps):
    out=[]
    for i in range(len(points)-1):
        a,b,c,d=points[max(0,i-1)],points[i],points[i+1],points[min(len(points)-1,i+2)]
        for j in range(steps):
            t=j/steps;out.append(tuple(.5*((2*b[k])+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in range(4)))
    out.append(tuple(points[-1]));return out

def sweep(mesh,control,lod,section=SECTION,uv_phase=0,flatten=1):
    """Follow original knots with parallel local frames and retained bark UVs."""
    path=catmull(control,[3,2,1][lod]);section=section if lod<2 else [section[i] for i in (0,2,4,6)] if len(section)==8 else [section[i] for i in (0,2,3,5)]
    rings=[];run=0
    for i,p in enumerate(path):
        centre=p[:3];tangent=unit(sub(path[min(i+1,len(path)-1)][:3],path[max(0,i-1)][:3]));basis=unit(cross((0,1,0),tangent));other=unit(cross(tangent,basis))
        if i:run+=length(sub(centre,path[i-1][:3]))
        radius=max(.0007,p[3]);rings.append(([],run))
        for x,y in section:rings[-1][0].append(mesh.vertex(add(centre,add(mul(basis,x*radius),mul(other,y*radius*flatten)))))
    side=len(section)
    for row in range(len(rings)-1):
        a,va=rings[row];b,vb=rings[row+1]
        for i in range(side):j=(i+1)%side;mesh.face([a[i],a[j],b[j],b[i]],[(uv_phase+i/side,va*.58),(uv_phase+(i+1)/side,va*.58),(uv_phase+(i+1)/side,vb*.58),(uv_phase+i/side,vb*.58)])
    # Caps are seated inside parent branches; isolated broken ends retain bark.
    for ring,reverse in [(rings[0][0],True),(rings[-1][0],False)]:
        indices=list(reversed(ring)) if reverse else ring;mesh.face(indices,[((section[ring.index(v)][0]+1)/2,(section[ring.index(v)][1]+1)/2) for v in indices])

def blade(mesh,base,direction,normal,blade_length,width,lod,kind='alder',phase=0,curl=.13):
    profile={'alder':ALDER_BLADE,'reed':REED_BLADE,'sedge':SEDGE_BLADE}[kind]
    if lod==1:profile=[profile[i] for i in range(0,len(profile)-1,2)]+[profile[-1]]
    if lod==2:profile=[profile[0],profile[len(profile)//3],profile[2*len(profile)//3],profile[-1]]
    axis=unit(direction);normal=unit(sub(normal,mul(axis,dot(axis,normal))));side=unit(cross(normal,axis));rings=[]
    if lod==2:
        # The distant organ remains a closed original outline with a raised
        # midrib, not a camera-facing card or a collapsed near mesh.
        outline=[(0,-.02),(.35,-.88),(.72,-.90),(1,.02),(.72,.90),(.35,.88)] if kind=='alder' else [(0,-.04),(.40,-1),(1,.008),(.40,1)]
        tile=phase%4 if kind=='alder' else 0
        def point(t,w,under):
            bend=(.025*t+.28*t*t*t) if kind=='sedge' else curl*math.sin(t*math.pi)-.26*t*t if kind=='reed' else curl*math.sin(t*math.pi)
            return add(base,add(mul(axis,t*blade_length),add(mul(side,w*width*.5),mul(normal,blade_length*bend+(-.0007 if under else .0007)))))
        def tex(t,w):return ((.5+w*.48+tile)/4 if kind=='alder' else .5+w*.48,t)
        top=[mesh.vertex(point(t,w,False)) for t,w in outline];bottom=[mesh.vertex(point(t,w,True)) for t,w in outline]
        middle_top=mesh.vertex(add(point(.47,0,False),mul(normal,width*.12)));middle_bottom=mesh.vertex(point(.47,0,True))
        for j in range(len(outline)):
            k=(j+1)%len(outline);uvj=tex(*outline[j]);uvk=tex(*outline[k]);uvc=tex(.47,0)
            mesh.face([top[j],top[k],middle_top],[uvj,uvk,uvc]);mesh.face([bottom[k],bottom[j],middle_bottom],[uvk,uvj,uvc])
            mesh.face([top[k],top[j],bottom[j],bottom[k]],[uvk,uvj,(uvj[0]+.0005,uvj[1]),(uvk[0]+.0005,uvk[1])])
        return
    for row,(t,w) in enumerate(profile):
        bend=(.025*t+.28*t*t*t) if kind=='sedge' else curl*math.sin(t*math.pi)-.26*t*t if kind=='reed' else curl*math.sin(t*math.pi)
        centre=add(base,add(mul(axis,t*blade_length),mul(normal,blade_length*bend)))
        ids=[]
        for underside in (False,True):
            for across in (-1,0,1):
                serration=1 if kind!='alder' or lod>0 else (1 if row%2 else .92)
                lateral=across*w*width*.5*serration
                fold=width*(.10 if kind=='alder' else .21)*(1-abs(across))*math.sin(t*math.pi)
                point=add(centre,add(mul(side,lateral),mul(normal,fold+(-.0007 if underside else .0007))))
                ids.append(mesh.vertex(point))
        rings.append((ids,t,w))
    tile=phase%4 if kind=='alder' else 0
    def uv(across,t,w):return ((.5+across*w*.48+tile)/4 if kind=='alder' else .5+across*w*.48,t)
    for row in range(len(rings)-1):
        a,t,w=rings[row];b,u,v=rings[row+1]
        for under in (0,3):
            for col in (0,1):
                face=[a[col+under],a[col+1+under],b[col+1+under],b[col+under]];coords=[uv(col-1,t,w),uv(col,t,w),uv(col,u,v),uv(col-1,u,v)]
                mesh.face(face if under==0 else list(reversed(face)),coords if under==0 else list(reversed(coords)))
        for col in (0,2):mesh.face([a[col],b[col],b[col+3],a[col+3]],[uv(col-1,t,w),uv(col-1,u,v),uv(col-1,u,v),uv(col-1,t,w)])
    for ids,t,w in (rings[0],rings[-1]):mesh.face([ids[0],ids[1],ids[2],ids[5],ids[4],ids[3]],[uv(-1,t,w),uv(0,t,w),uv(1,t,w),uv(1,t,w),uv(0,t,w),uv(-1,t,w)])

def tree(lod):
    bark=Mesh('root_flare_bole_and_authored_forks','alder_bark');leaves=Mesh('rounded_alternate_bronze_leaves','alder_leaf');cones=Mesh('retained_woody_alder_cones','seed_scales')
    sweep(bark,TRUNK,lod)
    for i,path in enumerate(ROOT_PATHS+LIMBS):sweep(bark,path,lod,uv_phase=i*.173)
    for branch,path in enumerate(LIMBS[:8]):
        # One crown sector is almost bare from steam exposure; living lower
        # shoots persist elsewhere. Each twig starts inside its parent limb.
        for j in range(1,5):
            a=path[min(j,len(path)-2)];b=path[min(j+1,len(path)-1)];base=mix(a[:3],b[:3],.23);sign=-1 if j%2 else 1
            radial=unit((base[0]+.3,base[1]-.2,.4));side=mul(unit(cross(radial,(0,0,1))),sign)
            tangent=unit(add(mul(side,.86),add(mul(radial,.24),(0,0,.47))))
            reach=.78+.14*((branch+j)%3)
            points=[(*base,.035),(*add(base,mul(tangent,reach*.39)),.026),(*add(add(base,mul(tangent,reach*.78)),(0,0,.10)),.014),(*add(add(base,mul(tangent,reach)),(0,0,.23)),.0035)]
            sweep(bark,points,lod,uv_phase=(branch+j)*.137)
            for twig in range(3):
                origin=mix(points[1][:3],points[2][:3],(twig+1)/4);out=unit(add(mul(side,-1 if twig%2 else 1),add(mul(radial,.2),(0,0,.30))))
                end=add(origin,mul(out,.38+twig*.06));small=[(*origin,.009),(*mix(origin,end,.6),.006),(*add(end,(0,0,.06)),.0016)]
                sweep(bark,small,min(2,lod+1),uv_phase=.21*twig)
                if branch in (5,6) and j>=3:continue
                for organ in range(7):
                    if lod==1 and organ not in (0,2,4,6):continue
                    if lod==2 and organ!=4:continue
                    t=(organ+1)/8;petiole=mix(origin,end,t);flip=1 if organ%2 else -1
                    phase=branch*13+j*7+twig*5+organ
                    d=unit(add(mul(side,flip*(.54+.29*math.sin(phase*1.37))),add(mul(radial,.34+.24*math.cos(phase*1.11)),(.12*math.sin(phase),.09*math.cos(phase),.24*math.sin(phase*.81)))))
                    tilt=(math.sin(phase*1.81)*.91,math.cos(phase*1.17)*.83,.42+.46*math.sin(phase*.39))
                    size=.18+((branch*7+j*5+twig*3+organ)%7)*.017
                    attach=add(petiole,mul(d,.035));blade(leaves,attach,d,tilt,size,size*.83,lod,phase=branch+j+organ,curl=.08+.03*(organ%3))
                    if lod==0:sweep(bark,[(*petiole,.0019),(*attach,.0012)],2,uv_phase=.7)
                if lod<2 and (branch+j+twig)%3==0:
                    pos=add(end,(0,0,-.065));sweep(cones,[(*add(pos,(0,0,-.026)),.008),(*pos,.025),(*add(pos,(0,0,.035)),.028),(*add(pos,(0,0,.071)),.009)],lod,uv_phase=.2*j)
    # Bark scars sit on the broken low branch and hollowed upper stub; no cone
    # or sphere ornament substitutes for woody organs.
    return [bark,leaves,cones]

REED_BASES=[(-.84,-.45,2.62,.18),(-.39,-.72,2.80,-.3),(.05,-.61,2.99,.1),(.48,-.73,2.44,.48),(.90,-.25,2.73,.81),(-.70,.04,2.84,1.2),(-.21,-.11,3.16,.7),(.30,-.06,2.92,-.1),(.67,.22,3.04,1.8),(-.88,.52,2.31,2.1),(-.45,.58,2.98,2.5),(.06,.57,2.71,2.9),(.47,.69,2.49,3.4),(-.20,1.02,2.35,3.6),(.88,.64,2.10,1.1),(-1.05,-.09,1.81,2.8),(-.61,-1.02,1.73,.7),(.32,-1.06,1.87,1.4),(.97,-.82,1.58,2.4),(-1.18,.73,1.94,3.1),(.18,.18,2.26,4.4),(.56,-.37,2.14,4.1),(-.18,.29,2.12,4.7)]
def reeds(lod):
    stems=Mesh('jointed_reed_culms_and_panicle_branches','reed_stem');foliage=Mesh('drooping_lanceolate_reed_leaves','reed_leaf');seed=Mesh('open_branched_rust_panicles','seed_scales')
    for i,(x,y,h,angle) in enumerate(REED_BASES):
        if lod==2 and i%3==2:continue
        drift=(.12*math.cos(angle),.12*math.sin(angle),0)
        knots=[(x,y,-.035,.017),(x+.035,y-.025,h*.25,.016),(x+drift[0]*.4,y+drift[1]*.4,h*.52,.014),(x+drift[0],y+drift[1],h*.80,.009),(x+drift[0]*1.5,y+drift[1]*1.5,h,.0035)]
        sweep(stems,knots,lod,CULM_SECTION,uv_phase=.083*i)
        for j in range(6):
            if lod==2 and j%2:continue
            t=.18+j*.112;p=(x+drift[0]*t,y+drift[1]*t,h*t);a=angle+j*2.43
            d=(math.cos(a),math.sin(a),.23);n=(0,0,1)
            blade(foliage,p,d,n,.51+.12*((i+j)%4),.078+.012*(i%3),lod,'reed',curl=.18)
            if lod==0:
                sweep(stems,[(*add(p,(0,0,-.028)),.018),(*add(p,(0,0,-.004)),.020),(*add(p,(0,0,.019)),.017)],2,CULM_SECTION,uv_phase=.29*j)
        tip=knots[-1][:3];spine=add(tip,(-.055,.03,.43))
        if i<15:
            sweep(seed,[(*tip,.0055),(*mix(tip,spine,.6),.004),(*spine,.0011)],lod,CULM_SECTION,uv_phase=.71)
            for tier in range(6 if lod<2 else 4):
                t=.07+tier*(.13 if lod<2 else .21);centre=mix(tip,spine,t)
                for ray in range(5 if lod==0 else 3):
                    a=i*.61+ray*2.399+tier*.72;radius=(.19*(1-t)+.015)*(1+.14*math.sin(i+ray))
                    end=add(centre,(radius*math.cos(a),radius*math.sin(a),.10+.045*t));mid=mix(centre,end,.52)
                    sweep(seed,[(*centre,.0036),(*add(mid,(0,0,.018)),.0025),(*end,.0009)],2,CULM_SECTION,uv_phase=.11*tier)
                    for kernel in range(3 if lod==0 else 1):
                        base=mix(mid,end,.2+kernel*.30);direction=(math.cos(a+.4),math.sin(a+.4),.8)
                        blade(seed,base,direction,(0,0,1),.065,.020 if lod<2 else .027,min(2,lod+1),'reed',curl=.04)
    # Fallen curled blades interrupt the perfect colony outline at its base.
    for i in range(10 if lod==0 else 5):
        a=.81*i;blade(foliage,(-.9+i*.18,.72*math.sin(i),.025),(math.cos(a),math.sin(a),.02),(0,0,1),.71,.035,lod,'reed',curl=.015)
    return [stems,foliage,seed]

TUFTS=[(-.78,-.35,.78),(-.35,-.65,.96),(.21,-.55,.75),(.63,-.17,1.05),(.04,.07,1.13),(-.52,.40,.86),(.45,.58,.87),(-.94,.60,.55),(.97,.49,.61)]
def groundcover(lod):
    sedge=Mesh('folded_rust_sedge_blades','sedge_leaf');jointed=Mesh('segmented_marsh_horsetail_and_whorls','horsetail');seed=Mesh('small_sedge_terminal_heads','seed_scales')
    for tuft,(x,y,h) in enumerate(TUFTS):
        for j in range(17):
            if lod==1 and j%3==1:continue
            if lod==2 and j%3!=0:continue
            a=j*2.399+tuft*.57;reach=.70+.17*math.sin(j*1.79);lean=.28+.32*((j%5)/4)
            d=(math.cos(a)*lean,math.sin(a)*lean,1);base=(x+math.cos(a)*.033,y+math.sin(a)*.033,-.025)
            blade(sedge,base,d,(math.cos(a),math.sin(a),-.3),h*reach,.027+.009*(j%3),lod,'sedge',curl=.19)
        tip=(x+.08,y-.04,h*.82);sweep(seed,[(x,y,0,.0035),(*mix((x,y,0),tip,.7),.0028),(*tip,.0018)],2,CULM_SECTION)
        for k in range(3):
            p=add(tip,(.012*k,0,-.03*k));blade(seed,p,(.15,0,1),(0,1,0),.09,.025,2,'reed',curl=.025)
    for i in range(15):
        if lod==2 and i%2:continue
        a=i*2.399;x=.87*math.cos(a)+.12;y=.71*math.sin(a)-.12;h=.36+.035*(i%5)
        path=[(x,y,-.035,.012),(x+.009,y,h*.3,.012),(x+.027,y+.007,h*.68,.010),(x+.044,y+.008,h,.004)]
        sweep(jointed,path,lod,CULM_SECTION,uv_phase=.03*i)
        for tier in range(1,7 if lod<2 else 5):
            t=tier/(7 if lod<2 else 5.5);p=(x+.044*t,y+.008*t,h*t)
            for ray in range(6 if lod==0 else 4):
                a=ray*math.pi/3+i*.4+tier*.2;reach=.13*(1-t)+.034
                tip=add(p,(math.cos(a)*reach,math.sin(a)*reach,.045))
                sweep(jointed,[(*p,.0025),(*mix(p,tip,.65),.0018),(*tip,.0007)],2,CULM_SECTION,uv_phase=.3)
            if lod==0:sweep(jointed,[(*add(p,(0,0,-.010)),.0135),(*p,.014),(*add(p,(0,0,.008)),.012)],2,CULM_SECTION,uv_phase=.4)
    return [sedge,jointed,seed]

# Four irregular cooling-fracture masses are drawn as independent horizontal
# surveys. Their unequal ridges, clefts and submerged toes are intentional.
ROCK_CAGES=[
 {'name':'west_lifted_cleft','rings':[
 [(-2.49,-.90,-.22),(-1.86,-1.43,-.20),(-.77,-1.26,-.19),(-.42,-.62,-.20),(-.57,.26,-.21),(-1.15,.96,-.23),(-2.06,.87,-.21),(-2.63,.12,-.20)],
 [(-2.42,-.91,.40),(-1.87,-1.37,.59),(-.82,-1.21,.79),(-.39,-.59,.91),(-.63,.32,1.02),(-1.19,1.00,.85),(-2.06,.76,.47),(-2.50,.06,.32)],
 [(-2.20,-.83,1.19),(-1.81,-1.20,1.49),(-.92,-1.08,1.84),(-.60,-.52,2.12),(-.81,.32,2.24),(-1.31,.78,2.12),(-2.04,.63,1.64),(-2.24,.04,1.31)],
 [(-1.88,-.64,1.65),(-1.60,-.94,1.97),(-1.10,-.84,2.34),(-.84,-.40,2.52),(-1.00,.27,2.64),(-1.36,.48,2.50),(-1.78,.38,2.07),(-1.93,-.05,1.81)]]},
 {'name':'east_offset_shear','rings':[
 [(-.53,-1.12,-.21),(.44,-1.35,-.22),(1.44,-1.14,-.24),(2.04,-.70,-.22),(2.25,.27,-.20),(1.55,1.09,-.21),(.50,1.23,-.22),(-.42,.64,-.23)],
 [(-.48,-1.09,.64),(.39,-1.32,.57),(1.35,-1.13,.39),(1.99,-.65,.28),(2.10,.20,.48),(1.55,1.04,.74),(.49,1.21,1.14),(-.36,.61,1.05)],
 [(-.40,-.94,1.35),(.32,-1.10,1.16),(1.23,-.94,.94),(1.81,-.54,.87),(1.90,.13,1.12),(1.40,.93,1.48),(.55,1.12,1.76),(-.26,.49,1.88)],
 [(-.32,-.78,1.65),(.27,-.92,1.48),(1.07,-.79,1.25),(1.54,-.48,1.18),(1.72,.12,1.39),(1.36,.72,1.70),(.49,.92,1.99),(-.18,.37,2.11)]]},
 {'name':'north_split_fin','rings':[
 [(-1.45,.89,-.23),(-.70,.50,-.20),(.12,.72,-.24),(.80,1.17,-.21),(.62,1.77,-.20),(-.03,2.06,-.23),(-.93,1.89,-.22),(-1.62,1.43,-.24)],
 [(-1.33,.95,.46),(-.65,.61,.79),(.10,.83,.96),(.65,1.20,.73),(.46,1.70,.56),(-.07,1.95,.50),(-.93,1.72,.37),(-1.45,1.38,.26)],
 [(-1.06,1.03,1.00),(-.54,.80,1.51),(.02,.96,1.69),(.38,1.23,1.23),(.27,1.56,1.07),(-.11,1.74,.90),(-.74,1.56,.71),(-1.16,1.29,.65)]]},
 {'name':'southern_talus_lip','rings':[
 [(-1.09,-1.80,-.20),(-.46,-2.01,-.22),(.40,-1.89,-.23),(1.00,-1.56,-.22),(.82,-1.06,-.21),(.06,-.87,-.20),(-.68,-1.05,-.21),(-1.19,-1.38,-.23)],
 [(-.95,-1.72,.14),(-.43,-1.87,.32),(.29,-1.75,.43),(.78,-1.51,.56),(.60,-1.12,.63),(.04,-1.03,.53),(-.59,-1.19,.41),(-1.01,-1.40,.21)]]},
]
def fracture_finish(mesh,lod):
    """Retained fracture/chip finishing on original rock surveys.

    Edge midpoints are shared across adjacent faces, keeping every shell closed.
    Localized spalls alter the surveyed mass; no replacement proxy is created.
    """
    triangles=[];coords=[]
    for face,uv in zip(mesh.faces,mesh.uv):
        a,b,c=[mesh.vertices[v] for v in face[:3]];n=cross(sub(b,a),sub(c,a));exclude=max(range(3),key=lambda k:abs(n[k]));axes=[k for k in range(3) if k!=exclude]
        uv=[rounded((mesh.vertices[v][axes[0]]*.57,mesh.vertices[v][axes[1]]*.57)) for v in face]
        for i in range(1,len(face)-1):triangles.append([face[0],face[i],face[i+1]]);coords.append([uv[0],uv[i],uv[i+1]])
    for iteration in range(2 if lod==0 else 1 if lod==1 else 0):
        cache={};new_faces=[];new_uv=[]
        for face,uv in zip(triangles,coords):
            mids=[];tex=[]
            for i in range(3):
                a,b=face[i],face[(i+1)%3];edge=tuple(sorted((a,b)))
                if edge not in cache:cache[edge]=mesh.vertex(mix(mesh.vertices[a],mesh.vertices[b],.5))
                mids.append(cache[edge]);tex.append(mix(uv[i],uv[(i+1)%3],.5))
            a,b,c=face;ab,bc,ca=mids;ua,ub,uc=uv;uab,ubc,uca=tex
            new_faces.extend([[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]);new_uv.extend([[ua,uab,uca],[uab,ub,ubc],[uca,ubc,uc],[uab,ubc,uca]])
        triangles,coords=new_faces,new_uv
    normals=[(0,0,0) for p in mesh.vertices]
    for face in triangles:
        a,b,c=[mesh.vertices[v] for v in face];n=cross(sub(b,a),sub(c,a))
        for v in face:normals[v]=add(normals[v],n)
    chips=[(-1.91,-1.13,1.2,.32,.075),(-1.05,-1.01,1.84,.25,.067),(-2.20,-.70,.73,.31,.052),(.51,-1.04,1.33,.36,.081),(1.49,-.74,1.1,.28,.067),(1.76,.12,.82,.24,.061),(-.72,1.35,1.28,.26,.072)]
    if lod<2:
        for index,(x,y,z) in enumerate(mesh.vertices):
            n=unit(normals[index]);wear=.016*math.sin(x*15.7+y*11.3+z*17.9)+.008*math.sin(x*29.9-y*23.1+z*31.3)
            for cx,cy,cz,radius,depth in chips:
                d=length((x-cx,y-cy,z-cz))/radius
                if d<1:wear-=depth*(1-d*d)**2
            if z<0:wear*=.2
            mesh.vertices[index]=rounded(add((x,y,z),mul(n,wear)))
    mesh.faces=triangles;mesh.uv=coords

def rock(lod):
    mass=Mesh('surveyed_irregular_basalt_cleavage_masses','basalt',True)
    for number,cage in enumerate(ROCK_CAGES):
        rows=cage['rings'];rings=[]
        for row in rows:rings.append([mass.vertex(p) for p in row])
        for row in range(len(rings)-1):
            for j in range(8):
                indices=[rings[row][j],rings[row][(j+1)%8],rings[row+1][(j+1)%8],rings[row+1][j]]
                coords=[(mass.vertices[v][0]*.46+number*.17,mass.vertices[v][2]*.46) for v in indices]
                # Each face has an authored offset cleavage intersection.
                centre=mul(tuple(sum(mass.vertices[v][k] for v in indices) for k in range(3)),.25)
                normal=unit(cross(sub(mass.vertices[indices[1]],mass.vertices[indices[0]]),sub(mass.vertices[indices[3]],mass.vertices[indices[0]])))
                centre=add(centre,mul(normal,[-.038,.022,-.019,.034,.011,-.026,.030,-.010][j]))
                if lod<2:
                    c=mass.vertex(centre);uv=(centre[0]*.46+number*.17,centre[2]*.46)
                    for k in range(4):mass.face([indices[k],indices[(k+1)%4],c],[coords[k],coords[(k+1)%4],uv])
                else:mass.face(indices,coords)
        for row,reverse in [(0,True),(-1,False)]:
            ids=list(reversed(rings[row])) if reverse else rings[row]
            centre=mul(tuple(sum(mass.vertices[v][k] for v in ids) for k in range(3)),1/len(ids));centre=add(centre,(0,0,.027 if not reverse else 0));c=mass.vertex(centre)
            for j in range(8):
                face=[ids[j],ids[(j+1)%8],c];mass.face(face,[(mass.vertices[v][0]*.5,mass.vertices[v][1]*.5) for v in face])
    fracture_finish(mass,lod)
    return [mass]

MATERIALS={
 'alder_bark':{'color':[71,70,61],'roughness':.87,'kind':'bark'},
 'alder_leaf':{'color':[102,100,48],'roughness':.77,'kind':'alder_leaf'},
 'reed_stem':{'color':[135,116,66],'roughness':.79,'kind':'stem'},
 'reed_leaf':{'color':[136,112,55],'roughness':.81,'kind':'reed_leaf'},
 'sedge_leaf':{'color':[121,88,47],'roughness':.84,'kind':'sedge_leaf'},
 'horsetail':{'color':[70,88,55],'roughness':.83,'kind':'horsetail'},
 'seed_scales':{'color':[102,76,51],'roughness':.90,'kind':'seed'},
 'basalt':{'color':[65,69,66],'roughness':.87,'kind':'rock'},
}
ASSETS={
 'frontier_cinderfen_marsh_alder':{'name':'Cinderfen steam-scarred marsh alder','builder':tree,'contract':{'kind':'tree','plantedDatum':0,'crownClearanceM':7.0,'colliders':[{'x':.10,'z':-.10,'width':1.06,'depth':1.06,'minY':0,'maxY':4.1}],'walkableSurfaces':[],'cameraSolid':True}},
 'frontier_cinderfen_reed_clump':{'name':'Cinderfen autumn reed colony','builder':reeds,'contract':{'kind':'foliage','plantedDatum':0,'colliders':[],'walkableSurfaces':[],'cameraSolid':False}},
 'frontier_cinderfen_sedge_horsetail':{'name':'Cinderfen rust sedge and marsh horsetail','builder':groundcover,'contract':{'kind':'foliage','plantedDatum':0,'colliders':[],'walkableSurfaces':[],'cameraSolid':False}},
 'frontier_cinderfen_basalt_outcrop':{'name':'Cinderfen fractured basalt outcrop','builder':rock,'contract':{'kind':'rock','plantedDatum':0,'colliders':[{'x':-1.42,'z':.13,'width':1.70,'depth':1.85,'minY':0,'maxY':2.42},{'x':.81,'z':-.02,'width':2.14,'depth':2.04,'minY':0,'maxY':1.75},{'x':-.39,'z':-1.34,'width':1.42,'depth':1.0,'minY':0,'maxY':1.18}],'walkableSurfaces':[],'cameraSolid':True}},
}
def main():
    source={'schemaVersion':1,'units':'metres','authoringUpAxis':'+Z','runtimeUpAxis':'+Y','frontAxis':'+Z','method':'original explicit botanical paths, section contours, thick blade topology and cooling-fracture surveys','materials':MATERIALS,'design':{'alderTrunk':TRUNK,'alderLimbs':LIMBS,'rootPaths':ROOT_PATHS,'alderSection':SECTION,'culmSection':CULM_SECTION,'bladeOutlines':{'alder':ALDER_BLADE,'reed':REED_BLADE,'sedge':SEDGE_BLADE},'reedBases':REED_BASES,'sedgeTufts':TUFTS,'rockCages':ROCK_CAGES},'assets':{}}
    for key,definition in ASSETS.items():
        record={k:v for k,v in definition.items() if k!='builder'};record['lods']=[]
        for lod in range(3):
            objects=[mesh.record() for mesh in definition['builder'](lod) if mesh.vertices];record['lods'].append({'level':lod,'objects':objects})
            print(key,lod,'vertices',sum(len(o['vertices']) for o in objects),'faces',sum(len(o['faces']) for o in objects),flush=True)
        source['assets'][key]=record
    target=ROOT/'source/nature.json';target.write_text(json.dumps(source,separators=(',',':'))+'\n')
    print('NATURE_SOURCE',hashlib.sha256(target.read_bytes()).hexdigest(),target.stat().st_size,flush=True)
if __name__=='__main__':main()
