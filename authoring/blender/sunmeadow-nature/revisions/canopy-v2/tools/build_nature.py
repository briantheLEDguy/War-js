"""Original branch-path, leaf-outline and stratified-rock mesh authoring; no mesh primitives."""
import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
DESIGN = json.loads((ROOT / 'source/design.json').read_text())
for folder in ['masters', 'runtime', 'review', 'textures']:
    (ROOT / folder).mkdir(parents=True, exist_ok=True)

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clamp(x, lo=0, hi=1): return max(lo, min(hi, x))

def paint_surfaces():
    """Shared UV atlases: leaf veins, stem fibres, bark fissures, sediment and lichen."""
    images = {}
    size = 1024
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    u, v = xx / size, yy / size
    palettes = [(0.22,.36,.10),(.14,.28,.065),(.32,.40,.12),(.38,.35,.13),
                (.23,.39,.13),(.15,.30,.095),(.17,.32,.085),(.32,.38,.12),
                (.32,.40,.15),(.47,.43,.23),(.66,.48,.23),(.77,.60,.32),
                (.88,.83,.63),(.47,.18,.39),(.52,.085,.045),(.31,.22,.12)]
    tile_x = (xx.astype(int) // 256); tile_y = (yy.astype(int) // 256)
    fu, fv = (xx % 256) / 255, (yy % 256) / 255
    colors = np.array(palettes)[tile_y * 4 + tile_x]
    midrib = np.exp(-((fu - .5) / .016) ** 2)
    veins = np.exp(-((np.mod(fv * 7 + np.abs(fu-.5)*4, 1) - .5)/.06)**2)
    tip_dry = np.clip((fv-.78)*2.2, 0, .3)
    mottling = .023 * np.sin(fu*57+fv*31) * np.sin(fv*39-fu*13)
    leaf_color = np.clip(colors * (.88 + fv[...,None]*.19 + mottling[...,None]) +
                         (midrib*.095 + veins*.035)[...,None] + tip_dry[...,None]*np.array([.17,.09,-.015]), 0, 1)
    leaf_height = .45 + midrib*.17 + veins*.045 + .018*np.sin(fv*95)
    bark_row=np.floor(v*13);bark_cell=np.mod(v*13+.14*np.sin(u*19),1)
    bark_phase=u*19+.13*np.sin(bark_row*2.37)+.11*np.sin(v*37)+.055*np.sin(v*83)
    bark_fissure = np.maximum(0, np.cos(bark_phase*math.tau))**11
    bark_cross_joint=np.exp(-((bark_cell-.12)/.055)**2)*(.55+.45*np.sin(u*31+bark_row)**2)
    bark_plate = .5 + .085*np.sin(u*66+v*8)*np.sin(v*47) - bark_fissure*.24 - bark_cross_joint*.19
    bark_color = np.clip(np.array([.255,.21,.155]) + (bark_plate-.5)[...,None]*.39 +
                         (.022*np.sin(v*149+u*117)*np.sin(u*73-v*41))[...,None], 0, 1)
    limestone_lines = np.exp(-((np.mod(v*10+.08*np.sin(u*19),1)-.12)/.055)**2)
    limestone_grain = .027*np.sin(u*127+v*31)*np.sin(v*119-u*13)+.012*np.sin(u*683-v*241)*np.cos(v*593+u*79)
    lichen = np.clip((np.sin(u*43)*np.cos(v*37)+np.sin(u*17+v*11)-1.15)*3, 0, 1)
    stone_color = np.clip(np.array([.32,.315,.265]) + limestone_grain[...,None] - limestone_lines[...,None]*.07 + lichen[...,None]*np.array([.07,.085,.005]), 0, 1)
    fields = {'foliage': (leaf_color, leaf_height, .79), 'bark': (bark_color, bark_plate, .89),
              'limestone': (stone_color, .5 - limestone_lines*.14 + limestone_grain*.5, .91)}
    for surface, (color, height, roughness) in fields.items():
        dy, dx = np.gradient(height)
        normal = np.stack([-dx*8, -dy*8, np.ones_like(dx)], axis=-1)
        normal /= np.linalg.norm(normal, axis=-1)[...,None]
        orm = np.stack([np.clip(.96 - (1-height)*.08, 0, 1), np.clip(roughness+(height-.5)*.08, 0, 1), np.zeros_like(height)], axis=-1)
        for channel, rgb in [('basecolor', color), ('normal', normal*.5+.5), ('orm', orm)]:
            pixels = np.ones((size,size,4), dtype=np.float32); pixels[:,:,:3] = rgb
            path = ROOT/'textures'/f'{surface}_{channel}.png'
            image = bpy.data.images.new(f'sunmeadow_{surface}_{channel}', width=size, height=size, alpha=False)
            image.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
            image.pixels.foreach_set(pixels.ravel()); image.filepath_raw = str(path); image.file_format = 'PNG'; image.save()
            images[(surface, channel)] = image
    record = {'method':'Original deterministic UV-associated pigment, vein, fissure and bedding fields; no photographs, copied textures or baked illumination',
              'source_sha256': sha(__file__), 'resolution':1024,
              'tiles':dict(enumerate(['oak_sun','oak_shade','oak_late','oak_dry','ash_sun','ash_shade','hawthorn_green','hawthorn_late','grass_green','grass_dry','wheat_husk','wheat_sun','petal_ivory','knapweed','haw_red','seed_brown'])),
              'images':{str(path.relative_to(ROOT)):sha(path) for path in sorted((ROOT/'textures').glob('*.png'))}}
    (ROOT/'textures/paint_record.json').write_text(json.dumps(record, indent=2)+'\n')
    return images

def materials(images):
    result = {}
    for kind in ['foliage','bark','limestone']:
        mat = bpy.data.materials.new('sunmeadow_'+kind); mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        shader = nodes.get('Principled BSDF')
        color = nodes.new('ShaderNodeTexImage'); color.image = images[(kind,'basecolor')]
        orm = nodes.new('ShaderNodeTexImage'); orm.image = images[(kind,'orm')]
        separate = nodes.new('ShaderNodeSeparateColor'); links.new(orm.outputs['Color'], separate.inputs[0])
        normal_tex = nodes.new('ShaderNodeTexImage'); normal_tex.image = images[(kind,'normal')]
        normal = nodes.new('ShaderNodeNormalMap'); normal.inputs['Strength'].default_value = .55 if kind == 'foliage' else .8
        links.new(color.outputs['Color'], shader.inputs['Base Color']); links.new(separate.outputs['Green'], shader.inputs['Roughness']); links.new(separate.outputs['Blue'], shader.inputs['Metallic'])
        links.new(normal_tex.outputs['Color'],normal.inputs['Color']); links.new(normal.outputs[0],shader.inputs['Normal'])
        # The named glTF settings group exports the shared red-channel ambient occlusion map.
        settings = bpy.data.node_groups.get('glTF Material Output') or bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
        if not settings.interface.items_tree: settings.interface.new_socket(name='Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
        group = nodes.new('ShaderNodeGroup'); group.node_tree = settings; links.new(separate.outputs['Red'], group.inputs['Occlusion'])
        mat.use_backface_culling = kind != 'foliage'
        result[kind] = mat
    return result

class Geometry:
    def __init__(self): self.parts = {}; self.paths = []
    def add(self, part, material, vertices, faces, uv, smooth=False):
        record = self.parts.setdefault(part, {'material':material,'vertices':[],'faces':[],'uv':[],'smooth':smooth})
        start = len(record['vertices']); record['vertices'].extend([list(p) for p in vertices])
        record['faces'].extend([[start+i for i in face] for face in faces]); record['uv'].extend(uv)
    def object(self, name, collection, mats):
        objects=[]
        for part, record in self.parts.items():
            mesh=bpy.data.meshes.new(name+'_'+part); mesh.from_pydata(record['vertices'],[],record['faces']); mesh.update()
            uv=mesh.uv_layers.new(name='SunmeadowUV')
            for polygon, coords in zip(mesh.polygons,record['uv']):
                polygon.use_smooth=record['smooth']
                for loop, value in zip(polygon.loop_indices,coords): uv.data[loop].uv=value
            mesh.materials.append(mats[record['material']])
            ob=bpy.data.objects.new(name+'_'+part,mesh); collection.objects.link(ob); objects.append(ob)
        return objects

def branch(g, name, points, radii, lod, material='bark', tile=15, sides=None):
    """Uneven fluted cross-sections swept through a bent, tapered anatomical branch path."""
    sides=sides or [11,7,5][lod]; points=[Vector(p) for p in points]
    controls=[list(p) for p in points];control_radii=list(radii)
    if len(points)>2 and max(radii)>.04 and lod<2:
        refined=[];refined_radii=[];steps=3 if lod==0 else 2
        for index in range(len(points)-1):
            a=points[max(0,index-1)];b=points[index];c=points[index+1];d=points[min(len(points)-1,index+2)]
            for step in range(steps):
                t=step/steps
                refined.append((b*2+(c-a)*t+(a*2-b*5+c*4-d)*(t*t)+(-a+b*3-c*3+d)*(t*t*t))*.5)
                refined_radii.append(radii[index]*(1-t)+radii[index+1]*t)
        refined.append(points[-1]);refined_radii.append(radii[-1]);points=refined;radii=refined_radii
    verts=[]; faces=[]; uvs=[]; lengths=[0]
    for a,b in zip(points,points[1:]): lengths.append(lengths[-1]+(b-a).length)
    for i,(point,radius) in enumerate(zip(points,radii)):
        axis=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        side=axis.cross(Vector((0,1,0)))
        if side.length<.01: side=axis.cross(Vector((1,0,0)))
        side.normalize(); up=axis.cross(side).normalized()
        for j in range(sides):
            a=j*math.tau/sides
            fluting=1+.032*math.sin(a*5+i*.37)+.023*math.cos(a*3-i*.26)
            verts.append(point+(side*math.cos(a)+up*math.sin(a))*radius*fluting)
    for i in range(len(points)-1):
        for j in range(sides):
            face=[i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j]
            faces.append(face)
            coords=[(j/sides,lengths[i]/max(lengths[-1],.01)),((j+1)/sides,lengths[i]/max(lengths[-1],.01)),((j+1)/sides,lengths[i+1]/max(lengths[-1],.01)),(j/sides,lengths[i+1]/max(lengths[-1],.01))]
            uvs.append([atlas(p,tile) if material=='foliage' else p for p in coords])
    for ring,reverse in [(0,True),(len(points)-1,False)]:
        indices=[ring*sides+j for j in range(sides)]
        if reverse: indices.reverse()
        faces.append(indices)
        coords=[(.5+.45*math.cos(j*math.tau/sides),.5+.45*math.sin(j*math.tau/sides)) for j in (range(sides-1,-1,-1) if reverse else range(sides))]
        uvs.append([atlas(p,tile) if material=='foliage' else p for p in coords])
    g.add('branch_structure' if material=='bark' else 'stems',material,verts,faces,uvs,True)
    g.paths.append({'name':name,'control_points':controls,'control_radii':control_radii,'points':[list(p) for p in points],'radii':radii})

def atlas(uv, tile): return ((tile%4+.035+uv[0]*.93)/4,(tile//4+.035+uv[1]*.93)/4)

OAK=[(0,0),(-.18,.08),(-.16,.18),(-.38,.22),(-.25,.34),(-.5,.42),(-.32,.54),(-.43,.65),(-.26,.73),(-.29,.84),(0,1),(.29,.84),(.26,.73),(.43,.65),(.32,.54),(.5,.42),(.25,.34),(.38,.22),(.16,.18),(.18,.08)]
HAWTHORN=[(0,0),(-.22,.16),(-.19,.31),(-.48,.39),(-.22,.5),(-.46,.69),(-.2,.66),(-.22,.85),(0,1),(.22,.85),(.2,.66),(.46,.69),(.22,.5),(.48,.39),(.19,.31),(.22,.16)]
LANCE=[(0,0),(-.17,.15),(-.34,.35),(-.43,.5),(-.29,.7),(-.13,.87),(0,1),(.13,.87),(.29,.7),(.43,.5),(.34,.35),(.17,.15)]

def leaf(g, point, direction, length, width, tile, species, lod, twist=0):
    contour=OAK if species=='oak' else HAWTHORN if species=='hawthorn' else LANCE
    if species=='oak' and lod==0: contour=[OAK[i] for i in [0,3,4,5,6,7,8,10,12,13,14,15,16,17]]
    if species=='lance' and lod==0: contour=[LANCE[i] for i in [0,2,3,4,6,8,9,10]]
    if lod==1: contour=contour[::2]
    if lod==2: contour=[(0,0),(-.44,.35),(-.27,.74),(0,1),(.27,.74),(.44,.35)]
    forward=Vector(direction).normalized(); side=forward.cross(Vector((0,0,1)))
    if side.length<.01: side=Vector((1,0,0))
    side.normalize(); normal=side.cross(forward).normalized()
    point=Vector(point); verts=[]; coords=[]
    for x,y in contour:
        curl=(math.sin(y*math.pi)*.055 + x*x*.16 + twist*x*y)*length
        verts.append(point+side*(x*width)+forward*(y*length)+normal*curl); coords.append(atlas((x+.5,y),tile))
    verts.append(point+forward*(length*.48)+normal*(length*.105));coords.append(atlas((.5,.48),tile))
    n=len(contour); faces=[(i,(i+1)%n,n) for i in range(n)]
    g.add('shaped_foliage','foliage',verts,faces,[[coords[j] for j in f] for f in faces],True)

def blade(g, base, length, yaw, lean, width, tile, lod):
    rows=[(0,0,1),(.24,.045,.9),(.52,.19,.63),(.79,.45,.35),(1,.8,0)]
    if lod==1: rows=[rows[i] for i in [0,2,3,4]]
    if lod==2: rows=[rows[i] for i in [0,2,4]]
    direction=Vector((math.cos(yaw),math.sin(yaw),0)); side=Vector((-direction.y,direction.x,0)); base=Vector(base)
    verts=[]; coords=[]
    for t,bend,w in rows:
        center=base+Vector((0,0,length*t))+direction*(length*bend*lean)
        if w==0:
            verts.append(center);coords.append(atlas((.5,t),tile))
        else:
            for s in [-1,0,1]:
                verts.append(center+side*(width*w*s*.5)+Vector((0,0,width*.2 if s==0 else 0)));coords.append(atlas((.5+s*.48,t),tile))
    faces=[]
    for row in range(len(rows)-2):
        for side_index in range(2):
            a=row*3+side_index;faces.append((a,a+1,a+4,a+3))
    start=(len(rows)-2)*3;tip=len(verts)-1
    faces.extend([(start,start+1,tip),(start+1,start+2,tip)])
    g.add('folded_blades','foliage',verts,faces,[[coords[j] for j in f] for f in faces],True)

def tree(kind,lod):
    definition=DESIGN['assets'][kind]; g=Geometry(); rng=random.Random({'oak_pasture':318,'oak_hedgerow':926,'ash':771}[kind])
    ash=kind=='ash';branch(g,'root_to_leader',definition['trunk'],definition['radii'],lod,sides=[17,12,8][lod])
    for i,a in enumerate([-.2,.55,1.25,2.1,2.85,3.65,4.3,5.25]):
        reach=definition['radii'][0]*(1.8+(i%3)*.3)
        branch(g,f'buttress_root_{i}',[(0,0,.56),(math.cos(a)*reach*.57,math.sin(a)*reach*.57,.20),(math.cos(a)*reach,math.sin(a)*reach,.025)],[definition['radii'][0]*.29,.13,.008],lod)
    leaf_index=0
    for bi,path in enumerate(definition['boughs']):
        branch(g,f'primary_bough_{bi:02}',path,[.24 if not ash else .18,.15,.075,.021],lod)
        end=Vector(path[-1]); start=Vector(path[-2]);angle=math.atan2(end.y-start.y,end.x-start.x)
        spread=.85 if kind=='oak_hedgerow' else 1.2
        for si in range(5):
            station=.13+si*.205
            attach=Vector(path[1]).lerp(Vector(path[2]),station*2) if station<.5 else Vector(path[2]).lerp(end,(station-.5)*2)
            a=angle+(si-2)*.76+math.sin(bi*1.8+si)*.23
            upward=(.5+(si%3)*.37)*(1 if bi<len(definition['boughs'])-3 else .58)
            tip=attach+Vector((math.cos(a)*spread,math.sin(a)*spread,upward))
            bend=attach.lerp(tip,.48)+Vector((0,0,-.08 if not ash else .10))
            branch(g,f'bough_{bi}_secondary_{si}',[attach,bend,tip],[.04,.026,.008],lod,sides=[8,5,4][lod])
            for ti in range(5 if ash else 8):
                origin=bend.lerp(tip,.10+ti*(.2 if ash else .125))
                ta=a+(ti-(2 if ash else 3.5))*.72; length=.67+(ti%3)*.12
                twig=origin+Vector((math.cos(ta)*length,math.sin(ta)*length,[-.18,.4,.85,.17,.55,1.05,.24,.72][ti]))
                if lod<2: branch(g,f'terminal_{bi}_{si}_{ti}',[origin,origin.lerp(twig,.52)+Vector((0,0,.055)),twig],[.012,.008,.0025],lod,sides=4)
                for li in range(10 if not ash else 5):
                    anchor=origin.lerp(twig,.12+li*.085 if not ash else .1+li*.175)
                    orient=ta+(-1 if li%2 else 1)*(1.05+rng.uniform(-.24,.24))
                    # Mixed drooping/upright leaves expose broad surfaces from a
                    # ground camera, rather than uniformly horizontal tiers.
                    growth=Vector((math.cos(orient),math.sin(orient),rng.uniform(-1.15,1.75)))
                    leaf_length=rng.uniform(.37,.46);leaf_width=rng.uniform(.31,.38);leaf_twist=rng.uniform(-.12,.12)
                    retain=lod==0 or (lod==1 and leaf_index%3!=0) or (lod==2 and leaf_index%3==0)
                    scale=[1,1.25,1.78][lod]; leaf_index+=1
                    if not retain: continue
                    if ash:
                        rachis_end=anchor+growth*.5*scale
                        if lod<2: branch(g,'compound_leaf_rachis',[anchor,rachis_end],[.0038,.001],lod,'foliage',4,sides=3)
                        for pair in range(3):
                            p=anchor.lerp(rachis_end,.13+pair*.25)
                            for side in [-1,1]:
                                direction=Vector((math.cos(orient+side*.85),math.sin(orient+side*.85),growth.z))
                                leaf(g,p,direction,(.28-pair*.022)*scale,.17*scale,4+(li%2),'lance',lod,side*.045)
                        leaf(g,anchor.lerp(rachis_end,.77),growth,.28*scale,.16*scale,4,'lance',lod)
                    else:
                        leaf(g,anchor,growth,leaf_length*scale,leaf_width*scale,(li+bi)%3,'oak',lod,leaf_twist)
    # Short inward/recurving shoots join the outer branch fans into a crown.
    # Each cluster grows along connected paths; no canopy hulls or cards.
    for ci, cluster in enumerate(definition['crown_infill']):
        root, tip = Vector(cluster[0]), Vector(cluster[1])
        bend = root.lerp(tip, .52) + Vector((.13*math.sin(ci), -.11*math.cos(ci*1.7), .15))
        branch(g, f'crown_infill_{ci}', [root,bend,tip], [.055,.025,.004], lod)
        for shoot in range(5):
            start = bend.lerp(tip, .08 + shoot*.18)
            angle = ci*2.399 + shoot*1.37
            end = start+Vector((math.cos(angle)*.62,math.sin(angle)*.62,.30+.19*(shoot%3)))
            if lod<2: branch(g,f'infill_terminal_{ci}_{shoot}',[start,start.lerp(end,.48),end],[.009,.005,.0015],lod,sides=4)
            for li in range(12):
                anchor=start.lerp(end,.08+li*.075)
                orient=angle+(-1 if li%2 else 1)*(1.0+.14*math.sin(li*2.3))
                growth=Vector((math.cos(orient),math.sin(orient),[-1.0,.8,1.7,-.35,1.1,.2][li%6]))
                retain=lod==0 or (lod==1 and li%3!=1) or (lod==2 and li%3==0)
                if not retain:continue
                scale=[1,1.25,1.78][lod]
                if ash:
                    for pair in range(2):
                        p=anchor+growth.normalized()*(.12+pair*.14)*scale
                        for side in [-1,1]:
                            direction=Vector((math.cos(orient+side*.8),math.sin(orient+side*.8),growth.z))
                            leaf(g,p,direction,.27*scale,.17*scale,4+(li%2),'lance',lod,.04*side)
                    if lod<2:leaf(g,anchor+growth.normalized()*.35*scale,growth,.27*scale,.16*scale,4,'lance',lod)
                else:leaf(g,anchor,growth,.43*scale,.34*scale,(li+ci)%3,'oak',lod,.08*math.sin(li))
    return g

def hawthorn(lod):
    g=Geometry();rng=random.Random(371);index=0
    for stem in range(9):
        x=-1.65+stem*.41;y=.20*math.sin(stem*1.7);h=1.35+(stem%3)*.13
        base=Vector((x,y,0)); top=Vector((x+.15*math.sin(stem),y+.18,h))
        branch(g,f'interwoven_stem_{stem}',[base,base.lerp(top,.35)+Vector((.13,-.07,0)),base.lerp(top,.68)+Vector((-.1,.08,0)),top],[.07,.045,.028,.006],lod,sides=[9,6,4][lod])
        for si in range(8):
            anchor=base.lerp(top,.28+si*.09);a=si*2.38+stem*.49
            tip=anchor+Vector((math.cos(a)*.65,math.sin(a)*.5,.34))
            branch(g,f'hedge_lateral_{stem}_{si}',[anchor,anchor.lerp(tip,.55)+Vector((0,0,.09)),tip],[.018,.01,.003],lod,sides=[5,4,3][lod])
            for ti in range(4):
                p=anchor.lerp(tip,.22+ti*.23);ta=a+(ti-1.5)*.9
                end=p+Vector((math.cos(ta)*.27,math.sin(ta)*.24,.14))
                if lod==0: branch(g,'thorn_and_twig',[p,end],[.005,.001],lod,sides=3)
                for li in range(5):
                    growth=Vector((math.cos(ta+li*.8),math.sin(ta+li*.8),rng.uniform(-.25,.65)))
                    keep=lod==0 or (lod==1 and index%3!=0) or (lod==2 and index%3==0);index+=1
                    if keep: leaf(g,p.lerp(end,.2+li*.17),growth,.19*[1,1.14,1.48][lod],.16*[1,1.14,1.48][lod],6+int(li==4),'hawthorn',lod)
                if lod<2 and (si+ti)%4==0:
                    # Haws are small faceted, tapered fruits with a persistent calyx, not foliage masses.
                    for fi in range(2):
                        fruit=end+Vector((fi*.035,0,-.02));branch(g,'haw_fruit',[fruit+Vector((0,0,.02)),fruit,fruit-Vector((0,0,.025))],[.008,.022,.006],lod,'foliage',14,sides=[7,5,4][lod])
    return g

def wheat(lod):
    g=Geometry();rng=random.Random(821)
    for plant in range(72):
        x=rng.uniform(-.77,.77);y=rng.uniform(-.77,.77);h=rng.uniform(.78,1.04);a=rng.random()*math.tau
        lean=Vector((math.cos(a)*.09,math.sin(a)*.09,0)); base=Vector((x,y,0)); neck=base+Vector((0,0,h))+lean
        keep=lod==0 or (lod==1 and plant%4!=0) or (lod==2 and plant%2==0)
        if not keep: continue
        branch(g,f'wheat_culm_{plant}',[base,base+Vector((0,0,h*.42))+lean*.2,base+Vector((0,0,h*.8))+lean*.6,neck],[.006,.0055,.0045,.0035],lod,'foliage',10,sides=[5,4,3][lod])
        blade(g,base+Vector((0,0,h*.28)),.37,a,.95,.035,10,lod)
        blade(g,base+Vector((0,0,h*.61)),.30,a+2.5,1.2,.038,11,lod)
        head_end=neck+Vector((math.cos(a)*.07,math.sin(a)*.07,.15))
        branch(g,'wheat_rachis',[neck,head_end],[.005,.002],lod,'foliage',11,sides=3)
        for row in range(8 if lod<2 else 5):
            t=row/(8 if lod<2 else 5);p=neck.lerp(head_end,t)
            for side in [-1,1]:
                direction=Vector((math.cos(a+side*1.2)*.65,math.sin(a+side*1.2)*.65,1))
                leaf(g,p,direction,.047*(1-t*.25),.035*(1-t*.25),11 if row%2 else 10,'lance',min(2,lod+1))
                if lod==0 and row<7:
                    awn=p+direction.normalized()*.038
                    blade(g,awn,.055,a+side*1.2,.65,.0018,11,2)
    return g

def meadow(lod):
    g=Geometry();rng=random.Random(128)
    for tuft in range(100):
        a=rng.random()*math.tau;radius=math.sqrt(rng.random())*1.0
        base=Vector((math.cos(a)*radius,math.sin(a)*radius,0)); h=rng.uniform(.18,.53)
        for i in range(6):
            yaw=rng.random()*math.tau;length=h*rng.uniform(.65,1.25);lean=rng.uniform(.35,.85);width=rng.uniform(.009,.023)
            position=base+Vector((rng.uniform(-.035,.035),rng.uniform(-.035,.035),0))
            index=tuft*6+i
            if lod==1 and index%3==0 or lod==2 and index%3!=0: continue
            blade(g,position,length,yaw,lean,width*[1,1.10,1.4][lod],8 if i<4 else 9,lod)
        if tuft%5==0:
            seed=base+Vector((.08,.01,h+.18));branch(g,'dry_grass_seed_stem',[base,seed],[.003,.0018],lod,'foliage',9,sides=3)
            for k in range(5 if lod<2 else 3):
                p=base.lerp(seed,.72+k*.05);leaf(g,p,(.4*math.sin(k*2),.4*math.cos(k*2),1),.08,.025,15,'lance',2)
    for flower in range(22):
        a=flower*2.39996;r=.18+(.79*((flower*7)%19)/19);base=Vector((math.cos(a)*r,math.sin(a)*r,0));h=.43+(flower%5)*.065
        if lod==2 and flower%2: continue
        top=base+Vector((.035*math.sin(a),.035*math.cos(a),h))
        branch(g,'wildflower_stem',[base,base.lerp(top,.6)+Vector((-.018,.008,0)),top],[.0045,.003,.002],lod,'foliage',8,sides=[5,4,3][lod])
        for k in range(3):leaf(g,base.lerp(top,.2+k*.15),(math.cos(a+k*2),math.sin(a+k*2),.7),.13,.07,8,'lance',lod)
        daisy=flower%5==0
        count=(13 if daisy else 17) if lod==0 else (9 if daisy else 10) if lod==1 else 6
        for petal in range(count):
            yaw=petal*math.tau/count
            leaf(g,top,(math.cos(yaw),math.sin(yaw),.12 if daisy else .8),.075 if daisy else .046,.019 if daisy else .011,12 if daisy else 13,'lance',min(2,lod+1))
        for k in range(5 if lod==0 else 3):
            leaf(g,top,(math.cos(k*2.4),math.sin(k*2.4),1),.018,.012,11 if daisy else 15,'lance',2)
    return g

STONE_BLOCKS=[
    {'height':1.64,'outline':[(-2.8,-.75),(-2.40,-1.41),(-1.38,-1.80),(-.76,-1.55),(-.71,-.64),(-.98,.13),(-.86,.85),(-1.17,1.52),(-1.92,1.35),(-2.60,.44)]},
    {'height':2.28,'outline':[(-.69,-1.93),(.30,-1.73),(1.06,-1.30),(.94,-.51),(1.16,.22),(.85,1.50),(.19,1.73),(-.66,1.58),(-.89,.84),(-.84,.04),(-.58,-.71)]},
    {'height':1.96,'outline':[(1.20,-1.74),(2.27,-1.39),(2.92,-.54),(2.74,.15),(2.29,.56),(2.31,1.38),(1.65,1.76),(1.09,1.47),(1.28,.73),(1.06,.14),(1.26,-.61)]}
]
def limestone(lod):
    g=Geometry()
    # Three distinct massifs share sedimentary bedding, split by deep irregular vertical joints.
    # Boundary subdivisions add actual chips to the silhouette instead of stacking identical slabs.
    for block_index,block in enumerate(STONE_BLOCKS):
        controls=block['outline'];center=Vector((sum(p[0] for p in controls)/len(controls),sum(p[1] for p in controls)/len(controls)))
        outline=[];steps=[4,2,1][lod]
        for i,(a,b) in enumerate(zip(controls,controls[1:]+controls[:1])):
            a=Vector(a);b=Vector(b);edge=b-a;normal=Vector((-edge.y,edge.x)).normalized()
            for s in range(steps):
                t=s/steps;p=a.lerp(b,t)+normal*(.065*math.sin(i*2.4+s*1.9)*math.sin(t*math.pi));outline.append(tuple(p))
        for band in range(5):
            bottom=block['height']*band/5;top=block['height']*(band+1)/5
            count=len(outline);verts=[];faces=[];uv=[]
            for ring in range(4):
                for i,(x,y) in enumerate(outline):
                    p=Vector((x,y));to_center=center-p
                    erosion=(.045+.019*band)+[.055,0,.018,.065][ring]+.035*math.sin(i*1.83+band*2.1+block_index)
                    p+=to_center*erosion
                    p.x+=.055*math.sin(band*2.1+block_index);p.y+=.045*math.cos(band*1.7+block_index)
                    z=[bottom+.008,bottom+.054,top-.048,top-.009][ring]
                    z+=.065*math.sin(x*2.1+y*.8)+.035*math.sin(y*5.4-x*1.2)
                    if band==0 and ring==0:z=0
                    verts.append((p.x,p.y,z))
            for ring in range(3):
                for i in range(count):
                    face=(ring*count+i,ring*count+(i+1)%count,(ring+1)*count+(i+1)%count,(ring+1)*count+i)
                    faces.append(face)
                    uv.append([(i/count,verts[face[0]][2]*.42),((i+1)/count,verts[face[1]][2]*.42),((i+1)/count,verts[face[2]][2]*.42),(i/count,verts[face[3]][2]*.42)])
            # A second irregular ring and a high ridge break the exposed upper face into worn planes.
            inner=len(verts)
            for i,(x,y) in enumerate(outline):
                p=Vector((x,y)).lerp(center,.56);z=top+.075*math.sin(p.x*2.1+p.y*.9)+.055*math.cos(p.y*4.7)
                verts.append((p.x,p.y,z))
            for i in range(count):
                face=(3*count+i,3*count+(i+1)%count,inner+(i+1)%count,inner+i);faces.append(face)
                uv.append([((verts[j][0]+3)/6,(verts[j][1]+2)/4) for j in face])
            hub=len(verts);verts.append((center.x+.025,center.y-.06,top+.11))
            for i in range(count):
                face=(inner+i,inner+(i+1)%count,hub);faces.append(face);uv.append([((verts[j][0]+3)/6,(verts[j][1]+2)/4) for j in face])
            faces.append(tuple(reversed(range(count))));uv.append([((verts[j][0]+3)/6,(verts[j][1]+2)/4) for j in reversed(range(count))])
            g.add(f'fracture_massif_{block_index}_bed_{band}','limestone',verts,faces,uv)
    # Detached chips follow authored fracture locations; remain geological parts, not primitive scatter.
    for chip,(x,y,s) in enumerate([(-2.65,-1.35,.26),(2.67,.61,.32),(1.68,-1.86,.27),(-1.50,1.70,.29)]):
        verts=[(x-s,y-s*.4,0),(x+s*.7,y-s*.7,.02),(x+s,y+s*.2,0),(x-s*.4,y+s*.7,0),(x-s*.4,y-s*.1,.23),(x+s*.4,y+s*.1,.18)]
        faces=[(0,1,5,4),(1,2,5),(2,3,4,5),(3,0,4),(3,2,1,0)]
        g.add('fracture_chips','limestone',verts,faces,[[((verts[j][0]+3)/6,(verts[j][1]+2)/4) for j in f] for f in faces])
    return g

def build(kind, mats):
    key='frontier_sunmeadow_'+kind
    for ob in list(bpy.data.objects): bpy.data.objects.remove(ob,do_unlink=True)
    for col in list(bpy.data.collections): bpy.data.collections.remove(col)
    lods=[];collections=[];all_objects=[]
    for level in range(3):
        geometry=tree(kind,level) if kind in ['oak_pasture','oak_hedgerow','ash'] else globals()[kind](level)
        collection=bpy.data.collections.new(f'{key}_LOD{level}');bpy.context.scene.collection.children.link(collection);collections.append(collection)
        objects=geometry.object(f'{key}_LOD{level}',collection,mats);all_objects.extend(objects)
        if level==0:
            path_record={'asset':key,'design_sha256':sha(ROOT/'source/design.json'),'paths':geometry.paths,'parts':{name:{'vertices':len(part['vertices']),'faces':len(part['faces'])} for name,part in geometry.parts.items()}}
            (ROOT/'source'/f'{key}_authored_paths.json').write_text(json.dumps(path_record,indent=2)+'\n')
        bpy.ops.object.select_all(action='DESELECT')
        for ob in objects:ob.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        # Join delivery parts by material; the editable master retains named source pieces per LOD.
        copies=[]
        for ob in objects:
            copy=ob.copy();copy.data=ob.data.copy();bpy.context.scene.collection.objects.link(copy);copies.append(copy)
        bpy.ops.object.select_all(action='DESELECT')
        for ob in copies:ob.select_set(True)
        bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();delivery=bpy.context.object;delivery.name=f'{key}_LOD{level}'
        modifier=delivery.modifiers.new('Authored_face_triangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=modifier.name)
        delivery.data.calc_loop_triangles()
        bounds=[delivery.matrix_world@Vector(v) for v in delivery.bound_box]
        low=[min(v[i] for v in bounds) for i in range(3)];high=[max(v[i] for v in bounds) for i in range(3)]
        filename=f'{key}_lod{level}.glb';path=ROOT/'runtime'/filename
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_texcoords=True,export_normals=True,export_tangents=True,export_materials='EXPORT',export_extras=True)
        lods.append({'level':level,'model':filename,'sha256':sha(path),'bytes':path.stat().st_size,'triangles':len(delivery.data.loop_triangles),'materials':len({m.name for m in delivery.data.materials}),
                     'bounds_blender':{'min':low,'max':high},'bounds_runtime':{'min':[low[0],low[2],-high[1]],'max':[high[0],high[2],-low[1]]}})
        bpy.data.objects.remove(delivery,do_unlink=True)
        print('NATURE_LOD',key,level,lods[-1]['triangles'],flush=True)
    for col in collections[1:]: col.hide_viewport=True;col.hide_render=True
    for image in bpy.data.images:
        if image.source=='FILE' or image.name.startswith('sunmeadow_'):
            try:image.pack()
            except RuntimeError:pass
    bpy.ops.object.select_all(action='DESELECT')
    master=ROOT/'masters'/f'{key}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(master),compress=True)
    record={'asset':key,'name':DESIGN['assets'][kind]['name'],'source_sha256':sha(ROOT/'source/design.json'),'builder_sha256':sha(__file__),
            'paint_record_sha256':sha(ROOT/'textures/paint_record.json'),'master':str(master.relative_to(ROOT)),'master_sha256':sha(master),'lods':lods,
            'limitations':['Static vegetation; no wind rig or seasonal growth simulation.','Opaque double-sided shaped leaves; deliberate open botanical surfaces.','Leaf sizes are stylized for readable game silhouettes.','Visual acceptance and runtime publication are separate from successful export.']}
    (ROOT/'review'/f'{key}_build.json').write_text(json.dumps(record,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default=','.join(DESIGN['assets']));args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats=materials(paint_surfaces())
    for kind in args.assets.split(','):build(kind,mats)
