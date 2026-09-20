"""Original skylark flight feathers, folded-wing landmarks and articulated feet."""
import math
from mathutils import Vector

def bird_bones(base):
    bones=list(base)
    bones.append({'name':'tail','head':(0,.059,.086),'tail':(0,.15,.072),'parent':'pelvis'})
    for side,label in [(1,'L'),(-1,'R')]:
        wing=[(.023,-.005,.112),(.085,.013,.114),(.132,.026,.100),(.188,.064,.084)]
        for i,name in enumerate(['wing_upper','wing_lower','wing_hand']):
            a=wing[i];b=wing[i+1];bones.append({'name':name+'_'+label,'head':(a[0]*side,*a[1:]),'tail':(b[0]*side,*b[1:]),'parent':'chest' if i==0 else ['wing_upper','wing_lower'][i-1]+'_'+label})
        leg=[(.019,.025,.071),(.020,.009,.038),(.019,.027,.012),(.019,-.003,.008)]
        for i,name in enumerate(['bird_thigh','bird_shin','bird_foot']):
            a=leg[i];b=leg[i+1];bones.append({'name':name+'_'+label,'head':(a[0]*side,*a[1:]),'tail':(b[0]*side,*b[1:]),'parent':'pelvis' if i==0 else ['bird_thigh','bird_shin'][i-1]+'_'+label})
    return bones

def feather(cage,name,path,width,lod,bone,atlas,tile=7):
    """Curved asymmetrical vane with thickness and a raised central rachis."""
    rows=[0,.14,.34,.56,.78,.94,1] if lod==0 else [0,.25,.55,.82,1]
    columns=[-1,-.5,0,.5,1] if lod<2 else [-1,0,1]
    points=[Vector(p) for p in path];direction=(points[-1]-points[0]).normalized();lateral=direction.cross(Vector((0,0,1))).normalized()
    vertices=[];uv=[];faces=[]
    for reverse in [False,True]:
        for t in rows:
            center=points[0].lerp(points[1],t*2) if t<.5 else points[1].lerp(points[2],(t-.5)*2)
            taper=max(.015,math.sin(math.pi*(.06+t*.94))**.58)
            for c in columns:
                asymmetry=.78 if c<0 else 1
                ridge=.0007*(1-abs(c))*math.sin(t*math.pi)
                p=center+lateral*(c*width*taper*asymmetry)+Vector((0,0,ridge+(-.00025 if reverse else .00025)))
                vertices.append(p);uv.append(atlas((c+1)/2,t,tile))
    panel=len(rows)*len(columns)
    for layer in [0,1]:
        for row in range(len(rows)-1):
            for col in range(len(columns)-1):
                a=layer*panel+row*len(columns)+col;f=[a,a+1,a+1+len(columns),a+len(columns)];faces.append(f[::-1] if layer else f)
    # Stitch both curved vanes; the feather is not a transparent card.
    perimeter=list(range(len(columns)))+[r*len(columns)+len(columns)-1 for r in range(1,len(rows))]
    perimeter+=list(range(panel-2,panel-len(columns)-1,-1))+[r*len(columns) for r in range(len(rows)-2,0,-1)]
    for i,a in enumerate(perimeter):
        b=perimeter[(i+1)%len(perimeter)];faces.append([a,b,b+panel,a+panel])
    cage.add(name,vertices,faces,[[uv[i] for i in f] for f in faces],[{bone:1} for _ in vertices])

