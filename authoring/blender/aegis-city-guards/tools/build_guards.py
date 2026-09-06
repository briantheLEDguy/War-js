"""Build/export four equipped NPCs using the verified local character contract."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent/'ember-arcanist-reference-rebuild'
sys.path.insert(0,str(BASE/'tools'))
sys.path.insert(0,str(ROOT/'tools'))
import build_proof as proof
import rig_character as binding

_base_finishing=binding.finishing_cap
_base_weights=binding.weights_for

def guard_finishing(source,slot,lod):
    _base_finishing(source,slot,lod)
    if source['source_part']=='head_skin' and lod==0:
        for modifier in source.modifiers:
            if modifier.type=='SUBSURF': modifier.levels=modifier.render_levels=2

def guard_weights(obj,co,slot):
    if obj['source_part']=='head_skin':
        head=max(0,min(1,(co.z-1.605)/.05)); head=head*head*(3-2*head)
        return {'neck':1-head,'head':head}
    if obj['source_part'] in {'eyes','ears','eyebrows'}: return {'head':1.0}
    return _base_weights(obj,co,slot)

binding.finishing_cap=guard_finishing
binding.weights_for=guard_weights

VARIANTS=['standard','halberd','crossbow','captain']


def materials():
    proof.ROOT=ROOT
    proof.PALETTE.update({'crimson':((.024,.061,.103,1),0,.86),
        'parchment':((.56,.52,.40,1),0,.86), 'steel':((.16,.19,.21,1),.76,.57),
        'brass':((.36,.245,.10,1),.72,.53), 'chainmail':((.065,.073,.077,1),.78,.57)})
    # Exportable UV textures are shared by material across all modules and variants.
    for name in proof.PALETTE:
        mat=proof.material(name)
        shader=mat.node_tree.nodes.get('Principled BSDF')
        path=ROOT/'textures'/f'{name}.png'
        imported=list((ROOT/'textures/imported').glob(name+'.*'))
        if imported: path=imported[0]
        if path.exists():
            tex=mat.node_tree.nodes.new('ShaderNodeTexImage')
            tex.image=bpy.data.images.load(str(path),check_existing=True)
            uv=mat.node_tree.nodes.new('ShaderNodeUVMap'); uv.uv_map='authored_uv'
            mat.node_tree.links.new(uv.outputs['UV'],tex.inputs['Vector'])
            mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])


def camera(name,position,target,scale):
    data=bpy.data.cameras.new(name); data.type='ORTHO'; data.ortho_scale=scale
    obj=bpy.data.objects.new(name,data); bpy.context.scene.collection.objects.link(obj)
    obj.location=position; obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj


def studio():
    scene=bpy.context.scene
    scene.render.engine='CYCLES'; scene.cycles.samples=24; scene.cycles.use_denoising=True
    scene.world=bpy.data.worlds.new('Charcoal studio'); scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.17,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
    for name,loc,power,size in [('key',(-3,-4,5),650,4),('fill',(4,-2,3),450,3),('rim',(2,3,4),700,3)]:
        d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size
        o=bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=loc
        o.rotation_euler=(Vector((1.5,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.view_transform='AgX'
    scene.render.image_settings.file_format='PNG'
    scene.render.resolution_percentage=100


def main():
    p=argparse.ArgumentParser(); p.add_argument('--export',action='store_true'); p.add_argument('--lods',default='0'); p.add_argument('--render',action='store_true'); args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials(); studio()
    rig=binding.import_contract_rig(BASE/'runtime/chr_civic_ember_arcanist_t1_m.glb')
    rig.data.pose_position='REST'
    report={'variants':{},'reference_sha256':hashlib.sha256((ROOT/'references/guard-guide.png').read_bytes()).hexdigest(),'rig':'humanoid_game_v2','review':'Pending visual inspection of exported models'}
    all_lod0=[]
    for index,variant in enumerate(VARIANTS):
        proof.COLLECTION='GUARD_SOURCE_'+variant
        source=ROOT/'source'/f'{variant}.json'
        from guard_pose import correct, place_weapon, audit_holds, GRIPS, GRIP_LOCAL
        deformations,wrists=correct(rig,variant)
        grip_audit=audit_holds(rig,variant,deformations)
        weapon_bones={p['id']:p['rigid_bone'] for p in json.loads(source.read_text())['parts'] if p.get('guard_weapon')}
        control,_=proof.load_sources(root=ROOT,snapshots={source.name:source.read_bytes()},scene_data={'comparison_pose':{}})
        report['variants'][variant]={}
        for lod in map(int,args.lods.split(',')):
            collection=bpy.data.collections.new(f'{variant}_LOD{lod}'); bpy.context.scene.collection.children.link(collection)
            groups={}
            for src in list(control.all_objects):
                if src.type!='MESH': continue
                if src['source_part']=='head_skin': src['slot']='body'
                obj=binding.evaluate_runtime_part(src,collection,rig,lod)
                if src['source_part'] in weapon_bones:
                    place_weapon(obj,variant,deformations,wrists,weapon_bones[src['source_part']])
                groups.setdefault(obj['slot'],[]).append(obj)
            modules=[binding.join_slot(objs,slot,lod) for slot,objs in groups.items()]
            triangles=sum(len(o.data.loop_triangles) for o in modules)
            for obj in modules: obj.data.calc_loop_triangles()
            triangles=sum(len(o.data.loop_triangles) for o in modules)
            filename=f'chr_aegis_city_guard_{variant}'+('' if lod==0 else f'_lod{lod}')+'.glb'
            entry={'triangles':triangles,'modules':len(modules),'materials':len({m.name for o in modules for m in o.data.materials}),'file':filename,'grip_audit':grip_audit}
            if args.export:
                # Keep editable armor modules in the master; batch the equipped NPC
                # into one skinned mesh to avoid a material draw for every armor slot.
                copies=[]
                for obj in modules:
                    duplicate=obj.copy(); duplicate.data=obj.data.copy(); collection.objects.link(duplicate); copies.append(duplicate)
                bpy.ops.object.select_all(action='DESELECT')
                for obj in copies: obj.select_set(True)
                bpy.context.view_layer.objects.active=copies[0]; bpy.ops.object.join()
                equipped=bpy.context.object; equipped.name='AegisGuard_'+variant
                equipped['guard_variant']=variant
                equipped['hand_grip_local']=list(GRIP_LOCAL)
                equipped['weapon_grip_bind_points']=json.dumps({side:{'driver':'R' if variant in {'crossbow','halberd'} else side,'point':list(deformations['R' if variant in {'crossbow','halberd'} else side].inverted() @ Vector(GRIPS[variant][side]))} for side in ['L','R']})
                from tessellate_runtime import prepare_tangents
                prepare_tangents(equipped)
                rig.data.pose_position='POSE'
                sockets=[o for o in bpy.data.objects if o.type=='EMPTY' and o.name.startswith('socket_')]
                binding.export_glb(ROOT/'runtime'/filename,[rig,equipped,*sockets],True)
                entry.update(bytes=(ROOT/'runtime'/filename).stat().st_size,sha256=hashlib.sha256((ROOT/'runtime'/filename).read_bytes()).hexdigest())
                bpy.data.objects.remove(equipped,do_unlink=True)
                rig.data.pose_position='REST'
            report['variants'][variant][str(lod)]=entry
            if lod==0:
                for obj in modules:
                    obj.name=f'{variant}.{obj["slot"]}'; obj.location.x=index*1.35
                all_lod0.extend(modules)
            else:
                for obj in modules: obj.hide_render=True; obj.hide_set(True)
        for obj in list(control.all_objects): obj.hide_render=True; obj.hide_set(True)
        print('GUARD_BUILT',variant,{lod:{k:v for k,v in record.items() if k!='grip_audit'} for lod,record in report['variants'][variant].items()},flush=True)
    bpy.context.scene.camera=camera('Guard lineup',(3.6,-8,3.0),(2.02,0,1.12),5.8)
    for name,pos in [('front',(0,-5,1.35)),('three_quarter',(3,-5,2.3)),('side',(5,0,1.4)),('back',(0,5,1.4))]: camera(name,pos,(0,0,1.1),2.5)
    for image in bpy.data.images:
        if image.source=='FILE': image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'aegis_city_guards_master.blend'),compress=True)
    if args.render:
        bpy.context.scene.render.resolution_x=1800; bpy.context.scene.render.resolution_y=880
        bpy.context.scene.render.filepath=str(ROOT/'review/lineup.png'); bpy.ops.render.render(write_still=True)
    (ROOT/'runtime/build-report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__': main()
