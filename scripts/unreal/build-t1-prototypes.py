"""Build first-pair review maps in new private packages; never attach them to the campaign."""
import hashlib
import datetime
import json
import math
import sys
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_build_assets import WorldAssets

DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'
def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
def package_file(package):return ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')
def position(row):return unreal.Vector(row['z']*100,row['x']*100,(row.get('groundY',row.get('y',0))+row.get('offsetY',0))*100)

plan=json.loads((DIRECTORY/'plan.json').read_text())
models=json.loads((DIRECTORY/'models.json').read_text())
fingerprint=sha(DIRECTORY/'plan.json')
for name,digest in plan['toolHashes'].items():
    if sha(ROOT/name)!=digest:raise RuntimeError('Authoring tool changed; regenerate candidate: '+name)
if models['planSha256']!=fingerprint:raise RuntimeError('Prototype models belong to a different plan')
for name,digest in plan['privateMapHashes'].items():
    if sha(ROOT/name)!=digest:raise RuntimeError('Saved native content changed; preserve and reconcile: '+name)
for zone,digest in plan['sourceHashes'].items():
    if sha(ROOT/'public/assets/maps'/(zone+'.json'))!=digest:raise RuntimeError('Campaign source changed: '+zone)
target=DIRECTORY/('native-'+fingerprint[:12]+'.json')
if target.exists():
    receipt=json.loads(target.read_text())
    for package,digest in receipt['packageHashes'].items():
        if sha(package_file(package))!=digest:raise RuntimeError('Candidate was owner-edited; preserve it and generate a new revision')
    unreal.log('WAR_T1_PROTOTYPES_ALREADY_BUILT='+fingerprint[:12])
else:
    collection='T1Redesign_'+fingerprint[:12]+'_'+datetime.datetime.now().strftime('%H%M%S_%f')
    assets=WorldAssets(ROOT,collection)
    meshes={}
    for model,row in models['models'].items():
        file=DIRECTORY/row['file']
        if sha(file)!=row['sha256']:raise RuntimeError('Prototype mesh export changed')
        if sha(ROOT/'public/assets/models'/model)!=row['sourceSha256']:raise RuntimeError('Admitted source model changed')
        meshes[model]=assets.composite(Path(model).stem,json.loads(file.read_text()),True)
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    packages,zones=[],[]
    for identity in plan['nativeBatch']:
        folder=assets.folder+'/'+identity
        map_package=folder+'/Review'
        if not levels.new_level(map_package):raise RuntimeError('Cannot create isolated review map')
        source_file=DIRECTORY/(identity+'.json')
        if sha(source_file)!=plan['candidateHashes'][identity]:raise RuntimeError('Candidate map changed; regenerate revision')
        source=json.loads(source_file.read_text())
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        anchor=actors.spawn_actor_from_class(unreal.WarZoneAnchor,unreal.Vector())
        anchor.set_editor_property('zone_id',identity);anchor.set_editor_property('zone_origin',unreal.Vector())
        b=source['spatial']['bounds']
        anchor.set_editor_property('use_spatial_bounds',True)
        anchor.set_editor_property('content_min',unreal.Vector2D(b['minZ']*100,b['minX']*100))
        anchor.set_editor_property('content_max',unreal.Vector2D(b['maxZ']*100,b['maxX']*100))
        anchor.set_editor_property('playable_outline',[unreal.Vector2D(p['z']*100,p['x']*100) for p in source['spatial']['playableOutline']])
        anchor.tags=['WarT1PrototypeRouting']
        streaming=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,folder+'/Generated',False)
        if not streaming:raise RuntimeError('Cannot create generated candidate layer')
        unreal.EditorLevelUtils.make_level_current(streaming)
        palette=source['orvrLayout']['biome']['palette']
        def color(value):
            def linear(channel):return channel/12.92 if channel<=.04045 else ((channel+.055)/1.055)**2.4
            return [linear(int(value[i:i+2],16)/255) for i in (1,3,5)]+[1]
        count=0;practical_count=0
        for suffix,collision,tint in [('_terrain',True,palette[0]),('_roads',False,palette[1])]:
            file=DIRECTORY/(identity+suffix+'.json')
            if sha(file)!=plan['terrainHashes'][identity+suffix]:raise RuntimeError('Terrain export changed')
            material=assets.material(identity+suffix,{'color':color(tint),'roughness':.95,'metallic':0})
            mesh=assets.mesh(identity+suffix,json.loads(file.read_text()),material,collision)
            actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
            actor.static_mesh_component.set_static_mesh(mesh)
            actor.static_mesh_component.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
            actor.tags=['WarT1PrototypeTerrain'];actor.set_actor_label(identity+suffix)
        for placement in models['placements']:
            if placement['zone']!=identity:continue
            p=placement['source'];p={**p,'offsetY':p.get('y',0)-p['groundY'] if p.get('heightMode')=='absolute' else p.get('y',0)}
            actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,position(p),unreal.Rotator(yaw=p.get('rotY',0)*180/math.pi))
            actor.static_mesh_component.set_static_mesh(meshes[placement['model']])
            actor.static_mesh_component.set_collision_profile_name('BlockAll')
            scale=p.get('scale',1);actor.set_actor_scale3d(unreal.Vector(scale*p.get('scaleZ',1),scale*p.get('scaleX',1),scale*p.get('scaleY',1)))
            actor.tags=['WarT1PrototypeScenery'];actor.set_actor_label(p.get('id','SourcePrototype'));count+=1
            if p.get('practical'):
                light=actors.spawn_actor_from_class(unreal.WarPracticalLight,position(p)+unreal.Vector(0,0,p['practical']['heightAboveFixture']*100))
                light.set_editor_property('zone_id',identity);light.set_editor_property('night_lumens',p['practical']['lumens'])
                light.set_actor_label(p['id']+'_light');light.tags=['WarT1PrototypePractical'];practical_count+=1
        if not levels.save_current_level():raise RuntimeError('Cannot save generated candidate')
        authored=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,folder+'/Authored',False)
        if not authored:raise RuntimeError('Cannot reserve owner-authored candidate layer')
        unreal.EditorLevelUtils.make_level_current(authored)
        if not levels.save_current_level():raise RuntimeError('Cannot save authored layer')
        levels.set_current_level_by_name('Review')
        anchor.set_editor_property('content_levels',[folder+'/Generated',folder+'/Authored'])
        if not levels.save_current_level():raise RuntimeError('Cannot save candidate routing')
        packages.extend([map_package,folder+'/Generated',folder+'/Authored'])
        zones.append({'id':identity,'map':map_package,'generated':folder+'/Generated','authored':folder+'/Authored',
                      'placedSourceModels':count,'practicalLights':practical_count,'villageShells':20,'furnishedHomesAccepted':0})
    for name,digest in plan['privateMapHashes'].items():
        if sha(ROOT/name)!=digest:raise RuntimeError('Existing native content was modified')
    receipt={'planSha256':fingerprint,'zones':zones,'packageHashes':{p:sha(package_file(p)) for p in packages},
        'pending':models['pending'],'activeCampaignChanged':False,'visualApproved':False,'walkDriveAccepted':False,'eighteenVersusEighteenAccepted':False}
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    (DIRECTORY/'native-latest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    unreal.log('WAR_T1_PROTOTYPES_BUILT='+fingerprint[:12])
