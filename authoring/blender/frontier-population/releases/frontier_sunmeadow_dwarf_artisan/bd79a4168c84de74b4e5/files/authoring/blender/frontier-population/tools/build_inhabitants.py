"""Fitted regional clothing and anatomy derivatives from retained local body meshes.

Drafts remain outside runtime publication. All added geometry comes from authored
garment patches, swept construction paths and shaped component profiles.
"""
import bpy
import bmesh
import math
import json
import hashlib
import os
import sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

WORK = Path(__file__).resolve().parents[1]
ROOT = WORK.parents[2]
sys.path.insert(0, str(ROOT / 'scripts/blender-character-pipeline/blender'))
from canonical_animation_pack import attach_canonical_animation_pack
sys.path.insert(0, str(WORK / 'tools'))
from tailored_clothing import tailor
from tailored_locomotion import fit_locomotion, refine_sole_contacts
from artisan_equipment import dress_artisan
from export_tangents import repair_export_tangents
from apron_clearance import fit_apron_clearance
from apron_details import make_apron_details
from surface_bindings import ClothSurface, bind_detail
from workwear_finish import sew_work_shirt, finish_apron
from authored_artisan_head import AUTHORING_INPUTS

for folder in ['sources', 'runtime', 'textures', 'review']:
    (WORK / folder).mkdir(parents=True, exist_ok=True)

CAST = {
    'dwarf_artisan': {'foundation': 'civic_humanoid_v2_m', 'race': 'dwarf', 'cloth': (.17, .23, .27), 'leather': (.24, .105, .046)},
    'empire_farmer': {'foundation': 'civic_humanoid_v2_m', 'race': 'empire', 'cloth': (.46, .39, .25), 'leather': (.19, .09, .043)},
    'empire_herbalist': {'foundation': 'civic_humanoid_v2_f', 'race': 'empire', 'cloth': (.19, .29, .22), 'leather': (.23, .105, .055)},
    'high_elf_scout': {'foundation': 'civic_humanoid_v2_m', 'race': 'high_elf', 'cloth': (.10, .20, .15), 'leather': (.16, .13, .07)},
    'greenskin_peat_worker': {'foundation': 'mire_brutish_v1_m', 'race': 'greenskin', 'cloth': (.22, .19, .105), 'leather': (.14, .08, .045)},
    'dark_elf_supply_officer': {'foundation': 'civic_humanoid_v2_f', 'race': 'dark_elf', 'cloth': (.115, .13, .20), 'leather': (.105, .062, .095)},
}