def bird_geometry(definition,lod,api):
    cage=api['Cage']();loft=api['skin_loft'];atlas=api['atlas']
    loft(cage,'continuous_rump_chest_neck_head',[[*row[:5],{row[5]:1}] for row in definition['body']],lod)
    for side,label in [(1,'L'),(-1,'R')]:
        api['eye_patch'](cage,definition['eye'],definition['eye_size'],side,lod,definition)
        wing=[(.023,-.005,.112,.022,.009,'chest'),(.056,.004,.115,.025,.008,'wing_upper_'+label),(.085,.013,.114,.023,.007,'wing_lower_'+label),(.113,.020,.106,.020,.005,'wing_lower_'+label),(.137,.03,.099,.013,.003,'wing_hand_'+label)]
        loft(cage,'feathered_wing_skin_'+label,[[x*side,y,z,w,d,{bone:1}] for x,y,z,w,d,bone in wing],lod,0)
        # Distinct primary lengths and fans follow the hand; secondaries follow
        # the ulna. Their overlaps persist when the wings fold alongside the body.
        primary_count=[10,8,6][lod]
        for i in range(primary_count):
            t=i/(primary_count-1);start=(side*(.11+t*.031),.021+t*.026,.103-t*.009)
            tip=(side*(.168+.025*math.sin(t*math.pi*.85)),.015+t*.087,.09-.007*t)
            middle=tuple((a+b)/2 for a,b in zip(start,tip));middle=(middle[0],middle[1],middle[2]+.003)
            feather(cage,f'primary_{label}_{i}',[start,middle,tip],.009 if lod<2 else .011,lod,'wing_hand_'+label,atlas)
        secondary_count=[8,6,4][lod]
        for i in range(secondary_count):
            t=i/(secondary_count-1);x=.075+t*.055;y=.001+t*.02
            feather(cage,f'secondary_{label}_{i}',[(side*x,y,.112-t*.005),(side*(x+.008),y+.04,.111-t*.008),(side*(x+.01),y+.075,.095-t*.004)],.011 if lod<2 else .014,lod,'wing_lower_'+label,atlas)
        # Smaller scapular coverts bridge body and flight-feather layers.
        for i in range([6,4,3][lod]):
            t=i/max(1,[6,4,3][lod]-1);x=.029+t*.045
            feather(cage,f'scapular_covert_{label}_{i}',[(side*x,-.007,.119),(side*(x+.003),.023,.128),(side*(x+.005),.053,.115)],.009,lod,'wing_upper_'+label,atlas,0)
        leg=[(.019,.025,.071,.0058,.0062,'bird_thigh_'+label),(.020,.009,.038,.0035,.0042,'bird_shin_'+label),(.019,.027,.012,.0031,.0032,'bird_foot_'+label)]
        loft(cage,'scaly_tarsus_'+label,[[x*side,y,z,w,d,{bone:1}] for x,y,z,w,d,bone in leg],lod,5)
        for toe in [-1,0,1,2]:
            foot=Vector((.019*side,.027,.010));direction=Vector(((toe-0.5)*.006,-.027 if toe!=2 else .021,-.003))
            end=foot+direction
            path=[[*foot,.0026,.0026,{'bird_foot_'+label:1}],list(foot.lerp(end,.5))+[.0019,.0021,{'bird_foot_'+label:1}],list(end)+[.0013,.0015,{'bird_foot_'+label:1}]]
            loft(cage,f'grasping_toe_{label}_{toe}',path,lod,5)
            tip=end+Vector((0,-.005 if toe!=2 else .009,-.0015))
            loft(cage,f'horn_claw_{label}_{toe}',[list(end)+[.0015,.0018,{'bird_foot_'+label:1}],list(tip)+[.0003,.0004,{'bird_foot_'+label:1}]],lod,2)
    tail_count=[10,8,6][lod]
    for i in range(tail_count):
        t=i/(tail_count-1);x=(t-.5)*.032
        feather(cage,f'rectrix_{i}',[(x*.4,.054,.085),(x*.8,.100,.085),(x,.151-.01*abs(t-.5),.074)],.0058 if lod<2 else .008,lod,'tail',atlas,1 if i in [0,tail_count-1] else 7)
    # Skylark's modest crest and streaked breast are individually shaped coverts.
    for i in range([7,5,3][lod]):
        x=(i-([7,5,3][lod]-1)/2)*.0038
        feather(cage,f'crest_{i}',[(x,-.043,.170),(x,-.030,.182),(x*.7,-.019,.182)],.003,lod,'head',atlas,0)
    muzzle=definition['body'][-1]
    loft(cage,'slender_upper_beak',[[0,muzzle[1],muzzle[2],.010,.008,{'head':1}],[0,-.093,.138,.006,.004,{'head':1}],[0,-.104,.136,.001,.001,{'head':1}]],lod,5)
    loft(cage,'slender_lower_beak',[[0,-.078,.133,.009,.003,{'jaw':1}],[0,-.093,.133,.005,.002,{'jaw':1}],[0,-.103,.135,.0008,.0006,{'jaw':1}]],lod,5)
    return cage
