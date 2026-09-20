"""Retain original tool, joinery, rope and cut-stone cages as explicit meshes."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TAU=math.tau
BEAM=[(-.40,-.50),(.34,-.49),(.49,-.34),(.48,.32),(.35,.49),(-.33,.50),(-.49,.34),(-.48,-.32)]
PLANK=[(-.47,-.50),(.44,-.50),(.50,-.29),(.50,.25),(.43,.45),(.14,.50),(-.28,.48),(-.49,.31),(-.50,-.30)]
SHAFT=[(.50,.01),(.425,.265),(.245,.445),(-.02,.51),(-.27,.42),(-.455,.23),(-.50,-.015),(-.42,-.27),(-.235,-.455),(.025,-.50),(.27,-.415),(.45,-.23)]
STRAP=[(-.48,-.48),(.43,-.49),(.50,-.29),(.49,.32),(.43,.49),(-.44,.50),(-.50,.28),(-.49,-.29)]
MATERIALS=['oak','oak_end','working_oak','forged_iron','worked_steel','hemp','cut_stone']
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def mul(a,s):return tuple(x*s for x in a)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a):return math.sqrt(dot(a,a))
def unit(a):return mul(a,1/max(norm(a),1e-12))
def rnd(a):return[round(float(x),7) for x in a]
def catmull(points,steps):
    result=[]
    for i in range(len(points)-1):
        a,b,c,d=[points[max(0,min(k,len(points)-1))] for k in (i-1,i,i+1,i+2)]
        for j in range(steps):
            t=j/steps;result.append(tuple(.5*(2*b[k]+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in range(len(b))))
    return result+[tuple(points[-1])]

class Cage:
    def __init__(self,name,material,role='visible',bevel=0,smooth=False):
        self.name=name;self.material=material;self.role=role;self.bevel=bevel;self.smooth=smooth;self.vertices=[];self.faces=[];self.uv=[];self.materials=[];self.grain=[];self.cuts=[]
    def vertex(self,p,grain):self.vertices.append(rnd(p));self.grain.append(rnd(grain));return len(self.vertices)-1
    def face(self,ids,uv,material=None):self.faces.append(ids);self.uv.append([rnd(p) for p in uv]);self.materials.append(material or self.material)
    def record(self):return{'name':self.name,'material':self.material,'role':self.role,'bevelM':self.bevel,'smooth':self.smooth,'vertices':self.vertices,'faces':self.faces,'corner_uv':self.uv,'face_materials':self.materials,'grain_coordinates':self.grain,'cutters':self.cuts}

def loft(name,path,section=BEAM,material='oak',guide=(0,0,1),bevel=.003,smooth=False,cap_material=None):
    """Path points retain centre and two real section dimensions, in metres."""
    mesh=Cage(name,material,bevel=bevel,smooth=smooth);rings=[];run=0
    for row,p in enumerate(path):
        tangent=unit(sub(path[min(row+1,len(path)-1)][:3],path[max(0,row-1)][:3]))
        selected=guide if abs(dot(tangent,guide))<.94 else (0,1,0)
        side=unit(cross(selected,tangent));up=unit(cross(tangent,side))
        if row:run+=norm(sub(p[:3],path[row-1][:3]))
        rings.append([mesh.vertex(add(p[:3],add(mul(side,x*p[3]),mul(up,y*p[4]))),(x*p[3],y*p[4],run)) for x,y in section])
    n=len(section)
    for row in range(len(rings)-1):
        for j in range(n):
            k=(j+1)%n;ids=[rings[row][j],rings[row][k],rings[row+1][k],rings[row+1][j]]
            mesh.face(ids,[(j/n,mesh.grain[ids[0]][2]),((j+1)/n,mesh.grain[ids[1]][2]),((j+1)/n,mesh.grain[ids[2]][2]),(j/n,mesh.grain[ids[3]][2])])
    end_material=cap_material or ('oak_end' if material in ('oak','working_oak') else material)
    mesh.face(list(reversed(rings[0])),list(reversed(section)),end_material);mesh.face(rings[-1],section,end_material)
    return mesh

def axis_path(a,b,width,height=None):return[(*a,width,height or width),(*b,width,height or width)]

def plate(name,outline,depth,axis='X',center=0,material='forged_iron',bevel=.003):
    mesh=Cage(name,material,bevel=bevel);rings=[]
    for offset in (-depth*.5,depth*.5):
        points=[(center+offset,a,b) if axis=='X' else (a,center+offset,b) if axis=='Y' else (a,b,center+offset) for a,b in outline]
        rings.append([mesh.vertex(p,(a,b,offset)) for p,(a,b) in zip(points,outline)])
    mesh.face(list(reversed(rings[0])),list(reversed(outline)));mesh.face(rings[1],outline)
    for j in range(len(outline)):
        k=(j+1)%len(outline);distance=norm(sub(outline[k],outline[j]));mesh.face([rings[0][j],rings[0][k],rings[1][k],rings[1][j]],[(0,0),(distance,0),(distance,depth),(0,depth)])
    return mesh

def pin(name,center,axis=(0,1,0),length=.18,diameter=.024,metal=False,lod=0):
    direction=unit(axis);a=add(center,mul(direction,-length*.5));b=add(center,mul(direction,length*.5));section=SHAFT if lod<2 else SHAFT[::2]
    return loft(name,axis_path(a,b,diameter),section,'forged_iron' if metal else 'oak_end',bevel=.001 if lod<2 else 0,smooth=True)

def screw_thread(name,center,length,radius,pitch,lod):
    samples=[12,7,4][lod];turns=length/pitch;path=[]
    for i in range(math.ceil(turns*samples)+1):
        t=min(turns,i/samples);angle=TAU*t
        path.append((center[0]+radius*math.cos(angle),center[1]+pitch*t,center[2]+radius*math.sin(angle),.007,.008))
    return loft(name,path,[(-.5,-.35),(.5,-.35),(.07,.65)],'worked_steel',bevel=0,smooth=False)

def rope(name,route,lod):
    path=catmull(route,[5,3,1][lod]);result=[];strands=3 if lod<2 else 1
    for strand in range(strands):
        ropepath=[];run=0
        for i,p in enumerate(path):
            if i:run+=norm(sub(p,path[i-1]))
            tangent=unit(sub(path[min(i+1,len(path)-1)],path[max(i-1,0)]));guide=(0,0,1) if abs(tangent[2])<.9 else(0,1,0);side=unit(cross(guide,tangent));normal=unit(cross(tangent,side));angle=run*TAU/.062+strand*TAU/3
            radius=.0048 if strands==3 else 0;point=add(p,add(mul(side,math.cos(angle)*radius),mul(normal,math.sin(angle)*radius)));width=.011 if strands==3 else .021
            ropepath.append((*point,width,width))
        result.append(loft(name+f'.strand{strand}',ropepath,SHAFT[::2] if lod else SHAFT,'hemp',bevel=0,smooth=True))
    return result

def bench(lod):
    parts=[];joints=[]
    def put(piece):parts.append(piece);return piece
    legs={}
    for sx in (-1,1):
        for sy in (-1,1):
            name=f'trestle_leg_{sx}_{sy}';leg=put(loft(name,[(sx*.977,sy*.303,0,.17,.155),(sx*.97,sy*.29,.055,.16,.15),(sx*.945,sy*.275,.46,.147,.145),(sx*.94,sy*.27,.842,.138,.145)],guide=(1,0,0),bevel=.005));legs[sx,sy]=leg
            for vertex in leg.vertices[:len(BEAM)]:vertex[2]=0
            for kind,z,w,h,direction in [('long',.465,.073,.069,(1,0,0)),('end',.245,.074,.070,(0,1,0))]:
                centre=(sx*.95,sy*.279,z);a=add(centre,mul(direction,-.16));b=add(centre,mul(direction,.16));cutter=put(loft(name+'.'+kind+'_mortise',axis_path(a,b,w,h),BEAM,'oak',bevel=0));cutter.role='cutter';leg.cuts.append(cutter.name)
            put(pin(name+'.drawbore_peg',(sx*.947,sy*.277,.465),(0,1,0),.17,.025,lod=lod))
            put(pin(name+'.end_rail_peg',(sx*.955,sy*.277,.245),(1,0,0),.17,.023,lod=lod))
    for sy in (-1,1):
        rail=put(loft(f'shouldered_long_stretcher_{sy}',[(-1.028,sy*.277,.465,.067,.063),(-.867,sy*.277,.465,.067,.063),(-.867,sy*.277,.465,.13,.14),(.867,sy*.277,.465,.13,.14),(.867,sy*.277,.465,.067,.063),(1.028,sy*.277,.465,.067,.063)],bevel=.003))
        joints.append({'part':rail.name,'receivers':[legs[-1,sy].name,legs[1,sy].name],'joint':'through tenons with drawbore pegs','axis':'X'})
    for sx in (-1,1):
        rail=put(loft(f'shouldered_end_stretcher_{sx}',[(sx*.95,-.362,.245,.068,.064),(sx*.95,-.205,.245,.068,.064),(sx*.95,-.205,.245,.13,.12),(sx*.95,.205,.245,.13,.12),(sx*.95,.205,.245,.068,.064),(sx*.95,.362,.245,.068,.064)],bevel=.003))
        joints.append({'part':rail.name,'receivers':[legs[sx,-1].name,legs[sx,1].name],'joint':'lower shouldered through tenons','axis':'Y'})
        put(loft(f'trestle_top_bearer_{sx}',[(sx*.94,-.398,.787,.19,.125),(sx*.94,-.36,.795,.21,.13),(sx*.94,.36,.795,.21,.13),(sx*.94,.398,.787,.19,.125)],bevel=.004))
        for sy in (-1,1):
            outline=[(sx*.94,.605),(sx*.94,.798),(sx*(.94-.30),.798),(sx*(.94-.22),.777),(sx*(.94-.15),.730),(sx*(.94-.08),.64)]
            if sx<0:outline.reverse()
            put(plate(f'shaped_trestle_knee_{sx}_{sy}',outline,.064,'Y',sy*.269,'oak',.004))
    for i,y in enumerate((-.304,-.102,.102,.304)):
        width=[.195,.197,.198,.195][i];put(loft(f'individual_worktop_plank_{i}',[(-1.16,y,.887,width,.102),(-1.12,y,.889,width,.105),(-.6,y+.001,.890,width,.107),(.15,y-.001,.891,width,.107),(.75,y+.001,.890,width,.104),(1.16,y,.887,width,.102)],PLANK,'working_oak',bevel=.002))
    for sx in (-1,1):
        put(loft(f'breadboard_end_{sx}',[(sx*1.22,-.408,.887,.12,.105),(sx*1.22,-.36,.890,.12,.108),(sx*1.22,.36,.890,.12,.108),(sx*1.22,.408,.887,.12,.105)],PLANK,'working_oak',bevel=.003))
        for y in (-.30,.1,.30):put(pin(f'breadboard_drawpin_{sx}_{y}',(sx*1.22,y,.89),(0,0,1),.112,.018,lod=lod))
    for sy in (-1,1):
        put(loft(f'pegged_upper_apron_{sy}',[(-1.03,sy*.32,.77,.078,.145),(-.95,sy*.34,.77,.085,.145),(.95,sy*.34,.77,.085,.145),(1.03,sy*.32,.77,.078,.145)],PLANK,bevel=.003))
    # Vise body has an actual shaped neck and receiving slide/screw openings.
    fixed_outline=[(-.48,.793),(-.32,.793),(-.275,.835),(-.275,.960),(-.30,1.019),(-.345,1.074),(-.445,1.074),(-.474,1.04),(-.46,.976),(-.46,.86)]
    fixed=put(plate('forged_vise_fixed_body',fixed_outline,.205,'X',-.74,bevel=.004))
    moving_outline=[(-.627,.865),(-.539,.868),(-.510,.953),(-.532,1.069),(-.638,1.069),(-.652,1.043),(-.627,.963)]
    moving=put(plate('forged_vise_moving_jaw',moving_outline,.208,'X',-.74,bevel=.004))
    for name,y in [('fixed',-.474),('moving',-.523)]:
        put(loft(f'worked_{name}_jaw_plate',axis_path((-.91,y,1.047),(-.57,y,1.047),.014,.073),PLANK,'worked_steel',bevel=.001))
        for x in (-.864,-.616):put(pin(f'{name}_jaw_retaining_rivet_{x}',(x,y,1.045),(0,1,0),.027,.019,True,lod))
    slide=put(loft('vise_fitted_lower_slide',axis_path((-.74,-.66,.89),(-.74,-.25,.89),.052,.062),BEAM,'worked_steel',bevel=.002))
    cutter=put(loft('vise_slide_socket',axis_path((-.74,-.71,.89),(-.74,-.22,.89),.055,.065),BEAM,'forged_iron',bevel=0));cutter.role='cutter';fixed.cuts.append(cutter.name)
    put(loft('vise_lead_screw_shank',axis_path((-.74,-.771,.971),(-.74,-.25,.971),.044),SHAFT if lod<2 else SHAFT[::2],'worked_steel',bevel=.001,smooth=True))
    screw_socket=put(loft('vise_threaded_receiving_socket',axis_path((-.74,-.69,.971),(-.74,-.20,.971),.047),SHAFT,'forged_iron',bevel=0));screw_socket.role='cutter';fixed.cuts.append(screw_socket.name);moving.cuts.append(screw_socket.name)
    if lod<2:put(screw_thread('lead_screw_visible_thread',(-.74,-.723,.971),.37,.024,.015,lod))
    hub=put(loft('vise_handle_cross_hub',[(-.74,-.802,.971,.073,.073),(-.74,-.782,.971,.086,.084),(-.74,-.735,.971,.078,.078)],SHAFT,'forged_iron',bevel=.002,smooth=True))
    hubsocket=put(loft('vise_handle_hub_socket',axis_path((-.74,-.774,.90),(-.74,-.774,1.04),.022),SHAFT,'forged_iron',bevel=0));hubsocket.role='cutter';hub.cuts.append(hubsocket.name)
    put(loft('sliding_vise_handle',[(-.74,-.774,.785,.037,.039),(-.74,-.774,.799,.026,.028),(-.74,-.774,.82,.019,.020),(-.74,-.774,1.118,.019,.020),(-.74,-.774,1.137,.027,.027),(-.74,-.774,1.149,.037,.038)],SHAFT if lod<2 else SHAFT[::2],'forged_iron',bevel=.001,smooth=True))
    strap=put(plate('bent_repair_strap_clamped_in_jaws',[(-.812,.995),(-.677,.995),(-.673,1.136),(-.625,1.202),(-.646,1.226),(-.698,1.193),(-.812,1.14)],.038,'Y',-.498,'forged_iron',.003))
    strap_hole=put(loft('repair_strap_pin_eye',axis_path((-.699,-.55,1.16),(-.699,-.45,1.16),.032),SHAFT,'forged_iron',bevel=0));strap_hole.role='cutter';strap.cuts.append(strap_hole.name)
    joints.extend([{'part':slide.name,'receivers':[fixed.name,moving.name],'joint':'fitted lower slide and screw through bored neck','axis':'Y'},{'part':'sliding_vise_handle','receivers':[hub.name],'joint':'sliding bar through bored cross hub','axis':'Z'}])
    for x in (-.816,-.664):put(pin('vise_mount_bolt_'+str(x),(x,-.317,.832),(0,0,1),.233,.024,True,lod))
    # Thick tool-rest is bored for the tapered handles/blades it actually holds.
    rack=put(loft('fitted_rear_tool_rest',[(x,.272,1.013,.175,.068) for x in (-.32,-.14,.04,.22,.40,.58,.76,.93)],PLANK,'oak',bevel=.003))
    for x in (-.25,.84):
        put(loft('tool_rest_support_'+str(x),axis_path((x,.279,.934),(x,.279,1.003),.082,.063),BEAM,bevel=.002))
        put(pin('tool_rest_mount_'+str(x),(x,.274,.977),(0,0,1),.09,.018,True,lod))
    hammerx=-.04;hammery=.273
    handle=put(loft('socketed_repair_hammer_handle',[(hammerx,hammery,.961,.043,.038),(hammerx,hammery,1.10,.038,.037),(hammerx+.014,hammery,1.28,.038,.045),(hammerx+.02,hammery,1.341,.044,.050)],SHAFT if lod<2 else SHAFT[::2],'oak',bevel=.001,smooth=True))
    head=put(loft('forged_repair_hammer_head',[(hammerx-.185,hammery,1.313,.071,.093),(hammerx-.166,hammery,1.313,.078,.105),(hammerx-.108,hammery,1.313,.063,.079),(hammerx-.028,hammery,1.313,.080,.077),(hammerx+.066,hammery,1.313,.08,.078),(hammerx+.126,hammery,1.313,.045,.064),(hammerx+.181,hammery,1.313,.022,.045)],BEAM,'forged_iron',bevel=.003))
    eye=put(loft('hammer_handle_eye',axis_path((hammerx+.016,hammery,1.245),(hammerx+.021,hammery,1.38),.046,.052),SHAFT,'oak',guide=(1,0,0),bevel=0));eye.role='cutter';head.cuts.append(eye.name)
    put(plate('hammer_handle_driven_wedge',[(hammerx+.005,1.312),(hammerx+.027,1.314),(hammerx+.033,1.354),(hammerx+.004,1.354)],.011,'Y',hammery,'worked_steel',.0008))
    for x,width in [(hammerx,.048),(.29,.029),(.61,.034)]:
        hole=put(loft('tool_rest_socket_'+str(x),axis_path((x,.273,.96),(x,.273,1.07),width),SHAFT,bevel=0));hole.role='cutter';rack.cuts.append(hole.name)
    for x,length,width in [(.29,.18,.030),(.61,.145,.036)]:
        put(loft('cold_chisel_blade_'+str(x),[(x,.273,.949,.030,.009),(x,.273,1.095,width,.012),(x,.273,1.123,.017,.018)],BEAM,'worked_steel',bevel=.001))
        grip=put(loft('chisel_turned_grip_'+str(x),[(x,.273,1.092,.025,.029),(x,.273,1.117,.042,.038),(x,.273,1.117+length*.45,.049,.048),(x,.273,1.117+length*.87,.043,.041),(x,.273,1.117+length,.031,.029)],SHAFT if lod<2 else SHAFT[::2],'oak',bevel=.001,smooth=True))
        put(loft('chisel_ferrule_'+str(x),axis_path((x,.273,1.090),(x,.273,1.119),.031),SHAFT,'forged_iron',bevel=.001,smooth=True))
    # Two drawn tong arms cross around an actual riveted pivot.
    for side in (-1,1):
        route=[(.39+side*.088,-.268,.956,.023,.018),(.55+side*.06,-.16,.958,.020,.018),(.72,-.068,.963+side*.008,.034,.024),(.84-side*.04,.008,.964,.025,.019),(.918-side*.055,.018,.965,.041,.021)]
        put(loft(f'forged_open_tong_arm_{side}',catmull(route,[3,2,1][lod]),STRAP,'forged_iron',bevel=.001,smooth=False))
    put(pin('tong_pivot_rivet',(.72,-.068,.969),(0,0,1),.064,.037,True,lod))
    contract={'kind':'siege_repair_station','plantedDatum':0,'worktopHeightM':.944,'front':'-Y source; +Z runtime','approachSource':{'minimum':[-.40,-1.48,0],'maximum':[1.05,-.49,1.9]},'colliders':[],'walkableSurfaces':[],'cameraSolid':True,'placement':'Leave at least 1.0 m open before the centre/right frontage; vise occupies the left corner.'}
    return parts,joints,contract

STONE_SURVEY=[
    (-.08,.05,-.95),(.3,-.20,-.86),(-.43,-.18,-.79),(-.2,.46,-.82),(.38,.48,-.74),(.64,.1,-.7),(-.67,.27,-.64),(-.30,-.63,-.65),(.24,-.74,-.55),(-.74,-.34,-.5),(.78,-.35,-.48),(.65,.65,-.40),(-.55,.72,-.43),(.15,.86,-.42),(-.86,.17,-.27),(-.15,-.96,-.1),(.6,-.76,-.12),(.96,-.11,-.18),(.90,.4,-.12),(.35,.92,-.04),(-.17,.97,-.14),(-.83,.54,-.08),(-.93,-.25,.03),(-.60,-.74,.11),(.27,-.92,.19),(.81,-.55,.21),(.96,.06,.2),(.70,.64,.26),(.10,.93,.25),(-.55,.78,.22),(-.91,.19,.29),(-.8,-.39,.39),(-.33,-.78,.46),(.25,-.76,.53),(.75,-.3,.54),(.75,.26,.61),(.3,.64,.7),(-.18,.73,.63),(-.60,.36,.64),(-.62,-.2,.7),(-.11,-.31,.91),(.26,.10,.9),(-.19,.26,.93)
]
# Separate dressing decisions alter silhouette and facet size on every load.
STONE_DRESSING=[
    {17:(-.12,.02,.06),25:(-.16,.06,-.04),40:(-.06,.09,-.07),5:(.06,.03,.08)},
    {20:(.04,-.12,.09),28:(-.02,-.14,.08),41:(-.10,-.03,-.05),9:(.09,-.03,.07)},
    {22:(.13,.06,.05),30:(.10,-.02,-.06),38:(.04,-.09,.08),33:(-.06,.02,-.09)},
    {15:(.07,.11,-.07),24:(-.04,.13,.02),34:(-.09,.02,.05),42:(.10,-.03,-.07)},
    {18:(-.11,-.02,-.04),27:(-.15,-.05,.09),36:(-.04,-.05,.05),7:(-.06,.04,.06)},
    {21:(.13,-.04,-.05),29:(.13,-.08,.04),39:(.04,.06,-.08),2:(.04,-.02,.08)},
    {16:(-.08,.12,.03),25:(-.09,.11,-.06),40:(.06,.07,-.10),12:(.04,-.03,.05)},
    {19:(.03,-.13,-.05),28:(.07,-.12,.01),41:(-.07,.02,-.08),31:(.07,.04,-.03)}
]

def convex_facets(points):
    """Triangulate a surveyed convex boundary; no generated sphere or lathe."""
    facets=[]
    for a in range(len(points)-2):
        for b in range(a+1,len(points)-1):
            for c in range(b+1,len(points)):
                normal=cross(sub(points[b],points[a]),sub(points[c],points[a]))
                if norm(normal)<1e-10:continue
                distances=[dot(normal,sub(p,points[a])) for i,p in enumerate(points) if i not in (a,b,c)]
                if max(distances)<1e-9:facets.append([a,b,c])
                elif min(distances)>-1e-9:facets.append([a,c,b])
    return facets

def cut_stone(name,center,scale,rotation,index,lod):
    mesh=Cage(name,'cut_stone',bevel=.013);c=math.cos(rotation);s=math.sin(rotation)
    survey=[add(p,STONE_DRESSING[index].get(i,(0,0,0))) for i,p in enumerate(STONE_SURVEY)]
    if lod==2:survey=[p for i,p in enumerate(survey) if i not in (2,5,7,9,11,13,18,21,24,27,30,33,35,37)]
    facets=convex_facets(survey);used=sorted(set(v for face in facets for v in face));mapping={old:new for new,old in enumerate(used)}
    for i in used:
        x,y,z=survey[i]
        p=(center[0]+(c*x-s*y)*scale[0],center[1]+(s*x+c*y)*scale[1],center[2]+z*scale[2]);mesh.vertex(p,(x*scale[0],y*scale[1],z*scale[2]))
    for face in facets:
        ids=[mapping[i] for i in face];points=[mesh.vertices[i] for i in ids];normal=cross(sub(points[1],points[0]),sub(points[2],points[0]));axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(normal[i]))]
        mesh.face(ids,[(mesh.grain[i][axes[0]],mesh.grain[i][axes[1]]) for i in ids])
    return mesh

def cradle(lod):
    parts=[];joints=[]
    def put(piece):parts.append(piece);return piece
    for x in (-.71,.71):
        put(loft('ammunition_sled_foot_'+str(x),[(x,-.681,.077,.18,.07),(x,-.60,.067,.215,.133),(x,-.42,.068,.22,.136),(x,.49,.068,.22,.136),(x,.64,.082,.19,.091),(x,.679,.107,.15,.04)],PLANK,bevel=.005))
    for i,y in enumerate((-.424,-.214,0,.214,.424)):
        put(loft('crib_floor_board_'+str(i),[(-.965,y,.185,.202,.09),(-.92,y,.188,.20,.092),(.93,y,.187,.20,.09),(.963,y,.182,.196,.082)],PLANK,'working_oak',bevel=.003))
    for sx in (-1,1):
        for sy in (-1,1):
            x=sx*.855;y=sy*.493;post=put(loft(f'crib_shouldered_corner_{sx}_{sy}',[(x,y,.135,.154,.15),(x,y,.18,.159,.153),(x+sx*.018,y+sy*.006,.49,.14,.137),(x+sx*.025,y+sy*.01,.72,.12,.12)],BEAM,guide=(1,0,0),bevel=.004))
            for z in ([.315,.575] if sy>0 else [.315]):
                mortise=put(loft(f'crib_rail_mortise_{sx}_{sy}_{z}',axis_path((x-.18,y,z),(x+.18,y,z),.063,.080),BEAM,bevel=0));mortise.role='cutter';post.cuts.append(mortise.name)
                put(pin(f'crib_drawpin_{sx}_{sy}_{z}',(x,y,z),(0,1,0),.16,.023,lod=lod))
            # Wide forged strap hugs the deck edge and carved post shoulder.
            route=[(x+sx*.027,y-sy*.08,.118,.056,.014),(x+sx*.079,y-sy*.04,.165,.059,.014),(x+sx*.087,y,.27,.055,.014),(x+sx*.079,y,.47,.052,.014),(x+sx*.069,y,.646,.043,.014)]
            put(loft(f'forged_cradle_retaining_strap_{sx}_{sy}',route,STRAP,'forged_iron',guide=(0,1,0),bevel=.0015))
            for z in (.268,.61):put(pin(f'cradle_strap_pin_{sx}_{sy}_{z}',(x+sx*.062,y,z),(1,0,0),.07,.025,True,lod))
            route=[(x-.095,y-.09,.49),(x+.096,y-.09,.513),(x+.105,y+.072,.526),(x-.094,y+.091,.51),(x-.105,y-.07,.489),(x+.098,y-.105,.473),(x+.114,y+.076,.491),(x-.093,y+.109,.473),(x-.112,y-.071,.452),(x-.085,y-.111,.48),(x-.012,y-.109,.543),(x+.040,y-.116,.505),(x-.065,y-.121,.453),(x-.112,y-.115,.388)]
            route=[(x+sx*.016+(px-x)*.72,y+sy*.005+(py-y)*.74,pz) for px,py,pz in route]
            parts.extend(rope(f'fitted_corner_binding_{sx}_{sy}',route,lod))
    for sy,z in [(-1,.315),(1,.315),(1,.575)]:
        rail=put(loft(f'shouldered_crib_long_retainer_{sy}_{z}',[(-.95,sy*.493,z,.058,.074),(-.78,sy*.493,z,.058,.074),(-.78,sy*.493,z,.102,.125),(.78,sy*.493,z,.102,.125),(.78,sy*.493,z,.058,.074),(.95,sy*.493,z,.058,.074)],PLANK,bevel=.003))
        joints.append({'part':rail.name,'receivers':[f'crib_shouldered_corner_{sx}_{sy}' for sx in (-1,1)],'joint':'drawbored rail tenons','axis':'X'})
    for sx in (-1,1):
        outline=[(-.53,.335),(-.53,.59),(-.44,.644),(-.28,.665),(.15,.662),(.43,.653),(.54,.601),(.54,.347),(.40,.339),(.37,.56),(-.35,.569),(-.395,.344)]
        put(plate('sculpted_open_crib_end_'+str(sx),outline,.076,'X',sx*.872,'oak',.003))
    placements=[(-.53,-.226,.462,.255,.229,.237,.17),(.00,-.232,.462,.251,.229,.241,.8),(.53,-.221,.462,.255,.223,.238,1.2),(-.535,.227,.462,.248,.227,.241,.42),(.01,.225,.462,.252,.224,.235,-.18),(.54,.228,.462,.247,.227,.241,.51),(-.274,.01,.87,.243,.221,.233,.63),(.273,.008,.87,.244,.217,.234,-.48)]
    for i,(x,y,z,sx,sy,sz,angle) in enumerate(placements):
        stone=put(cut_stone('individually_cut_siege_stone_'+str(i),(x,y,z),(sx,sy,sz),angle,i,lod));stone.bevel=.013 if lod==0 else .007 if lod==1 else 0
    contract={'kind':'siege_ammunition_storage','plantedDatum':0,'front':'-Y source; +Z runtime','approachSource':{'minimum':[-.71,-1.60,0],'maximum':[.71,-.71,1.9]},'colliders':[],'walkableSurfaces':[],'cameraSolid':True,'placement':'Low front rail faces the loading approach; preserve 1 m clear frontage. Stone loads are visual static supply.'}
    return parts,joints,contract

def main():
    assets={}
    for key,name,builder in [('frontier_siege_repair_bench','Frontier siege repair bench',bench),('frontier_siege_ammunition_cradle','Frontier siege ammunition cradle',cradle)]:
        asset={'name':name,'lods':[]}
        for lod in range(3):
            parts,joints,contract=builder(lod)
            if lod==2:
                for p in parts:p.bevel=0
            asset['contract']=contract;asset['joints']=joints;asset['lods'].append({'level':lod,'objects':[p.record() for p in parts]})
        assets[key]=asset
    source={'schemaVersion':1,'units':'metres','authoringUpAxis':'+Z','sourceFront':'-Y','materials':MATERIALS,'originalSections':{'dressedTimber':BEAM,'wornPlank':PLANK,'forgedShaft':SHAFT,'edgeFinishedStrap':STRAP},'originalStoneSurvey':STONE_SURVEY,'individualStoneDressing':STONE_DRESSING,'assets':assets}
    target=ROOT/'source/items.json';temporary=target.with_suffix('.json.tmp');temporary.write_text(json.dumps(source,separators=(',',':'))+'\n');temporary.replace(target)
    for key,a in assets.items():print(key,[(l['level'],len(l['objects']),sum(sum(len(f)-2 for f in o['faces']) for o in l['objects'] if o['role']=='visible')) for l in a['lods']],flush=True)
if __name__=='__main__':main()
