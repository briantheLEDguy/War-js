"""Detailed, opaque-leaf city planting; editable masters and three runtime LODs."""
import bpy
import math
import random
import hashlib
import json
from pathlib import Path
from mathutils import Vector
import numpy as np

WORK = Path(__file__).resolve().parents[1]
for folder in ['sources', 'runtime', 'review', 'textures']:
    (WORK / folder).mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
# Retain 2K surface masters; modeled leaves/petals supply the silhouette detail.
rng = np.random.default_rng(811)
y, x = np.mgrid[0:2048, 0:2048]
grain = rng.normal(0, .023, (2048, 2048)) + .018*np.sin(x*.24 + 4*np.sin(y*.014))
images = {}
for name in ['color', 'roughness', 'normal']:
    pixels = np.ones((2048, 2048, 4), dtype=np.float32)
    if name == 'color':
        pixels[:, :, :3] = np.clip(.83 + grain[:, :, None], 0, 1)
    elif name == 'roughness':
        pixels[:, :, :3] = np.clip(.78 + grain[:, :, None]*2, 0, 1)
    else:
        dy, dx = np.gradient(grain)
        pixels[:, :, 0] = .5 - dx*1.1
        pixels[:, :, 1] = .5 - dy*1.1
        pixels[:, :, 2] = 1
    im = bpy.data.images.new('aegis_garden_'+name, width=2048, height=2048)
    im.colorspace_settings.name = 'sRGB' if name == 'color' else 'Non-Color'
    im.pixels.foreach_set(pixels.ravel())
    im.filepath_raw = str(WORK/'textures'/f'{name}.png')
    im.file_format = 'PNG'
    im.save()
    images[name] = im

M = {}
for name, color in {'bark':(.18,.095,.045), 'leaf':(.11,.25,.055), 'leaf_light':(.23,.36,.075),
                    'stone':(.38,.40,.31), 'soil':(.09,.055,.03), 'rose':(.48,.045,.09),
                    'ivory':(.85,.76,.43), 'violet':(.25,.13,.48)}.items():
    mat = bpy.data.materials.new('aegis_garden_'+name)
    mat.diffuse_color = (*color,1)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    tex = nodes.new('ShaderNodeTexImage'); tex.image = images['color']
    multiply = nodes.new('ShaderNodeMixRGB'); multiply.blend_type = 'MULTIPLY'
    multiply.inputs[0].default_value = 1; multiply.inputs[2].default_value = (*color,1)
    # glTF exports the base color factor multiplied by the shared color texture.
    links.new(tex.outputs['Color'], multiply.inputs[1]); links.new(multiply.outputs[0],bsdf.inputs['Base Color'])
    rough = nodes.new('ShaderNodeTexImage'); rough.image = images['roughness']
    links.new(rough.outputs['Color'], bsdf.inputs['Roughness'])
    normal = nodes.new('ShaderNodeTexImage'); normal.image = images['normal']
    bump = nodes.new('ShaderNodeNormalMap'); bump.inputs['Strength'].default_value = .22
    links.new(normal.outputs['Color'], bump.inputs['Color']); links.new(bump.outputs[0],bsdf.inputs['Normal'])
    mat.use_backface_culling = name not in ['leaf','leaf_light','rose','ivory','violet']
    M[name] = mat

def mesh(name, verts, faces, material, smooth=False):
    data = bpy.data.meshes.new(name); data.from_pydata(verts, [], faces); data.update()
    ob = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(ob)
    data.materials.append(M[material])
    for face in data.polygons: face.use_smooth = smooth
    return ob

def tube(name, points, radii, material='bark', sides=9):
    verts, faces = [], []
    for i, (point,radius) in enumerate(zip(points,radii)):
        direction = Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
        q = direction.to_track_quat('Z','Y')
        for j in range(sides):
            a = j*2*math.pi/sides
            verts.append(Vector(point)+q@Vector((radius*math.cos(a),radius*math.sin(a),0)))
    for i in range(len(points)-1):
        for j in range(sides):
            k=i*sides+j; n=i*sides+(j+1)%sides
            faces.append((k,n,n+sides,k+sides))
    faces.extend([tuple(reversed(range(sides))),tuple(range((len(points)-1)*sides,len(points)*sides))])
    return mesh(name,verts,faces,material,True)

