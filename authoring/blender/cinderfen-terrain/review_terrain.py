"""Render the actual exported sector GLBs, never the authoring substitutes."""
import bpy,json,math,hashlib,struct,re,argparse,sys
from pathlib import Path
from mathutils import Vector
WORK=Path(__file__).resolve().parent
def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
report_file=WORK/'build-report.json';source_file=WORK/'terrain-source.json'
report=json.loads(report_file.read_text())
parser=argparse.ArgumentParser();parser.add_argument('--views',default='terrain_overview_lod0,road_material,terrain_overview_lod1,terrain_overview_lod2,road_junction_lod0')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
views=set(args.views.split(','));receipt_file=WORK/'review/render_receipt.json'
receipt={'schemaVersion':1,'buildSha256':sha(report_file),'sourceSha256':sha(source_file),'views':[]}
if len(views)<5 and receipt_file.exists():
    previous=json.loads(receipt_file.read_text())
    if previous['buildSha256']!=receipt['buildSha256'] or previous['sourceSha256']!=receipt['sourceSha256']:
        raise RuntimeError('Cannot merge individual views with an older build receipt')
    receipt=previous
receipt['rendering']={'engine':'Cycles','samples':24,'terrainCastsShadow':False,'runtimeContract':'src/world/Terrain.ts sets all authored terrain meshes castShadow=false; they still receive light and shadows.'}
def model_evidence(model):
    file=WORK/'runtime'/model;data=file.read_bytes()
    doc=json.loads(data[20:20+struct.unpack_from('<I',data,12)[0]])
    textures=[]
    for image in doc.get('images',[]):
        uri=image['uri']
        if not re.fullmatch(r'\.\./textures/cinderfen_terrain/[a-f0-9]{20}\.png',uri):raise RuntimeError('Unexpected texture path')
        textures.append({'uri':uri,'sha256':sha(WORK/'runtime'/uri)})
    return {'model':model,'sha256':hashlib.sha256(data).hexdigest(),'externalTextures':sorted(textures,key=lambda item:item['uri'])}

def record_view(name,models):
    if sha(report_file)!=receipt['buildSha256'] or sha(source_file)!=receipt['sourceSha256']:
        raise RuntimeError('Survey/build changed during review rendering')
    if [model_evidence(item['model']) for item in models]!=models:
        raise RuntimeError('Mesh or texture changed during review rendering')
    image=name+'.png'
    receipt['views']=[view for view in receipt['views'] if view['image']!=image]
    receipt['views'].append({'image':image,'imageSha256':sha(WORK/'review'/image),'models':models})
    receipt_file.write_text(json.dumps(receipt,indent=2)+'\n')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.world.color=(.35,.4,.48)
sun=bpy.data.lights.new('afternoon_sun','SUN');sun.energy=3;sun.angle=.12
o=bpy.data.objects.new('afternoon_sun',sun);scene.collection.objects.link(o);o.rotation_euler=(.42,-.55,-.38)
world=scene.world;world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[0].default_value=(.48,.57,.7,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.6
cam=bpy.data.cameras.new('review_camera');camera=bpy.data.objects.new('review_camera',cam);scene.collection.objects.link(camera);scene.camera=camera
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
def render(name,position,target,lens=45):
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();cam.lens=lens;cam.clip_end=5000
    scene.render.filepath=str(WORK/'review'/(name+'.png'));bpy.ops.render.render(write_still=True)
for level in [0,1,2]:
    if f'terrain_overview_lod{level}' not in views and not (level==0 and {'road_material','road_junction_lod0'} & views):continue
    for obj in list(scene.objects):
        if obj.type=='MESH':bpy.data.objects.remove(obj,do_unlink=True)
    models=[]
    for asset in report:
        lod=asset['lods'][level];captured=model_evidence(lod['model'])
        if captured['sha256']!=lod['sha256']:raise RuntimeError('Build report does not match export')
        models.append(captured)
        before=set(scene.objects)
        bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime'/asset['lods'][level]['model']))
        imported=set(scene.objects)-before
        for obj in imported:
            if obj.type=='MESH':obj.visible_shadow=False
            if obj.parent not in imported:obj.location+=Vector((asset['x'],-asset['z'],0))
    if f'terrain_overview_lod{level}' in views:
        render(f'terrain_overview_lod{level}',(1150,-1400,1350),(0,0,0))
        record_view(f'terrain_overview_lod{level}',models)
    if level==0 and 'road_junction_lod0' in views:
        render('road_junction_lod0',(-369,105,29),(-350,78,0),48)
        record_view('road_junction_lod0',models)
    if level==0 and 'road_material' in views:
        render('road_material',(-125,29,2.4),(-165,46,.8),40)
        record_view('road_material',models)
        bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'review/terrain_reimport.blend'))
