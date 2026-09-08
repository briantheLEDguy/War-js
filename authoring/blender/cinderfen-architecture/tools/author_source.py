"""Original Cinderfen construction cages and finite, inspectable placements.

No stock shapes or imported Sunmeadow geometry. Profiles are deliberately drawn
construction boundaries; thickness and curved/splayed sections remain editable.
"""
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS={};ASSETS={}


def mesh(name,vertices,faces,material,bevel=.008,description='',**extra):
    if isinstance(vertices,str):vertices=[list(map(float,row.split())) for row in vertices.strip().splitlines()]
    if isinstance(faces,str):faces=[list(map(int,row.split())) for row in faces.strip().splitlines()]
    uvs=[]
    for face in faces:
        n=[0.,0.,0.]
        for a,b in zip(face,face[1:]+face[:1]):
            p,q=vertices[a],vertices[b]
            for i in range(3):n[i]+=(p[(i+1)%3]-q[(i+1)%3])*(p[(i+2)%3]+q[(i+2)%3])
        axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(n[i]))]
        uvs.append([[round(vertices[index][axes[0]],6),round(vertices[index][axes[1]],6)] for index in face])
    PARTS[name]={'vertices':vertices,'faces':faces,'corner_uv':uvs,'material':material,'bevel':bevel,'description':description,'source':'literal_authored_mesh',**extra}


