"""Render the generated map using the actual exported modular GLBs."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
WORK=Path(__file__).resolve().parents[1];ROOT=WORK.parents[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
zone=json.loads((ROOT/'public/assets/maps/riftspire_capital.json').read_text())
cache={}
for prop in zone['props']:
 model=prop['model']
 if model not in cache:
  before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime'/model))
  cache[model]=[(o.data,o.matrix_world.copy()) for o in set(bpy.data.objects)-before if o.type=='MESH']
  for ob in set(bpy.data.objects)-before:bpy.data.objects.remove(ob,do_unlink=True)
 s=prop.get('scale',1)
 matrix=Matrix.Translation((prop['x'],-prop['z'],prop.get('y',0)))@Matrix.Rotation(prop.get('rotX',0),4,'X')@Matrix.Rotation(prop.get('rotY',0),4,'Z')@Matrix.Rotation(-prop.get('rotZ',0),4,'Y')@Matrix.Diagonal((s*prop.get('scaleX',1),s*prop.get('scaleZ',1),s*prop.get('scaleY',1),1))
 for mesh,local in cache[model]:
  ob=bpy.data.objects.new(prop['id'],mesh);bpy.context.collection.objects.link(ob);ob.matrix_world=matrix@local
scene=bpy.context.scene;scene.world=bpy.data.worlds.new('Crater daylight');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.28,.34,.43,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
bpy.ops.object.light_add(type='SUN',location=(-350,-100,700));sun=bpy.context.object;sun.data.energy=2.4;sun.rotation_euler=(Vector((0,0,-120))-sun.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
for light in zone['craterCity'].get('lights',[]):
 bpy.ops.object.light_add(type='POINT',location=(light['x'],-light['z'],light['y']));bpy.context.object.data.energy=light['intensity']*4;bpy.context.object.data.color=(1,.73,.46);bpy.context.object.data.shadow_soft_size=1.2
views=[('rim',(12,-396,34),(0,0,-130)),('terrace',(60,-322,-101),(24,-337,-97)),('neighborhood',(90,-220,-65),(150,-325,-62)),('bridge',(12,-175,-99),(0,150,-90)),('commons',(35,-55,-118),(4,-106,-134)),('works',(20,-219,-239),(0,0,-130)),('palace',(0,454,-101),(0,499,-99))]
for district,kind in [('ashgate','arms_rack'),('market','market_stall'),('warrens','laundry_rig'),('commons','communal_hearth'),('works','water_pump'),('crown','oath_monument')]:
 choices=[p for p in zone['props'] if p['id'].startswith('riftspire_district_'+district+'_') and p['kind']=='riftspire_'+kind]
 prop=next((p for p in choices if math.sin(p['rotY'])*p['x']+math.cos(p['rotY'])*p['z']<0),choices[0])
 yaw=prop['rotY'];distance=15 if kind=='oath_monument' else 11
 eye=(prop['x']+math.sin(yaw)*distance+math.cos(yaw)*6,-prop['z']-math.cos(yaw)*distance+math.sin(yaw)*6,prop['y']+(8 if kind=='oath_monument' else 5))
 target=(prop['x'],-prop['z'],prop['y']+(5 if kind=='oath_monument' else 1.8))
 views.append(('district-'+district,eye,target))
for name,eye,target in views:
 if any(a.startswith('--views=') for a in sys.argv) and name not in next(a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--views=')):continue
 bpy.ops.object.camera_add(location=eye);cam=bpy.context.object;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=23;cam.data.clip_end=2500;scene.camera=cam
 scene.render.filepath=str(WORK/'review'/f'city-{name}.png');bpy.ops.render.render(write_still=True)
