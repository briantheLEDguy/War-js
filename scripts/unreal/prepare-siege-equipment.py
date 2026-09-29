"""Convert retained siege meshes and sample their authored mechanical animation.

No character motions or visible substitute geometry are generated here.
"""
import hashlib
import json
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/siege/equipment'
OUT.mkdir(parents=True,exist_ok=True)
ROT=Matrix.Rotation(math.pi/2,4,'Z')
BASES={}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def pin(objects,clip):
    for obj in objects:
        if not obj.animation_data: continue
        obj.animation_data.action=None
        for track in obj.animation_data.nla_tracks:
            track.mute=True
            if track.name==clip:
                obj.animation_data.action=track.strips[0].action
                obj.animation_data.action_slot=track.strips[0].action_slot
        if obj.name in BASES:obj.matrix_basis=BASES[obj.name].copy()

def native(matrix):
    p,q,s=matrix.decompose()
    # Blender -Y forward becomes Unreal +X; Unreal reverses handedness.
    return dict(p=[-p.y*100,-p.x*100,p.z*100],q=[q.y,q.x,-q.z,q.w],s=list(s))

def export(name,objects):
    folder=OUT/name;folder.mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    glb=folder/(name+'.glb');fbx=folder/(name+'.fbx')
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False)
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',use_triangles=True,bake_anim=False)
    return dict(source=glb.relative_to(ROOT).as_posix(),fbx=fbx.relative_to(ROOT).as_posix(),sourceSha256=sha(glb),fbxSha256=sha(fbx))

result={}
for name,source,roll,strike in [('Ram','frontier_battering_ram_lod0','siege_roll','ram_strike'),
                              ('Catapult','frontier_field_catapult_lod0','siege_roll',None),
                              ('RiftboundStandard','prop_riftspire_war_standard',None,None)]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path=ROOT/'public/assets/models'/f'{source}.glb'
    bpy.ops.import_scene.gltf(filepath=str(path))
    if name!='RiftboundStandard':
        # The shared frontier engine carries an Aegis pennant by default. Replace
        # that exact mesh with a portable adaptation of the retained Riftbound standard.
        old=bpy.data.objects.get('realm_standard')
        if not old:raise RuntimeError('Missing engine pennant binding')
        bpy.data.objects.remove(old,do_unlink=True)
        before=set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/assets/models/prop_riftspire_war_standard.glb'))
        flag=next(o for o in bpy.data.objects if o not in before and o.type=='MESH' and not o.name.startswith('Icosphere'))
        flag.name='realm_standard';flag.data=flag.data.copy()
        bm=bmesh.new();bm.from_mesh(flag.data)
        stone=[face for face in bm.faces if flag.data.materials[face.material_index].name.startswith('riftspire_basalt')]
        bmesh.ops.delete(bm,geom=stone,context='FACES');bm.to_mesh(flag.data);bm.free()
        flag.matrix_world=Matrix.Translation((1.35,-1.3,.85))@Matrix.Scale(.15,4)
    objects=list(bpy.context.scene.objects)
    BASES={o.name:o.matrix_basis.copy() for o in objects}
    meshes=[o for o in objects if o.type=='MESH' and not o.hide_render and not o.name.startswith('Icosphere')]
    pin(objects,None);bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
    rest={o.name:o.matrix_world.copy() for o in meshes}
    low=min((rest[o.name]@v.co).z for o in meshes for v in o.data.vertices)
    lift=Matrix.Translation((0,0,-low))
    tracks={o.name:{} for o in meshes}
    for key,clip,duration in [('roll',roll,1.6),('strike',strike,1.5)]:
        if not clip: continue
        pin(objects,clip)
        for i in range(round(duration*30)+1):
            frame=i/30*bpy.context.scene.render.fps;bpy.context.scene.frame_set(int(frame),subframe=frame%1)
            for o in meshes:
                delta=lift@o.matrix_world@rest[o.name].inverted()@lift.inverted()
                tracks[o.name].setdefault(key,[]).append(native(delta))
    parts=[]
    pin(objects,None);bpy.context.scene.frame_set(0)
    for i,obj in enumerate(meshes):
        original=obj.name
        transform=ROT@lift@rest[original]
        # GLTF wheels instance a shared mesh datablock. Baking one pivot must not
        # alter the geometry exported at the other three pivots.
        obj.data=obj.data.copy()
        obj.parent=None;obj.animation_data_clear();obj.matrix_world=Matrix.Identity(4)
        obj.data.transform(transform)
        row=export(name+'_'+original.replace('.','_'),[obj]);row.update(tracks[original]);parts.append(row)
    result[name]=dict(source=path.relative_to(ROOT).as_posix(),sourceSha256=sha(path),parts=parts)
(OUT/'sources.json').write_text(json.dumps(result,indent=2)+'\n')
