"""Fit an original pentagonal defense landing to the reviewed Cinderfen kit.

The existing hand-authored stone, staves and fixings are repeated as finished
construction pieces. The deck outline and corner layout are new literal data.
No stock solid constructors or changes to the seven companion source modules.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
source=json.loads((BASE/'source/architecture.json').read_text())
parts={name:copy.deepcopy(source['parts'][name]) for name in ('fen_basalt','fen_basalt_cleft','fen_basalt_shelf','fen_basalt_riven','fen_basalt_dressed','ash_mortar_bedding','alder_pile','fortified_stave','palisade_shield','scarf_tie','hinge_strap','driven_pin','swept_knee','fen_deck_plank')}
instances=[]

def place(part,x,z,y,scale=(1,1,1),yaw=0,material=None,detail=0,lods=None):
    entry={'part':part,'location':[x,-z,y],'scale':list(scale),'rotation_degrees':[0,0,-yaw],'detail':detail}
    if material:entry['material']=material
    if lods is not None:entry['lod_levels']=lods
    instances.append(entry)

def slab(name,outline,top,bottom,material,levels):
    """Paired fitted board perimeter; retain every corner and face explicitly."""
    n=len(outline);vertices=[[x,-z,y] for y in (bottom,top) for x,z in outline]
    faces=[list(range(n-1,-1,-1)),list(range(n,2*n))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
    corners=[]
    for face in faces:
        a,b,c=[vertices[index] for index in face[:3]]
        u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
        normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(normal[i]))]
        corners.append([[vertices[index][axis] for axis in axes] for index in face])
    parts[name]={'vertices':vertices,'faces':faces,'corner_uv':corners,'material':material,'bevel':.004,'protected':True,'source':'literal_authored_mesh','description':'Fitted pentagonal corner deck board with a beveled courtyard stair opening; closed underside and hand-shaped shoulders.'}
    place(name,0,0,0,lods=levels)

# Clockwise runtime X/Z outline. The southwest cut is the physical stair mouth.
outline=[[-2.4,-.7],[-.7,-2.4],[2.4,-2.4],[2.4,2.4],[-2.4,2.4]]
edges=list(zip(outline,outline[1:]+outline[:1]))
for edge,(a,b) in enumerate(edges):
    dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz);ux,uz=dx/length,dz/length
    angle=math.degrees(math.atan2(dz,dx))
    # Alternating joints stop just short of corners, with larger ashlar quoins.
    for row in range(7):
        pitch=length/math.ceil(length/.94)
        ends=[.018]+([pitch*.5+i*pitch for i in range(math.ceil(length/.94))] if row%2 else [i*pitch for i in range(1,math.ceil(length/.94))])+[length-.018]
        for number,(start,end) in enumerate(zip(ends,ends[1:])):
            t=(start+end)/2
            part=['fen_basalt','fen_basalt_cleft','fen_basalt_shelf','fen_basalt_riven','fen_basalt_dressed'][(number+row*3+edge)%5]
            scale=((end-start-.004)/1.03,1,(2.6/7)/.429)
            place(part,a[0]+ux*t,a[1]+uz*t,row*2.6/7,scale,angle,'mineral_basalt' if row<2 else 'dressed_basalt' if (number+row)%5==0 else 'basalt')
            place('ash_mortar_bedding',a[0]+ux*t,a[1]+uz*t,row*2.6/7,scale,angle,lods=[0,1])
    count=math.ceil(length/.68);pitch=length/count
    for i in range(count):
        t=(i+.5)*pitch
        place('fortified_stave',a[0]+ux*t,a[1]+uz*t,2.52,(pitch/.48,.72,3.65/4.8),angle)
        place('hinge_strap',a[0]+ux*t-uz*.14,a[1]+uz*t+ux*.14,3.02,(.45,1.1,1.1),angle,detail=1)
        place('driven_pin',a[0]+ux*t-uz*.17,a[1]+uz*t+ux*.17,3.02,yaw=angle,detail=1)
    for t in (.23,length-.23):place('alder_pile',a[0]+ux*t,a[1]+uz*t,2.35,(1.05,1.0,3.9/3.4))
    place('scarf_tie',(a[0]+b[0])/2,(a[1]+b[1])/2,5.99,(length/2.5,.85,1),angle)

# Board end fits follow x+z=-3.1 at the stair mouth. Short pointed fragments are
# avoided; the final course spans the remaining useful width as one closed piece.
for levels,pitch in [([0,1],.40),([2],.8)]:
    for row in range(round(4.8/pitch)):
        za=-2.4+row*pitch+.003;zb=za+pitch-.006
        xa=max(-2.4,-3.1-za);xb=max(-2.4,-3.1-zb)
        board=[[xa+.003,za],[2.395,za],[2.397,zb-.018],[2.378,zb],[xb+.003,zb]]
        if xb<=-2.397 and xa>-2.397:board.append([-2.397,-.703])
        slab(f'corner_deck_{len(levels)}_{row:02}',board,6.3,6.15,'worn_alder',levels)

# Full exterior parapets, with short returns beside the two open wall sockets.
rails=[([2.26,-2.16],[2.26,2.24]),([2.20,2.26],[-2.20,2.26]),([-2.26,2.08],[-2.26,1.20]),([1.20,-2.26],[2.08,-2.26])]
colliders=[]
for index,(a,b) in enumerate(rails):
    dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz);yaw=math.degrees(math.atan2(dz,dx));count=max(1,math.ceil(length/.78));pitch=length/count
    for i in range(count):
        t=(i+.5)/count
        place('palisade_shield',a[0]+dx*t,a[1]+dz*t,6.3,(pitch/.82,1,1.05),yaw)
    for t in (0,1):place('alder_pile',a[0]+dx*t,a[1]+dz*t,6.3,(.63,.63,1.18/3.4))
    place('scarf_tie',(a[0]+b[0])/2,(a[1]+b[1])/2,7.34,(length/2.5,.65,.6),yaw)
    colliders.append({'x':(a[0]+b[0])/2,'z':(a[1]+b[1])/2,'width':length+.1,'depth':.30,'rotY':-math.radians(yaw),'minY':6.3,'maxY':8.3})

# Rectangular support union remains entirely inside the actual pentagonal deck.
surfaces=[{'id':'corner_main','x':.82,'z':.82,'width':3.08,'depth':3.08,'fromY':6.3,'toY':6.3},
 {'id':'west_socket','x':-1.56,'z':.82,'width':1.68,'depth':3.08,'fromY':6.3,'toY':6.3},
 {'id':'south_socket','x':.82,'z':-1.56,'width':3.08,'depth':1.68,'fromY':6.3,'toY':6.3},
 {'id':'diagonal_stair_mouth','x':-1.30,'z':-1.30,'width':2.35,'depth':.70,'rotY':math.pi/4,'fromY':6.3,'toY':6.3}]
for s in surfaces:colliders.append({key:s[key] for key in ('x','z','width','depth','rotY') if key in s}|{'minY':0,'maxY':6.29})
# The switchback's lower entry sits beside its upper landing. Carry the actual
# landing into the courtyard so that entry clears both adjacent curtain bases.
start,end=-3.5,-1.55;length=(end-start)*2**.5;steps=9;step=length/steps
for row in range(steps):
    point=start+(row+.5)*(end-start)/steps
    place('fen_deck_plank',point,point,6.225,(2.35/1.004,(step-.005)/.498,1),-45)
for side in (-1,1):
    offset=side*1.12/2**.5
    for point in (start+.08,end-.08):
        place('alder_pile',point+offset,point-offset,0,(.64,.64,7.35/3.4))
        colliders.append({'x':point+offset,'z':point-offset,'width':.25,'depth':.25,'minY':0,'maxY':7.35})
    mid=(start+end)/2
    place('scarf_tie',mid+offset,mid-offset,7.27,(length/2.5,.65,.60),45)
    place('scarf_tie',mid+offset,mid-offset,6.01,(length/2.5,1,1.2),45)
    colliders.append({'x':mid+offset,'z':mid-offset,'width':length,'depth':.20,'rotY':-math.pi/4,'minY':6.3,'maxY':7.42})
gangway={'id':'courtyard_stair_landing','x':(start+end)/2,'z':(start+end)/2,'width':2.20,'depth':length+.03,'rotY':math.pi/4,'fromY':6.3,'toY':6.3}
surfaces.append(gangway);colliders.append({key:gangway[key] for key in ('x','z','width','depth','rotY')}|{'minY':6.15,'maxY':6.29})
contract={'footprint':[4.8,4.8],'floor_height':6.3,'anchor':'ground centre','walkway_sockets_runtime':[[-2.4,6.3,0],[0,6.3,-2.4]],'stair_socket_runtime':[-3.5,6.3,-3.5],'stair_socket_forward_runtime':[2**-.5,0,2**-.5],'walkableSurfaces':surfaces,'colliders':colliders,'assembly_note':'Two perpendicular wall ends join the west and south openings. The supported diagonal gangway carries the stair socket into the courtyard so the lower stair entry clears both curtain bases. Rotate the complete assembly for each keep corner. No visible rail crosses any socket.'}
record={'materials':source['materials'],'parts':parts,'assets':{'frontier_cinderfen_corner_access':{'name':'Cinderfen corner landing and courtyard stair access','contract':contract,'instances':instances}},'reused_authored_construction':{'path':'../source/architecture.json','sha256':hashlib.sha256((BASE/'source/architecture.json').read_bytes()).hexdigest(),'scope':'Original Cinderfen stone/stave/fixing cages and material fields, fitted into a new pentagonal corner assembly; no stock primitive construction. Visual acceptance is recorded separately.'}}
for folder in ('source','runtime','masters','review','textures/source'): (ROOT/folder).mkdir(parents=True,exist_ok=True)
(ROOT/'source/architecture.json').write_text(json.dumps(record,indent=2)+'\n')
for path in (BASE/'textures/source').glob('*.png'):shutil.copyfile(path,ROOT/'textures/source'/path.name)
shutil.copyfile(BASE/'textures/paint_records.json',ROOT/'textures/paint_records.json')
print(f'Authored corner with {len(parts)} retained cages and {len(instances)} fitted placements.')