def skin(name,front,back,material,bevel=.008,description='',**extra):
    a=[list(map(float,row.split())) for row in front.strip().splitlines()];b=[list(map(float,row.split())) for row in back.strip().splitlines()];n=len(a);assert n==len(b)
    faces=[list(range(n-1,-1,-1)),list(range(n,n*2))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
    mesh(name,a+b,faces,material,bevel,description,**extra)


def profile(name,outline,front,back,material,bevel=.008,description='',plane='XZ',**extra):
    """Thicken a specific hand-authored section; no generic solid constructors."""
    points=[list(map(float,row.split())) for row in outline.strip().splitlines()]
    def record(depth):
        return '\n'.join(' '.join(map(str,(x,depth,z) if plane=='XZ' else (x,z,depth))) for x,z in points)
    skin(name,record(front),record(back),material,bevel,description,**extra)


skin('fen_basalt','''
-.51 -.25 .025
-.46 -.282 -.004
-.12 -.292 .012
.31 -.268 -.003
.49 -.249 .039
.512 -.262 .193
.469 -.254 .394
.341 -.275 .427
.04 -.287 .413
-.314 -.271 .438
-.493 -.247 .387
-.522 -.259 .149
''','''
-.49 .231 .022
-.445 .218 .006
-.12 .232 .009
.301 .217 .014
.479 .221 .038
.495 .223 .198
.455 .222 .388
.33 .229 .416
.04 .237 .414
-.307 .231 .424
-.481 .218 .379
-.497 .224 .152
''','basalt',.008,'Split marsh basalt with angular cleft shoulders, shallow mineral pockets and an irregular fitted bearing face.',reduce=.42)

# Fracture ridges cross the actual face rather than relying on a smooth cap and
# painted lines. The three interior vertices retain irregular cleaved planes.
basalt=PARTS['fen_basalt'];vertices=basalt['vertices']+[
 [-.28,-.313,.13],[.26,-.296,.20],[-.06,-.329,.31]]
front=[[24,0,1],[24,1,2],[24,2,3],[24,3,25],[25,3,4],[25,4,5],
 [25,5,6],[25,6,7],[25,7,26],[26,7,8],[26,8,9],[26,9,10],
 [26,10,11],[26,11,24],[24,11,0],[24,25,26]]
mesh('fen_basalt',vertices,front+basalt['faces'][1:],'basalt',.008,
 'Split basalt with three retained fracture ridges, uneven dressed shoulders and a closed bearing shell.',reduce=.48)

# Authored cleft alternatives break repeated fracture silhouettes within courses.
BASALT_VARIANTS=[
 ('cleft',[[-.34,-.293,.11],[.21,-.309,.24],[-.13,-.300,.33]],[(0,.010,.004),(4,-.012,.008),(7,-.010,-.008)]),
 ('shelf',[[-.19,-.297,.09],[.31,-.280,.18],[.01,-.302,.32]],[(1,.010,.006),(6,-.012,-.005),(10,.015,-.012)]),
 ('riven',[[-.32,-.307,.19],[.27,-.289,.13],[-.03,-.314,.34]],[(3,-.020,.012),(8,.018,-.009),(11,.009,.008)]),
 ('dressed',[[-.26,-.280,.13],[.22,-.283,.21],[-.02,-.287,.30]],[(0,.004,.003),(4,-.005,.004),(10,.007,-.006)]),
]
for variant,interior,shoulders in BASALT_VARIANTS:
    points=[list(v) for v in vertices[:24]]+[list(v) for v in interior]
    for index,dx,dz in shoulders:points[index][0]+=dx;points[index][2]+=dz
    mesh('fen_basalt_'+variant,points,front+basalt['faces'][1:],'basalt',.008,'Individually drawn '+variant+' basalt cleavage and fitted bearing shoulders.',reduce=.48)

profile('ash_mortar_bedding','''
-.522 .004
-.508 -.003
.509 -.001
.521 .013
.518 .428
.503 .438
-.510 .435
-.521 .421
''',-.218,.184,'ash_mortar',0,'Thin packed volcanic-ash bedding behind the dressed faces; a fitted perimeter fills exposed stone joints without changing the structural opening.',protected=True)

mesh('basalt_footing','''
-.48 -.36 .012
-.31 -.48 0
.26 -.45 .008
.49 -.28 .016
.47 .31 .005
.24 .46 .009
-.29 .44 .002
-.49 .24 .017
-.43 -.34 .19
-.28 -.43 .18
.25 -.42 .19
.44 -.25 .20
.42 .28 .18
.22 .41 .19
-.26 .40 .20
-.44 .22 .18
-.31 -.24 .59
-.19 -.31 .61
.18 -.30 .60
.32 -.18 .58
.30 .19 .61
.17 .31 .60
-.20 .29 .59
-.32 .17 .60
''',[list(range(7,-1,-1)),list(range(16,24))]+[[r+i,r+(i+1)%8,r+(i+1)%8+8,r+i+8] for r in (0,8) for i in range(8)],'mineral_basalt',.014,'Battered eight-faced basalt footing, broad uneven mud bearing and dressed alder socket crown.',protected=True)

mesh('alder_pile','''
-.18 -.12 0
-.09 -.20 .012
.10 -.18 .005
.20 -.075 0
.18 .13 .007
.08 .21 .011
-.12 .19 0
-.21 .07 .008
-.17 -.135 .38
-.073 -.185 .39
.12 -.16 .38
.204 -.06 .4
.177 .139 .39
.076 .188 .38
-.13 .16 .4
-.199 .047 .39
-.127 -.13 1.71
-.04 -.162 1.73
.12 -.136 1.72
.178 -.046 1.74
.154 .122 1.72
.053 .167 1.73
-.113 .146 1.74
-.162 .04 1.72
-.092 -.111 3.09
-.015 -.143 3.11
.12 -.123 3.10
.155 -.037 3.08
.132 .104 3.11
.039 .142 3.10
-.091 .121 3.09
-.136 .021 3.11
-.060 -.074 3.4
-.008 -.094 3.4
.078 -.083 3.4
.106 -.024 3.4
.089 .068 3.4
.026 .095 3.4
-.061 .081 3.4
-.090 .014 3.4
''',[list(range(7,-1,-1)),list(range(32,40))]+[[r+i,r+(i+1)%8,r+(i+1)%8+8,r+i+8] for r in (0,8,16,24) for i in range(8)],'tarred_alder',.008,'Hand-hewn alder pile with a subtle grown sweep, splayed lower bearing and reduced tenon at the crown.',protected=True)

profile('scarf_tie','''
-1.24 -.135
-1.15 -.177
-.91 -.170
-.88 -.098
-.65 -.105
-.63 -.180
.69 -.163
.72 -.105
.92 -.095
.95 -.154
1.20 -.129
1.24 -.070
1.23 .105
1.14 .169
.73 .174
.37 .151
-.16 .171
-.71 .151
-1.18 .170
-1.25 .097
''',-.16,.16,'alder',.009,'Fitted scarf tie with shouldered end housings and a slightly hewn upper arris.',protected=True)

profile('swept_knee','''
0 0
.17 .015
.27 .38
.48 .68
.82 .98
1.21 1.20
1.48 1.28
1.52 1.47
1.26 1.44
.81 1.27
.44 1.02
.16 .70
.026 .35
''',-.11,.11,'alder',.015,'Curved grown-alder knee with tapered haunch and housed crown, carrying the roof load into the bent.',protected=True)

profile('fen_deck_plank','''
-.5 -.222
-.463 -.249
-.19 -.237
.12 -.249
.468 -.229
.499 -.191
.490 .176
.45 .231
.17 .242
-.14 .229
-.466 .244
-.505 .195
''',-.075,.075,'worn_alder',.007,'Thick adzed deck board with hewn long edges, eased end grain and localized threshold wear.',plane='XY',reduce=.48)

skin('reed_wall_panel','''
-.48 -.055 .018
-.425 -.07 0
.12 -.084 .009
.454 -.055 .002
.49 -.065 .041
.478 -.08 .66
.499 -.068 1.58
.472 -.063 2.02
.405 -.067 2.055
-.01 -.079 2.036
-.45 -.064 2.06
-.491 -.058 1.97
-.468 -.085 1.01
''','''
-.48 .051 .018
-.425 .052 0
.12 .050 .009
.454 .05 .002
.49 .052 .041
.478 .058 .66
.499 .052 1.58
.472 .049 2.02
.405 .051 2.055
-.01 .050 2.036
-.45 .051 2.06
-.491 .052 1.97
-.468 .056 1.01
''','reed_weave',.005,'Bound reed wall infill with bowed weave, trimmed shoulder edges and separate real thickness.',reduce=.48)

skin('alder_cladding_board','''
-.48 -.051 .012
-.45 -.066 0
.41 -.048 .004
.483 -.059 .027
.469 -.074 .72
.49 -.049 1.58
.462 -.058 2.037
.414 -.045 2.055
-.416 -.057 2.06
-.484 -.063 2.03
-.471 -.073 .97
''','''
-.48 .039 .012
-.45 .040 0
.41 .044 .004
.483 .039 .027
.469 .041 .72
.49 .042 1.58
.462 .040 2.037
.414 .042 2.055
-.416 .039 2.06
-.484 .041 2.03
-.471 .040 .97
''','alder',.006,'Individually adzed alder cladding board, with uneven long grain shoulders, trimmed end grain and a bowed exposed face.',reduce=.52)

profile('vault_board','''
-1 0
-.94 .18
-.84 .39
-.71 .59
-.56 .75
-.39 .88
-.20 .965
0 1
.20 .965
.39 .88
.56 .75
.71 .59
.84 .39
.94 .18
1 0
.972 -.022
.911 .160
.813 .365
.686 .562
.536 .717
.372 .844
.19 .927
0 .961
-.19 .927
-.372 .844
-.536 .717
-.686 .562
-.813 .365
-.911 .160
-.972 -.022
''',-.31,.31,'alder',.001,'Original cambered roof stave section; paired curved boundaries retain actual underside thickness.',protected=True)

profile('reed_roof_bundle','''
-.49 -.258
-.43 -.271
-.36 -.249
-.28 -.283
-.20 -.258
-.12 -.285
-.04 -.264
.04 -.287
.13 -.258
.20 -.275
.28 -.253
.36 -.282
.44 -.258
.493 -.230
.48 .225
.433 .251
.19 .238
-.15 .248
-.444 .235
-.49 .198
''',-.058,.074,'roof_reed',.002,'Dense laid reed bundle with a comb-cut drip edge, bound upper head and substantial overlapping thatch thickness.',plane='XY',reduce=.42)

profile('vault_iron_rib','''
-1.012 -.018
-.95 .179
-.849 .390
-.718 .592
-.566 .755
-.394 .887
-.202 .974
0 1.009
.202 .974
.394 .887
.566 .755
.718 .592
.849 .390
.95 .179
1.012 -.018
.98 -.022
.92 .165
.821 .367
.691 .566
.541 .724
.376 .853
.192 .936
0 .971
-.192 .936
-.376 .853
-.541 .724
-.691 .566
-.821 .367
-.92 .165
-.98 -.022
''',-.045,.045,'black_iron',.001,'Forged segmented roof binding following the original cambered profile, with a narrow raised shoulder.',protected=True)

mesh('cut_reed_tip','''
.006 -.009 0
-.004 -.002 .009
.003 .007 .006
0 .010 -.005
.004 -.004 -.009
-.182 -.006 .003
-.180 .001 .011
-.176 .010 .008
-.181 .013 -.002
-.179 -.001 -.007
.003 -.0054 0
-.006 -.0012 .0054
0 .0042 .0036
-.003 .006 -.003
.001 -.0024 -.0054
-.023 -.0051 .001
-.025 -.0009 .0064
-.021 .0045 .0046
-.024 .0063 -.002
-.022 -.0021 -.0044
''','''
0 1 6 5
1 2 7 6
2 3 8 7
3 4 9 8
4 0 5 9
5 6 7 8 9
0 10 11 1
1 11 12 2
2 12 13 3
3 13 14 4
4 14 10 0
10 15 16 11
11 16 17 12
12 17 18 13
13 18 19 14
14 19 15 10
15 19 18 17 16
''','roof_reed',0,'Bent cut marsh reed with an uneven lip, thick organic rim and recessed hollow pith; original literal plant fragment for exposed thatch ends.',protected=True)

profile('reed_gable','''
-1 0
-.94 .18
-.84 .39
-.71 .59
-.56 .75
-.39 .88
-.20 .965
0 1
.20 .965
.39 .88
.56 .75
.71 .59
.84 .39
.94 .18
1 0
''',-.075,.075,'reed_weave',.002,'Cambered gable infill cut to the actual barrel roof profile, separately bound at the verge.',protected=True)

profile('ceramic_weather_cap','''
-.43 -.03
-.38 .15
-.24 .31
-.09 .385
.09 .385
.24 .31
.38 .15
.43 -.03
.335 -.05
.291 .107
.182 .229
.067 .284
-.067 .284
-.182 .229
-.291 .107
-.335 -.05
''',-.38,.38,'smoked_ceramic',.012,'Open-underneath fired clay weather cap with broad rolled lips and a shallow flattened crown.',protected=True)

profile('eave_trough','''
-.35 .18
-.285 .175
-.221 -.018
-.117 -.086
.121 -.086
.222 -.017
.282 .175
.35 .18
.288 -.05
.154 -.163
-.153 -.163
-.287 -.05
''',-.51,.51,'black_iron',.008,'Folded rain trough with an open water channel and turned drip lips, rather than a solid eave rail.',protected=True)

profile('hinge_strap','''
-.61 -.066
-.49 -.11
-.35 -.058
.28 -.050
.39 -.111
.56 -.102
.67 0
.56 .102
.39 .111
.28 .05
-.35 .058
-.49 .11
-.61 .066
''',-.026,.026,'black_iron',.006,'Blackened forged strap: flared bearing heel, slender worked shank and chisel-point terminal.',protected=True)

profile('driven_pin','''
-.048 -.016
-.033 -.055
.02 -.052
.052 -.013
.044 .036
.014 .055
-.032 .044
''',-.053,.032,'burnished_iron',.005,'Uneven upset pin head with a driven back shank; placed individually at structural fixings.',protected=True)

profile('vent_cowl','''
-.55 0
-.50 .18
-.36 .42
-.17 .59
.03 .67
.25 .58
.47 .40
.58 .19
.52 .10
.40 .29
.20 .45
.02 .54
-.13 .49
-.28 .36
-.40 .14
-.44 -.018
''',-.42,.42,'smoked_ceramic',.011,'Curved rain-sheltered vent hood; open throat and thick rolled ceramic mouth.',protected=True)

profile('louver_slat','''
-.48 -.031
-.43 -.067
.39 -.063
.49 -.02
.45 .035
.27 .058
-.23 .071
-.44 .034
''',-.032,.032,'alder',.005,'Canted vent lath with adzed shoulders and a small drainage crown.',protected=True)

profile('fortified_stave','''
-.225 .024
-.195 0
.184 .013
.218 .052
.228 .67
.21 1.71
.235 2.76
.221 4.32
.183 4.80
-.166 4.80
-.218 4.36
-.234 3.22
-.213 1.94
-.231 .56
''',-.14,.14,'tarred_alder',.01,'Full-thickness reinforced gate stave with shouldered crown and a hand-hewn bowed face.',protected=True)

profile('gate_arch','''
-3.38 4.66
-3.38 6.10
3.38 6.10
3.38 4.66
3.0 4.80
2.55 5.02
1.87 5.30
1.14 5.53
.48 5.66
0 5.70
-.48 5.66
-1.14 5.53
-1.87 5.30
-2.55 5.02
-3.0 4.80
''',-6,6,'dressed_basalt',.012,'Full-depth low cambered basalt vault: six-metre ram passage, 4.8m side clearance and 5.7m crown below the defense platform.',protected=True)

profile('palisade_shield','''
-.39 0
.384 .012
.41 .30
.382 1.03
.39 1.42
.22 1.71
.055 1.83
-.11 1.70
-.335 1.61
-.408 1.36
-.388 .64
''',-.14,.14,'tarred_alder',.012,'Broad defensive alder crest with a split angled crown and a reinforced lower shoulder.',protected=True)

profile('pintle','''
-.078 0
.072 0
.078 .42
.12 .46
.118 .57
.064 .62
-.063 .62
-.113 .576
-.126 .469
-.074 .423
''',-.076,.076,'burnished_iron',.016,'Upset forged pintle, with a retained bearing shoulder and shouldered driving foot.',protected=True)

profile('step_tread','''
-.50 -.23
-.47 -.265
-.18 -.253
.17 -.26
.464 -.243
.505 -.193
.498 .19
.459 .227
.14 .234
-.20 .224
-.467 .242
-.503 .185
''',-.084,.04,'worn_alder',.008,'Heavy stair tread with eased drainage nosing and uneven adzed rear bearing.',plane='XY',reduce=.5)

profile('vault_face_stone','''
-.28 .018
-.244 -.008
.25 .004
.29 .029
.344 .51
.301 .566
-.303 .559
-.346 .508
''',-.18,.18,'dressed_basalt',.009,'Dressed cambered-vault face stone, slightly wider at the outer bearing and with chipped keyed shoulders.',protected=True)

skin('supply_tally_cloth','''
-.33 -.006 0
.32 .008 .012
.35 -.029 -.16
.309 -.057 -.48
.344 -.031 -.82
.14 -.018 -.95
.055 -.041 -.72
-.042 -.055 -.93
-.25 -.020 -.83
-.34 .003 -.48
''','''
-.33 .008 0
.32 .021 .012
.35 -.016 -.16
.309 -.044 -.48
.344 -.018 -.82
.14 -.005 -.95
.055 -.028 -.72
-.042 -.042 -.93
-.25 -.007 -.83
-.34 .016 -.48
''','officer_cloth',.001,'Weighted supply tally cloth with hand-cut split hem and a shallow wind fold; original regional signal, no borrowed insignia.',protected=True)

MATERIALS={
 'ash_mortar':{'color':[101,104,95],'kind':'stone','roughness':.96,'weather':'ash_mortar'},
 'basalt':{'color':[73,80,79],'kind':'stone','roughness':.87},
 'dressed_basalt':{'color':[92,99,96],'kind':'stone','roughness':.77},
 'mineral_basalt':{'color':[84,91,74],'kind':'stone','roughness':.93,'weather':'mineral_splash'},
 'alder':{'color':[106,76,47],'kind':'wood','roughness':.82},
 'tarred_alder':{'color':[57,51,38],'kind':'wood','roughness':.71,'weather':'tar'},
 'worn_alder':{'color':[118,91,58],'kind':'wood','roughness':.78,'weather':'footwear'},
 'reed_weave':{'color':[102,94,60],'kind':'reed','roughness':.95,'weather':'damp_weave'},
 'roof_reed':{'color':[88,72,44],'kind':'reed','roughness':.94,'weather':'exposed_tips'},
 'reed_cut_ends':{'color':[119,101,62],'kind':'reed','roughness':.97,'weather':'cut_pith'},
 'smoked_ceramic':{'color':[63,53,43],'kind':'ceramic','roughness':.76},
 'black_iron':{'color':[42,48,46],'kind':'metal','roughness':.56,'metallic':.83},
 'burnished_iron':{'color':[95,104,102],'kind':'metal','roughness':.40,'metallic':.89},
 'officer_cloth':{'color':[59,42,62],'kind':'cloth','roughness':.95},
}


def asset(key,name,contract):
    ASSETS[key]={'name':name,'contract':contract,'instances':[]};return ASSETS[key]['instances']


def place(items,part,xyz=(0,0,0),scale=(1,1,1),rotation=(0,0,0),material=None,detail=0,lods=None):
    entry={'part':part,'location':list(xyz),'scale':list(scale),'rotation_degrees':list(rotation),'detail':detail}
    if material:entry['material']=material
    if lods is not None:entry['lod_levels']=list(lods)
    items.append(entry)


def deck(items,width,depth,level,cx=0,cy=0):
    for levels,row_width in [([0,1],.45),([2],.9)]:
        rows=math.ceil(depth/row_width);step=depth/rows;columns=math.ceil(width/2.3);span=width/columns
        for row in range(rows):
            for col in range(columns):
                place(items,'fen_deck_plank',(cx-width/2+(col+.5)*span,cy-depth/2+(row+.5)*step,level-.075),((span-.012)/1.004,(step-.008)/.498,1),lods=levels)


def ramp(items,width,start_y,run,rise):
    rows=math.ceil(run/.30);step=run/rows;angle=math.atan(rise/run)
    for row in range(rows):
        t=(row+.5)/rows;y=start_y-run+t*run
        place(items,'fen_deck_plank',(0,y,rise*t-.075/math.cos(angle)),((width-.006)/1.004,(step-.004)/(.498*math.cos(angle)),1),(math.degrees(angle),0,0))
    for x in (-width/2+.13,width/2-.13):
        place(items,'scarf_tie',(x,start_y-run/2,rise/2-.20),(run/(2.48*math.cos(angle)),.72,.8),(0,-math.degrees(angle),90))


def stone_course(items,left,right,y,level,height=.43,depth=.60,rotation=0,seed=0):
    span=right-left;count=max(1,math.ceil(span/1.04));pitch=span/count
    ends=[left]+([left+pitch*.5+i*pitch for i in range(count)] if seed%2 else [left+i*pitch for i in range(1,count)])+[right]
    for index,(a,b) in enumerate(zip(ends,ends[1:])):
        x=(a+b)/2;loc=(x,y,level) if not rotation else (y,-x,level)
        material='mineral_basalt' if level<1.05 and (index+seed)%5!=2 else 'dressed_basalt' if (index+seed)%6==0 else 'basalt'
        scale=((b-a-.004)/1.03,depth/.52,height/.429)
        part=['fen_basalt','fen_basalt_cleft','fen_basalt_shelf','fen_basalt_riven','fen_basalt_dressed'][(index+seed*3)%5]
        place(items,part,loc,scale,(0,0,rotation),material)
        place(items,'ash_mortar_bedding',loc,scale,(0,0,rotation),lods=[0,1])


def stone_wall(items,left,right,y,height,depth=.6,rotation=0,bottom=0):
    rows=math.ceil(height/.43);pitch=height/rows
    for row in range(rows):stone_course(items,left,right,y,bottom+row*pitch,pitch,depth,rotation,row)


def bound_wall(items,left,right,y,bottom,height,rotation=0):
    if right-left<.03 or height<.03:return
    count=math.ceil((right-left)/.94);pitch=(right-left)/count
    for index in range(count):
        x=left+(index+.5)*pitch;loc=(x,y,bottom) if not rotation else (y,-x,bottom)
        place(items,'reed_wall_panel',loc,((pitch-.006)/.99,1,height/2.06),(0,0,rotation))
    for level in (bottom+.08,bottom+height-.09):
        centre=(left+right)/2;loc=(centre,y-.078,level) if not rotation else (y-.078,-centre,level)
        place(items,'scarf_tie',loc,((right-left)/2.5,.3,.25),(0,0,rotation))


def fixing(items,x,y,z,rotation=0):
    place(items,'driven_pin',(x,y,z),(1,1,1),(0,0,rotation),detail=1)


def frame(items,x,y,bottom,width,height,rotation=0):
    def point(dx,dz):return (x+dx,y,bottom+dz) if not rotation else (x,y-dx,bottom+dz)
    for dx in (-width/2-.13,width/2+.13):
        place(items,'alder_pile',point(dx,0),(.68,.68,height/3.4),(0,0,rotation))
        for dz in (.22,height-.21):fixing(items,*point(dx,dz),rotation)
    place(items,'scarf_tie',point(0,height+.15),((width+.5)/2.5,.65,.7),(0,0,rotation))
    place(items,'fen_deck_plank',point(0,-.025),((width+.48)/1.004,1.2,.8),(0,0,rotation))


ROOF_CAMBER=[(-1.012,-.025),(-1,0),(-.94,.18),(-.84,.39),(-.71,.59),(-.56,.75),(-.39,.88),(-.20,.965),(0,1),(.20,.965),(.39,.88),(.56,.75),(.71,.59),(.84,.39),(.94,.18),(1,0),(1.012,-.025)]


def roof_height(x):
    for (a,za),(b,zb) in zip(ROOF_CAMBER,ROOF_CAMBER[1:]):
        if x<=b:return za+(zb-za)*(x-a)/(b-a)
    return ROOF_CAMBER[-1][1]


def fitted_roof_parts(width,rise):
    """Fit original reed cage and drawn binding to the same cambered boundary.

    The retained finite records describe the finished curved pieces. Sharing a
    common bearing surface prevents flat overlapping bundles piercing the band.
    """
    key=f'{width:g}_{rise:g}'.replace('.','p');half=width/2;parts=[]
    for index in range(14):
        centre=-1+(index+.5)*2/14;span=width/14*1.04
        name=f'fitted_reed_{key}_{index:02}';base=PARTS['reed_roof_bundle']
        if name not in PARTS:
            # Reeds run down the camber. Comb-cut outer tips cover the next
            # course's thinner head, exposing a real layered thatch edge.
            direction=-1 if centre<0 else 1
            tip=[(-.252,.476),(-.211,.507),(-.167,.478),(-.126,.514),(-.084,.489),(-.043,.508),(.001,.481),(.044,.516),(.087,.493),(.129,.510),(.174,.480),(.217,.506),(.252,.483)]
            outline=[(direction*x,y) for y,x in tip]+[(direction*-.492,.245),(direction*-.501,.078),(direction*-.483,-.11),(direction*-.497,-.246)]
            vertices=[]
            for layer in (0,1):
                for x,y in outline:
                    xx=centre*half+x*span;outer=(direction*x+.5)
                    lift=.024 if layer==0 else .153+.068*outer
                    vertices.append([xx,y,roof_height(xx/half)*rise+lift])
            n=len(outline);faces=[list(range(n-1,-1,-1)),list(range(n,2*n))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
            face_materials=['roof_reed']*len(faces)
            for face_index in range(2,14):face_materials[face_index]='reed_cut_ends'
            mesh(name,vertices,faces,'roof_reed',.001,'Down-slope laid reed sheaf, irregular comb-cut exposed tips and thinner covered head; paired surfaces retain actual overlapping thatch thickness.',protected=True,face_materials=face_materials)
        parts.append(name)
    band=f'fitted_binding_{key}';base=PARTS['vault_iron_rib']
    if band not in PARTS:
        vertices=[]
        for number,(x,y,z) in enumerate(base['vertices']):
            # The first fifteen section vertices form the outer face; the
            # return boundary lies directly on the reed's finished surface.
            outer=(number%30)<15
            vertices.append([x*half,y,roof_height(x)*rise+(.265 if outer else .224)])
        mesh(band,vertices,base['faces'],'black_iron',.001,'Continuous fitted roof binding, inner face bears on the curved reed course; ends turn down over the drip edge.',protected=True)
    return parts,band


def vaulted_roof(items,width,depth,eave,rise,cx=0,cy=0):
    half=width/2
    for lod,pitch in [(0,.59),(1,.9),(2,3.0)]:
        rows=math.ceil(depth/pitch);step=depth/rows
        for row in range(rows):
            y=cy-depth/2+(row+.5)*step
            place(items,'vault_board',(cx,y,eave),(half,(step-.006)/.62,rise),lods=[lod])
    fitted,band=fitted_roof_parts(width,rise)
    for lod,pitch in [(0,.48),(1,.72),(2,2.4)]:
        reed_rows=math.ceil(depth/pitch);reed_pitch=depth/reed_rows
        for row in range(reed_rows):
            y=cy-depth/2+(row+.5)*reed_pitch
            for part in fitted:place(items,part,(cx,y,eave),(1,reed_pitch/.515,1),lods=[lod])
    for y in (cy-depth/2+.06,cy,cy+depth/2-.06):
        place(items,band,(cx,y,eave),(1,1.6,1))
    caps=math.ceil(depth/.70)
    for index in range(caps):place(items,'ceramic_weather_cap',(cx,cy-depth/2+(index+.5)*depth/caps,eave+rise+.19+index*.0007),(1,(depth/caps+.022)/.76,1))
    for side in (-1,1):
        count=math.ceil(depth/.96)
        for index in range(count):place(items,'eave_trough',(cx+side*(half+.02),cy-depth/2+(index+.5)*depth/count,eave-.16+index*.0006),(.72,(depth/count+.012)/1.02,.72))
        # Two sparse layers of literal hollow reed ends break the thatch edge.
        # Fine cavities are close-LOD detail; lower LODs retain the sheaf profile.
        count=math.ceil(depth/.085)
        for index in range(count):
            y=cy-depth/2+(index+.5)*depth/count
            for layer in range(2):
                name=f'eave_reed_tip_{width:g}_{rise:g}_{side}_{layer}'.replace('.','p')
                if name not in PARTS:
                    original=PARTS['cut_reed_tip'];vertices=[]
                    for x,yy,z in original['vertices']:
                        xx=side*(half+.055+x)
                        vertices.append([xx,yy,roof_height(xx/half)*rise+.062+layer*.073+z])
                    mesh(name,vertices,original['faces'],'roof_reed',0,'Original hollow reed tip fitted to the actual eave camber and thatch layer.',protected=True)
                place(items,name,(cx,y+(.007 if layer else 0),eave),(1,1,1),lods=[0])


def structure(items,width,depth,floor_level,eave,open_front=False):
    deck(items,width,depth,floor_level)
    for x in (-width/2+.20,width/2-.20):
        for y in (-depth/2+.18,0,depth/2-.18):
            place(items,'basalt_footing',(x,y,0),(1,1,.62))
            place(items,'alder_pile',(x,y,.1),(1,1,(eave-.1)/3.4))
            place(items,'hinge_strap',(x,y-.22,floor_level+.2),(.48,1,1),(0,0,0),detail=1)
    for y in (-depth/2+.16,0,depth/2-.16):
        place(items,'scarf_tie',(0,y,eave-.15),(width/2.5,1,1))
        for side in (-1,1):
            place(items,'swept_knee',(side*(width/2-.35),y,eave-1.4),(.46 if open_front else .72,1,.82),(0,0,0 if side<0 else 180))
    for side in (-1,1):
        place(items,'scarf_tie',(side*(width/2-.28),0,floor_level-.24),(depth/2.5,1.1,1),(0,0,90))


def building_contract(width,depth,floor_level,door,door_height,ramp_width,ramp_run):
    return {'footprint':[width,depth],'floor_height':floor_level,'front_door_clearance':[door,door_height],
            'front_door_runtime':{'x':0,'y':floor_level,'z':depth/2},'anchor':'ground centre','door_faces':'glTF +Z',
            'ramp':{'width':ramp_width,'depth':ramp_run,'front_z':depth/2+ramp_run,'back_z':depth/2},
            'walkableSurfaces':[{'id':'interior_deck','x':0,'z':0,'width':width-.2,'depth':depth-.2,'fromY':floor_level,'toY':floor_level},
                               {'id':'front_ramp','x':0,'z':depth/2+ramp_run/2,'width':ramp_width,'depth':ramp_run+.12,'fromY':floor_level,'toY':0,'axis':'z'}],
            'colliders':[{'x':-width/2,'z':0,'width':.40,'depth':depth,'minY':0,'maxY':4.4},
                         {'x':width/2,'z':0,'width':.40,'depth':depth,'minY':0,'maxY':4.4},
                         {'x':0,'z':-depth/2,'width':width,'depth':.4,'minY':0,'maxY':4.4},
                         {'x':-(width+door)/4,'z':depth/2,'width':(width-door)/2,'depth':.4,'minY':0,'maxY':4.4},
                         {'x':(width+door)/4,'z':depth/2,'width':(width-door)/2,'depth':.4,'minY':0,'maxY':4.4}]}


dwelling=asset('frontier_cinderfen_dwelling','Cinderfen raised reed dwelling',building_contract(8,9,.6,1.8,2.6,2.2,3))
structure(dwelling,8,9,.6,4.08)
bound_wall(dwelling,-4,-.9,-4.5,.6,3.48);bound_wall(dwelling,.9,4,-4.5,.6,3.48)
bound_wall(dwelling,-.9,.9,-4.5,3.28,.80);bound_wall(dwelling,-4,4,4.5,.6,3.48)
for side in (-1,1):
    bound_wall(dwelling,-4.5,-.8,side*4,.6,3.48,90);bound_wall(dwelling,.8,4.5,side*4,.6,3.48,90)
    bound_wall(dwelling,-.8,.8,side*4,.6,1.15,90);bound_wall(dwelling,-.8,.8,side*4,3.05,1.03,90)
    frame(dwelling,side*4,0,1.75,1.6,1.3,90)
    for y in (-.54,0,.54):place(dwelling,'louver_slat',(side*4,y,2.29),(1.08,1,.55),(18,0,90))
frame(dwelling,0,-4.57,.6,1.8,2.6)
for y in (-4.54,4.54):place(dwelling,'reed_gable',(0,y,4.02),(4.22,1,2.62))
vaulted_roof(dwelling,8.7,10.05,4.05,2.6)
ramp(dwelling,2.2,-4.5,3,.6)
for x in (-1.17,1.17):place(dwelling,'alder_pile',(x,-4.28,.6),(.37,.37,.73))

workshop=asset('frontier_cinderfen_workshop','Cinderfen raised causeway workshop',building_contract(10,8,.6,2.6,3.0,3,3))
structure(workshop,10,8,.6,4.5)
bound_wall(workshop,-5,-1.3,-4,.6,3.9);bound_wall(workshop,1.3,5,-4,.6,3.9);bound_wall(workshop,-1.3,1.3,-4,3.68,.82)
bound_wall(workshop,-5,5,4,.6,3.9)
for side in (-1,1):bound_wall(workshop,-4,4,side*5,.6,2.3,90)
for side in (-1,1):
    for row in range(6):
        place(workshop,'louver_slat',(side*5,0,3.03+row*.21),(7.7,1,.82),(22,0,90))
frame(workshop,0,-4.07,.6,2.6,3.0)
for y in (-4.04,4.04):place(workshop,'reed_gable',(0,y,4.48),(5.2,1,2.18))
vaulted_roof(workshop,10.7,9.15,4.5,2.15)
ramp(workshop,3,-4,3,.6)
for y in (-2.4,0,2.4):
    place(workshop,'vent_cowl',(0,y,6.95),(1.3,1.7,1.3))
    for level in (7.05,7.21,7.37):place(workshop,'louver_slat',(0,y-.6,level),(1.03,1,.68))
# Workbench remains usable beside the entrance approach, with a thick adzed top.
deck(workshop,2.7,1.15,1.55,cx=-3.25,cy=1.75)
ASSETS['frontier_cinderfen_workshop']['contract']['colliders'].append({'x':-3.25,'z':-1.75,'width':2.7,'depth':1.15,'minY':.6,'maxY':1.55})
for x in (-4.3,-2.2):
    for y in (1.35,2.15):place(workshop,'alder_pile',(x,y,.6),(.47,.47,.93/3.4))

# Workshop walls are individual alder boards; woven reed remains specific to
# the dwelling and shelter rather than reading as a grid over timber cladding.
cladding=[]
for instance in workshop:
    if instance['part']!='reed_wall_panel':cladding.append(instance);continue
    for column in range(4):
        item={**instance,'part':'alder_cladding_board','location':list(instance['location']),'scale':list(instance['scale'])}
        offset=(column-1.5)*instance['scale'][0]*.99/4;angle=math.radians(instance['rotation_degrees'][2])
        item['location'][0]+=math.cos(angle)*offset;item['location'][1]+=math.sin(angle)*offset
        item['scale'][0]*=.246;item['material']='tarred_alder' if column==3 and len(cladding)%11==0 else 'alder'
        cladding.append(item)
workshop[:]=cladding

shelter_contract=building_contract(8,6,.35,5.8,3.1,3,1.75)
shelter_contract['colliders']=shelter_contract['colliders'][:3]
for collider in shelter_contract['colliders']:collider['maxY']=1.55
shelter=asset('frontier_cinderfen_supply_shelter','Cinderfen open supply shelter',shelter_contract)
structure(shelter,8,6,.35,3.82,True)
bound_wall(shelter,-4,4,3,.35,2.9)
for side in (-1,1):bound_wall(shelter,-3,3,side*4,.35,1.15,90)
vaulted_roof(shelter,8.65,7.05,3.82,1.9)
ramp(shelter,3,-3,1.75,.35)
place(shelter,'supply_tally_cloth',(3.56,-3.28,3.45),(1.25,1,1.3))
place(shelter,'hinge_strap',(3.56,-3.3,3.48),(.62,1,1))
for side in (-1,1):
    deck(shelter,.7,3.4,1.17,cx=side*3.35,cy=.6)
    shelter_contract['colliders'].append({'x':side*3.35,'z':-.6,'width':.7,'depth':3.4,'minY':.35,'maxY':1.17})
    for y in (-.7,1.8):place(shelter,'alder_pile',(side*3.35,y,.35),(.4,.4,.8/3.4))


def curtain(items,cx,width=8):
    for y in (-.88,.88):stone_wall(items,cx-width/2,cx+width/2,y,2.6,.7)
    for x in (cx-width/2+.22,cx,cx+width/2-.22):
        for y in (-.86,.86):place(items,'alder_pile',(x,y,2.34),(1.35,1.25,3.9/3.4))
    # Adzed revetment staves carry the lower face; a staggered crest rises above.
    count=math.ceil(width/.74);pitch=width/count
    for i in range(count):
        x=cx-width/2+(i+.5)*pitch
        place(items,'fortified_stave',(x,-.96,2.52),(pitch/.48,.80,3.65/4.8))
        if i%3!=1:place(items,'palisade_shield',(x,-.96,6.30),(pitch/.82,1.08,1.05))
        place(items,'hinge_strap',(x,-1.11,3.02),(.50,1.35,1.15),(0,0,0),detail=1)
        fixing(items,x,-1.16,3.02)
    deck(items,width,2.4,6.3,cx=cx)
    for y in (-.9,.9):place(items,'scarf_tie',(cx,y,5.96),(width/2.5,1,1.1))
    for x in (cx-width/2+.22,cx,cx+width/2-.22):place(items,'alder_pile',(x,1.01,6.3),(.62,.62,1.13/3.4))
    place(items,'scarf_tie',(cx,1.01,7.28),(width/2.5,.62,.60))
    for side in (-1,1):place(items,'swept_knee',(cx+side*(width/2-.26),.84,4.65),(1,.8,.82),(0,0,0 if side<0 else 180))


wall_contract={'footprint':[8,2.4],'wall_walk_height':6.3,'fitted_end_planes':[-4,4],'walkway_sockets_runtime':[[-4,6.3,0],[4,6.3,0]],'anchor':'ground centre',
 'walkableSurfaces':[{'id':'wall_walk','x':0,'z':0,'width':8,'depth':1.7,'fromY':6.3,'toY':6.3}],
 'colliders':[{'x':0,'z':0,'width':8,'depth':2.4,'minY':0,'maxY':6.29},{'x':0,'z':.96,'width':8,'depth':.3,'minY':6.3,'maxY':8.3},{'x':0,'z':-1.01,'width':8,'depth':.22,'minY':6.3,'maxY':7.5}]}
curtain_module=asset('frontier_cinderfen_curtain_walk','Cinderfen basalt and alder curtain walk',wall_contract)
curtain(curtain_module,0)

gate_contract={'footprint':[28,12],'passage_clearance':[6,4.8],'passage_rectangle':[[-3,-6],[3,6]],'passage_floor_height':0,'defense_deck_height':6.3,
 'wing_sockets_runtime':[[-14,6.3,0],[14,6.3,0]],'gate_socket_runtime':[0,0,6],'anchor':'ground centre','passage_faces':'glTF ±Z',
 'walkableSurfaces':[{'id':'defense_crosswalk','x':0,'z':0,'width':28,'depth':1.8,'fromY':6.3,'toY':6.3},{'id':'central_oil_platform','x':0,'z':0,'width':6.2,'depth':11.4,'fromY':6.3,'toY':6.3},
                     {'id':'left_sentry_platform','x':-6.75,'z':0,'width':6.8,'depth':10.8,'fromY':6.3,'toY':6.3},{'id':'right_sentry_platform','x':6.75,'z':0,'width':6.8,'depth':10.8,'fromY':6.3,'toY':6.3}],
 'colliders':[{'x':-6.85,'z':0,'width':7.7,'depth':12,'minY':0,'maxY':6.15},{'x':6.85,'z':0,'width':7.7,'depth':12,'minY':0,'maxY':6.15},
              {'x':0,'z':0,'width':6,'depth':12,'minY':4.8,'maxY':6.15}]}
gatehouse=asset('frontier_cinderfen_gatehouse','Cinderfen six-metre causeway gatehouse',gate_contract)
place(gatehouse,'gate_arch')
deck(gatehouse,6.6,12,6.3)
for y in (-6.18,6.18):
    for x,z,angle in [(-2.75,4.99,-26),(-2.21,5.22,-22),(-1.65,5.40,-18),(-1.09,5.55,-12),(-.54,5.65,-6),(0,5.72,0),(.54,5.65,6),(1.09,5.55,12),(1.65,5.40,18),(2.21,5.22,22),(2.75,4.99,26)]:
        place(gatehouse,'vault_face_stone',(x,y,z),(.99,1,1),(0,angle,0))
place(gatehouse,'supply_tally_cloth',(0,-6.38,7.98),(2.3,1,1.6))
for side in (-1,1):
    centre=side*6.85;left=centre-3.45;right=centre+3.45
    for runtime_z in (-5.45,5.45):gate_contract['colliders'].append({'x':centre,'z':runtime_z,'width':6.9,'depth':.6,'minY':6.3,'maxY':7.55})
    for x in (left,right):
        for runtime_z in (-3.325,3.325):gate_contract['colliders'].append({'x':x,'z':runtime_z,'width':.55,'depth':4.15,'minY':6.3,'maxY':7.5})
    for x in (left+.2,right-.2):
        for runtime_z in (-5.4,-1.6,1.6,5.4):gate_contract['colliders'].append({'x':x,'z':runtime_z,'width':.50,'depth':.5,'minY':6.3,'maxY':8.92})
    for y in (-5.62,5.62):stone_wall(gatehouse,left,right,y,6.12,.72)
    for x in (left,right):stone_wall(gatehouse,-5.65,5.65,x,6.12,.64,90)
    deck(gatehouse,7.05,11.5,6.3,cx=centre)
    for x in (left+.2,right-.2):
        for y in (-5.4,-1.6,1.6,5.4):place(gatehouse,'alder_pile',(x,y,6.08),(1.2,1.2,2.84/3.4))
    for y in (-5.4,5.4):
        place(gatehouse,'scarf_tie',(centre,y,8.86),(7.1/2.5,1.1,1.1))
        for x in (left+.25,right-.25):place(gatehouse,'swept_knee',(x,y,7.37),(.70,1,.83),(0,0,0 if x<centre else 180))
    # Upper parapets leave real 2.4m crosswalk openings toward wing and oil platform.
    for x in (left,right):
        for a,b in ((-5.4,-1.25),(1.25,5.4)):
            stone_wall(gatehouse,a,b,x,1.20,.55,90,bottom=6.3)
    for y in (-5.45,5.45):stone_wall(gatehouse,left,right,y,1.25,.6,bottom=6.3)
    vaulted_roof(gatehouse,7.8,12,8.92,2.5,cx=centre)
    wing=[];curtain(wing,side*12.15,3.7);gatehouse.extend(wing)
    for item in wall_contract['colliders']:
        gate_contract['colliders'].append({**item,'x':side*12.15,'width':3.7})
    # Guard rails run on the outer edge of the oil platform, leaving its centre open.
for y in (-5.86,5.86):
    gate_contract['colliders'].append({'x':0,'z':-y,'width':6.25,'depth':.30,'minY':6.3,'maxY':8.0})
    for x in (-2.45,-.82,.82,2.45):place(gatehouse,'palisade_shield',(x,y,6.3),(.82,1,.9))
    place(gatehouse,'scarf_tie',(0,y,6.53),(6.25/2.5,.8,.8))

leaves=asset('frontier_cinderfen_gate_leaves','Cinderfen paired reinforced gate leaves',{'footprint':[6,.72],'closed_width':6,'nominal_height':4.8,'hinges_z_up':[[-3,0,0],[3,0,0]],'leaf_nodes':['gate_leaf_left','gate_leaf_right'],'clips':['gate_open','gate_close'],'swing_degrees':90,'anchor':'ground centre','door_faces':'glTF +Z','collision_policy':'dynamic closed rectangle','closed_collision_runtime':{'x':0,'z':-.3,'width':6,'depth':.72,'minY':0,'maxY':4.8}})
for side in (-1,1):
    begin=len(leaves);centre=side*1.5
    for index in range(7):place(leaves,'fortified_stave',(centre+(index-3)*.423,.22,0),(.905,1,1))
    for z in (.40,2.39,4.36):
        place(leaves,'scarf_tie',(centre,.46,z),(2.91/2.5,.7,.90))
        place(leaves,'hinge_strap',(centre,.055,z),(2.20,1,1.40))
        for x in (centre-1.14,centre-.57,centre,centre+.57,centre+1.14):fixing(leaves,x,.070,z)
    for z in (.77,2.72):place(leaves,'swept_knee',(centre-1.19,.49,z),(1.56,.65,1.07))
    for z in (.07,2.02,3.91):place(leaves,'pintle',(side*2.97,.12,z),(.96,.96,.94))
    for item in leaves[begin:]:item['rigid_group']='gate_leaf_left' if side<0 else 'gate_leaf_right'

stair_contract={'footprint':[5.6,8.8],'landing_heights':[3.15,6.3],'ground_socket_runtime':[-1.3,0,4.2],'top_socket_runtime':[1.3,6.3,4.5],'anchor':'ground centre',
 'walkableSurfaces':[{'id':'turn_landing','x':0,'z':-2.68,'width':4.8,'depth':2.24,'fromY':3.15,'toY':3.15},
                     {'id':'upper_landing','x':1.3,'z':4.34,'width':2.2,'depth':.32,'fromY':6.3,'toY':6.3}],
 'colliders':[]}
stair=asset('frontier_cinderfen_wall_stair','Cinderfen switchback wall stair',stair_contract)
for flight in (0,1):
    centre=-1.3 if flight==0 else 1.3
    for step in range(18):
        y=-4.2+(step+.5)*.32 if flight==0 else 1.56-(step+.5)*.32
        z=(step+1)*.175+(3.15 if flight else 0)
        place(stair,'step_tread',(centre,y,z-.04),(2.25,.64,1))
        stair_contract['walkableSurfaces'].append({'id':f'tread_{flight}_{step:02}','x':centre,'z':-y,'width':2.15,'depth':.32,'fromY':round(z,6),'toY':round(z,6)})
        stair_contract['colliders'].append({'x':centre,'z':-y,'width':2.25,'depth':.32,'minY':round(z-.124,6),'maxY':round(z,6)})
    for side in (-1,1):
        x=centre+side*1.13
        for step in (0,6,12,18):
            y=-4.2+step*.32 if flight==0 else 1.56-step*.32;z=step*.175+(3.15 if flight else 0)
            place(stair,'alder_pile',(x,y,z),(.56,.56,1.05/3.4))
            stair_contract['colliders'].append({'x':x,'z':-y,'width':.23,'depth':.23,'minY':z,'maxY':z+1.05})
        angle=math.degrees(math.atan(3.15/5.76))*(1 if flight==0 else -1)
        place(stair,'scarf_tie',(x,-1.32,1.575+(3.15 if flight else 0)+.95),(math.hypot(5.76,3.15)/2.5,.46,.46),(0,-angle,90))
        place(stair,'scarf_tie',(x,-1.32,1.575+(3.15 if flight else 0)-.24),(math.hypot(5.76,3.15)/2.5,.9,1.1),(0,-angle,90))
deck(stair,4.8,2.24,3.15,cy=2.68)
deck(stair,2.3,.32,6.3,cx=1.3,cy=-4.34)
stair_contract['colliders'].extend([{'x':0,'z':-2.68,'width':4.8,'depth':2.24,'minY':3.0,'maxY':3.15},{'x':1.3,'z':4.34,'width':2.3,'depth':.32,'minY':6.15,'maxY':6.3}])
for x in (-2.36,0,2.36):
    for y in (1.70,3.70):
        place(stair,'basalt_footing',(x,y,0),(.8,.8,.67))
        place(stair,'alder_pile',(x,y,.15),(.82,.82,3.0/3.4))
for x in (-2.36,2.36):
    place(stair,'alder_pile',(x,3.7,3.15),(.57,.57,1.05/3.4))
place(stair,'scarf_tie',(0,3.7,4.09),(4.9/2.5,.46,.46))


def coarse(name,selected):
    base=PARTS[name];n=len(base['vertices'])//2
    a=[base['vertices'][i] for i in selected];b=[base['vertices'][i+n] for i in selected]
    temporary='coarse_'+name
    skin(temporary,'\n'.join(' '.join(map(str,p)) for p in a),'\n'.join(' '.join(map(str,p)) for p in b),base['material'],0,'Explicit retained distant boundary of '+name)
    base['lod2']=PARTS.pop(temporary)


skin('distant_fen_basalt','''
-.512 -.265 .012
-.468 -.270 -.002
.493 -.268 .008
.489 -.260 .430
-.503 -.263 .425
''','''
-.492 .225 .019
-.454 .220 .007
.478 .223 .014
.471 .220 .427
-.483 .223 .422
''','basalt',0,'Explicit distant basalt retopology keeps complete bearing faces and course height, with a small hewn lower corner; it does not skip structural silhouette corners.')
PARTS['fen_basalt']['lod2']=PARTS.pop('distant_fen_basalt')
for variant,_,_ in BASALT_VARIANTS:PARTS['fen_basalt_'+variant]['lod2']=PARTS['fen_basalt']['lod2']
profile('distant_adzed_deck','''
-.501 -.225
-.487 -.247
.478 -.243
.497 -.221
.494 .222
.478 .244
-.485 .243
-.503 .224
''',-.075,.075,'worn_alder',0,'Explicit distant deck retopology: small adzed corner shoulders retain the fitted bearing envelope without enlarging drainage gaps.',plane='XY')
PARTS['fen_deck_plank']['lod2']=PARTS.pop('distant_adzed_deck')
coarse('reed_wall_panel',[0,3,5,8,10,12])
coarse('reed_roof_bundle',[0,5,10,13,14,15,18,19])
coarse('step_tread',[0,3,5,6,8,10,11])
for name in list(PARTS):
    if name.startswith('fitted_reed_'):
        coarse(name,[0,3,6,9,12,13,14,15,16])
        record=PARTS[name]['lod2'];record['face_materials']=['roof_reed']*len(record['faces'])
        for face_index in range(2,6):record['face_materials'][face_index]='reed_cut_ends'
        PARTS[name]['lod1']=record


def serialize():
    for directory in ['source','textures/source','masters','runtime','review']:(ROOT/directory).mkdir(parents=True,exist_ok=True)
    source={'units':'metres','up_axis':'Z','front_axis':'-Y','provenance':'Original Cinderfen control cages and finite construction placements; Sunmeadow finishing/export utilities are reused with attribution, never its geometry or textures.','parts':PARTS,'materials':MATERIALS,'assets':ASSETS}
    (ROOT/'source/architecture.json').write_text(json.dumps(source,indent=2)+'\n')
    print(f'Authored {len(PARTS)} original construction cages and {len(ASSETS)} Cinderfen modules.')


if __name__=='__main__':serialize()
