"""Inspect the actual Blender master; native gameplay/lighting approval stays separate."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0,str(Path(__file__).parent))
from aegis_citadel_blueprint import OUT, sha
from aegis_citadel_mesh import blender_export_point

current=json.loads((OUT/'current.json').read_text());RUN=OUT/current['revision']
blueprint=json.loads((RUN/'blueprint.json').read_text())
source=json.loads((RUN/'assets-source.json').read_text())
master=RUN/source['sourceMaster']['path']
if sha(master)!=source['sourceMaster']['sha256']:raise RuntimeError('Preserve an edited Blender master')
bpy.ops.wm.open_mainfile(filepath=str(master))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.world=bpy.data.worlds.new('Bastion storm sky')
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.13,.18,.24,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55
scene.view_settings.view_transform='AgX'
def point(p):return Vector(blender_export_point(p))
def light(name,kind,position,energy,color,size=100):
    data=bpy.data.lights.new(name,kind);data.energy=energy;data.color=color
    if kind=='AREA':data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=point(position)
    obj.rotation_euler=(point([25500,0,8000])-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj
sun=light('Warm dusk sun','SUN',[7000,-20000,30000],3.2,(1,.79,.57));sun.data.angle=.12
light('Cool storm fill','AREA',[19000,10000,18000],190000,(.50,.64,1),150)
light('Front architectural fill','AREA',[11000,-16000,15000],180000,(.77,.84,1),120)
for row in blueprint['architecturalLights']:
    p=light(row['id'],'POINT',row['pointCm'],row['sourceWatts'],(1,.49,.19))
    p.data.shadow_soft_size=row['sourceRadiusCm']/100
    p.data.use_shadow=row['castShadows']
camera=bpy.data.cameras.new('Reference review camera');obj=bpy.data.objects.new('Reference review camera',camera)
scene.collection.objects.link(obj);scene.camera=obj;camera.clip_end=1500;camera.lens=40
folder=RUN/'source-review';folder.mkdir(exist_ok=True)
frames=[]
selected=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
mass=blueprint['upperMassing'];cut=mass['preservedThroughZCm']
def upper_height(z):return cut+(z-cut)*(mass['coreCompressionHighestZCm']-cut)/(mass['originalHighestZCm']-cut) if z>cut else z
monument=next(row for row in source['assets'] if row['id']=='furnishing_court_oath')
monument_top=max(p[2] for p in json.loads((RUN/monument['meshFile']).read_text())['positions'])
facade=next(row for row in source['assets'] if row['id']=='gothic_facade_and_spires')
facade_data=json.loads((RUN/facade['meshFile']).read_text())
spire_top=max((p for p in facade_data['positions'] if 27000<=p[0]<=33400 and abs(p[1])<=4000),
              key=lambda p:(p[2],-abs(p[1]),-abs(p[0]-30400)))
landmarks=dict(keepLeft=[26000,-4600,6010],keepRight=[26000,4600,6010],
    wingFacadeLeft=[26000,-7200,6010],wingFacadeRight=[26000,7200,6010],
    crownLeft=[26000,-4600,upper_height(14400)],crownRight=[26000,4600,upper_height(14400)],
    portalLeft=[26000,-900,6010],portalRight=[26000,900,6010],portalApex=[26000,0,8610],
    outerLeft=[27000,-9100,6010],outerRight=[27000,9100,6010],
    courtLeft=[20800,-7200,4210],courtRight=[20800,7200,4210],
    lowerCurtainLeft=[14200,-7500,5410],lowerCurtainRight=[14200,7500,5410],
    mainSpireTop=spire_top,monumentCenter=[20800,0,4210],
    monumentTop=[20800,0,monument_top],primaryCapture=blueprint['objectives'][6])
views=blueprint['reviewViews']+[v for v in blueprint.get('diagnosticReviewViews',[]) if v['id'] in selected]
for view in views:
    name,eye,target=view['id'],view['eyeCm'],view['targetCm']
    if selected and name not in selected:continue
    camera.type='ORTHO' if 'orthographicWidthCm' in view else 'PERSP'
    camera.ortho_scale=view.get('orthographicWidthCm',26000)/100
    camera.lens=view['focalLengthMm']
    obj.location=point(eye);obj.rotation_euler=(point(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    file=folder/(name+'.png');scene.render.filepath=str(file);bpy.ops.render.render(write_still=True)
    projected={}
    for key,p in landmarks.items():
        q=world_to_camera_view(scene,obj,point(p));projected[key]=[round(q.x*1600,2),round((1-q.y)*900,2)]
    frames.append(dict(id=name,path=file.relative_to(RUN).as_posix(),sha256=sha(file),eyeCm=eye,targetCm=target,
                       focalLengthMm=camera.lens,resolutionPx=[1600,900],landmarkPositionsCm=landmarks,
                       mainSpireTopPolicy='highest_actual_central_facade_source_vertex',projectedLandmarksPx=projected))
    (folder/'receipt.json').write_text(json.dumps(dict(revision=current['revision'],sourceMaster=source['sourceMaster'],
        frames=frames,nativeGameplayEvidence=False,visualApproved=False),indent=2)+'\n')
(folder/'receipt.json').write_text(json.dumps(dict(revision=current['revision'],sourceMaster=source['sourceMaster'],
    frames=frames,nativeGameplayEvidence=False,visualApproved=False),indent=2)+'\n')
print('WAR_CITADEL_SOURCE_REVIEW='+str(folder),flush=True)
