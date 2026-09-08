"""Review exported runtime GLBs, never the higher-detail source scene."""
import bpy,sys,math
from pathlib import Path
from mathutils import Vector
WORK=Path(__file__).resolve().parents[1]
requested=next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--assets=')),['house_1','assembly','palace'])
for kind in requested:
  for lod in next(([int(v) for v in a.split('=',1)[1].split(',')] for a in sys.argv if a.startswith('--lods=')),[0,2]):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def add(k,pos=(0,0,0),scale=(1,1,1)):
      before=set(bpy.data.objects)
      model=('chr_riftspire_'+k.replace('population_','')) if k.startswith('population_') else 'prop_riftspire_'+k
      bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime'/f'{model}{"_lod"+str(lod) if lod else ""}.glb'))
      for ob in set(bpy.data.objects)-before:
        if not ob.parent:ob.location+=Vector(pos);ob.scale=scale
    if kind=='assembly':
      add('bridge',(0,0,18));add('hut')
      for x in [-3,3]:add('chain',(x,0,9),(1,1,.46))
    else:add(kind)
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    pts=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box]
    lo=Vector([min(v[i] for v in pts) for i in range(3)]);hi=Vector([max(v[i] for v in pts) for i in range(3)])
    center=(lo+hi)/2;extent=max(hi-lo)
    scene=bpy.context.scene;scene.world=bpy.data.worlds.new('daylight');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.28,.34,.42,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
    bpy.ops.object.light_add(type='SUN',location=(-40,-80,100));sun=bpy.context.object;sun.data.energy=3
    sun.rotation_euler=(Vector((0,0,0))-sun.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add(location=center+Vector((extent*.85,-extent*1.9,extent*.35)))
    cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=45;cam.data.clip_end=3000;scene.camera=cam
    scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    scene.render.filepath=str(WORK/'review'/f'{kind}-lod{lod}.png');bpy.ops.render.render(write_still=True)