def digest(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def build_provenance(source,master,recipe,body):
    inputs={Path(__file__).resolve(),source.resolve(),master.resolve(),
            (WORK/'foundations'/f"{recipe['foundation']}.quad-surface.json.gz").resolve(),
            (ROOT/'scripts/blender-character-pipeline/data/body-families/canonical-animation-pack.json').resolve()}
    inputs.update(AUTHORING_INPUTS)
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if not filename:continue
        path=Path(filename).resolve()
        if path.suffix=='.py' and path.is_relative_to(ROOT):inputs.add(path)
    images={node.image for mat in body.data.materials if mat and mat.use_nodes
            for node in mat.node_tree.nodes if node.type=='TEX_IMAGE' and node.image}
    packed=[]
    for image in sorted(images,key=lambda image:image.name):
        path=Path(bpy.path.abspath(image.filepath_raw)).resolve() if image.filepath_raw else None
        if path and path.is_file() and path.is_relative_to(ROOT):inputs.add(path)
        if not image.packed_file:raise RuntimeError('Material image is not retained in master: '+image.name)
        data=bytes(image.packed_file.data)
        packed.append({'name':image.name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    files=[]
    for path in sorted(inputs):
        data=path.read_bytes()
        files.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    return files,packed

def _body_morphology(p, race):
    x, y, z = p
    if race == 'dwarf':
        levels = [(0, 0), (.12, .105), (.55, .37), (1.0, .70), (1.55, 1.075), (1.86, 1.38)]
        section=next((i for i in range(len(levels)-1) if z<=levels[i+1][0]),len(levels)-2)
        slopes=[(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(levels,levels[1:])]
        derivatives=[slopes[0]]+[2*a*b/(a+b) for a,b in zip(slopes,slopes[1:])]+[slopes[-1]]
        a,b=levels[section],levels[section+1];h=b[0]-a[0];t=(z-a[0])/h
        mapped=(2*t**3-3*t*t+1)*a[1]+(t**3-2*t*t+t)*h*derivatives[section]+(-2*t**3+3*t*t)*b[1]+(t**3-t*t)*h*derivatives[section+1]
        head = max(0, min(1, (z - 1.5) / .14))
        head=head*head*(3-2*head)
        nose=math.exp(-((x/.037)**2+((z-1.69)/.040)**2))*max(0,min(1,(-y-.145)/.025))
        brow=math.exp(-((z-1.751)/.021)**2)*max(0,min(1,(-y-.145)/.025))
        return Vector((x * (1.27 - .07 * head), y * (1.28 - .12 * head)-.015*nose-.006*brow, mapped))
    if race in ('high_elf', 'dark_elf'):
        # Preserve joints and facial volume while changing the torso/limb proportions together.
        slim = .94 if race == 'high_elf' else .96
        return Vector((x * slim, y * .97, z * (1.055 if race == 'high_elf' else 1.025)))
    return Vector(p)


def morphology(p, race):
    result = _body_morphology(p, race)
    if race != 'dwarf': return result
    # The stature warp is appropriate for the trunk but would squash the exposed
    # arm in world Z. Transport its retained anatomical section along the morphed
    # limb instead. This same mapping fits skin, garment cuffs and finger joints.
    side = 1 if p[0] >= 0 else -1
    elbow = Vector((side * .3750006557, -.0191267282, 1.2762502432))
    wrist = Vector((side * .5159764290, -.2193496078, 1.1416108608))
    axis = wrist - elbow
    along = (Vector(p) - elbow).dot(axis) / axis.length_squared
    center = elbow + axis * along
    offset = Vector(p) - center
    if along <= .10 or along >= 1.85 or offset.length >= .18: return result
    blend = max(0, min(1, (along - .10) / .30))
    blend = blend * blend * (3 - 2 * blend)
    radial = max(0, min(1, (.18 - offset.length) / .05))
    blend *= radial * radial * (3 - 2 * radial)
    rotation = axis.rotation_difference(_body_morphology(wrist, race) - _body_morphology(elbow, race))
    rounded = _body_morphology(center, race) + rotation @ (offset * 1.28)
    return result.lerp(rounded, blend)

def material(name, color, rough=.8, metal=0, textile=False):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = rough
    shader.inputs['Metallic'].default_value = metal
    if textile:
        size = 1024; yy, xx = np.mgrid[0:size, 0:size]
        mottling=(np.sin(xx*.028+np.sin(yy*.009))*np.cos(yy*.037)+np.sin(xx*.051-yy*.019))*.5
        if 'tool_ash' in name:
            grain=np.sin(xx*.065+1.8*np.sin(yy*.008))+ .3*np.sin(xx*.29+np.sin(yy*.017))
            relief=.18*grain; pigment=.89+.10*grain+.025*mottling
            roughness=np.clip(rough+.03*grain,.5,.92)
        elif 'leather' in name:
            grain=np.sin(xx*.72+np.sin(yy*.23)*2)*np.sin(yy*.83+np.cos(xx*.21))
            relief=.34*grain+.13*np.sin(xx*.12+yy*.17)+.08*mottling
            pigment=.91+.065*mottling+.025*grain
            roughness=np.clip(rough+.06*mottling+.04*grain,.35,.94)
        elif 'woven_linen' in name:
            # Coarse work linen has readable paired threads and dye variation;
            # the fine fibrils sit beneath the weave, not over the whole shape.
            warp=np.cos(xx*math.pi/4+.20*np.sin(yy*.017))
            weft=np.cos(yy*math.pi/4+.18*np.sin(xx*.023))
            relief=.27*(warp+weft)+.14*warp*weft
            pigment=.965+.012*mottling+.023*warp+.018*weft
            roughness=np.clip(rough+.022*(warp+weft),.82,.98)
        else:
            warp=np.cos(xx*math.pi/2+.1*np.sin(yy*.035))
            weft=np.cos(yy*math.pi/2+.1*np.sin(xx*.027))
            relief=.20*(warp+weft)+.10*warp*weft
            pigment=.97+.012*mottling+.006*(warp+weft)
            roughness=np.clip(rough+.018*mottling,.5,.99)
        gy,gx=np.gradient(relief)
        normal=np.stack((-gx*.65,-gy*.65,np.ones_like(gx)),axis=-1)
        normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
        for channel,data in [('basecolor',np.array(color)[None,None,:]*pigment[:,:,None]),
                             ('normal',normal*.5+.5),('roughness',np.repeat(roughness[:,:,None],3,axis=2))]:
            pixels=np.ones((size,size,4),dtype=np.float32);pixels[:,:,:3]=data
            image=bpy.data.images.new(name+'_'+channel,width=size,height=size,alpha=True)
            image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
            image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(WORK/'textures'/(image.name+'.png'))
            image.file_format='PNG';image.save();image.pack()
            node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
            if channel=='normal':
                normal_node=mat.node_tree.nodes.new('ShaderNodeNormalMap');normal_node.uv_map='UVMap'
                normal_node.inputs['Strength'].default_value=.5 if 'woven_linen' in name else .3
                mat.node_tree.links.new(node.outputs['Color'],normal_node.inputs['Color'])
                mat.node_tree.links.new(normal_node.outputs['Normal'],shader.inputs['Normal'])
            else:mat.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    return mat

def build(kind, recipe):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source = WORK / 'foundations' / f"body_{recipe['foundation']}.glb"
    bpy.ops.import_scene.gltf(filepath=str(source))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    rig.animation_data_clear(); rig.data.pose_position = 'REST'
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    body = max(meshes, key=lambda o: len(o.data.vertices))
    # The old body export made the eye helper/cornea opaque. Keep the real iris
    # surface; remove only the reserved helper UV patch from this derivative.
    for eye in [o for o in meshes if 'high-poly' in o.name]:
        helper_faces={f.index for f in eye.data.polygons if all(eye.data.uv_layers.active.data[i].uv.x>.85
                      and eye.data.uv_layers.active.data[i].uv.y<.15 for i in f.loop_indices)}
        bm=bmesh.new();bm.from_mesh(eye.data);bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index in helper_faces],context='FACES')
        bm.to_mesh(eye.data);bm.free()
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [rig, *meshes]: ob.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    race = recipe['race']
    for ob in meshes:
        for v in ob.data.vertices: v.co = morphology(v.co, race)
    if race=='dwarf':
        body.data.update()
        names={group.index:group.name for group in body.vertex_groups}
        normals=[vertex.normal.copy() for vertex in body.data.vertices]
        for vertex in body.data.vertices:
            palm=sum(g.weight for g in vertex.groups if names[g.group].startswith('hand_'))
            fingers=sum(g.weight for g in vertex.groups if names[g.group].startswith(('thumb','index','middle','ring','pinky')))
            vertex.co+=normals[vertex.index]*(.0045*palm+.0018*fingers)
        for mat in body.data.materials:
            shader=mat.node_tree.nodes.get('Principled BSDF') if mat.use_nodes else None
            if shader and shader.inputs['Base Color'].is_linked:
                source_node=shader.inputs['Base Color'].links[0].from_node
                if source_node.type=='TEX_IMAGE' and source_node.image:
                    source_node.image=source_node.image.copy();source_node.image.name='artisan_hand_skin'
                    pixels=np.array(source_node.image.pixels[:],dtype=np.float32).reshape(-1,4)
                    pixels[:,:3]*=np.array([.80,.72,.64])[None,:]
                    source_node.image.pixels.foreach_set(pixels.ravel());source_node.image.pack()
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:
        bone.head = morphology(bone.head, race); bone.tail = morphology(bone.tail, race)
    bpy.ops.object.mode_set(mode='OBJECT'); rig.data.pose_position = 'POSE'
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'; bone.rotation_quaternion = (1, 0, 0, 0)
        bone.location = (0, 0, 0); bone.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    scale_z = morphology((0, 0, 1), race).z
    mapped = lambda z: morphology((0, 0, z), race).z
    body.data.update()
    kd = KDTree(len(body.data.vertices))
    for v in body.data.vertices: kd.insert(v.co, v.index)
    kd.balance()
    group_names = {g.index: g.name for g in body.vertex_groups}
    weights = []
    for v in body.data.vertices:
        influences = [(group_names[g.group], g.weight) for g in v.groups if group_names[g.group] in rig.data.bones]
        weights.append(sorted(influences, key=lambda entry: -entry[1])[:4])
    cloth = material(kind + '_woven_linen', recipe['cloth'], .92, textile=True)
    trousers = material(kind + '_wool', tuple(c * .65 for c in recipe['cloth']), .95, textile=True)
    leather = material(kind + '_worked_leather', recipe['leather'], .72, textile=True)
    seam = material(kind + '_linen_seam', (.39, .30, .19), .94)
    iron = material(kind + '_forged_iron', (.13, .15, .16), .42, .82)
    brass = material(kind + '_handled_brass', (.47, .29, .105), .4, .78)
    hair = material(kind + '_hair', (.075, .033, .017) if race == 'dwarf' else (.15, .105, .055), .85)
    wood = material(kind + '_tool_ash', (.28, .17, .072), .8,textile=True)
    authored = []

    def make(name, verts, faces, mat, bone=None, custom_weights=None):
        mesh = bpy.data.meshes.new(name); mesh.from_pydata(verts, [], faces); mesh.update(); mesh.materials.append(mat)
        ob = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(ob)
        for face in mesh.polygons: face.use_smooth = True
        uv = mesh.uv_layers.new(name='UVMap')
        for face in mesh.polygons:
            axis = max(range(3), key=lambda a: abs(face.normal[a]))
            axes = [(1, 2), (0, 2), (0, 1)][axis]
            for li in face.loop_indices:
                p = mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv = (p[axes[0]] * 2, p[axes[1]] * 2)
        groups = {}
        for i, p in enumerate(verts):
            values = [(bone, 1)] if bone else custom_weights[i] if custom_weights else weights[kd.find(Vector(p))[1]]
            total = sum(w for _, w in values)
            for name, weight in values:
                if name not in groups: groups[name] = ob.vertex_groups.new(name=name)
                groups[name].add([i], weight / total, 'REPLACE')
        mod = ob.modifiers.new('Fitted_body_rig', 'ARMATURE'); mod.object = rig
        authored.append(ob); return ob

    def sweep(name, points, radii, mat, bone=None, sides=8):
        verts = []; uv_faces = []
        for i, p in enumerate(points):
            tangent = Vector(points[min(len(points)-1, i+1)]) - Vector(points[max(0, i-1)])
            rotation = tangent.to_track_quat('Z', 'Y')
            for j in range(sides):
                angle = j * math.tau / sides
                verts.append(tuple(Vector(p) + rotation @ Vector((math.cos(angle) * radii[i], math.sin(angle) * radii[i], 0))))
        faces = [(i*sides+j, i*sides+(j+1)%sides, (i+1)*sides+(j+1)%sides, (i+1)*sides+j)
                 for i in range(len(points)-1) for j in range(sides)]
        faces.extend([tuple(reversed(range(sides))), tuple((len(points)-1)*sides+j for j in range(sides))])
        return make(name, verts, faces, mat, bone)

    covered = tailor(kind, race, body, rig, make, sweep, morphology,
                     {'cloth':cloth,'trousers':trousers,'leather':leather,'seam':seam,'iron':iron,'brass':brass,'hair':hair,'wood':wood})
    if race == 'dwarf':
        for original in meshes:
            if original != body:bpy.data.objects.remove(original,do_unlink=True)

    # The apron is an intentionally folded panel rather than a colored area of skin.
    bpy.context.view_layer.update()
    garment_trees=[BVHTree.FromObject(o,bpy.context.evaluated_depsgraph_get()) for o in authored if 'continuous_tailored_surface' in o.name]
    def front_at(x,z):
        hits=[tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))[0] for tree in garment_trees]
        return min((hit.y for hit in hits if hit is not None),default=-.20)
    if kind in ('dwarf_artisan', 'greenskin_peat_worker', 'empire_herbalist'):
        rows = [(mapped(z),w) for z,w in [(1.42,.13),(1.34,.16),(1.22,.19),(1.10,.20),(1.0,.20),(.90,.195),(.79,.195),(.68,.205),(.62,.22)]]
        verts = []
        # The free-hanging leather follows the torso envelope; tucking the
        # shirt hem must not pull its lower pattern inward through the knees.
        waist_y=min(front_at(0,mapped(1.01))-.022,front_at(0,mapped(1.22))-.015)
        for r, (z, width) in enumerate(rows):
            for c in range(13):
                t = c/12; x = (t-.5)*2*width*(1.17 if race=='dwarf' else 1)
                drop=max(0,min(1,(mapped(1.0)-z)/.27))
                y=front_at(x,z)-.018 if z>mapped(1.0) else min(waist_y-.05*drop,front_at(x,z)-.018)
                verts.append((x,y-.004*math.sin(t*math.tau*3)*(r/8),z))
        faces = [(r*13+c,r*13+c+1,(r+1)*13+c+1,(r+1)*13+c) for r in range(len(rows)-1) for c in range(12)]
        apron = make(kind + '_folded_work_apron', verts, faces, leather if kind != 'empire_herbalist' else cloth)
        smooth=apron.modifiers.new('Supple_leather_finish','SUBSURF');smooth.levels=2;smooth.render_levels=2
        solid = apron.modifiers.new('Sewn_panel_thickness', 'SOLIDIFY'); solid.thickness = .004
        make_apron_details(apron,make,lambda point:morphology(point,race),leather)
    # Curved belt construction with a deliberately overlapped tongue and square forged buckle.
    belt_z = mapped(1.02)
    bpy.context.view_layer.update()
    belt_surfaces=[ClothSurface(o) for o in authored
                   if 'continuous_tailored_surface' in o.name or 'folded_work_apron' in o.name]
    # A belt wraps the exterior hull, bridging the apron edge instead of
    # abruptly diving toward the shirt when a radial ray misses that edge.
    def belt_hull(height):
        points=[];plane=belt_z+height
        # Exact cross-sections retain narrow apron corners which radial probes
        # can miss. The belt must wrap the whole sewn panel's exterior.
        for surface in belt_surfaces:
            for triangle in surface.triangles:
                for first,second in zip(triangle,triangle[1:]+triangle[:1]):
                    a,b=surface.points[first],surface.points[second]
                    if (a.z>plane)!=(b.z>plane):
                        point=a.lerp(b,(plane-a.z)/(b.z-a.z))
                        points.append((point.x,point.y))
        points=sorted(set(points))
        def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        lower=[];upper=[]
        for point in points:
            while len(lower)>1 and cross(lower[-2],lower[-1],point)<=0:lower.pop()
            lower.append(point)
        for point in reversed(points):
            while len(upper)>1 and cross(upper[-2],upper[-1],point)<=0:upper.pop()
            upper.append(point)
        return lower[:-1]+upper[:-1]
    def hull_radius(hull,direction):
        cross=lambda a,b:a[0]*b[1]-a[1]*b[0]
        candidates=[]
        for a,b in zip(hull,hull[1:]+hull[:1]):
            edge=(b[0]-a[0],b[1]-a[1]);denominator=cross(direction,edge)
            if abs(denominator)<1e-8:continue
            distance=cross(a,edge)/denominator;fraction=cross(a,direction)/denominator
            if distance>0 and -1e-7<=fraction<=1+1e-7:candidates.append(distance)
        if not candidates:raise RuntimeError('Authored belt profile is not closed')
        return min(candidates)
    heights=[-.023,-.0115,0,.0115,.023]
    hulls={height:belt_hull(height) for height in heights}
    verts=[];belt_sections=96
    # Preserve the leather's six-millimetre thickness as a paired profile.
    # Independently pushing its two surfaces outward collapses the inner face
    # onto the outer one and creates visible overlapping triangles.
    profile=[(.021,height) for height in heights]+[(.015,height) for height in reversed(heights)]
    for depth,height in profile:
        for i in range(belt_sections):
            direction=Vector((math.sin(i*math.tau/belt_sections),math.cos(i*math.tau/belt_sections),0));origin=Vector((0,0,belt_z+height))
            distance=hull_radius(hulls[height],direction)
            verts.append(origin+direction*(distance+depth))
    make('work_belt', verts, [(r*belt_sections+i,r*belt_sections+(i+1)%belt_sections,((r+1)%len(profile))*belt_sections+(i+1)%belt_sections,((r+1)%len(profile))*belt_sections+i)
                            for r in range(len(profile)) for i in range(belt_sections)], leather, 'hips')
    buckle_y = min(vertex.co.y for vertex in bpy.data.objects['work_belt'].data.vertices if abs(vertex.co.x)<.05)-.010
    for a,b in [((-.035,buckle_y,belt_z-.032),(.035,buckle_y,belt_z-.032)),
                ((-.035,buckle_y,belt_z+.032),(.035,buckle_y,belt_z+.032)),
                ((-.035,buckle_y,belt_z-.032),(-.035,buckle_y,belt_z+.032)),
                ((.035,buckle_y,belt_z-.032),(.035,buckle_y,belt_z+.032))]:
        sweep('forged_buckle_frame', [a,b], [.006,.006], brass, 'hips', 8)
    if kind=='dwarf_artisan':
        dress_artisan(apron,make,sweep,{'leather':leather,'seam':seam,'wood':wood,'iron':iron},belt_z)
        bpy.context.view_layer.objects.active=rig;rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        hinge=rig.data.edit_bones.new('apron_lower');hinge.parent=rig.data.edit_bones['hips']
        hinge.head=(0,waist_y,belt_z);hinge.tail=(0,waist_y,belt_z-.28)
        bpy.ops.object.mode_set(mode='OBJECT')
    # A hanging leather apron is suspended from the waist, not skinned to each
    # nearest thigh. Its pockets and bound edges must use the same cloth field.
    for ob in authored:
        if kind=='dwarf_artisan' and ob.name=='work_belt':
            ob.vertex_groups.clear()
            hips=ob.vertex_groups.new(name='hips');chest=ob.vertex_groups.new(name='chest')
            hinge=ob.vertex_groups.new(name='apron_lower')
            for vertex in ob.data.vertices:
                t=max(0,min(1,(vertex.co.z-belt_z)/.22));t=t*t*(3-2*t)
                fold=max(0,min(1,(belt_z-vertex.co.z)/.18));fold=fold*fold*(3-2*fold)
                front=max(0,min(1,(-vertex.co.y-.06)/.10));fold*=front
                hips.add([vertex.index],1-t-fold,'REPLACE');chest.add([vertex.index],t,'REPLACE');hinge.add([vertex.index],fold,'REPLACE')
        if 'folded_work_apron' in ob.name or (ob.name.startswith(('apron_','artisan_apron_tool_pocket','pocket_','saddle_stitch')) and ob.name!='apron_continuous_neck_loop'):
            ob.vertex_groups.clear()
            hips=ob.vertex_groups.new(name='hips');chest=ob.vertex_groups.new(name='chest')
            left=ob.vertex_groups.new(name='thigh_L');right=ob.vertex_groups.new(name='thigh_R')
            hinge=ob.vertex_groups.new(name='apron_lower') if kind=='dwarf_artisan' else None
            for vertex in ob.data.vertices:
                t=max(0,min(1,(vertex.co.z-belt_z)/.22));t=t*t*(3-2*t)
                leg=max(0,min(1,(belt_z-vertex.co.z-.035)/.22));leg=leg*leg*(3-2*leg)*.32
                side=max(0,min(1,(vertex.co.x+.04)/.08));side=side*side*(3-2*side)
                if hinge:
                    fold=max(0,min(1,(belt_z-vertex.co.z)/.18));fold=fold*fold*(3-2*fold)
                    hips.add([vertex.index],1-t-fold,'REPLACE');chest.add([vertex.index],t,'REPLACE');hinge.add([vertex.index],fold,'REPLACE')
                else:
                    hips.add([vertex.index],1-t-leg,'REPLACE');chest.add([vertex.index],t,'REPLACE')
                    left.add([vertex.index],leg*side,'REPLACE');right.add([vertex.index],leg*(1-side),'REPLACE')
        if ob.name.startswith(('welt_stitch','crossed_boot_lace')):
            ob.vertex_groups.clear()
            side='L' if sum(v.co.x for v in ob.data.vertices)>0 else 'R'
            foot=ob.vertex_groups.new(name='foot_'+side);shin=ob.vertex_groups.new(name='shin_'+side)
            for vertex in ob.data.vertices:
                t=max(0,min(1,(vertex.co.z-mapped(.12))/(mapped(.27)-mapped(.12))));t=t*t*(3-2*t)
                foot.add([vertex.index],1-t,'REPLACE');shin.add([vertex.index],t,'REPLACE')
    if kind=='dwarf_artisan':
        apron_surface=ClothSurface(apron)
        belt=bpy.data.objects['work_belt']
        bind_detail(belt,[apron_surface],select=lambda point:point.y<-.06)
        belt_surface=ClothSurface(belt)
        for obj in authored:
            if obj.name.startswith('forged_buckle_frame'):bind_detail(obj,[belt_surface])
        bind_detail(bpy.data.objects['apron_bound_perimeter'],[apron_surface])
        supports=[apron_surface]+[ClothSurface(obj) for obj in authored if 'shirt_continuous_tailored_surface' in obj.name or 'standing_shirt_collar' in obj.name]
        bind_detail(bpy.data.objects['apron_continuous_neck_loop'],supports)
        sew_work_shirt(make,material,lambda point:morphology(point,race),rig)
        finish_apron(apron,authored,belt_z,WORK)
    # Keep source anatomical image bytes and rig data within the editable derivative.
    bm = bmesh.new(); bm.from_mesh(body.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[face for face in bm.faces if face.index in covered], context='FACES')
    bm.to_mesh(body.data); bm.free()
    body.name = kind + '_exposed_anatomy'; rig.name = kind + '_rig'
    rig['skeletonId'] = 'humanoid_game_v2'; rig['bindPoseId'] = 'a_pose_v2'
    # Keep editable pose evaluation identical to export: finish the rest cage,
    # add cloth thickness, then deform that surface with the rig.
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        bpy.context.view_layer.objects.active=ob
        finish=[modifier for modifier in ob.modifiers if modifier.type in ('SUBSURF','SOLIDIFY')]
        for index,modifier in enumerate(finish):
            while list(ob.modifiers).index(modifier)>index:bpy.ops.object.modifier_move_up(modifier=modifier.name)
    attach_canonical_animation_pack(rig, profile='unarmed')
    if race == 'dwarf':
        # Contact fitting reads bones and boot soles. Avoid deforming every
        # embroidered garment for each intermediate IK dependency update.
        muted=[modifier for ob in bpy.context.scene.objects if ob.type=='MESH' and not ob.name.startswith('fitted_boot_')
               for modifier in ob.modifiers if modifier.type=='ARMATURE' and modifier.show_viewport]
        for modifier in muted:modifier.show_viewport=False
        try:
            fit_locomotion(rig)
            refine_sole_contacts(rig)
            fit_apron_clearance(rig)
        finally:
            for modifier in muted:modifier.show_viewport=True
            bpy.context.view_layer.update()
    for image in bpy.data.images:
        if image.size[0] and not image.packed_file: image.pack()
    bpy.context.scene.frame_set(1)
    key = 'frontier_' + ('cinderfen_' if race in ('greenskin','dark_elf') else 'sunmeadow_') + kind
    master = WORK/'sources'/f'{key}.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    meshes = [o for o in bpy.context.scene.objects if o.type=='MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for ob in meshes: ob.select_set(True)
    bpy.context.view_layer.objects.active=body
    # Apply only authored thickness before joining; bone deformation remains live.
    for ob in meshes:
        bpy.context.view_layer.objects.active=ob
        for modifier in list(ob.modifiers):
            if modifier.type in ('SUBSURF','SOLIDIFY'):
                while list(ob.modifiers).index(modifier)>0:bpy.ops.object.modifier_move_up(modifier=modifier.name)
                bpy.ops.object.modifier_apply(modifier=modifier.name)
        if ob.data.uv_layers:
            ob.data.uv_layers.active_index=0; ob.data.uv_layers[0].active_render=True
    bpy.context.view_layer.objects.active=body; bpy.ops.object.join()
    world_matrix=body.matrix_world.copy();body.parent=None;body.matrix_world=world_matrix
    base = body.data.copy(); lods=[]; pending_exports=[]
    for lod, ratio in enumerate([1,.58,.27]):
        body.data=base.copy()
        if ratio<1:
            dec=body.modifiers.new('Reviewed_LOD_reduction','DECIMATE'); dec.ratio=ratio
            bpy.ops.object.modifier_move_up(modifier=dec.name)
            bpy.ops.object.modifier_apply(modifier=dec.name)
        bm=bmesh.new(); bm.from_mesh(body.data)
        bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='FIXED',ngon_method='BEAUTY')
        bmesh.ops.dissolve_degenerate(bm,dist=0.000001,edges=list(bm.edges))
        loose=[v for v in bm.verts if not v.link_faces]
        if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(body.data);bm.free();body.data.validate();body.data.update()
        for vertex in body.data.vertices:
            ranked=sorted([(g.group,g.weight) for g in vertex.groups],key=lambda p:-p[1])
            total=sum(w for _,w in ranked[:4])
            for index,weight in ranked[4:]:body.vertex_groups[index].remove([vertex.index])
            for index,weight in ranked[:4]:body.vertex_groups[index].add([vertex.index],weight/total,'REPLACE')
        bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); rig.select_set(True)
        filename=f'{key}_lod{lod}.glb'; output=WORK/'runtime'/filename
        staged=output.with_name(output.stem+'.pending.glb')
        bpy.ops.export_scene.gltf(filepath=str(staged),export_format='GLB',use_selection=True,export_animations=True,export_tangents=True,
                                  export_animation_mode='ACTIONS',export_skins=True,export_morph=False)
        tangent_repair=repair_export_tangents(staged)
        data=staged.read_bytes(); doc=json.loads(data[20:20+int.from_bytes(data[12:16],'little')])
        pending_exports.append((staged,output))
        lods.append({'level':lod,'model':filename,'sha256':digest(staged),'bytes':len(data),'tangentRepair':tangent_repair,
                     'triangles':sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives']),
                     'clips':[a['name'] for a in doc.get('animations',[])]})
    source_files,embedded_images=build_provenance(source,master,recipe,body)
    # Complete all exports before replacing reviewable bytes. A failed Blender
    # write must not truncate a model currently open in the inspection viewer.
    for staged,output in pending_exports:os.replace(staged,output)
    (WORK/'review'/f'{key}_build.json').write_text(json.dumps({'key':key,'status':'draft', 'sourceFoundationSha256':digest(source),
        'masterSha256':digest(master),'generatorSha256':digest(__file__),
        'sourceFiles':source_files,'embeddedImages':embedded_images,
        'sourceTools':{str(path.relative_to(WORK)):digest(path) for path in sorted((WORK/'tools').glob('*.py'))},'lods':lods},indent=2))

if __name__ == '__main__':
    selected = next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--assets=')), ['dwarf_artisan'])
    for kind in selected: build(kind, CAST[kind])
