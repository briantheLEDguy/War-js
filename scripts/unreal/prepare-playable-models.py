"""Assemble four authored bodies without animation tracks; author Templar equipment.

The Prelate's source modules remain unchanged. The new Templar retains that
body/rig and articulated plate construction, with its own sun heraldry,
open-faced sallet, split tabard, sword and heater shield.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"artifacts/unreal/animation-replacement/models"
MODELS=ROOT/"public/assets/models"
OUT.mkdir(parents=True,exist_ok=True)

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); result=importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result

def clear_tracks():
    for obj in bpy.data.objects:
        obj.animation_data_clear()
        if obj.type=="ARMATURE":
            obj.data.pose_position="REST"
            for bone in obj.pose.bones: bone.matrix_basis=Matrix.Identity(4)
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    bpy.context.view_layer.update()

def export(name,objects):
    folder=OUT/name; folder.mkdir(exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects: obj.hide_set(False); obj.hide_viewport=False; obj.hide_render=False; obj.select_set(True)
    bpy.context.view_layer.objects.active=next(o for o in objects if o.type=="MESH")
    glb=folder/(name+".glb"); fbx=folder/(name+".fbx")
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",use_selection=True,export_animations=False,export_extras=True)
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={"MESH","ARMATURE","EMPTY"},
        axis_forward="-Y",axis_up="Z",global_scale=1.,apply_unit_scale=True,apply_scale_options="FBX_SCALE_NONE",
        add_leaf_bones=False,use_armature_deform_only=False,use_triangles=True,bake_anim=False,path_mode="COPY",embed_textures=False)
    return dict(source=glb.relative_to(ROOT).as_posix(),fbx=fbx.relative_to(ROOT).as_posix(),
        sourceSha256=hashlib.sha256(glb.read_bytes()).hexdigest(),fbxSha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),
        triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects if o.type=="MESH"),animations=[])

def material(name,color,metal=0,rough=.45):
    mat=bpy.data.materials.new(name); mat.use_nodes=True
    shader=mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value=(*color,1); shader.inputs["Metallic"].default_value=metal; shader.inputs["Roughness"].default_value=rough
    return mat

def tint(mat,color):
    shader=mat.node_tree.nodes.get("Principled BSDF")
    socket=shader.inputs["Base Color"]
    if socket.is_linked:
        node=socket.links[0].from_node
        if node.type!='TEX_IMAGE' or not node.image:
            raise RuntimeError('Skin tint requires a direct authored color image')
        source=node.image
        pixels=np.empty(len(source.pixels),dtype=np.float32); source.pixels.foreach_get(pixels)
        pixels=pixels.reshape((-1,4)); pixels[:,:3]*=np.array(color)
        image=bpy.data.images.new(source.name+'_greenskin',width=source.size[0],height=source.size[1],alpha=True)
        image.colorspace_settings.name=source.colorspace_settings.name
        image.pixels.foreach_set(pixels.ravel()); image.update(); image.pack(); node.image=image
    else: socket.default_value=(*color,1)

def surface(name,vertices,faces,mat,thickness=0,bevel=0):
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(vertices,[],faces); mesh.update()
    obj=bpy.data.objects.new(name,mesh); bpy.context.scene.collection.objects.link(obj); obj.data.materials.append(mat)
    bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
    if thickness:
        m=obj.modifiers.new("Forged wall","SOLIDIFY"); m.thickness=thickness; m.offset=0
    if bevel:
        m=obj.modifiers.new("Worked edge","BEVEL"); m.width=bevel; m.segments=3
    bpy.context.view_layer.objects.active=obj; obj.select_set(True)
    for m in list(obj.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)
    for p in obj.data.polygons: p.use_smooth=True
    return obj

def bind(obj,rig,bone):
    obj.parent=rig
    group=obj.vertex_groups.new(name=bone); group.add(list(range(len(obj.data.vertices))),1,"REPLACE")
    mod=obj.modifiers.new("Articulated armor","ARMATURE"); mod.object=rig
    return obj

def ribbon(name,points,width,mat):
    vertices=[]
    for i,p in enumerate(points):
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
        side=Vector((-tangent.z,0,tangent.x)).normalized()*width/2
        vertices.extend([Vector(p)-side,Vector(p)+side])
    return surface(name,vertices,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(points)-1)],mat,.002,.001)

def sun(name,center,radius,mat):
    x,y,z=center; vertices=[(x,y-.01,z)]
    for i in range(48):
        a=2*math.pi*i/48; r=radius*(1 if i%4==0 else .60 if i%4==2 else .53)
        vertices.append((x+math.sin(a)*r,y,z+math.cos(a)*r))
    return surface(name,vertices,[(0,1+i,1+(i+1)%48) for i in range(48)],mat,.004,.0008)

def blade(name,anchor,steel,gold,leather,brutish=False):
    x,y,z=anchor; objects=[]
    # Lenticular cross-section and explicitly tapered/faceted silhouette.
    widths=[(.0,.032),(.12,.046),(.72,.036),(.9,0)] if not brutish else [(.0,.037),(.12,.10),(.58,.105),(.74,.03),(.79,0)]
    vertices=[]
    for height,width in widths: vertices.extend([(x-width,y,z+height),(x,y-.014,z+height),(x+width,y,z+height),(x,y+.014,z+height)])
    faces=[]
    for i in range(len(widths)-1):
        for j in range(4): faces.append((i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j))
    objects.append(surface(name+"_forged_blade",vertices,faces,steel,0,.0014))
    objects.append(ribbon(name+"_fuller",[(x,y-.016,z+.1),(x,y-.016,z+.65)],.007,gold))
    guard=[(-.16,-.025),(-.1,.025),(-.04,.045),(0,.038),(.04,.045),(.1,.025),(.16,-.025),(.12,-.035),(.055,.001),(-.055,.001),(-.12,-.035)]
    objects.append(surface(name+"_swept_guard",[(x+a,y,z+b) for a,b in guard],[tuple(range(len(guard)))],gold,.025,.003))
    for i in range(10):
        ring=[]
        for j in range(12):
            a=math.tau*j/12; ring.append((x+.021*math.cos(a),y+.016*math.sin(a),z-.015-i*.014))
        ring2=[(a,b,c-.013) for a,b,c in ring]
        objects.append(surface(name+"_grip_wrap_"+str(i),ring+ring2,[(j,(j+1)%12,(j+1)%12+12,j+12) for j in range(12)],leather))
    objects.append(sun(name+"_pommel",(x,y,z-.175),.032,gold))
    return objects

def shield(name,anchor,steel,gold,paint,brutish=False):
    x,y,z=anchor; outline=[(-.26,.35),(0,.40),(.26,.35),(.27,.05),(.18,-.23),(0,-.40),(-.18,-.23),(-.27,.05)]
    if brutish: outline=[(-.3,.34),(-.09,.41),(.05,.32),(.24,.4),(.29,.07),(.2,-.25),(0,-.37),(-.26,-.2)]
    vertices=[(x,y-.065,z)]+[(x+a,y,z+b) for a,b in outline]
    objects=[surface(name+"_bowed_face",vertices,[(0,1+i,1+(i+1)%8) for i in range(8)],paint,.018,.004)]
    objects.append(ribbon(name+"_rolled_border",[(x+a,y-.014,z+b) for a,b in outline+[outline[0]]],.024,gold))
    if not brutish: objects.append(sun(name+"_aegis_sun",(x,y-.084,z+.05),.17,gold))
    else:
        for side in (-1,1):
            fang=[(x+side*.14,y-.09,z+.2),(x+side*.055,y-.09,z+.17),(x+side*.035,y-.09,z-.17),(x+side*.09,y-.09,z-.075)]
            objects.append(surface(name+"_fang_mark",fang,[(0,1,2,3)],gold,.009,.002))
    for side in (-1,1):
        objects.append(ribbon(name+"_rear_grip",[(x+side*.1,y+.02,z-.12),(x+side*.1,y+.1,z),(x+side*.1,y+.02,z+.12)],.037,steel))
    return objects

def assembled(career):
    tool=ROOT/f"authoring/blender/{career.replace('_','-')}-reference-rebuild/tools/reimport_review.py"
    review=module("review_"+career,tool); review.bpy=bpy; review.Matrix=Matrix
    return review.assemble(MODELS,0)

def render(name,objects):
    scene=bpy.context.scene
    for obj in bpy.data.objects:
        if obj.type=="MESH": obj.hide_render=obj not in objects
    world=bpy.data.worlds.new("Review studio"); world.use_nodes=True; world.node_tree.nodes["Background"].inputs[0].default_value=(.055,.063,.085,1); world.node_tree.nodes["Background"].inputs[1].default_value=.4; scene.world=world
    scene.render.engine="CYCLES"; scene.cycles.samples=24; scene.cycles.use_denoising=True
    scene.render.resolution_x=950; scene.render.resolution_y=1150; scene.render.resolution_percentage=100
    for location,energy,size in [((3,-4,5),700,4),((-3,-1,3),500,3),((0,3,4),650,3)]:
        light=bpy.data.lights.new("Studio softbox","AREA"); light.energy=energy; light.shape="DISK"; light.size=size
        obj=bpy.data.objects.new(light.name,light); scene.collection.objects.link(obj); obj.location=location; obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.cameras.new("Matched review"); cam=bpy.data.objects.new(camera.name,camera); scene.collection.objects.link(cam); scene.camera=cam
    camera.type="ORTHO"; camera.ortho_scale=2.45
    for view,loc in [("front",(0,-5,2.15)),("three_quarter",(3,-5,2.4)),("back",(0,5,2.1))]:
        cam.location=loc; cam.rotation_euler=(Vector((0,0,1.05))-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(OUT/name/(view+".png")); bpy.ops.render.render(write_still=True)

receipts={}
# Preserve the equipped Prelate, extracting the same hammer as separate equipment.
assembly=assembled("battle_prelate"); clear_tracks()
rig=assembly["rig"]; meshes=assembly["all_meshes"]; weapon=[o for o in assembly["weapon"] if o.type=="MESH"]
# Existing approved two-handed grip adaptation moves this same hammer along its shaft.
grip=json.loads((ROOT/"scripts/unreal/animation-recipes/corrections/prelate-grip.json").read_text())
for obj in weapon:
    matrix=obj.matrix_world.copy(); obj.parent=None; obj.matrix_world=matrix
    shift=Vector(grip["hammerShiftMeters"])
    for vertex in obj.data.vertices: vertex.co += obj.matrix_world.to_3x3().inverted()@shift
receipts["civic_battle_prelate_m"]=export("civic_battle_prelate_m",[rig]+[o for o in meshes if o not in weapon])
receipts["civic_battle_prelate_m"]["weapon"]=export("PrelateHammer",weapon)
render("civic_battle_prelate_m",meshes)

# Use individual authored surfaces before atlas joining to remove the Prelate's
# religious ornaments without deleting armor, skin, joint seams or rig details.
master=ROOT/"authoring/blender/battle-prelate-reference-rebuild/battle_prelate_game_master.blend"
bpy.ops.wm.open_mainfile(filepath=str(master)); clear_tracks(); rig=bpy.data.objects["humanoid_game_v2"]
for collection in bpy.data.collections: collection.hide_viewport=False; collection.hide_render=False
def show(layer):
    layer.exclude=False; layer.hide_viewport=False
    for child in layer.children: show(child)
show(bpy.context.view_layer.layer_collection)
for obj in bpy.data.objects: obj.hide_set(False); obj.hide_viewport=False
bpy.context.view_layer.update()
rigging=module("prelate_rig",master.parent/"tools/rig_character.py")
collection=bpy.data.collections.new("SUNFIRE_TEMPLAR"); bpy.context.scene.collection.children.link(collection)
source=[o for o in bpy.data.objects if o.type=="MESH" and "source_part" in o and not o.name.startswith("battle_prelate_")]
meshes=[]
for obj in source:
    part=obj["source_part"]
    if any(word in part for word in ("reliquary","warhammer","tome_","parchment","wax_","censer","skull","cross","creed","fringe","manual_ink")): continue
    if part.startswith("breastplate_diagonal") or part=="breastplate_reinforcement_steel_inset": continue
    if part=="relic_tabard_gilded_pointed_hem": continue
    obj.hide_set(False); obj.hide_viewport=False
    made=rigging.evaluate_runtime_part(obj,collection,rig,0)
    if part in ("front_crimson_tabard","rear_crimson_surcoat"):
        for vertex in made.data.vertices:
            if vertex.co.z < 1.12: vertex.co.z=1.12+(vertex.co.z-1.12)*.72
    meshes.append(made)
steel=bpy.data.materials.get("proof.steel") or material("TemplarSteel",(.2,.25,.3),.85,.32)
gold=bpy.data.materials.get("proof.brass") or material("TemplarGold",(.48,.32,.12),.8,.3)
blue=material("AegisBlueEnamel",(.015,.055,.13),.35,.31); leather=material("TemplarGripLeather",(.045,.023,.011),0,.7)
cloth=material("AegisBlueWovenTabard",(.014,.041,.10),0,.88)
for obj in meshes:
    for slot in obj.material_slots:
        if slot.material and "crimson" in slot.material.name: slot.material=cloth
meshes.append(bind(sun("BastionSunBreastplate",(0,-.215,1.433),.092,gold),rig,"upper_chest"))
meshes.append(bind(sun("BastionSunTabard",(0,-.228,.96),.065,gold),rig,"hips"))
# Sallet formed as joined contour rings, with brow peak, side cheek extensions
# and an open face; deliberately distinct from the Prelate's bare head.
rings=[(1.72,.107,.097),(1.82,.113,.106),(1.90,.080,.078),(1.945,.015,.02)]
vertices=[]
for z,rx,ry in rings:
    for i in range(20):
        angle=math.tau*i/20; vertices.append((math.sin(angle)*rx,math.cos(angle)*ry+.014,z))
faces=[]
for row in range(3):
    for i in range(20):
        # Cut the lower front away from the face, retaining the brow crown.
        if row==0 and 7<=i<=12: continue
        faces.append((row*20+i,row*20+(i+1)%20,(row+1)*20+(i+1)%20,(row+1)*20+i))
meshes.append(bind(surface("TemplarSallet",vertices,faces,steel,.006,.0015),rig,"head"))
meshes.append(bind(ribbon("SalletSunCrest",[(0,-.1,1.84),(0,-.055,1.94),(0,.03,1.97),(0,.105,1.86)],.018,gold),rig,"head"))
for side in (-1,1):
    for offset in (0,.035,.07):
        meshes.append(bind(ribbon("TemplarRadialFlute",[(side*.035,-.213,1.44),(side*(.11+offset),-.145,1.53),(side*(.15+offset),-.065,1.58)],.009,gold),rig,"upper_chest"))
right=rig.matrix_world@rig.data.bones["hand_R"].head_local; left=rig.matrix_world@rig.data.bones["hand_L"].head_local
weapon=blade("DawnwardSword",right+Vector((0,-.018,.07)),steel,gold,leather)
offhand=shield("BastionHeater",left+Vector((.05,-.18,0)),steel,gold,blue)
# Bake the same authored surface channels used by the Prelate. A single UV
# channel per module preserves the source normal maps through FBX and Unreal.
baker=module('templar_atlas',master.parent/'tools/bake_atlas.py')
groups={}
for obj in meshes:
    slot=obj.get('slot','head' if 'Sallet' in obj.name else 'tabard' if 'Tabard' in obj.name else 'chest')
    if not obj.data.uv_layers: obj.data.uv_layers.new(name='authored_uv')
    groups.setdefault(slot,[]).append(obj)
meshes=[]
for slot,parts in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts: obj.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    if len(parts)>1: bpy.ops.object.join()
    obj=bpy.context.object; obj.name='SunfireTemplar_'+slot
    baker.bake_module_atlas(obj,'templar_'+slot,OUT/'civic_sunfire_templar_m'/'textures',resolution=1024)
    meshes.append(obj)
receipts["civic_sunfire_templar_m"]=export("civic_sunfire_templar_m",[rig]+meshes)
receipts["civic_sunfire_templar_m"]["weapon"]=export("TemplarSword",weapon)
receipts["civic_sunfire_templar_m"]["shield"]=export("TemplarShield",offhand)
render("civic_sunfire_templar_m",meshes+weapon+offhand)

assembly=assembled("ember_arcanist"); clear_tracks(); rig=assembly["rig"]
meshes=assembly["all_meshes"]; weapon=[o for o in assembly["weapon"] if o.type=="MESH"]
receipts["civic_ember_arcanist_m"]=export("civic_ember_arcanist_m",[rig]+[o for o in meshes if o not in weapon])
receipts["civic_ember_arcanist_m"]["weapon"]=export("EmberStaff",weapon)
render("civic_ember_arcanist_m",meshes)

bpy.ops.wm.read_factory_settings(use_empty=True)
review=module("assembly_common",ROOT/"authoring/blender/battle-prelate-reference-rebuild/tools/reimport_review.py"); review.bpy=bpy; review.Matrix=Matrix
body=review.import_body(MODELS/"chr_mire_warbrute_t1_m.glb"); rig=body["rig"]; meshes=list(body["meshes"])
for obj in meshes:
    for mat in obj.data.materials:
        if mat and (mat.name.endswith(".body") or mat.name.endswith(".high-poly")): tint(mat,(.18,.58,.13))
for slot in ("head","shoulders","chest","hands","waist","legs","feet","back","tabard"):
    armor,_=review.rebind_armor(MODELS/f"arm_mire_warbrute_{slot}_t1_m.glb",rig,slot); meshes.extend(armor)
clear_tracks()
iron=material("WarbruteBlackIron",(.08,.10,.105),.8,.48); bronze=material("WarbruteBatteredBronze",(.32,.18,.06),.8,.48)
red=material("WarbruteOxblood",(.13,.022,.012),.25,.57); leather=material("WarbruteWrap",(.065,.036,.013),0,.78)
right=rig.matrix_world@rig.data.bones["hand_R"].head_local; left=rig.matrix_world@rig.data.bones["hand_L"].head_local
weapon=blade("WarbruteCleaver",right+Vector((0,-.018,.07)),iron,bronze,leather,True)
offhand=shield("WarbruteScavengedShield",left+Vector((.05,-.18,0)),iron,bronze,red,True)
receipts["mire_warbrute_m"]=export("mire_warbrute_m",[rig]+meshes)
receipts["mire_warbrute_m"]["weapon"]=export("WarbruteCleaver",weapon)
receipts["mire_warbrute_m"]["shield"]=export("WarbruteShield",offhand)
render("mire_warbrute_m",meshes+weapon+offhand)

# The relic is an original open reliquary: stepped plinth, swept uprights and
# suspended sun icon. It has actual modeled sides and back, not an effect proxy.
bpy.ops.wm.read_factory_settings(use_empty=True)
gold=material("RelicWorkedGold",(.46,.29,.08),.85,.32); dark=material("RelicBlueSteel",(.027,.044,.08),.7,.42)
objects=[]
for z,r in [(0,.16),(.035,.17),(.055,.135),(.075,.14)]:
    points=[(math.cos(i*math.tau/8)*r,math.sin(i*math.tau/8)*r,z) for i in range(8)]
    objects.append(surface("RelicPlinth",points,[tuple(range(8))],dark,.026,.004))
for side in (-1,1): objects.append(ribbon("RelicSweptUpright",[(side*.115,0,.065),(side*.13,0,.17),(side*.10,0,.29),(side*.04,0,.39)],.027,gold))
objects.append(sun("RelicSun",(0,-.02,.25),.09,gold))
objects.append(ribbon("RelicCrown",[(-.12,0,.31),(0,0,.425),(.12,0,.31)],.018,gold))
receipts["IconOfWrath"]=export("IconOfWrath",objects)
(OUT.parent/"model-sources.json").write_text(json.dumps(dict(schemaVersion=1,profiles=receipts),indent=2)+"\n")