def box(name, pos, size, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    ob=bpy.context.object; ob.name=name; ob.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    ob.data.materials.append(M[material])
    mod=ob.modifiers.new('worn_masonry_edges','BEVEL'); mod.width=.025; mod.segments=3
    return ob

def leaves(name, samples, material='leaf'):
    verts, faces=[],[]
    for point, length, width, yaw, tilt in samples:
        # Six triangles around a raised midrib form a curled lance/heart leaf.
        q=Vector((math.cos(yaw)*math.cos(tilt),math.sin(yaw)*math.cos(tilt),math.sin(tilt))).to_track_quat('Y','Z')
        shape=[(0,0,0),(-width*.5,length*.35,0),(-width*.36,length*.7,0),(0,length,.025),
               (width*.36,length*.7,0),(width*.5,length*.35,0),(0,length*.48,width*.15)]
        start=len(verts)
        verts.extend(Vector(point)+q@Vector(v) for v in shape)
        faces.extend(tuple(start+k for k in f) for f in [(0,1,6),(1,2,6),(2,3,6),(3,4,6),(4,5,6),(5,0,6)])
    return mesh(name,verts,faces,material)

def linden():
    r=random.Random(291)
    tube('twisting_fluted_linden_trunk',[(0,0,0),(.05,-.05,1.5),(-.12,0,3),(.08,.12,4.6),(0,0,6.8)],[.32,.25,.2,.14,.035],sides=14)
    for i in range(7):
        a=i*2*math.pi/7
        tube('exposed_root',[(0,0,.24),(.5*math.cos(a),.5*math.sin(a),.08),(.72*math.cos(a),.72*math.sin(a),0)],[.12,.065,.015])
    samples=[[],[]]
    for branch in range(15):
        a=branch*2.39996; h=3.1+(branch%5)*.63
        reach=2.15 if branch<10 else 1.5
        end=Vector((math.cos(a)*reach,math.sin(a)*reach,h+1.5))
        tube('forked_linden_bough',[(0,0,h),end*.55+Vector((0,0,h*.45)),end],[.12,.065,.018])
        for j in range(5):
            t=a+(j-2)*.38
            tip=end+Vector((math.cos(t)*.55,math.sin(t)*.55,.22+(j%2)*.35))
            tube('terminal_twigs',[end,tip],[.02,.006],sides=5)
        for j in range(70):
            direction=Vector((r.uniform(-1,1),r.uniform(-1,1),r.uniform(-.6,.8)))
            point=end+direction*.85
            point.x=max(-2.65,min(2.65,point.x)); point.y=max(-2.65,min(2.65,point.y))
            samples[j%2].append((point,.32+r.random()*.12,.21+r.random()*.08,r.random()*math.tau,r.uniform(-.7,.8)))
    for index, material in enumerate(['leaf','leaf_light']): leaves('individual_linden_leaves',samples[index],material)

def cypress():
    r=random.Random(440)
    tube('cypress_fluted_trunk',[(0,0,0),(.04,0,3),(-.06,.05,6),(0,0,8.8)],[.27,.17,.07,.012],sides=14)
    samples=[[],[]]
    for i in range(42):
        h=2.8+i*.14; a=i*2.39996; radius=.86*(1-(h-2.8)/7.3)
        start=Vector((0,0,h)); end=Vector((radius*math.cos(a),radius*math.sin(a),h+.45))
        tube('ascending_cypress_branch',[start,end],[.06*(1-i/50),.008],sides=6)
        for j in range(30):
            point=end+Vector((r.uniform(-.32,.32),r.uniform(-.32,.32),r.uniform(-.3,.55)))
            samples[j%2].append((point,.36,.11,a+r.uniform(-1,1),r.uniform(.15,1.15)))
    for index, material in enumerate(['leaf','leaf_light']): leaves('cypress_scale_sprays',samples[index],material)

def flowerbed(rose):
    r=random.Random(870 if rose else 900)
    box('dark_earth',(0,0,.15),(3.7,1.7,.3),'soil')
    for side in [-1,1]:
        for i in range(8):box('individual_curb_stones',(-1.75+i*.5,side*.9,.19),(.49,.2,.38),'stone')
        for i in range(3):box('end_curb_stones',(side*1.9,-.5+i*.5,.19),(.2,.49,.38),'stone')
    greens=[[],[]]; petals=[[],[]]
    for i in range(42):
        px=r.uniform(-1.66,1.66); py=r.uniform(-.67,.67); h=r.uniform(.62,.9) if rose else r.uniform(.48,.72)
        tube('flower_stem',[(px,py,.28),(px+.04,py,h)],[.012,.005],'leaf',sides=5)
        for j in range(5):
            a=r.random()*math.tau
            greens[j%2].append(((px,py,.3+j*.07),.22,.14,a,.25))
        for tier in range(3 if rose else 1):
            for j in range(8 if rose else 6):
                a=j*math.tau/(8 if rose else 6)+tier*.45
                radius=.06+tier*.022 if rose else .018
                petals[0].append(((px+math.cos(a)*radius,py+math.sin(a)*radius,h+.022*tier),.12-tier*.015,.105,a,.45+tier*.27))
        petals[1].append(((px,py,h+.055),.045,.06,0,.1))
    for index, material in enumerate(['leaf','leaf_light']):leaves('garden_foliage',greens[index],material)
    leaves('layered_rose_petals' if rose else 'six_petalled_violets',petals[0],'rose' if rose else 'violet')
    leaves('golden_flower_centres',petals[1],'ivory')

BUILDERS={'garden_linden':linden,'garden_cypress':cypress,'flowerbed_roses':lambda:flowerbed(True),'flowerbed_violets':lambda:flowerbed(False)}
report=[]
for kind, build in BUILDERS.items():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    build()
    bpy.data.libraries.write(str(WORK/'sources'/f'{kind}.blend'),{bpy.context.scene},fake_user=True,compress=True)
    bpy.ops.object.select_all(action='SELECT'); bpy.context.view_layer.objects.active=next(iter(bpy.context.selected_objects))
    bpy.ops.object.convert(target='MESH'); bpy.ops.object.join()
    source=bpy.context.object; source.name='aegis_'+kind
    bpy.context.scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.002)
    bpy.ops.object.mode_set(mode='OBJECT')
    bounds=[source.matrix_world@Vector(c) for c in source.bound_box]
    envelope=[round(max(v[i] for v in bounds)-min(v[i] for v in bounds),3) for i in [0,1,2]]
    lods=[]
    for level,ratio in enumerate([1,.56,.28]):
        ob=source.copy(); ob.data=source.data.copy(); bpy.context.collection.objects.link(ob)
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active=ob
        if level:
            # Keep structural wood and the stone border intact; reduce only planting.
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.separate(type='MATERIAL'); bpy.ops.object.mode_set(mode='OBJECT')
            parts=list(bpy.context.selected_objects)
            for part in parts:
                bpy.context.view_layer.objects.active=part
                material=part.data.materials[0].name
                if material not in ['aegis_garden_bark','aegis_garden_stone','aegis_garden_soil']:
                    mod=part.modifiers.new('distance_reduction','DECIMATE'); mod.ratio=ratio
                    bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.context.view_layer.objects.active=parts[0]; bpy.ops.object.join(); ob=bpy.context.object
        mod=ob.modifiers.new('triangles','TRIANGULATE'); bpy.ops.object.modifier_apply(modifier=mod.name)
        ob.data.calc_loop_triangles()
        model='prop_aegis_'+kind+(f'_lod{level}' if level else '')+'.glb'; file=WORK/'runtime'/model
        bpy.ops.export_scene.gltf(filepath=str(file),export_format='GLB',use_selection=True,export_yup=True,export_texcoords=True,export_normals=True,export_tangents=True)
        lods.append({'level':level,'model':model,'triangles':len(ob.data.loop_triangles),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
        bpy.data.objects.remove(ob,do_unlink=True)
    report.append({'kind':kind,'envelope':envelope,'lods':lods})
    print('GARDEN_COMPLETE',kind,envelope,flush=True)
(WORK/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
