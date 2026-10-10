"""Blender: compare six draft race bodies at the same real metre scale."""
from pathlib import Path
import argparse
import bpy, math, hashlib, json, sys
from mathutils import Vector

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
run = Path(args.run).resolve()
run.relative_to(Path(__file__).resolve().parents[2] / 'artifacts/unreal/class-characters')
examples = [('Empire','ember_arcanist_m'),('Dwarf','stoneguard_m'),('High Elf','aether_sage_m'),
            ('Chaos','dreadsworn_m'),('Greenskin','warbrute_m'),('Dark Elf','dusk_weaver_m')]
bpy.ops.wm.read_factory_settings(use_empty=True)
evidence=[]
for index,(race,identity) in enumerate(examples):
    corrected=run/identity/'dentition-v1/review.json'
    candidate='dentition-v1' if corrected.exists() and json.loads(corrected.read_text())['passed'] else 'optimized-v2'
    model=run/identity/candidate/'body.glb'
    report=json.loads((model.parent/'review.json').read_text())
    assert report['passed']
    for evidence_file in report['files']:
        if Path(evidence_file['path']).name != evidence_file['path'] or hashlib.sha256((model.parent/evidence_file['path']).read_bytes()).hexdigest() != evidence_file['sha256']:
            raise RuntimeError('Changed lineup source evidence')
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(model))
    imported=set(bpy.data.objects)-before
    shift=(index-2.5)*1.3
    for obj in imported:
        if obj.parent is None and obj.type in ('ARMATURE','EMPTY'): obj.location.x+=shift
    height=json.loads((model.parent/'anatomy.json').read_text())['heightM']
    for line,z,size in ((race,-.22,.14),(f'{height:.2f} m',-.40,.105)):
        data=bpy.data.curves.new('ScaleLabel','FONT')
        data.body, data.align_x, data.size=line,'CENTER',size
        obj=bpy.data.objects.new('ScaleLabel',data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location=(shift,-.7,z)
        obj.rotation_euler=(math.pi/2,0,0)
        mat=bpy.data.materials.get('Label')
        if not mat:
            mat=bpy.data.materials.new('Label'); mat.diffuse_color=(.8,.83,.88,1)
        data.materials.append(mat)
    evidence.append(dict(race=race,identity=identity,heightM=height,model=model.relative_to(run).as_posix(),sha256=hashlib.sha256(model.read_bytes()).hexdigest()))
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x,scene.render.resolution_y=1800,680
scene.render.resolution_percentage=100
scene.eevee.taa_render_samples=64
scene.world=bpy.data.worlds.new('Studio');scene.world.color=(.04,.04,.045)
scene.view_settings.view_transform,scene.view_settings.exposure='AgX',-1.1
center=Vector((0,0,.95))
camera=bpy.data.objects.new('ScaleCamera',bpy.data.cameras.new('ScaleCamera'))
scene.collection.objects.link(camera)
camera.data.type,camera.data.ortho_scale='ORTHO',8.4
camera.location=(0,-10,.95)
camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera=camera
for position,energy,size in (((-3,-4,4),1300,6),((3,-4,3),1000,6),((0,3,4),1200,8)):
    data=bpy.data.lights.new('Studio','AREA');data.energy,data.size=energy,size
    obj=bpy.data.objects.new('Studio',data);scene.collection.objects.link(obj);obj.location=position
    obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(run/'race-lineup.png')
bpy.ops.render.render(write_still=True)
(run/'race-lineup.json').write_text(json.dumps(dict(models=evidence,imageSha256=hashlib.sha256((run/'race-lineup.png').read_bytes()).hexdigest(),
    renderToolSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),nativeAccepted=False,runtimeEligible=False),indent=2))
