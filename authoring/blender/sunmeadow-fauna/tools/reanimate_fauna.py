"""Rebake motion on a hash-verified editable master without rebuilding its skin."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_fauna import ROOT,resolve,sha
from motion import mammal_clips,bird_clips


def geometry_sha(obj):
    vertices=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',vertices)
    return hashlib.sha256(vertices.tobytes()+json.dumps([list(p.vertices) for p in obj.data.polygons],separators=(',',':')).encode()).hexdigest()


def update(kind):
    key='frontier_sunmeadow_'+kind;report_path=ROOT/'review'/f'{key}_build.json';report=json.loads(report_path.read_text())
    allowed={'tools/motion.py','tools/quadruped_rig.py','tools/reanimate_fauna.py','tools/gait_curves.py'}
    for file,digest in {**report['source_files'],**report['texture_sources'],report['master']:report['master_sha256'],report['cage']:report['cage_sha256']}.items():
        if file not in allowed and sha(ROOT/file)!=digest:raise RuntimeError('Geometry/source changed; full build required: '+file)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/report['master']))
    rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE')
    models=[next(obj for obj in bpy.context.scene.objects if obj.type=='MESH' and obj.name.startswith(key+f'_LOD{lod}') and any(mod.type=='ARMATURE' for mod in obj.modifiers)) for lod in range(3)]
    geometry=[geometry_sha(obj) for obj in models]
    for action in list(bpy.data.actions):bpy.data.actions.remove(action,do_unlink=True)
    _,motion=(bird_clips if kind=='skylark' else mammal_clips)(rig,kind,resolve(kind))
    for level,obj in enumerate(models):
        obj.hide_set(False);obj.hide_render=False;rig.hide_set(False)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=obj
        target=ROOT/'runtime'/report['lods'][level]['model']
        bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_yup=True,export_normals=True,export_tangents=True,export_texcoords=True,export_skins=True,export_animations=True,export_animation_mode='ACTIONS',export_anim_single_armature=True,export_force_sampling=True,export_frame_range=False,export_vertex_color='NAME',export_vertex_color_name='AnatomicalTint',export_all_vertex_colors=False)
        report['lods'][level].update(sha256=sha(target),bytes=target.stat().st_size)
        obj.hide_set(level!=0);obj.hide_render=level!=0
    if geometry!=[geometry_sha(obj) for obj in models]:raise RuntimeError('Animation-only update changed editable skin geometry')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/report['master']),compress=True)
    report.update(motion=motion,master_sha256=sha(ROOT/report['master']),motion_source_sha256=sha(ROOT/'tools/motion.py'),rig_helper_sha256=sha(ROOT/'tools/quadruped_rig.py'))
    for file in allowed:report['source_files'][file]=sha(ROOT/file)
    report['animation_update']={'source_sha256':sha(__file__),'unchanged_geometry_sha256':geometry,'status':'actual_export_review_required'}
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print('FAUNA_REANIMATED',key,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default='roe_deer_buck');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for kind in args.assets.split(','):update(kind)
