"""Prepare private, animation-free supplied bodies without changing their geometry."""
import json
import shutil
import sys
from pathlib import Path
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from imported_population import ROOT, OUT, LEDGER, digest, models, verify_sources


def bone_names():
    result = dict(Hips='hips', Spine='spine', Spine1='chest', Spine2='upper_chest', Neck='neck', Head='head')
    for side, suffix in [('Left', 'L'), ('Right', 'R')]:
        for old, new in [('Shoulder','shoulder'), ('Arm','upper_arm'), ('ForeArm','forearm'),
                         ('Hand','hand'), ('UpLeg','thigh'), ('Leg','shin'), ('Foot','foot'), ('ToeBase','toe')]:
            result[side+old] = new+'_'+suffix
        for finger in ['Thumb','Index','Middle','Ring','Pinky']:
            for number in range(1,5):
                result[side+'Hand'+finger+str(number)] = finger.lower()+'_%02d_'%number+suffix
    return result


def prepare(row):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/row['source']), use_anim=False, use_image_search=False)
    omitted = []
    if row['key'] == 'brute':
        axe = bpy.data.objects.get('BattleAxe_GEO')
        if axe is None or axe.type != 'MESH': raise ValueError('Brute equipment topology changed')
        omitted.append(dict(object=axe.name,vertices=len(axe.data.vertices),reason='Separate civilian body from supplied weapon; original FBX retained'))
        bpy.data.objects.remove(axe,do_unlink=True)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    if len(rigs) != 1 or not meshes:
        raise ValueError('Expected one rig and authored meshes: '+row['key'])
    rig = rigs[0]
    mapping = bone_names()
    renames = {b.name: mapping.get(b.name.rsplit(':',1)[-1], b.name.replace(':','_')) for b in rig.data.bones}
    if len(set(renames.values())) != len(renames):
        raise ValueError('Ambiguous rig names: '+row['key'])
    for obj in meshes:
        for group in obj.vertex_groups:
            if group.name in renames: group.name = renames[group.name]
    for old, new in renames.items(): rig.data.bones[old].name = new
    # The new nondeforming root preserves the original hips rest matrix and units.
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    root = rig.data.edit_bones.new('root'); root.head=(0,0,0); root.tail=(0,0,1)
    root.use_deform = False
    for bone in rig.data.edit_bones:
        if bone != root and bone.parent is None: bone.parent = root
    bpy.ops.object.mode_set(mode='OBJECT')
    missing = []
    for material in bpy.data.materials:
        if not material.use_nodes: continue
        for node in list(material.node_tree.nodes):
            if node.type == 'TEX_IMAGE' and node.image and not node.image.has_data:
                # Missing optional maps are recorded for native material review, never replaced by imagery.
                missing.append(dict(material=material.name,image=node.image.name,
                                    outputs=[link.to_socket.name for output in node.outputs for link in output.links]))
                material.node_tree.nodes.remove(node)
    points = [o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
    bounds = [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]
    folder = OUT/'models'/row['profile']; folder.mkdir(parents=True, exist_ok=True)
    glb, fbx = folder/(row['profile']+'.glb'), folder/(row['profile']+'.fbx')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [rig]+meshes: obj.select_set(True); obj.animation_data_clear()
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True, export_animations=False)
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH','ARMATURE'},
        axis_forward='-Y', axis_up='Z', global_scale=1., apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
        add_leaf_bones=False, use_armature_deform_only=False, use_triangles=True, bake_anim=False)
    return dict(source=glb.relative_to(ROOT).as_posix(),fbx=fbx.relative_to(ROOT).as_posix(),
        sourceSha256=digest(glb),fbxSha256=digest(fbx),originalSource=row['source'],originalSha256=row['sha256'],
        boundsMeters=bounds,boneMap=renames,bindScale=list(rig.scale),missingTextureReferences=missing,
        materialNames=[m.name for m in bpy.data.materials],omittedEquipment=omitted,animations=[],nativeVisualVerified=False)


def main():
    verify_sources(); OUT.mkdir(parents=True,exist_ok=True)
    result = dict(schemaVersion=1,ledgerSha256=digest(LEDGER),profiles={})
    for row in models().values():
        result['profiles'][row['profile']] = prepare(row)
        (OUT/'model-sources.json').write_text(json.dumps(result,indent=2)+'\n')
    # Reuse the inventoried supplied animation sources, not any animation embedded in the new bodies.
    source = ROOT/'artifacts/unreal/animation-replacement/sources.json'
    if not source.is_file(): raise RuntimeError('Inventory the supplied animation set first')
    shutil.copy2(source, OUT/'sources.json')


if __name__ == '__main__': main()
