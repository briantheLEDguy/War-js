"""Original anatomical skin cages, detailed appendages and explicit animal rigs."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
sys.path.insert(0,str(Path(__file__).resolve().parent))
from quadruped_rig import create_rig, bind_explicit_weights
from motion import mammal_clips,bird_clips
from bird_geometry import bird_bones,bird_geometry
from stitched_skin import build_stitched_skin
from atlas_checks import assert_single_atlas_island
from surface_detail import deer_face_position
from texture_detail import pelt_strokes,tangent_normals

ROOT = Path(__file__).resolve().parents[1]
SOURCE = json.loads((ROOT/'source/anatomy.json').read_text())
for directory in ['runtime','review','masters','textures']:(ROOT/directory).mkdir(exist_ok=True)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def mix(a,b,t):return a*(1-t)+b*t
def resolve(kind):
    record=SOURCE['assets'][kind]
    if 'inherits' in record:return {**resolve(record['inherits']),**record}
    return record

def paint_material(kind,definition):
    """Pigment follows UV surface directions; hair shafts are normal detail, not alpha fur."""
    tile_size=1024; width,height=tile_size*4,tile_size*2
    yy,xx=np.mgrid[:height,:width].astype(np.float32)
    tile_x=(xx//tile_size).astype(int);tile_y=(yy//tile_size).astype(int);tile=tile_y*4+tile_x
    u=(xx%tile_size)/(tile_size-1);v=(yy%tile_size)/(tile_size-1)
    p=definition['palette'];iris=[.12,.077,.035] if 'roe_deer' in kind else [.14,.075,.022]
    colors=np.array([[.78,.73,.66] if kind!='skylark' else p['coat'],p['cream'],p['dark'],p['ear'],iris,[.45,.355,.22],[.31,.071,.053],p['coat'] if kind=='skylark' else p['cream']])
    color=colors[tile].copy()
    # Irregular overlapping strokes follow the pelt UV direction. They have
    # no cell rows; unoccupied/non-pelt islands do not carry fur relief.
    relief,hair_pigment=pelt_strokes(tile_size)
    shaft=np.tile(relief,(2,4));breaks=1
    pelt=(tile==0)|(tile==1)
    mottling=.019*np.sin(u*41+v*17)*np.cos(v*29-u*11)
    pigment=np.tile(hair_pigment,(2,4))*1.8+mottling
    color=np.clip(color+(pigment*pelt)[...,None],0,1)
    belly=np.exp(-((u-.75)/.13)**4)*(tile==0)*(kind=='skylark')
    if 'roe_deer' in kind:belly*=np.clip((.63-v)*6,0,1)*.40
    dorsal=np.exp(-((u-.25)/.18)**4)*(tile==0)
    color=color*(1-belly[...,None]*.62)+np.array(p['cream'])*belly[...,None]*.62
    color*=1-dorsal[...,None]*.035
    if kind=='brown_hare':color+=((shaft*breaks>.68)*(tile==0))[...,None]*np.array([.095,.07,.02])
    if kind=='skylark':
        streak=np.exp(-((np.mod(u*13+.1*np.sin(v*9),1)-.5)/.12)**2)*np.sin(v*19)**4*(tile==0)
        color-=streak[...,None]*.12
    # Short summer hair has broken directional relief; the eye atlas carries
    # its own uninterrupted cornea and horizontal ungulate pupil.
    if 'roe_deer' in kind:
        eye_radius=((u-.5)/.45)**2+((v-.5)/.32)**2
        pupil=(np.abs(v-.5)<.080*np.sqrt(np.maximum(0,1-((u-.5)/.35)**2)))
        eye_color=np.stack([.085+.020*np.sin(np.arctan2(v-.5,u-.5)*37),np.full_like(u,.046),np.full_like(u,.018)],axis=-1)
        eye_color=np.where((pupil|(eye_radius>.90))[...,None],np.array([.012,.009,.006]),eye_color)
        color=np.where((tile==4)[...,None],eye_color,color)
    antler_grain=np.sin(u*83+.15*np.sin(v*29))*.025*(1-v)* (tile==5)
    color+=antler_grain[...,None]
    surface=.5+shaft*.0028*pelt
    surface=np.where(tile==2,.5+shaft*.0012,surface)
    surface=np.where(tile==4,.5,surface)+antler_grain*.25
    # Blender image.pixels rows run bottom-up, as does UV V: both gradients
    # therefore point against the height slope (Pillow's raster-Y is opposite).
    normal=tangent_normals(surface,38,rows_bottom_up=True)
    rough=np.where(tile==4,.17,np.where(tile==2,.46,.80+shaft*.045*pelt))
    orm=np.stack([np.clip(.97-(1-surface)*.06,0,1),rough,np.zeros_like(rough)],axis=-1)
    images={}
    for channel,rgb in [('basecolor',np.clip(color,0,1)),('normal',normal*.5+.5),('orm',orm)]:
        image=bpy.data.images.new(f'{kind}_{channel}',width=width,height=height,alpha=False)
        image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        pixels=np.ones((height,width,4),dtype=np.float32);pixels[:,:,:3]=rgb
        image.pixels.foreach_set(pixels.ravel());image.file_format='PNG';image.filepath_raw=str(ROOT/'textures'/f'{kind}_{channel}.png');image.save();image.pack();images[channel]=image
    mat=bpy.data.materials.new(kind+'_authored_pelt');mat.use_nodes=True;nodes,links=mat.node_tree.nodes,mat.node_tree.links;bsdf=nodes.get('Principled BSDF')
    base=nodes.new('ShaderNodeTexImage');base.image=images['basecolor']
    tint=nodes.new('ShaderNodeVertexColor');tint.layer_name='AnatomicalTint'
    multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
    links.new(base.outputs['Color'],multiply.inputs[1]);links.new(tint.outputs['Color'],multiply.inputs[2]);links.new(multiply.outputs[0],bsdf.inputs['Base Color'])
    packed=nodes.new('ShaderNodeTexImage');packed.image=images['orm'];separate=nodes.new('ShaderNodeSeparateColor');links.new(packed.outputs['Color'],separate.inputs[0]);links.new(separate.outputs['Green'],bsdf.inputs['Roughness']);links.new(separate.outputs['Blue'],bsdf.inputs['Metallic'])
    image_normal=nodes.new('ShaderNodeTexImage');image_normal.image=images['normal'];normal_node=nodes.new('ShaderNodeNormalMap');normal_node.inputs['Strength'].default_value=.6;links.new(image_normal.outputs['Color'],normal_node.inputs['Color']);links.new(normal_node.outputs[0],bsdf.inputs['Normal'])
    group=bpy.data.node_groups.get('glTF Material Output') or bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
    if not group.interface.items_tree:group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
    node=nodes.new('ShaderNodeGroup');node.node_tree=group;links.new(separate.outputs['Red'],node.inputs['Occlusion'])
    return mat

def tint_anatomy(obj,kind,definition):
    """Paint anatomically located coat markings into the actual surface corners."""
    colors=obj.data.color_attributes.new(name='AnatomicalTint',type='FLOAT_COLOR',domain='CORNER')
    uv=obj.data.uv_layers['AnatomicalUV'];palette=definition['palette'];base=np.array(palette['coat']);cream=np.array(palette['cream']);dark=np.array(palette['dark']);neutral=np.array([.78,.73,.66])
    body=definition['body'];centers=np.array([row[:3] for row in body]);depths=np.array([row[4] for row in body]);vertices=np.array([list(v.co) for v in obj.data.vertices]);tints=[]
    for point in vertices:
        candidates=[]
        for index in range(len(centers)-1):
            delta=centers[index+1]-centers[index];t=np.clip(np.dot(point-centers[index],delta)/np.dot(delta,delta),0,1);axis=centers[index]+delta*t
            candidates.append((np.linalg.norm(point-axis),axis,mix(depths[index],depths[index+1],t)))
        _,axis,depth=min(candidates,key=lambda item:item[0])
        underside=max(0,min(1,(axis[2]-point[2])/max(.01,depth)*1.3-.2));pigment=base.copy()
        if kind=='red_fox':
            belly=underside*.92 if point[2]>.25 and point[1]<.40 else 0;pigment=pigment*(1-belly)+cream*belly
            boot=max(0,min(1,(.23-point[2])/.09));pigment=pigment*(1-boot)+dark*boot
            tip=max(0,min(1,(point[1]-.70)/.10));pigment=pigment*(1-tip)+cream*tip
            if point[2]>.59:pigment*=.35
        elif 'roe_deer' in kind:
            pigment=pigment*(1-underside*.18)+cream*underside*.18
            rump=max(0,min(1,(point[1]-.39)/.075))*max(0,min(1,(.77-point[2])/.10));pigment=pigment*(1-rump)+cream*rump
            chin=max(0,min(1,(-point[1]-.63)/.08))*underside; pigment=pigment*(1-chin*.85)+cream*chin*.85
            ey=definition['eye'];side=min(1,abs(point[0])/.045)
            orbit=math.exp(-((point[1]-ey[1])/.034)**2-((point[2]-ey[2])/.021)**2)*side
            pigment*=1-orbit*.42
            brow=math.exp(-((point[1]-ey[1])/.037)**2-((point[2]-ey[2]-.029)/.013)**2)*side
            pigment=pigment*(1-brow*.20)+cream*brow*.20
            muzzle=math.exp(-((point[1]+.792)/.041)**2-((point[2]-.984)/.037)**2)
            pigment*=1-muzzle*.26
            forehead=math.exp(-((point[1]+.614)/.085)**2-((point[2]-1.142)/.027)**2)
            pigment*=1-forehead*.14
        elif kind=='barrow_wolf':
            belly=underside*.7;pigment=pigment*(1-belly)+cream*belly
            saddle=max(0,min(1,(point[2]-axis[2])/max(.01,depth)))*(.38 if point[1]>-.5 else .12);pigment*=1-saddle
            fleck=.06*math.sin(point[0]*231+point[1]*83)*math.sin(point[2]*174);pigment+=fleck
        elif kind=='brown_hare':
            belly=underside*.7;pigment=pigment*(1-belly)+cream*belly
            if point[2]>.485:pigment=dark*.85
            fleck=.035*math.sin(point[0]*483+point[1]*229)*math.cos(point[2]*491);pigment+=fleck
        tints.append(np.clip(pigment/neutral,0,1)**2.2)
    for index,loop in enumerate(obj.data.loops):
        tex=uv.data[index].uv;tile=int(min(3,tex.x*4))+int(min(1,tex.y*2))*4
        color=tints[loop.vertex_index] if tile==0 and kind!='skylark' else (1,1,1)
        colors.data[index].color=(*color,1)

def atlas(u,v,tile):return ((tile%4+.018+u*.964)/4,(tile//4+.018+v*.964)/2)

class Cage:
    def __init__(self):self.vertices=[];self.faces=[];self.uv=[];self.weights=[];self.parts=[]
    def add(self,name,vertices,faces,uv,weights):
        if len(faces)!=len(uv) or len(vertices)!=len(weights):raise ValueError(name+': cage attribute lengths differ')
        for index,coordinates in enumerate(uv):assert_single_atlas_island(coordinates,f'{name} face {index}')
        offset=len(self.vertices);self.vertices.extend([list(v) for v in vertices]);self.faces.extend([[offset+i for i in f] for f in faces]);self.uv.extend(uv);self.weights.extend(weights)
        self.parts.append({'name':name,'first_vertex':offset,'vertices':len(vertices),'faces':len(faces)})
    def object(self,name,material):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(self.vertices,[],self.faces);mesh.update();layer=mesh.uv_layers.new(name='AnatomicalUV')
        for poly,uv in zip(mesh.polygons,self.uv):
            poly.use_smooth=True
            for index,value in zip(poly.loop_indices,uv):layer.data[index].uv=value
        mesh.materials.append(material);obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);return obj
    def subset(self,predicate):
        result=Cage()
        for part in self.parts:
            if not predicate(part['name']):continue
            first=part['first_vertex'];last=first+part['vertices'];faces=[];uv=[]
            for face,coords in zip(self.faces,self.uv):
                if first<=face[0]<last:faces.append([index-first for index in face]);uv.append(coords)
            result.add(part['name'],self.vertices[first:last],faces,uv,self.weights[first:last])
        return result

def blended_weights(a,b,t):
    result={}
    for name,value in a.items():result[name]=result.get(name,0)+value*(1-t)
    for name,value in b.items():result[name]=result.get(name,0)+value*t
    return {name:value for name,value in result.items() if value>1e-6}

def skin_loft(cage,name,sections,lod,tile=0,shape='skin',cap=True):
    """Connected, refined sections retain the literal cage's anatomical landmarks."""
    sides=[24,16,10][lod];steps=[4,3,2][lod];rings=[]
    for index in range(len(sections)-1):
        previous=sections[max(0,index-1)];a=sections[index];b=sections[index+1];following=sections[min(len(sections)-1,index+2)]
        for step in range(steps):
            t=step/steps;row=[]
            for coordinate in range(5):
                p0,p1,p2,p3=previous[coordinate],a[coordinate],b[coordinate],following[coordinate]
                value=.5*(2*p1+(p2-p0)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
                row.append(max(.001,value) if coordinate>=3 else value)
            row.append(blended_weights(a[5],b[5],t));rings.append(row)
    rings.append(sections[-1]);vertices=[];coords=[];weights=[]
    for i,row in enumerate(rings):
        center=Vector(row[:3]);direction=(Vector(rings[min(i+1,len(rings)-1)][:3])-Vector(rings[max(0,i-1)][:3])).normalized()
        lateral=Vector((1,0,0));up=direction.cross(lateral).normalized()
        if name=='continuous_rump_chest_neck_head':up=Vector((0,0,1))
        if up.length<.01:up=Vector((0,0,1));lateral=up.cross(direction).normalized()
        for j in range(sides):
            angle=j*math.tau/sides;cross_x=math.cos(angle);cross_z=math.sin(angle)
            # Keel, haunch and dorsal planes avoid a uniform circular section.
            plane=1+.04*math.cos(angle*4)+(0.055*max(0,cross_z)**6 if shape=='skin' else 0)
            if shape=='antler':plane=1+.11*math.sin(angle*5+i*.52)+.045*math.sin(angle*9-i*.81)
            point=center+lateral*(row[3]*cross_x*plane)+up*(row[4]*cross_z)
            vertices.append(point);coords.append(atlas(j/sides,i/(len(rings)-1),tile));weights.append(row[5])
    faces=[];uv=[]
    for i in range(len(rings)-1):
        for j in range(sides):
            face=[i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j];faces.append(face)
            uv.append([atlas(j/sides,i/(len(rings)-1),tile),atlas((j+1)/sides,i/(len(rings)-1),tile),atlas((j+1)/sides,(i+1)/(len(rings)-1),tile),atlas(j/sides,(i+1)/(len(rings)-1),tile)])
    if cap:
        for ring,reverse in [(0,True),(len(rings)-1,False)]:
            face=list(range(ring*sides,(ring+1)*sides));face=face[::-1] if reverse else face;faces.append(face)
            uv.append([atlas(.5+.45*math.cos((index%sides)*math.tau/sides),.5+.45*math.sin((index%sides)*math.tau/sides),tile) for index in face])
    cage.add(name,vertices,faces,uv,weights)

def ear_patch(cage,definition,side,lod):
    points=[Vector((p[0]*side,p[1],p[2])) for p in definition['ear']];width=definition['ear_width'];steps=[16,10,6][lod];rows=[i/steps for i in range(steps+1)]
    columns=[[-1,-.82,-.44,0,.44,.82,1],[-1,-.65,0,.65,1],[-1,0,1]][lod];cols=len(columns)
    vertices=[];coords=[];weights=[];bone='ear_L' if side>0 else 'ear_R'
    for back in [False,True]:
        for t in rows:
            center=points[0]*(1-t)**2+points[1]*(2*t*(1-t))+points[2]*t*t
            span=(max(.015,(1-t)**.8*(.6+.4*math.sin(math.pi*t))) if definition.get('ear_shape')=='triangular' else max(.015,math.sin(math.pi*(.10+t*.9))**.7))*width
            for across in columns:
                cup=.019*math.sin(t*math.pi)*(1-across*across)
                rim=.0015*math.sin(t*math.pi)*math.exp(-((abs(across)-.94)/.11)**2)
                thickness=.0035*(.6+.4*math.sin(t*math.pi))
                vertices.append(center+Vector((span*across,cup-rim+(thickness if back else 0),0)))
                coords.append(atlas((across+1)/2,t,0 if back else 3));weights.append({bone:1})
    faces=[];uv=[];count=len(rows)*cols
    for back in [0,1]:
        for row in range(len(rows)-1):
            for column in range(cols-1):
                a=back*count+row*cols+column;face=[a,a+1,a+cols+1,a+cols];face=face[::-1] if back else face;faces.append(face);uv.append([coords[i] for i in face])
    for row in range(len(rows)-1):
        for column in [0,cols-1]:
            a=row*cols+column;face=[a,a+cols,a+cols+count,a+count];faces.append(face)
            uv.append([atlas(.1,row/(len(rows)-1),0),atlas(.1,(row+1)/(len(rows)-1),0),atlas(.15,(row+1)/(len(rows)-1),0),atlas(.15,row/(len(rows)-1),0)])
    for row in [0,len(rows)-1]:
        for column in range(cols-1):
            a=row*cols+column;face=[a,a+1,a+1+count,a+count]
            if row==0:face.reverse()
            faces.append(face);v=.05 if row==0 else .94
            uv.append([atlas(u,w,0) for u,w in [(.10,v),(.13,v),(.13,v+.01),(.10,v+.01)]])
    cage.add('concave_ear_'+bone,vertices,faces,uv,weights)

def eye_patch(cage,point,size,side,lod,definition=None):
    center=Vector((point[0]*side,point[1],point[2]));segments=[24,16,10][lod];vertices=[];coords=[]
    for radius,depth,tile in [(1.18,0,0),(1.03,.0008,2),(.96,.0017,4),(.73,.0028,4),(.38,.0035,4),(.015,.0037,4)]:
        depth*=size/.021
        for i in range(segments):
            angle=i*math.tau/segments
            vertical=math.sin(angle)*(.63-.08*abs(math.cos(angle)))
            vertex=center+Vector((depth*side,math.cos(angle)*size*radius,vertical*size*radius))
            if definition:
                rows=definition['body'];pair=min(zip(rows,rows[1:]),key=lambda pair:abs(vertex.y-max(min(vertex.y,max(pair[0][1],pair[1][1])),min(pair[0][1],pair[1][1]))))
                a,b=pair;t=max(0,min(1,(vertex.y-a[1])/(b[1]-a[1])))
                cz=mix(a[2],b[2],t);width=mix(a[3],b[3],t);height=mix(a[4],b[4],t)
                surface=width*1.035*math.sqrt(max(0,1-((vertex.z-cz)/height)**2));vertex.x=side*(surface+size*.05+depth)
            vertices.append(vertex)
            coords.append((.5+.42*min(1,radius)*math.cos(angle),.5+.42*min(1,radius)*vertical))
    faces=[]
    for row in range(5):
        for j in range(segments):
            face=[row*segments+j,row*segments+(j+1)%segments,(row+1)*segments+(j+1)%segments,(row+1)*segments+j]
            faces.append(face if side>0 else face[::-1])
    # Each strip stays within one atlas island. Connecting UVs from coat to
    # cornea across separate tiles samples the intervening cream/antler atlas.
    face_uv=[[atlas(*coords[j],0 if index<segments else 4) for j in face] for index,face in enumerate(faces)]
    cage.add('orbital_rim_iris_pupil_'+str(side),vertices,faces,face_uv,[{'head':1} for _ in vertices])

def nose_patch(cage,definition,lod):
    """Flattened, divided rhinarium with shaped alae and recessed nostrils."""
    muzzle=definition['body'][-1];x,y,z=muzzle[:3];w=muzzle[3];h=muzzle[4]
    outline=[(0,-.57),(-.45,-.52),(-.86,-.18),(-1,.20),(-.80,.55),(-.33,.62),(0,.47),(.33,.62),(.80,.55),(1,.20),(.86,-.18),(.45,-.52)]
    if lod==2:outline=outline[::2]
    vertices=[];coords=[];faces=[];count=len(outline)
    for scale,forward in [(1,.010),(.94,-.003),(.66,-.010),(.06,-.010)]:
        for u,v in outline:
            vertices.append((x+u*w*scale,y+forward,z+v*h*scale))
            coords.append(atlas(.5+u*.35,.5+v*.5,2))
    for row in range(3):
        for i in range(count):faces.append([row*count+i,row*count+(i+1)%count,(row+1)*count+(i+1)%count,(row+1)*count+i])
    faces.append(list(range(3*count,4*count)))
    cage.add('sculpted_rhinarium_alar_folds',vertices,faces,[[coords[i] for i in f] for f in faces],[{'head':1} for _ in vertices])
    for side in [-1,1]:
        center=Vector((x+side*w*.57,y-.010,z+h*.18));verts=[];uv=[];n=[16,12,8][lod]
        for radius,depth in [(1,0),(.74,.001),(.10,.005)]:
            for i in range(n):
                a=i*math.tau/n;verts.append(center+Vector((math.cos(a)*w*.22*radius,depth,math.sin(a)*h*.16*radius)))
                uv.append(atlas(.35,.5,2))
        faces=[]
        for row in range(2):
            for i in range(n):faces.append([row*n+i,row*n+(i+1)%n,(row+1)*n+(i+1)%n,(row+1)*n+i])
        cage.add('nostril_recess_'+str(side),verts,faces,[[uv[i] for i in f] for f in faces],[{'head':1} for _ in verts])

def animal_rig(definition):
    body=definition['body'];positions={}
    for row in body:positions.setdefault(row[5],row[:3])
    positions['neck_base']=definition.get('neck_base_origin',positions['chest'])
    if 'chest_origin' in definition:positions['chest']=definition['chest_origin']
    names=['pelvis','spine','chest',*(['neck_root'] if 'neck_root_origin' in definition else []),'neck_base','neck_01','neck_02','head'];bones=[{'name':'root','head':(0,0,0),'tail':(0,0,.15)}]
    if 'neck_root_origin' in definition:positions['neck_root']=definition['neck_root_origin']
    for name in names:
        if name not in positions:positions[name]=positions.get('head',body[-1][:3])
    for i,name in enumerate(names):
        if name not in positions:positions[name]=positions.get('head',body[-1][:3])
        head=positions[name];tail=positions[names[i+1]] if i<len(names)-1 else body[-1][:3]
        if (Vector(tail)-Vector(head)).length<.01:tail=Vector(head)+Vector((0,-.035,0))
        bones.append({'name':name,'head':head,'tail':tail,'parent':names[i-1] if i else 'root'})
    bones.append({'name':'jaw','head':positions['head'],'tail':Vector(body[-1][:3])+Vector((0,.015,-.025)),'parent':'head'})
    for side,label in [(1,'L'),(-1,'R')]:
        if 'ear' in definition:bones.append({'name':'ear_'+label,'head':(definition['ear'][0][0]*side,*definition['ear'][0][1:]),'tail':(definition['ear'][-1][0]*side,*definition['ear'][-1][1:]),'parent':'head'})
        for limb,names_limb,parent in [('front_leg',['shoulder','forearm','carpal','pastern_front','hoof_front'],'chest'),('hind_leg',['thigh','shin','hock','pastern_hind','hoof_hind'],'pelvis')]:
            if limb not in definition:continue
            path=definition[limb];indices=[0,2,4,5,6] if len(path)==7 else [0,1,2,3,4]
            scapula=limb=='front_leg' and 'scapula_origin' in definition
            if scapula:
                head=Vector(definition['scapula_origin']);head.x*=side;tail=Vector(definition['front_shoulder_joint']);tail.x*=side
                bones.append({'name':'scapula_'+label,'head':head,'tail':tail,'parent':parent})
            for i,bone in enumerate(names_limb):
                head=Vector(definition['front_shoulder_joint'] if scapula and i==0 else path[indices[i]][:3]);head.x*=side
                tail=Vector(path[indices[i+1]][:3]) if i<4 else Vector(path[-1][:3])+Vector((0,-.055,0));tail.x*=side
                bones.append({'name':bone+'_'+label,'head':head,'tail':tail,'parent':names_limb[i-1]+'_'+label if i else 'scapula_'+label if scapula else parent})
    if 'tail' in definition:
        path=definition['tail']
        for i in range(3):
            a=Vector(path[round(i*(len(path)-1)/3)][:3]);b=Vector(path[round((i+1)*(len(path)-1)/3)][:3])
            bones.append({'name':f'tail_{i+1:02}','head':a,'tail':b,'parent':'pelvis' if i==0 else f'tail_{i:02}'})
    return bones

def anatomical_weight_fields(vertices,definition):
    """Continuous volumetric fields across the fused skin, including attachments.

    Bone radii derive from anatomical cage widths. A stable normalized field
    avoids nearest-surface ownership jumps where the original cages intersect.
    """
    def blend(a,b,value):
        t=max(0,min(1,(value-a)/(b-a)));return t*t*(3-2*t)
    def field(value,anchors):
        if value<=anchors[0][0]:return {anchors[0][1]:1}
        for (a,left),(b,right) in zip(anchors,anchors[1:]):
            if value<=b:
                t=blend(a,b,value);return {left:1-t,right:t}
        return {anchors[-1][1]:1}
    groups={}
    for row in definition['body']:groups.setdefault(row[5],[]).append(row[1])
    anchors=sorted(definition.get('skin_body_anchors',[(sum(values)/len(values),name) for name,values in groups.items()]))
    body_width=max(row[3] for row in definition['body']);result=[]
    for vertex in vertices:
        point=vertex.co;label='L' if point.x>=0 else 'R';trunk=field(point.y,anchors);candidates=[]
        for limb,names in [('front_leg',['shoulder','forearm','carpal','pastern_front','hoof_front']),('hind_leg',['thigh','shin','hock','pastern_hind','hoof_hind'])]:
            rows=definition[limb];indices=[0,2,4,5,6] if len(rows)==7 else [0,1,2,3,4];path=[Vector((row[0]*(1 if label=='L' else -1),row[1],row[2])) for row in rows]
            stations=sorted(((rows[indices[i]][2]+rows[indices[min(i+1,4)]][2])*.5,name+'_'+label) for i,name in enumerate(names))
            # Keep the upper muscle attached to its shoulder/thigh; a forearm
            # contribution in rib skin causes a false crease during flexion.
            stations[-1]=(rows[indices[1]][2]+(rows[indices[0]][2]-rows[indices[1]][2])*.16,names[0]+'_'+label)
            if limb=='front_leg' and 'scapula_origin' in definition:
                stations[-1]=(rows[indices[1]][2]+.025,'shoulder_'+label)
                stations.append(((definition['scapula_origin'][2]+definition['front_shoulder_joint'][2])*.5,'scapula_'+label))
            ordered=sorted(rows,key=lambda row:row[2]);section=ordered[-1]
            for a,b in zip(ordered,ordered[1:]):
                if point.z<=b[2]:
                    t=max(0,min(1,(point.z-a[2])/(b[2]-a[2])));section=[mix(a[i],b[i],t) for i in range(5)];break
            radial=math.hypot((abs(point.x)-section[0])/section[3],(point.y-section[1])/section[4])
            support=1-blend(1.15,4.0,radial)
            if limb=='hind_leg':
                proximal=blend(rows[2][2],rows[0][2],point.z)
                support*=1-proximal*blend(rows[0][4]*.9,rows[0][4]*2.0,abs(point.y-rows[0][1]))
            candidates.append((support,rows,stations,limb))
        candidates.sort(key=lambda item:-item[0]);support,rows,stations,limb_name=candidates[0];root=rows[0];knee=rows[2] if len(rows)==7 else rows[1]
        side=blend(0,body_width*.90,abs(point.x));below=1-blend(knee[2]*.6,knee[2]*.9,point.z);side=mix(side,1,below)
        low=knee[2]*.95 if limb_name=='hind_leg' else knee[2]*.78;high=root[2]+root[4]*(2.10 if limb_name=='hind_leg' else .85)
        limb=(1-blend(low,high,point.z))*side
        # Compact support vanishes at competing limb regions, preserving
        # continuity without dropping a fifth influence by rank.
        limb*=max(0,support-candidates[1][0])
        legs=field(point.z,stations);weights={name:value*(1-limb) for name,value in trunk.items()}
        weights.update({name:value*limb for name,value in legs.items()});weights={name:value for name,value in weights.items() if value>1e-8}
        if len(weights)>4:raise ValueError('Continuous body/limb fields exceeded four influences')
        total=sum(weights.values());result.append({name:value/total for name,value in weights.items()})
        if definition.get('integrated_jaw') and point.y<-.65:
            pair=min(zip(definition['body'],definition['body'][1:]),key=lambda pair:abs(point.y-max(min(point.y,max(pair[0][1],pair[1][1])),min(pair[0][1],pair[1][1]))))
            a,b=pair;t=max(0,min(1,(point.y-a[1])/(b[1]-a[1])));cz=mix(a[2],b[2],t);depth=mix(a[4],b[4],t)
            jaw=.75*blend(.15,.8,(cz-point.z)/depth)*blend(-.65,-.73,point.y)
            result[-1]={'head':1-jaw,'jaw':jaw}
    return result

def mammal_geometry(kind,definition,lod):
    cage=Cage();skin_loft(cage,'continuous_rump_chest_neck_head',[[*row[:5],{row[5]:1}] for row in definition['body']],lod)
    for side,label in [(1,'L'),(-1,'R')]:
        ear_patch(cage,definition,side,lod);eye_patch(cage,definition['eye'],definition['eye_size'],side,lod,definition)
        for limb,names,parent in [('front_leg',['shoulder','forearm','carpal','pastern_front','hoof_front'],'chest'),('hind_leg',['thigh','shin','hock','pastern_hind','hoof_hind'],'pelvis')]:
            path=definition[limb];root=path[0]
            # Bury the skin root inside the chest/haunch. A capped limb starting
            # on the outer surface leaves a false shoulder ledge after fusion.
            sections=[[root[0]*side*.35,root[1],root[2]+root[4]*.95,root[3]*.40,root[4]*.40,{parent:1}]]
            for i,row in enumerate(path):
                if len(path)==7:
                    profile=[{0:.4,'body':.6},{0:.9,1:.1},{0:.45,1:.55},{1:.9,2:.1},{1:.45,2:.55},{2:.45,3:.55},{3:.3,4:.7}][i]
                else:profile=({0:.4,'body':.6} if i==0 else {i-1:.45,i:.55})
                weights={(parent if bone=='body' else names[bone]+'_'+label):weight for bone,weight in profile.items()}
                sections.append([row[0]*side,*row[1:],weights])
            skin_loft(cage,limb+'_'+label,sections,lod)
            foot=path[-1];split='roe_deer' in kind
            for toe in [-1,1] if split else [-1.5,-.5,.5,1.5]:
                width=.012 if split else foot[3]*.32
                x=foot[0]*side+toe*width*(1.10 if split else 1.7);y=foot[1];z=max(.018,foot[2]*.58)
                if kind=='brown_hare':length=.06;width=.011
                else:length=.052 if split else .062
                sections=[[x,y+.024,z,width*.72,z*.8,{names[-1]+'_'+label:1}],[x,y,z,width,z,{names[-1]+'_'+label:1}],[x,y-length*.65,z*.84,width*.94,z*.78,{names[-1]+'_'+label:1}],[x,y-length,z*.71,width*.50,z*.56,{names[-1]+'_'+label:1}]]
                skin_loft(cage,('cloven_hoof' if split else 'articulated_toe')+f'_{limb}_{label}_{toe}',sections,lod,2 if split else 0)
                if not split:
                    claw=[[x,y-length*.78,z*.9,width*.35,z*.24,{names[-1]+'_'+label:1}],[x,y-length-.011,z*.42,width*.08,z*.06,{names[-1]+'_'+label:1}]]
                    skin_loft(cage,f'curved_claw_{limb}_{label}_{toe}',claw,lod,2)
    tail=definition['tail'];skin_loft(cage,'tapered_tail',[[*row,{f'tail_{min(3,1+int(i/len(tail)*3)):02}':1}] for i,row in enumerate(tail)],lod,1 if 'roe_deer' in kind else 0)
    nose_patch(cage,definition,lod)
    # Lower jaw is independently weighted and meets the head at an authored lip seam.
    last=definition['body'];jaw=[]
    for row in last[-4:]:jaw.append([row[0],row[1]+.008,row[2]-row[4]*.74,row[3]*.81,row[4]*.29,{'jaw':1}])
    if not definition.get('integrated_jaw'):skin_loft(cage,'mandible_lower_lip',jaw,lod,1)
    if definition.get('antlers'):
        for side in [-1,1]:
            points=[(.061,-.565,1.139),(.083,-.53,1.23),(.108,-.49,1.335),(.126,-.43,1.43)]
            skin_loft(cage,'antler_beam_'+str(side),[[x*side,y,z,r,r*.84,{'head':1}] for (x,y,z),r in zip(points,[.019,.016,.011,.0018])],lod,5,shape='antler')
            skin_loft(cage,'antler_burr_'+str(side),[[.061*side,-.565,z,r,r*.85,{'head':1}] for z,r in [(1.125,.018),(1.134,.026),(1.145,.022),(1.158,.017)]],lod,5,shape='antler')
            for branch in [[(.079,-.535,1.21),(.08,-.62,1.29),(.064,-.67,1.345)],[(.109,-.486,1.345),(.166,-.465,1.403),(.183,-.44,1.439)]]:
                skin_loft(cage,'antler_tine_'+str(side),[[x*side,y,z,r,r,{'head':1}] for (x,y,z),r in zip(branch,[.010,.006,.0015])],lod,5,shape='antler')
    return cage

def antler_surface(cage,key,material,lod):
    """Fuse literal branch cages at their grafts, preserving editable originals."""
    obj=cage.object(key+'_continuous_antlers',material)
    obj.data.calc_loop_triangles();positions=[v.co.copy() for v in obj.data.vertices]
    triangles=[tuple(t.vertices) for t in obj.data.loop_triangles];layer=obj.data.uv_layers.active
    coordinates=[[Vector((*layer.data[i].uv,0)) for i in t.loops] for t in obj.data.loop_triangles]
    tree=BVHTree.FromPolygons(positions,triangles,all_triangles=True)
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    obj.data.remesh_voxel_size=[.0016,.0023,.0032][lod];obj.data.use_remesh_preserve_volume=True;bpy.ops.object.voxel_remesh()
    modifier=obj.modifiers.new('Continuous_branch_grafts','SMOOTH');modifier.factor=.35;modifier.iterations=3;bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.calc_loop_triangles();modifier=obj.modifiers.new('Retain_beam_tines_and_burrs','DECIMATE');modifier.ratio=min(1,[6800,3000,1100][lod]/len(obj.data.loop_triangles));bpy.ops.object.modifier_apply(modifier=modifier.name)
    while obj.data.uv_layers:obj.data.uv_layers.remove(obj.data.uv_layers[0])
    layer=obj.data.uv_layers.new(name='AnatomicalUV')
    for polygon in obj.data.polygons:
        polygon.use_smooth=True;uvs=[]
        for loop in polygon.loop_indices:
            point,_,index,_=tree.find_nearest(obj.data.vertices[obj.data.loops[loop].vertex_index].co)
            uv=barycentric_transform(point,*[positions[i] for i in triangles[index]],*coordinates[index]);uvs.append([uv.x,uv.y])
        if max(uv[0] for uv in uvs)-min(uv[0] for uv in uvs)>.125:
            # Keep source circumference seams on the antler atlas boundary.
            high=sum(uv[0]>.375 for uv in uvs)>=len(uvs)/2
            for uv in uvs:
                if high and uv[0]<.375:uv[0]=.4955
                elif not high and uv[0]>.375:uv[0]=.2545
        for loop,uv in zip(polygon.loop_indices,uvs):layer.data[loop].uv=uv
    return obj,[{'head':1} for _ in obj.data.vertices]


def unify_skin(cage,key,material,lod,definition):
    """Fuse the authored chest/haunch/limb skin and transfer its exact UV/skin fields.

    The source cages remain editable and serialized separately. This removes
    intersecting attachment caps; fine ears, eyes, toes and antlers stay authored.
    """
    is_skin=lambda name:name=='continuous_rump_chest_neck_head' or name.startswith(('front_leg_','hind_leg_'))
    skin=cage.subset(is_skin);antlers=cage.subset(lambda name:name.startswith('antler_'));extras=cage.subset(lambda name:not is_skin(name) and not name.startswith('antler_'));obj=skin.object(key+'_continuous_skin',material)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    refine=obj.modifiers.new('Smooth_authored_cage_cross_sections','SUBSURF');refine.levels=2 if lod==0 else 1;bpy.ops.object.modifier_apply(modifier=refine.name)
    obj.data.calc_loop_triangles();positions=[v.co.copy() for v in obj.data.vertices];triangles=[tuple(t.vertices) for t in obj.data.loop_triangles];uv_layer=obj.data.uv_layers.active
    triangle_uv=[[Vector((*uv_layer.data[loop].uv,0)) for loop in triangle.loops] for triangle in obj.data.loop_triangles]
    tree=BVHTree.FromPolygons(positions,triangles,all_triangles=True)
    body_height=max(row[2]+row[4] for row in definition['body']);resolution_scale=max(.35,min(1.2,body_height/.98))
    bpy.context.view_layer.objects.active=obj;obj.select_set(True);obj.data.remesh_voxel_size=[.008,.013,.014][lod]*resolution_scale;obj.data.use_remesh_preserve_volume=True;bpy.ops.object.voxel_remesh()
    smooth=obj.modifiers.new('Anatomical_attachment_blend','SMOOTH');smooth.factor=.75;smooth.iterations=4;bpy.ops.object.modifier_apply(modifier=smooth.name)
    # Broad attachment relaxation follows the authored shoulder/haunch landmarks;
    # it removes cap-like ledges without smoothing the lower-leg joints.
    attachments=obj.vertex_groups.new(name='shoulder_haunch_transition')
    for vertex in obj.data.vertices:
        weight=0
        for limb in ['front_leg','hind_leg']:
            landmark=definition[limb][0]
            radius=max(landmark[3],landmark[4])*2.4
            for side in [-1,1]:
                center=Vector((landmark[0]*side,landmark[1],landmark[2]))
                weight=max(weight,max(0,1-(vertex.co-center).length/radius)**1.2)
        if weight>0:attachments.add([vertex.index],weight,'REPLACE')
    blend=obj.modifiers.new('Broad_muscle_attachment_relaxation','SMOOTH');blend.factor=1;blend.iterations=45;blend.vertex_group=attachments.name;bpy.ops.object.modifier_apply(modifier=blend.name)
    obj.vertex_groups.remove(obj.vertex_groups['shoulder_haunch_transition'])
    if definition.get('antlers') or definition.get('inherits')=='roe_deer_buck':
        for vertex in obj.data.vertices:vertex.co=deer_face_position(vertex.co,definition['eye'])
    surface_budgets=definition.get('skin_triangle_budgets',[35000,15000,6000]);obj.data.calc_loop_triangles()
    reduce=obj.modifiers.new('Retain_anatomical_silhouette','DECIMATE');reduce.ratio=min([.58,.7,.9][lod],surface_budgets[lod]/max(1,len(obj.data.loop_triangles)));bpy.ops.object.modifier_apply(modifier=reduce.name)
    # Voxel remesh may retain a nearest-sample UV layer. Replace it explicitly;
    # otherwise glTF uses that stale render-active layer instead of our transfer.
    while obj.data.uv_layers:obj.data.uv_layers.remove(obj.data.uv_layers[0])
    layer=obj.data.uv_layers.new(name='AnatomicalUV')
    weights=anatomical_weight_fields(obj.data.vertices,definition)
    for polygon in obj.data.polygons:
        polygon.use_smooth=True
        coordinates=[]
        for loop in polygon.loop_indices:
            position=obj.data.vertices[obj.data.loops[loop].vertex_index].co;point,normal,index,distance=tree.find_nearest(position);a,b,c=[positions[i] for i in triangles[index]]
            uv=barycentric_transform(point,a,b,c,*triangle_uv[index]);coordinates.append([uv.x,uv.y])
        # Split the circumference seam instead of interpolating across the
        # unrelated ventral pigment in the middle of the atlas island.
        if max(uv[0] for uv in coordinates)-min(uv[0] for uv in coordinates)>.125:
            high=sum(uv[0]>.125 for uv in coordinates)>=len(coordinates)/2
            for uv in coordinates:
                if high and uv[0]<.125:uv[0]=.2455
                elif not high and uv[0]>.125:uv[0]=.0045
        for loop,uv in zip(polygon.loop_indices,coordinates):layer.data[loop].uv=uv
    # Fit each eyelid/cornea to the finished continuous skin, not its coarse
    # reference cage, so there is no floating metallic-looking orbital ring.
    obj.data.calc_loop_triangles();finished=BVHTree.FromPolygons([v.co.copy() for v in obj.data.vertices],[tuple(t.vertices) for t in obj.data.loop_triangles],all_triangles=True)
    segments=[24,16,10][lod];depths=[0,.0008,.0017,.0028,.0035,.0037]
    for part in extras.parts:
        if not part['name'].startswith('orbital_rim_iris_pupil_'):continue
        side=int(part['name'].rsplit('_',1)[1])
        for local,index in enumerate(range(part['first_vertex'],part['first_vertex']+part['vertices'])):
            x,y,z=extras.vertices[index];hit=finished.ray_cast(Vector((side*2,y,z)),Vector((-side,0,0)))[0]
            upper=max(0,math.sin((local%segments)*math.tau/segments))**.65
            lid=upper*[0,.0014,.0008,0,0,0][local//segments]
            if hit is not None:extras.vertices[index][0]=hit.x+side*(.0003+(depths[local//segments]+lid)*definition['eye_size']/.021)
    extra=extras.object(key+'_features',material);original_count=len(obj.data.vertices);weights.extend(extras.weights)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);extra.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
    if len(obj.data.vertices)!=original_count+len(extras.vertices):raise RuntimeError('Skin/feature join changed weight ordering')
    if antlers.vertices:
        branch_obj,branch_weights=antler_surface(antlers,key,material,lod);original_count=len(obj.data.vertices);weights.extend(branch_weights)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);branch_obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
        if len(obj.data.vertices)!=original_count+len(branch_weights):raise RuntimeError('Antler join changed weight ordering')
    return obj,weights

def build(kind,definition,rest_only=False):
    bpy.ops.wm.read_factory_settings(use_empty=True);material=paint_material(kind,definition);bones=animal_rig(definition)
    if kind=='skylark':bones=bird_bones(bones)
    rig=create_rig(kind+'_rig',bones);key='frontier_sunmeadow_'+kind;lods=[];models=[]
    for level in range(3):
        if kind=='skylark':
            cage=bird_geometry(definition,level,{'Cage':Cage,'skin_loft':skin_loft,'eye_patch':eye_patch,'atlas':atlas});obj=cage.object(key+f'_LOD{level}',material);weights=cage.weights
        else:
            cage=mammal_geometry(kind,definition,level)
            if definition.get('skin_method')=='stitched_quads':obj,weights,cage=build_stitched_skin(cage,key+f'_LOD{level}',material,level,definition,Cage,atlas,anatomical_weight_fields)
            else:obj,weights=unify_skin(cage,key+f'_LOD{level}',material,level,definition)
        tint_anatomy(obj,kind,definition)
        for vertex in obj.data.vertices:vertex.co*=definition.get('scale',1)
        # Scale skeleton and all deformation landmarks together for sex/size variants.
        if level==0 and definition.get('scale',1)!=1:
            bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
            for bone in rig.data.edit_bones:bone.head*=definition['scale'];bone.tail*=definition['scale']
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active=obj
        modifier=obj.modifiers.new('Delivery_face_tessellation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=modifier.name)
        bind_explicit_weights(obj,rig,weights)
        # The skin references its armature through the modifier; an identity
        # parent is unnecessary and triggers glTF's non-root skin warning.
        obj.parent=None
        models.append(obj)
        obj.data.calc_loop_triangles();triangles=len(obj.data.loop_triangles)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=obj
        target=ROOT/'runtime'/f'{key}_lod{level}.glb'
        bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_yup=True,export_normals=True,export_tangents=True,export_texcoords=True,export_skins=True,export_animations=False,export_vertex_color='NAME',export_vertex_color_name='AnatomicalTint',export_all_vertex_colors=False)
        points=[obj.matrix_world@vertex.co for vertex in obj.data.vertices];minimum=[min(p[i] for p in points) for i in range(3)];maximum=[max(p[i] for p in points) for i in range(3)]
        lods.append({'level':level,'model':target.name,'sha256':sha(target),'bytes':target.stat().st_size,'triangles':triangles,'vertices':len(obj.data.vertices),'bounds_blender':{'min':minimum,'max':maximum},'parts':cage.parts})
        if level==0:(ROOT/'source'/f'{key}_cage.json').write_text(json.dumps({'vertices':cage.vertices,'faces':cage.faces,'uv':cage.uv,'weights':cage.weights,'parts':cage.parts},separators=(',',':')))
        if level==0:
            control=cage.object(key+'_editable_anatomical_cage',material);control.hide_set(True);control.hide_render=True
        obj.hide_set(level!=0);obj.hide_render=level!=0
        print('FAUNA_GEOMETRY',key,level,triangles,flush=True)
    motion=[]
    if not rest_only:
        actions,motion=(bird_clips if kind=='skylark' else mammal_clips)(rig,kind,definition)
        for level,obj in enumerate(models):
            obj.hide_set(False);obj.hide_render=False;bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=obj
            target=ROOT/'runtime'/lods[level]['model']
            bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_yup=True,export_normals=True,export_tangents=True,export_texcoords=True,export_skins=True,export_animations=True,export_animation_mode='ACTIONS',export_anim_single_armature=True,export_force_sampling=True,export_frame_range=False,export_vertex_color='NAME',export_vertex_color_name='AnatomicalTint',export_all_vertex_colors=False)
            lods[level].update(sha256=sha(target),bytes=target.stat().st_size)
            obj.hide_set(level!=0);obj.hide_render=level!=0
    master=ROOT/'masters'/f'{key}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(master),compress=True)
    source_files=['source/anatomy.json',*['tools/'+name for name in ['build_fauna.py','quadruped_rig.py','motion.py','bird_geometry.py','stitched_skin.py','atlas_checks.py','surface_detail.py','texture_detail.py']]]
    (ROOT/'review'/f'{key}_build.json').write_text(json.dumps({'asset':key,'status':'anatomy-prototype-motion-pending' if rest_only else 'anatomy-and-motion-review-required','source_sha256':sha(ROOT/'source/anatomy.json'),'builder_sha256':sha(__file__),'rig_helper_sha256':sha(ROOT/'tools/quadruped_rig.py'),'motion_source_sha256':sha(ROOT/'tools/motion.py'),'source_files':{file:sha(ROOT/file) for file in source_files},'texture_sources':{file.relative_to(ROOT).as_posix():sha(file) for file in sorted((ROOT/'textures').glob(kind+'_*.png'))},'cage':(ROOT/'source'/f'{key}_cage.json').relative_to(ROOT).as_posix(),'cage_sha256':sha(ROOT/'source'/f'{key}_cage.json'),'motion':motion,'master':master.relative_to(ROOT).as_posix(),'master_sha256':sha(master),'lods':lods,'bones':bones},indent=2,default=list)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default='roe_deer_buck');parser.add_argument('--rest-only',action='store_true');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for kind in args.assets.split(','):build(kind,resolve(kind),args.rest_only)
