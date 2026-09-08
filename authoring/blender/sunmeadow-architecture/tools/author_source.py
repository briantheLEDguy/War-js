"""Original Sunmeadow masonry, joinery and roof control cages.

All visible geometry starts with the literal shaped vertex records below.
Finite placements repeat finished construction pieces; no stock mesh factory,
boolean-cut primitive or tessellated box supplies any visible model.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS={}; ASSETS={}


def mesh(name,coordinates,faces,material,bevel=.01,description=''):
    vertices=[list(map(float,row.split())) for row in coordinates.strip().splitlines()]
    polygons=[list(map(int,row.split())) for row in faces.strip().splitlines()]
    uv=[]
    for face in polygons:
        n=[0.,0.,0.]
        for a,b in zip(face,face[1:]+face[:1]):
            p,q=vertices[a],vertices[b]
            for i in range(3):n[i]+=(p[(i+1)%3]-q[(i+1)%3])*(p[(i+2)%3]+q[(i+2)%3])
        axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(n[i]))]
        uv.append([[round(vertices[index][axes[0]],6),round(vertices[index][axes[1]],6)] for index in face])
    PARTS[name]={'vertices':vertices,'faces':polygons,'corner_uv':uv,'material':material,'bevel':bevel,'description':description,'source':'literal_authored_mesh'}


def skin(name,front,back,material,bevel=.01,description=''):
    """Stitch two specifically authored matching perimeter records."""
    a=front.strip().splitlines(); b=back.strip().splitlines(); count=len(a); assert count==len(b)
    faces=[' '.join(map(str,range(count-1,-1,-1))),' '.join(map(str,range(count,count*2)))]
    faces+=[' '.join(map(str,(i,(i+1)%count,(i+1)%count+count,i+count))) for i in range(count)]
    mesh(name,'\n'.join(a+b),'\n'.join(faces),material,bevel,description)


skin('coursed_ashlar','''
-.50 -.242 .035
-.465 -.259 .002
-.18 -.264 -.008
.29 -.253 .009
.478 -.242 .036
.502 -.245 .182
.492 -.250 .404
.455 -.251 .447
.16 -.266 .459
-.26 -.257 .450
-.483 -.240 .423
-.504 -.242 .223
''','''
-.50 .22 .035
-.465 .22 .002
-.18 .22 -.008
.29 .22 .009
.478 .22 .036
.502 .22 .182
.492 .22 .404
.455 .22 .447
.16 .22 .459
-.26 .22 .450
-.483 .22 .423
-.504 .22 .223
''','limestone',.012,'Hand-dressed limestone ashlar: irregular arris, swollen cleft face, fitted rear wythe and chipped corners.')

skin('quoin_stone','''
-.50 -.31 .025
-.475 -.335 0
.455 -.327 .012
.50 -.305 .046
.495 -.323 .444
.450 -.332 .482
-.452 -.329 .474
-.502 -.302 .430
''','''
-.50 .31 .025
-.475 .335 0
.455 .327 .012
.50 .305 .046
.495 .323 .444
.450 .332 .482
-.452 .329 .474
-.502 .302 .430
''','cut_stone',.012,'Through-bonded corner quoin with individually dressed shoulders and softened weather-exposed arrises.')

skin('mortar_bed','''
-.51 -.205 -.014
-.49 -.217 -.030
.49 -.212 -.025
.51 -.201 -.002
.493 -.208 .447
.48 -.211 .465
-.491 -.209 .460
-.51 -.205 .438
''','''
-.51 .205 -.014
-.49 .217 -.030
.49 .212 -.025
.51 .201 -.002
.493 .208 .447
.48 .211 .465
-.491 .209 .460
-.51 .205 .438
''','mortar',.001,'Recessed lime bedding fills the masonry joints behind dressed stone faces; never a visible mass proxy.')

skin('slate_course','''
-.30 -.43 .005
-.273 -.46 -.004
-.08 -.454 .008
.035 -.472 -.006
.244 -.455 .003
.29 -.417 .012
.285 .430 .034
.249 .455 .029
-.272 .449 .037
-.300 .401 .032
''','''
-.30 -.43 -.034
-.273 -.46 -.040
-.08 -.454 -.031
.035 -.472 -.044
.244 -.455 -.035
.29 -.417 -.029
.285 .430 -.009
.249 .455 -.011
-.272 .449 -.003
-.300 .401 -.008
''','slate',.004,'Split slate with irregular cleft lower edge, lifted head-lap and distinct thickness; laid in overlapping courses.')

skin('roof_ridge','''
-.34 -.41 -.08
-.26 -.41 .045
-.12 -.41 .182
0 -.41 .208
.13 -.41 .171
.28 -.41 .022
.34 -.41 -.083
.25 -.41 -.094
.10 -.41 .079
0 -.41 .105
-.10 -.41 .073
-.26 -.41 -.098
''','''
-.34 .41 -.08
-.26 .41 .045
-.12 .41 .182
0 .41 .208
.13 .41 .171
.28 .41 .022
.34 .41 -.083
.25 .41 -.094
.10 .41 .079
0 .41 .105
-.10 .41 .073
-.26 .41 -.098
''','slate',.008,'Saddle ridge cap with an open underside, shaped crown and doubled weather lap.')

skin('oak_joined_post','''
-.145 -.17 0
.144 -.17 0
.163 -.168 .20
.141 -.173 .84
.124 -.180 1.75
.146 -.17 2.64
.187 -.171 2.76
.185 -.17 3.04
.094 -.17 3.08
.092 -.17 3.22
-.091 -.17 3.22
-.095 -.17 3.08
-.187 -.17 3.04
-.187 -.17 2.75
-.155 -.171 2.66
-.143 -.179 1.42
-.163 -.17 .18
''','''
-.145 .17 0
.144 .17 0
.163 .168 .20
.141 .173 .84
.124 .180 1.75
.146 .17 2.64
.187 .171 2.76
.185 .17 3.04
.094 .17 3.08
.092 .17 3.22
-.091 .17 3.22
-.095 .17 3.08
-.187 .17 3.04
-.187 .17 2.75
-.155 .171 2.66
-.143 .179 1.42
-.163 .17 .18
''','oak',.009,'Adzed structural oak post with shouldered head, projecting tenon and uneven hewing along the full grain direction.')

skin('curved_brace','''
0 -.10 0
.15 -.10 .03
.42 -.10 .40
.77 -.10 .68
1.18 -.10 .84
1.49 -.10 .86
1.53 -.10 1.09
1.19 -.10 1.08
.74 -.10 .91
.33 -.10 .54
.06 -.10 .14
''','''
0 .10 0
.15 .10 .03
.42 .10 .40
.77 .10 .68
1.18 .10 .84
1.49 .10 .86
1.53 .10 1.09
1.19 .10 1.08
.74 .10 .91
.33 .10 .54
.06 .10 .14
''','oak',.009,'Crook-grown knee brace fitted between the post shoulder and wall plate; concave lower sweep retains the natural grain path.')

skin('ledged_plank','''
-.225 -.045 .024
-.197 -.057 0
.198 -.052 .012
.226 -.040 .040
.216 -.048 1.420
.199 -.052 1.474
-.194 -.052 1.462
-.226 -.043 1.423
''','''
-.225 .046 .024
-.197 .055 0
.198 .050 .012
.226 .043 .040
.216 .051 1.420
.199 .054 1.474
-.194 .051 1.462
-.226 .044 1.423
''','oak',.006,'Rebated door, shutter and loft-floor plank with chamfered heads, full board thickness and modeled edge irregularity.')

skin('forged_hinge','''
-.48 -.020 -.04
-.38 -.020 -.07
.22 -.022 -.050
.34 -.023 -.10
.42 -.024 -.078
.455 -.025 0
.42 -.024 .080
.34 -.023 .10
.22 -.021 .05
-.38 -.02 .070
-.48 -.020 .04
''','''
-.48 .012 -.04
-.38 .012 -.07
.22 .012 -.050
.34 .012 -.10
.42 .012 -.078
.455 .012 0
.42 .012 .080
.34 .012 .10
.22 .012 .05
-.38 .012 .070
-.48 .012 .04
''','iron',.003,'Forged butterfly strap hinge with swelled leaf, folded root and a hammered scalloped end.')

mesh('square_nail','''
-.029 -.012 -.023
.027 -.012 -.024
.030 -.012 .024
-.026 -.012 .025
-.018 -.034 -.014
.017 -.036 -.015
.018 -.038 .014
-.017 -.035 .015
''','''
0 1 2 3
0 4 5 1
1 5 6 2
2 6 7 3
3 7 4 0
4 7 6 5
''','iron',.002,'Individually forged square nail head with a skewed pyramidal crown and nonuniform hammered edges.')

skin('threshold','''
-.50 -.34 .024
-.46 -.38 0
.46 -.38 0
.50 -.33 .040
.493 -.335 .14
.453 -.357 .185
-.45 -.356 .178
-.50 -.338 .140
''','''
-.50 .34 .024
-.46 .38 0
.46 .38 0
.50 .33 .040
.493 .335 .14
.453 .357 .185
-.45 .356 .178
-.50 .338 .140
''','cut_stone',.014,'Worn threshold or coping slab with a rounded nosing and sloped rain-shedding top face.')

skin('plaster_infill','''
-.50 -.05 .025
-.478 -.051 0
.468 -.043 .008
.499 -.054 .037
.480 -.050 .993
.445 -.046 1.011
-.459 -.055 .989
-.503 -.045 .958
''','''
-.50 .055 .025
-.478 .056 0
.468 .055 .008
.499 .055 .037
.480 .055 .993
.445 .055 1.011
-.459 .055 .989
-.503 .055 .958
''','plaster',.003,'Lime-plaster infill panel fitted within timber framing, slightly concave and uneven at its hand-trowelled perimeter.')

skin('arch_spandrel','''
-1 -.22 0
-1 -.22 1.6
-.966 -.22 1.859
-.866 -.22 2.10
-.707 -.22 2.307
-.50 -.22 2.466
-.259 -.22 2.566
0 -.22 2.600
.259 -.22 2.566
.50 -.22 2.466
.707 -.22 2.307
.866 -.22 2.10
.966 -.22 1.859
1 -.22 1.6
1 -.22 0
1.4 -.22 0
1.4 -.22 3.12
-1.4 -.22 3.12
-1.4 -.22 0
''','''
-1 .22 0
-1 .22 1.6
-.966 .22 1.859
-.866 .22 2.10
-.707 .22 2.307
-.50 .22 2.466
-.259 .22 2.566
0 .22 2.600
.259 .22 2.566
.50 .22 2.466
.707 .22 2.307
.866 .22 2.10
.966 .22 1.859
1 .22 1.6
1 .22 0
1.4 .22 0
1.4 .22 3.12
-1.4 .22 3.12
-1.4 .22 0
''','limestone',.012,'Continuous authored barrel arch and spandrel. The opening is topology, not a painted door or primitive boolean; its jambs and soffit have full masonry thickness.')

skin('arch_voussoir','''
-.132 -.27 .995
.126 -.27 .995
.159 -.274 1.216
.139 -.273 1.244
-.142 -.272 1.248
-.160 -.267 1.222
''','''
-.132 .23 .995
.126 .23 .995
.159 .23 1.216
.139 .23 1.244
-.142 .23 1.248
-.160 .23 1.222
''','cut_stone',.009,'Tapered wedge voussoir with dressed radial beds, cleft visible face and a proud softened outer arris.')

skin('splayed_arrow_slit','''
-.48 -.22 0
-.045 -.22 0
-.045 -.22 1.40
.045 -.22 1.40
.045 -.22 0
.48 -.22 0
.48 -.22 1.82
-.48 -.22 1.82
''','''
-.48 .22 0
-.18 .22 0
-.18 .22 1.40
.18 .22 1.40
.18 .22 0
.48 .22 0
.48 .22 1.82
-.48 .22 1.82
''','cut_stone',.008,'Actual pierced arrow slit with a widened internal splay and a continuous dressed lintel.')

skin('sunburst_relief','''
0 -.040 .61
.11 -.045 .32
.34 -.044 .44
.29 -.046 .18
.54 -.047 .13
.31 -.050 -.025
.42 -.046 -.26
.17 -.047 -.22
.045 -.052 -.49
-.09 -.046 -.26
-.34 -.043 -.35
-.25 -.047 -.07
-.51 -.046 .04
-.29 -.045 .17
-.32 -.043 .41
-.10 -.043 .29
''','''
0 .012 .61
.11 .012 .32
.34 .012 .44
.29 .012 .18
.54 .012 .13
.31 .012 -.025
.42 .012 -.26
.17 .012 -.22
.045 .012 -.49
-.09 .012 -.26
-.34 .012 -.35
-.25 .012 -.07
-.51 .012 .04
-.29 .012 .17
-.32 .012 .41
-.10 .012 .29
''','brass',.01,'Original asymmetric rising-sun relief used as the Sunmeadow civic mark; hand-cut rays and a raised face.')

skin('cloth_pennant','''
-.42 -.01 0
-.19 -.07 -.02
.09 .045 .02
.42 0 .01
.40 -.03 -1.36
.20 -.075 -1.19
.015 -.015 -1.47
-.20 .04 -1.18
-.43 -.03 -1.33
''','''
-.42 .001 0
-.19 -.059 -.02
.09 .056 .02
.42 .011 .01
.40 -.019 -1.36
.20 -.064 -1.19
.015 -.004 -1.47
-.20 .051 -1.18
-.43 -.019 -1.33
''','green_cloth',.003,'Thick woven green civic pennant with a folded top and three tailored hanging points; original Sunmeadow colors.')


def asset(key,name,contract):
    ASSETS[key]={'name':name,'instances':[],'contract':contract}; return ASSETS[key]['instances']


def place(items,part,xyz=(0,0,0),scale=(1,1,1),rotation=(0,0,0),material=None,detail=0):
    row={'part':part,'location':list(xyz),'scale':list(scale),'rotation_degrees':list(rotation),'detail':detail}
    if material: row['material']=material
    items.append(row)


def course(items,left,right,y,z,height=.48,depth=1,rotation=0,alternate=0):
    if right-left<.06:return
    span=right-left; count=max(1,round(span/(1.08 if alternate%2 else .95)))
    width=span/count
    for index in range(count):
        x=left+(index+.5)*width
        xx,yy=(x,y) if rotation==0 else (y,-x)
        shade='limestone_foot' if z<.9 else 'limestone_warm' if (index+alternate*3)%7==0 else None
        place(items,'mortar_bed',(xx,yy,z),(width,.99*depth,height/.48),(0,0,rotation))
        place(items,'coursed_ashlar',(xx,yy,z),(width*.978,depth,height/.48),(0,0,rotation),shade)


def wall(items,left,right,y,height,depth=1,rotation=0,openings=()):
    rows=round(height/.48); step=height/rows
    for row in range(rows):
        z=row*step; spans=[(left,right)]
        for a,b,bottom,top in openings:
            if z<top-.015 and z+step>bottom+.015:
                next_spans=[]
                for lo,hi in spans:
                    if a>lo:next_spans.append((lo,min(hi,a)))
                    if b<hi:next_spans.append((max(lo,b),hi))
                spans=[segment for segment in next_spans if segment[1]>segment[0]]
        for lo,hi in spans: course(items,lo,hi,y,z,step,depth,rotation,row)


def frame(items,x,y,bottom,width,height,rotation=0,shutters=True):
    def at(dx,dz): return (x+dx,y,bottom+dz) if rotation==0 else (x,y-dx,bottom+dz)
    for dx in (-width/2-.15,width/2+.15):place(items,'oak_joined_post',at(dx,0),(.78,.8,height/3.22),(0,0,rotation))
    for dx in (-width/2-.15,width/2+.15):
        for dz in (.32,height-.26):place(items,'square_nail',at(dx,dz),(1.15,1.15,1.15),(0,0,rotation),detail=1)
    place(items,'threshold',at(0,-.12),(width+.55,.9,1),(0,0,rotation))
    place(items,'oak_joined_post',at(-width/2-.22,height+.1),(.82,.85,(width+.44)/3.22),(0,90,rotation))
    if shutters:
        for side in (-1,1):
            centre=side*(width/2+.25)
            for plank in range(2): place(items,'ledged_plank',at(centre+(plank-.5)*.25,0),(.60,.9,height/1.47),(0,0,rotation))
            for dz in (.18,height-.22):place(items,'forged_hinge',at(centre,dz),(.55,1,1),(0,0,rotation),detail=1)


def roof(items,width,depth,eave,rise):
    import math
    pitch=math.atan2(rise,width/2); length=math.hypot(width/2,rise)
    rows=max(2,round(length/.48)); cols=max(2,round(depth/.56))
    for side in (-1,1):
        for row in range(rows):
            distance=(row+.32)*length/rows
            x=side*(width/2-distance*math.cos(pitch)); z=eave+distance*math.sin(pitch)
            for col in range(cols):
                y=-depth/2+(col+.5)*depth/cols+(row%2)*.035
                place(items,'slate_course',(x,y,z),(.96,1,1),(side*math.degrees(pitch),0,90),'slate_light' if (row*5+col)%11==0 else None,detail=0)
        for end in (-1,1):
            # Fitted bargeboard under the slate verge, with a shouldered ridge joint.
            place(items,'oak_joined_post',(side*width/2,end*(depth/2-.15),eave-.10),(.9,.8,length/3.22),(0,-side*(90-math.degrees(pitch)),0))
    for index in range(max(1,round(depth/.76))):place(items,'roof_ridge',(0,-depth/2+(index+.5)*.76,eave+rise+.10))


def shell(items,width,depth,height,door=1.6,window=True,door_height=2.62):
    openings=[(-door/2,door/2,0,door_height)]
    if window:openings += [(-width*.36,-width*.36+1.05,1.32,2.76),(width*.36-1.05,width*.36,1.32,2.76)]
    wall(items,-width/2,width/2,-depth/2,height,openings=openings)
    wall(items,-width/2,width/2,depth/2,height)
    for side in (-1,1):wall(items,-depth/2,depth/2,side*width/2,height,rotation=90,openings=[(-.65,.65,1.32,2.76)])
    for side in (-1,1):
        for end in (-1,1):
            for row in range(round(height/.48)):
                place(items,'quoin_stone',(side*(width/2-.12),end*(depth/2-.03),row*.48),(.86,1.0,1),(0,0,90 if row%2 else 0))
    frame(items,0,-depth/2-.31,0,door,door_height,shutters=False)
    if window:
        for x in (-width*.36+.525,width*.36-.525):frame(items,x,-depth/2-.31,1.32,1.05,1.44)
    for side in (-1,1):frame(items,side*(width/2+.31),0,1.32,1.3,1.44,90)
    # The open leaf is fitted at the left jamb; opening clearance stays real.
    for i in range(4):place(items,'ledged_plank',(-door/2-.17,-depth/2+.17+i*door/4,.10),(door/4/.45*.98,1,(door_height-.16)/1.47),(0,0,90))
    for z in (.6,2.1):place(items,'forged_hinge',(-door/2-.22,-depth/2+.70,z),(door*.95,1,1),(0,0,90),detail=1)


def floor(items,width,depth,z):
    count=max(2,round(width/.41))
    for index in range(count):
        place(items,'ledged_plank',(-width/2+(index+.5)*width/count,depth/2,z),(width/count/.45,1,depth/1.47),(90,0,0))


def gables(items,width,depth,eave,rise):
    for end in (-1,1):
        rows=max(1,round(rise/.48))
        for row in range(rows):
            z=row*rise/rows; half=width/2*(1-(z+rise/rows*.52)/rise)
            course(items,-half,half,end*depth/2,eave+z,rise/rows,1,0,row)
        place(items,'sunburst_relief',(0,end*(depth/2+.27),eave+rise*.35),(.55,.8,.55),(0,0,0 if end<0 else 180),detail=1)


def chimney(items,x,y,height):
    start=len(items)
    for row in range(round(height/.48)):
        for side in (-1,1):
            course(items,x-.57,x+.57,y+side*.47,row*.48,.48,.8,0,row)
            course(items,-y-.27,-y+.27,x+side*.43,row*.48,.48,.8,90,row)
    for side in (-1,1):
        place(items,'threshold',(x+side*.45,y,height),(1.16,.52,1),(0,0,90))
        place(items,'threshold',(x,y+side*.45,height),(1.16,.52,1))
    for item in items[start:]:
        if item['location'][2]>height-1.0:item['material']='sooted_stone'


farm=asset('frontier_sunmeadow_farmhouse','Sunmeadow limestone farmhouse',{'footprint':[8,10],'nominal_roof_envelope':[9.4,11.4],'front_door_clearance':[1.6,2.5],'collision_walls':[[[-4,-5],[-.8,-5]],[ [.8,-5],[4,-5]],[[-4,5],[4,5]],[[-4,-5],[-4,5]],[[4,-5],[4,5]]],'wall_thickness':.5,'anchor':'ground centre','door_faces':'glTF +Z'})
shell(farm,8,10,3.84); floor(farm,7.4,9.4,.04); gables(farm,8,10,3.84,2.75); roof(farm,9.4,11.4,3.75,3.22)
chimney(farm,2.25,2.25,7.20)
for y in (-4.2,0,4.2):place(farm,'oak_joined_post',(-3.7,y,3.46),(.8,.8,7.4/3.22),(0,90,0))

work=asset('frontier_sunmeadow_workshop','Sunmeadow granary and workshop',{'footprint':[10,8],'nominal_roof_envelope':[11.4,9.4],'front_door_clearance':[2.6,3.0],'collision_walls':[[[-5,-4],[-1.3,-4]],[[1.3,-4],[5,-4]],[[-5,4],[5,4]],[[-5,-4],[-5,4]],[[5,-4],[5,4]]],'wall_thickness':.5,'anchor':'ground centre','door_faces':'glTF +Z'})
shell(work,10,8,3.36,door=2.6,window=False,door_height=3.12)
# Raise the workshop opening to its three-metre lintel contract.
work[:]=[i for i in work if not(i['part'] in ('coursed_ashlar','mortar_bed') and i['location'][1]==-4 and abs(i['location'][0])<1.3 and i['location'][2]<3.05)]
for end in (-1,1):
    for x in (-4.8,-2.4,0,2.4,4.8):place(work,'oak_joined_post',(x,end*4,3.34),(1,1,.65))
    for x in (-3.6,-1.2,1.2,3.6):place(work,'plaster_infill',(x,end*4,3.42),(2.08,1,1.95))
    for x in (-4.65,-2.25,.15,2.55):place(work,'curved_brace',(x,end*4-.03,4.24),(1.3,1,1))
for side in (-1,1):
    for y in (-2,0,2):place(work,'oak_joined_post',(side*5,y,3.34),(1,1,.65))
    for y in (-3,-1,1,3):place(work,'plaster_infill',(side*5,y,3.4),(1.7,1,1.95),(0,0,90))
floor(work,9.4,7.4,.04)
# Retain a ladder opening in the northwest corner of the grain loft.
loft=[];floor(loft,6.8,7.4,3.33)
for item in loft:item['location'][0]+=1.3
work.extend(loft);loft=[];floor(loft,2.6,5.5,3.33)
for item in loft:item['location'][0]-=3.4;item['location'][1]-=.95
work.extend(loft)
for x in (-4.4,-3.5):place(work,'oak_joined_post',(x,2.8,.08),(.34,.34,1.12))
for row in range(10):place(work,'ledged_plank',(-4.45,2.74,.31+row*.32),(.18,.9,.67),(0,90,0))
gables(work,10,8,5.40,2.28); roof(work,11.4,9.4,5.36,2.61)
for y in (-3,0,3):place(work,'oak_joined_post',(-4.7,y,3.25),(1.1,1.1,9.4/3.22),(0,90,0))
place(work,'sunburst_relief',(0,-4.21,4.37),(.68,1,.68),detail=1)
chimney(work,3.15,2,8.25)

post=asset('frontier_sunmeadow_supply_post','Sunmeadow wayside supply post',{'footprint':[8,5],'nominal_roof_envelope':[9.2,6.2],'front_bay_clearance':[5.6,3.1],'collision_walls':[[[-4,2.5],[4,2.5]],[[-4,-2.5],[-4,2.5]],[[4,-2.5],[4,2.5]]],'wall_thickness':.5,'anchor':'ground centre','door_faces':'glTF +Z'})
wall(post,-4,4,2.5,1.44)
for side in (-1,1):wall(post,-2.5,2.5,side*4,1.44,rotation=90)
for x in (-3.7,3.7):
    for y in (-2.25,2.25):place(post,'oak_joined_post',(x,y,0),(1.25,1.25,1.03))
for x in (-3.6,3.6):place(post,'curved_brace',(x,-2.26,2.05),(.43,1,1),(0,0,0 if x<0 else 180))
for y in (-2.25,2.25):place(post,'oak_joined_post',(-3.7,y,3.36),(1.15,1.15,7.4/3.22),(0,90,0))
roof(post,9.2,6.2,3.58,1.45); floor(post,7.3,4.3,.04)
for x in (-3.45,3.45):
    for y in (-1.0,1.0):place(post,'oak_joined_post',(x,y,0),(.8,.8,.32))
    for i in range(3):place(post,'ledged_plank',(x+(i-1)*.32,1.4,1.03),(.80,1,2.8/1.47),(90,0,0))
place(post,'cloth_pennant',(-3.66,-2.5,3.0),(.78,1,.95))
place(post,'sunburst_relief',(-3.66,-2.63,2.36),(.40,1,.40),detail=1)


def curtain(items,centre,width,depth=2.2,height=6.3,crest=8.3):
    for side in (-1,1):wall(items,centre-width/2,centre+width/2,side*(depth/2-.23),height)
    # The masonry wall walk is a real deck between its two stone wythes.
    for i in range(round(width/.95)):
        x=centre-width/2+(i+.5)*width/round(width/.95)
        place(items,'threshold',(x,0,height-.18),(width/round(width/.95),depth/.76,1))
    for side in (-1,1):
        # Parapet courses sit on the wall walk, with merlons preserving real embrasures.
        for row in range(2):course(items,centre-width/2,centre+width/2,side*(depth/2-.23),height+row*.48,.48,1,0,row)
        bays=max(2,round(width/2))
        for bay in range(bays):
            x=centre-width/2+(bay+.5)*width/bays
            for row in range(2):course(items,x-.47,x+.47,side*(depth/2-.23),height+.96+row*.48,.48,1,0,row)
            place(items,'threshold',(x,side*(depth/2-.23),crest-.12),(1.06,.88,.9))


wallkit=asset('frontier_sunmeadow_curtain_wall','Sunmeadow eight-metre curtain wall',{'footprint':[8,2.2],'nominal_height':8.3,'wall_walk_height':6.3,'fitted_end_planes':[-4,4],'collision_walls':[[[-4,0],[4,0]]],'wall_thickness':2.2,'anchor':'ground centre'})
curtain(wallkit,0,8)

gate=asset('frontier_sunmeadow_gatehouse','Sunmeadow six-metre passage gatehouse',{'footprint':[28,12],'nominal_height':12,'passage_clearance':[6,4.8],'passage_rectangle':[[-3,-6],[3,6]],'collision_walls':[[[-14,-5.4],[-3,-5.4]],[[3,-5.4],[14,-5.4]],[[-10,-5.4],[-10,5.4]],[[10,-5.4],[10,5.4]],[[-10,5.4],[-3,5.4]],[[3,5.4],[10,5.4]],[[-3.3,-5.4],[-3.3,5.4]],[[3.3,-5.4],[3.3,5.4]]],'wall_thickness':.6,'anchor':'ground centre','passage_faces':'glTF ±Z'})
place(gate,'arch_spandrel',(0,0,0),(3,12/.44,3))
for end in (-1,1):
    for angle in range(-90,91,15):place(gate,'arch_voussoir',(0,end*5.81,4.8),(3.05,1.2,3.05),(0,angle,0))
for side in (-1,1):
    centre=side*6.9; left=centre-3.1; right=centre+3.1
    for y in (-5.4,5.4):
        openings=[(centre-1.90,centre-.94,4.32,6.24),(centre+.94,centre+1.90,4.32,6.24)]
        wall(gate,left,right,y,9.12,1.3,openings=openings)
        for x in (centre-1.42,centre+1.42):place(gate,'splayed_arrow_slit',(x,y,4.32),(1,1.3,1.92/1.82),(0,0,0 if y<0 else 180))
    for x in (left,right):wall(gate,-5.4,5.4,x,9.12,1.3,90)
    for x in (left,right):
        for y in (-5.4,5.4):
            for row in range(19):place(gate,'quoin_stone',(x,y,row*.48),(1.16,1.14,1),(0,0,90 if row%2 else 0))
    for end in (-1,1):
        for x in (centre-1.6,centre+1.6):
            for row in range(3):course(gate,x-.50,x+.5,end*5.4,9.12+row*.48,.48,1.3,0,row)
            place(gate,'threshold',(x,end*5.4,10.52),(1.15,1.22,1))
    for x in (left,right):
        for y in (-3.6,0,3.6):
            for row in range(3):course(gate,y-.52,y+.52,x,9.12+row*.48,.48,1.3,90,row)
    floor_pieces=[];floor(floor_pieces,5.65,10.2,9.05)
    for piece in floor_pieces:piece['location'][0]+=centre
    gate.extend(floor_pieces)
    place(gate,'cloth_pennant',(centre,-5.77,8.28),(1.7,1,1.85))
    place(gate,'sunburst_relief',(centre,-5.91,7.13),(1.05,1,1.05))
# Tower sentry roofs are created separately to preserve exact placement records.
for side in (-1,1):
    pieces=[];roof(pieces,6.9,11.6,10.68,2.0)
    for piece in pieces:piece['location'][0]+=side*6.9
    gate.extend(pieces)
for side in (-1,1):
    wing=[];curtain(wing,side*12,4)
    for piece in wing:piece['location'][1]-=4.6
    gate.extend(wing)
place(gate,'sunburst_relief',(0,-6.12,9.05),(1.15,1,1.15))
for end in (-1,1):
    for side in (-1,1):
        for row in range(10):place(gate,'quoin_stone',(side*3.45,end*5.99,row*.48),(.88,.48,1))
    for row in range(2):course(gate,-4.2,4.2,end*5.68,9.36+row*.48,.48,1,0,row)
    for x in (-3.2,-1.1,1.1,3.2):
        for row in range(2):course(gate,x-.47,x+.47,end*5.68,10.32+row*.48,.48,1,0,row)
        place(gate,'threshold',(x,end*5.68,11.20),(1.06,.88,.9))
for x in (-3.6,-2.7,-1.8,-.9,0,.9,1.8,2.7,3.6):
    for y in (-5.1,-4.2,-3.3,-2.4,-1.5,-.6,.3,1.2,2.1,3.0,3.9,4.8):place(gate,'threshold',(x,y,9.27),(.92,1.20,.65))

skin('gate_leaf_plank','''
-.215 -.11 0
.214 -.109 0
.222 -.119 .14
.207 -.125 1.66
.218 -.121 3.54
.204 -.116 4.73
.183 -.111 4.80
-.184 -.113 4.80
-.209 -.115 4.75
-.221 -.121 3.21
-.207 -.123 1.08
-.222 -.116 .12
''','''
-.215 .11 0
.214 .109 0
.222 .119 .14
.207 .125 1.66
.218 .121 3.54
.204 .116 4.73
.183 .111 4.80
-.184 .113 4.80
-.209 .115 4.75
-.221 .121 3.21
-.207 .123 1.08
-.222 .116 .12
''','oak',.012,'Fortified gate stave with full 220mm thickness, shouldered head, weathered lower toe and subtle hand-hewn bow.')

skin('forged_pintle','''
-.086 -.086 0
.083 -.087 0
.086 -.083 .62
.13 -.118 .65
.119 -.113 .76
.077 -.079 .80
-.078 -.082 .80
-.123 -.118 .75
-.13 -.114 .65
-.085 -.085 .61
''','''
-.086 .086 0
.083 .087 0
.086 .083 .62
.13 .118 .65
.119 .113 .76
.077 .079 .80
-.078 .082 .80
-.123 .118 .75
-.13 .114 .65
-.085 .085 .61
''','iron',.025,'Forged hinge pintle with an upset head, chamfered bearing shoulder and irregular square driving end.')

leaves=asset('frontier_sunmeadow_gate_leaves','Sunmeadow paired fortified gate leaves',{'footprint':[6,.65],'nominal_height':4.8,'closed_width':6,'hinges_z_up':[[-3,0,0],[3,0,0]],'leaf_nodes':['gate_leaf_left','gate_leaf_right'],'clips':['gate_open','gate_close'],'swing_degrees':90,'anchor':'ground centre','door_faces':'glTF +Z','collision_policy':'dynamic closed rectangle; disable central blocker when opened'})
for side in (-1,1):
    start=len(leaves);centre=side*1.5
    for index in range(7):place(leaves,'gate_leaf_plank',(centre+(index-3)*.424,0,0),(.95,1,1))
    for x in (centre-1.29,centre+1.29):place(leaves,'oak_joined_post',(x,.26,.06),(.72,.58,4.65/3.22))
    for z in (.36,2.35,4.28):
        place(leaves,'oak_joined_post',(centre-1.43,.26,z),(.87,.7,2.86/3.22),(0,90,0))
        place(leaves,'forged_hinge',(centre,-.158,z),(2.80,2,1.38))
        for x in (centre-1.15,centre-.64,centre,centre+.64,centre+1.15):place(leaves,'square_nail',(x,-.22,z),(1.7,1.7,1.7))
    for z in (.68,2.66):place(leaves,'curved_brace',(centre-1.15,.3,z),(1.53,.65,1.34))
    for z in (.02,1.95,3.90):place(leaves,'forged_pintle',(side*2.965,0,z),(.88,.88,.9))
    for item in leaves[start:]:item['rigid_group']='gate_leaf_left' if side<0 else 'gate_leaf_right'


MATERIALS={
'limestone':{'color':[172,167,144],'kind':'stone','roughness':.84},
'limestone_warm':{'color':[180,163,130],'kind':'stone','roughness':.84},
'limestone_foot':{'color':[132,134,106],'kind':'stone','roughness':.94,'weather':'ground_splash'},
'sooted_stone':{'color':[135,128,113],'kind':'stone','roughness':.90,'weather':'soot'},
'cut_stone':{'color':[196,185,154],'kind':'stone','roughness':.76},
'mortar':{'color':[118,117,100],'kind':'lime','roughness':.94},
'slate':{'color':[55,67,70],'kind':'slate','roughness':.75},
'slate_light':{'color':[68,77,77],'kind':'slate','roughness':.79},
'oak':{'color':[95,64,36],'kind':'wood','roughness':.79},
'plaster':{'color':[195,189,155],'kind':'lime','roughness':.90},
'iron':{'color':[50,55,54],'kind':'metal','roughness':.52,'metallic':.82},
'brass':{'color':[146,104,46],'kind':'metal','roughness':.44,'metallic':.78},
'green_cloth':{'color':[42,75,48],'kind':'cloth','roughness':.94},
}


def boundary_lod(name,front,back):
    temporary='boundary.'+name
    skin(temporary,front,back,PARTS[name]['material'],0,'Manually retained outer boundary of the corresponding authored component for its distant LOD.')
    PARTS[name]['lod2']=PARTS.pop(temporary)


boundary_lod('coursed_ashlar','''
-.504 -.248 -.008
.502 -.245 .002
.492 -.250 .459
-.483 -.240 .450
''','''
-.504 .220 -.008
.502 .220 .002
.492 .220 .459
-.483 .220 .450
''')
boundary_lod('quoin_stone','''
-.502 -.315 0
.500 -.305 .012
.495 -.323 .482
-.502 -.302 .474
''','''
-.502 .315 0
.500 .305 .012
.495 .323 .482
-.502 .302 .474
''')
boundary_lod('slate_course','''
-.300 -.460 .005
.290 -.455 .003
.285 .455 .034
-.300 .449 .037
''','''
-.300 -.460 -.040
.290 -.455 -.035
.285 .455 -.011
-.300 .449 -.003
''')
boundary_lod('threshold','''
-.500 -.350 0
.500 -.350 0
.493 -.357 .185
-.500 -.356 .178
''','''
-.500 .350 0
.500 .350 0
.493 .357 .185
-.500 .356 .178
''')


if __name__=='__main__':
    source={'units':'metres','up_axis':'Z','front_axis':'-Y','provenance':'Original literal architecture cages and finite construction placements; no primitive mesh constructors.','parts':PARTS,'materials':MATERIALS,'assets':ASSETS}
    (ROOT/'source/architecture.json').write_text(json.dumps(source,indent=2)+'\n')
    print(f'Authored {len(PARTS)} control cages and {len(ASSETS)} architectural modules.')
