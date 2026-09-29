"""Private, hash-guarded native pilot. Never modifies a source capital package."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import unreal

sys.path.insert(0,str(Path(__file__).parent))
from dutch_bastion import ROOT, OUT, digest, validate, native_mesh
from world_actor_state import snapshot
from capital_geography import height

CONTENT=ROOT/'unreal/AegisWar/Content'
assets=unreal.EditorAssetLibrary
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
plan=json.loads((OUT/'pilot-plan.json').read_text());validate(plan)
architecture=json.loads((OUT/'architecture.json').read_text())
if architecture['planSignature']!=plan['signature']: raise RuntimeError('Stale architecture')
if architecture['geometrySignature']!=digest(architecture['houses']): raise RuntimeError('Geometry fingerprint changed')
if hashlib.sha256((ROOT/'public/assets/maps/aegis_capital.json').read_bytes()).hexdigest()!=plan['sourceSha256']:
    raise RuntimeError('Campaign terrain changed after planning')
revision=digest(dict(plan=plan['signature'],geometry=architecture['geometrySignature'],nativeRevision=6))[:12]
DEST='/Game/WorldRebuild/DutchBastion_'+revision
RUN=OUT/revision;RUN.mkdir(parents=True,exist_ok=True)


def sha(file): return hashlib.sha256(file.read_bytes()).hexdigest()


def package_file(package,extension='.umap'):
    if not package.startswith('/Game/'): raise RuntimeError('Private project package required')
    file=(CONTENT/(package[6:]+extension)).resolve();file.relative_to(CONTENT.resolve())
    return file


def save(asset):
    if not assets.save_loaded_asset(asset,False): raise RuntimeError('Save failed: '+asset.get_path_name())


def baseline():
    path=OUT/'baseline.json'
    if path.exists():
        data=json.loads(path.read_text())
        for file,expected in data['hashes'].items():
            if sha(ROOT/file)!=expected: raise RuntimeError('Source changed; preserve and reconcile: '+file)
        return data
    manifest=json.loads((ROOT/'artifacts/unreal/world-portals/zone-manifest.json').read_text())
    zone=next(z for z in manifest['zones'] if z['id']=='aegis_capital')
    hashes={};rows={}
    for kind,package in zone['levels'].items():
        file=package_file(package);hashes[file.relative_to(ROOT).as_posix()]=sha(file)
        if not levels.load_level(package): raise RuntimeError('Source map missing')
        rows[kind]=[dict(name=a.get_name(),state=snapshot(a)) for a in actors.get_all_level_actors()
                    if a.get_outer().get_path_name().split('.')[0]==package]
    for file in (ROOT/'unreal/AegisWar/Saved/WorldEdit/crownward-draft.json',ROOT/'public/assets/maps/aegis_capital.json'):
        if file.exists(): hashes[file.relative_to(ROOT).as_posix()]=sha(file)
    data=dict(schemaVersion=1,levels=zone['levels'],hashes=hashes,actors=rows)
    path.write_text(json.dumps(data,indent=2)+'\n')
    return data


def material(role,palette):
    if role.startswith('/Game/'):
        result=unreal.load_asset(role)
        if not isinstance(result,unreal.MaterialInterface): raise RuntimeError('Missing retained surface material: '+role)
        return result
    name=f'M_{role}_{palette}'
    path=DEST+'/Materials/'+name
    if assets.does_asset_exist(path):
        obj=unreal.load_asset(path)
        if assets.get_metadata_tag(obj,'WarDutchRevision')!=revision: raise RuntimeError('Unowned material')
        return obj
    tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
    result=tools.create_asset(name,DEST+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    if not result: raise RuntimeError('Cannot create material')
    texture_name={'brick':'brick_baseColor','limestone':'stone_baseColor','paving':'paving_baseColor','plaster':'stone_baseColor'}
    if role in texture_name:
        source=ROOT/'public/assets/textures/aegis_city'/(texture_name[role]+'.png')
        target=DEST+'/Textures/'+texture_name[role]
        if not assets.does_asset_exist(target):
            task=unreal.AssetImportTask();task.filename=str(source);task.destination_path=DEST+'/Textures'
            task.destination_name=texture_name[role];task.automated=True;task.save=True
            tools.import_asset_tasks([task])
        texture=unreal.load_asset(target)
    elif role=='timber':
        relative=Path('Medieval_Mod_Town/Textures/Seamless/T_Wood_Plank.uasset')
        source=ROOT/'artifacts/unreal/licensed-kits/CityKitStaging/Content'/relative
        target=CONTENT/relative
        if target.exists() and sha(target)!=sha(source): raise RuntimeError('Preserve changed purchased texture')
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        texture=unreal.load_asset('/Game/'+relative.with_suffix('').as_posix())
    else:
        texture=unreal.load_asset('/Game/Medieval_Mod_Town/Textures/'+{
            'roof':'T_Roof_Hipoly','timber':'T_Roof_Frame','glass':'T_Wall_W','iron':'T_Roof_Frame'}[role])
    if not isinstance(texture,unreal.Texture2D): raise RuntimeError('Missing authored texture: '+role)
    tex=lib.create_material_expression(result,unreal.MaterialExpressionTextureSample)
    tex.texture=texture;tex.sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR
    tint=lib.create_material_expression(result,unreal.MaterialExpressionConstant3Vector)
    colors={'brick':[(1.1,.94,.83),(.83,.68,.61),(1.3,1.07,.88),(.67,.62,.57),(1.1,.95,.8)][palette],
        'limestone':(1.1,1.07,.94),'roof':(.85,.7,.57) if palette%2 else (.42,.52,.62),
        'timber':(.31,.37,.32),'glass':(.005,.009,.012),'iron':(.10,.11,.12),
        'paving':(.80,.82,.79),'plaster':(1.5,1.42,1.23)}
    tint.constant=unreal.LinearColor(*colors[role],1)
    multiply=lib.create_material_expression(result,unreal.MaterialExpressionMultiply)
    lib.connect_material_expressions(tex,'RGB',multiply,'A');lib.connect_material_expressions(tint,'',multiply,'B')
    lib.connect_material_property(tint if role in ('glass','iron') else multiply,'',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=lib.create_material_expression(result,unreal.MaterialExpressionConstant);rough.r=.28 if role=='glass' else .85
    lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    if role=='glass':
        glow=lib.create_material_expression(result,unreal.MaterialExpressionConstant3Vector)
        glow.constant=unreal.LinearColor(.06,.025,.008,1) if palette%3==0 else unreal.LinearColor(0,0,0,1)
        lib.connect_material_property(glow,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    assets.set_metadata_tag(result,'WarDutchRevision',revision)
    lib.recompile_material(result);save(result)
    return result


def build_assets():
    receipt=RUN/'assets.json'
    if receipt.exists():
        data=json.loads(receipt.read_text())
        for r in data['houses']:
            if sha(package_file(r['mesh'].split('.')[0],'.uasset'))!=r['sha256']: raise RuntimeError('Preserve edited house')
        return data
    progress=RUN/'assets-progress.json'
    rows=json.loads(progress.read_text()) if progress.exists() else []
    existing={r['id']:r for r in rows}
    reusable={}
    recipe=RUN/'asset-recipe.json'
    if recipe.exists():
        for old_receipt in OUT.glob('*/assets.json'):
            previous=old_receipt.parent
            if previous==RUN or not (previous/'asset-recipe.json').exists(): continue
            if json.loads((previous/'asset-recipe.json').read_text())!=json.loads(recipe.read_text()): continue
            source_files=[previous/'source-architecture.json',previous/'source-placement.json']
            if not all(p.exists() for p in source_files): continue
            sources=json.loads(source_files[0].read_text())['houses']+json.loads(source_files[1].read_text())['surfaces']
            bindings={r['id']:r for r in json.loads(old_receipt.read_text())['houses']}
            for source in sources:
                if source['id'] in bindings:
                    reusable[(source['meshSha256'],source['palette'],tuple(source['materials']))]=bindings[source['id']]
    tools=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem)
    for row in architecture['houses']:
        key='SM_'+row['id'];path=DEST+'/Meshes/'+key
        if row['id'] in existing:
            if sha(package_file(existing[row['id']]['mesh'].split('.')[0],'.uasset'))!=existing[row['id']]['sha256']: raise RuntimeError('Edited partial asset')
            continue
        reusable_key=(row.get('meshSha256'),row['palette'],tuple(row['materials']))
        if reusable_key in reusable:
            binding=reusable[reusable_key]
            if sha(package_file(binding['mesh'].split('.')[0],'.uasset'))!=binding['sha256']: raise RuntimeError('Changed reusable asset')
            rows.append({**binding,'id':row['id']})
            progress.write_text(json.dumps(rows,indent=2)+'\n')
            continue
        if assets.does_asset_exist(path): raise RuntimeError('Unreceipted native house: '+path)
        if 'meshFile' in row:
            source=(OUT/row['meshFile']).resolve();source.relative_to(OUT.resolve())
            if sha(source)!=row['meshSha256']: raise RuntimeError('Edited source geometry')
            m=native_mesh(json.loads(source.read_text()))
        else: m=row['mesh']
        materials=[material(role,row['palette']) for role in row['materials']]
        mesh=unreal.WarImportLibrary.create_composite_world_surface('DutchBastion_'+revision,key,
            [unreal.Vector(*p) for p in m['positions']],m['indices'],[unreal.Vector(*n) for n in m['normals']],
            [unreal.Vector2D(*uv) for uv in m['uvs']],[],m['triangleMaterials'],materials,True)
        if not mesh: raise RuntimeError('Native mesh construction failed: '+key)
        lod=unreal.EditorScriptingMeshReductionOptions();lod.auto_compute_lod_screen_size=True
        lod.reduction_settings=[unreal.EditorScriptingMeshReductionSettings(percent_triangles=p,screen_size=s)
                                for p,s in ((1,1),(.65,.4),(.3,.15))]
        tools.set_lods(mesh,lod);save(mesh)
        rows.append(dict(id=row['id'],mesh=mesh.get_path_name(),sha256=sha(package_file(path,'.uasset')),
                         triangles=[mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())]))
        progress.write_text(json.dumps(rows,indent=2)+'\n')
        unreal.log('WAR_DUTCH_HOUSE='+key)
    data=dict(revision=revision,geometrySignature=architecture['geometrySignature'],houses=rows)
    receipt.write_text(json.dumps(data,indent=2)+'\n')
    return data


def in_pilot(a):
    centre,extent=a.get_actor_bounds(False)
    return centre.y+extent.y>-11400 and centre.y-extent.y<-7000 and centre.x+extent.x>-5600 and centre.x-extent.x<400


def furnish(parent,row):
    """Fit reviewed kit furniture around a clear entrance lane; attach to GM owner."""
    lot=next(l for b in plan['blocks'] for l in b['lots'] if l['id']==row['id'])
    a,b=row.get('frame',lot['polygon'][:2]);width=math.dist(a,b);dx,dy=(b[0]-a[0])/width,(b[1]-a[1])/width
    local=lambda p:((p[0]-a[0])*dx+(p[1]-a[1])*dy,-(p[0]-a[0])*dy+(p[1]-a[1])*dx)
    polygon=[local(p) for p in lot['polygon']]
    def inside(p):
        return all((v[0]-u[0])*(p[1]-u[1])-(v[1]-u[1])*(p[0]-u[0])>.12*math.dist(u,v)
                   for u,v in zip(polygon,polygon[1:]+polygon[:1]))
    occupied=[];result=[];yaw=math.degrees(math.atan2(dx,dy))
    centre=[sum(p[i] for p in polygon)/len(polygon) for i in range(2)]
    lane=[(width*.25,0),(width*.25,.8),centre]
    def distance_to_segment(p,a,b):
        v=[b[i]-a[i] for i in range(2)];length=sum(x*x for x in v)
        t=max(0,min(1,sum((p[i]-a[i])*v[i] for i in range(2))/length))
        return math.dist(p,[a[i]+t*v[i] for i in range(2)])
    names=[('SM_Table',(.45,.6,.9)),('SM_Bench',(.5,1,1)),('SM_Barrel',(1,1,1))]
    if row['publicInterior']['kind']=='shop': names.append(('SM_Bookshelf',(.55,.55,.65)))
    for index,(name,scale) in enumerate(names):
        mesh=unreal.load_asset('/Game/Medieval_Mod_Town/Meshes/'+name)
        if not isinstance(mesh,unreal.StaticMesh): raise RuntimeError('Missing reviewed furnishing: '+name)
        bounds=mesh.get_bounds();ex=bounds.box_extent.x*scale[0]/100;ey=bounds.box_extent.y*scale[1]/100
        found=None
        for y_step in range(22,5,-1):
            y=y_step*.25
            for x_step in range(int(width*4)-2,2,-1):
                x=x_step*.25;corners=[(x+s*ex,y+t*ey) for s in (-1,1) for t in (-1,1)]
                if not all(inside(p) for p in corners): continue
                # Reserve a 1.6m lane from the actual door through the room.
                if any(distance_to_segment((x,y),u,v)<math.hypot(ex,ey)+.6 for u,v in zip(lane,lane[1:])): continue
                if any(abs(x-u)<ex+rx+.18 and abs(y-v)<ey+ry+.18 for u,v,rx,ry in occupied): continue
                found=(x,y);break
            if found: break
        if found is None: raise RuntimeError('Cannot furnish without clipping: '+row['id']+'/'+name)
        x,y=found;occupied.append((x,y,ex,ey))
        centre=[row['position'][0]+(dy*x+dx*y)*100,row['position'][1]+(dx*x-dy*y)*100,row['position'][2]]
        angle=math.radians(yaw);ox=bounds.origin.x*scale[0];oy=bounds.origin.y*scale[1]
        position=[centre[0]-math.cos(angle)*ox+math.sin(angle)*oy,centre[1]-math.sin(angle)*ox-math.cos(angle)*oy,
                  centre[2]-(bounds.origin.z-bounds.box_extent.z)*scale[2]]
        actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*position),unreal.Rotator(yaw=yaw))
        actor.set_actor_scale3d(unreal.Vector(*scale));actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_collision_profile_name('BlockAll');actor.tags=['WarDutchFurnishing',row['actorId']]
        actor.attach_to_actor(parent,'',unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False)
        result.append(dict(name=name,actor=actor.get_name(),state=snapshot(actor)))
    lamp=actors.spawn_actor_from_class(unreal.PointLight,unreal.Vector(row['entrance'][0]+row['direction'][0]*270,
        row['entrance'][1]+row['direction'][1]*270,row['position'][2]+265))
    lamp.light_component.set_editor_property('intensity',1600)
    lamp.light_component.set_editor_property('intensity_units',unreal.LightUnits.LUMENS)
    lamp.light_component.set_editor_property('attenuation_radius',750)
    lamp.light_component.set_editor_property('use_temperature',True);lamp.light_component.set_editor_property('temperature',2900)
    lamp.light_component.set_editor_property('cast_shadows',False)
    lamp.tags=['WarDutchFurnishing',row['actorId']]
    lamp.attach_to_actor(parent,'',unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False)
    result.append(dict(name='warm_interior_light',actor=lamp.get_name(),state=snapshot(lamp)))
    return result


def build_pilot():
    original=baseline();models=build_assets();receipt=RUN/'pilot.json'
    if receipt.exists():
        data=json.loads(receipt.read_text())
        for p,h in data['packageHashes'].items():
            if sha(package_file(p))!=h: raise RuntimeError('Pilot changed; preserve editor changes')
        unreal.log('WAR_DUTCH_ALREADY_BUILT');return data
    copied=[];removed=[];preserved=[];relocated=[]
    # Duplicates remain private and detached from the current map/zone manifest.
    # Record removals before applying them; only owned house meshes are eligible.
    for kind,source in original['levels'].items():
        target=DEST+'/Layers/'+kind
        if assets.does_asset_exist(target): raise RuntimeError('Unreceipted copied level: '+target)
        if not assets.duplicate_asset(source,target) or not levels.load_level(target): raise RuntimeError('Copy failed')
        for a in list(actors.get_all_level_actors()):
            if a.get_outer().get_path_name().split('.')[0]!=target: continue
            tags={str(t) for t in a.tags}
            mesh=a.static_mesh_component.static_mesh if isinstance(a,unreal.StaticMeshActor) else None
            path=mesh.get_path_name() if mesh else ''
            owned=bool(tags.intersection({'WarCapitalBuilding','WarCapitalExpansionV1','WarCrownwardKit'}))
            house=('/Crownward/SM_MH_02_House_' in path or '/CapitalExpansion/' in path)
            if owned and house and 'WarCapitalInterior' not in tags and in_pilot(a):
                removed.append(dict(layer=kind,name=a.get_name(),state=snapshot(a)))
            else: preserved.append(dict(layer=kind,name=a.get_name(),state=snapshot(a)))
        (RUN/'copy-journal.json').write_text(json.dumps(dict(sourceHashes=original['hashes'],removed=removed),indent=2)+'\n')
        by_name={a.get_name():a for a in actors.get_all_level_actors()}
        for row in [r for r in removed if r['layer']==kind]:
            a=by_name[row['name']]
            if snapshot(a)!=row['state'] or not actors.destroy_actor(a): raise RuntimeError('Copied actor changed')
        # Retain this existing furnished home, including its attached lighting,
        # as an enclosed court house. Its old footprint crosses the new frontage.
        for a in by_name.values():
            if 'WarWorldObject_expansion_v1_aegis_capital_001' not in {str(t) for t in a.tags}: continue
            family=[a]+list(a.get_attached_actors())
            before={child.get_name():snapshot(child) for child in family}
            centre,extent=a.get_actor_bounds(False)
            destination=unreal.Vector(-2350,-9380,a.get_actor_location().z)
            offset=destination-a.get_actor_location()
            corners=[((centre.y+offset.y+sy*extent.y)/100,(centre.x+offset.x+sx*extent.x)/100)
                     for sx in (-1,1) for sy in (-1,1)]
            court=plan['blocks'][0]['court']
            for p in corners:
                if not all((v[0]-u[0])*(p[1]-u[1])-(v[1]-u[1])*(p[0]-u[0])>math.dist(u,v)
                           for u,v in zip(court,court[1:]+court[:1])):
                    raise RuntimeError('Retained home does not fit the backcourt')
            a.set_actor_location(destination,False,True)
            for child in family:
                relocated.append(dict(layer=kind,name=child.get_name(),before=before[child.get_name()],after=snapshot(child)))
        for row in [r for r in preserved if r['layer']==kind]:
            if any(r['layer']==kind and r['name']==row['name'] for r in relocated): continue
            a=by_name[row['name']]
            if snapshot(a)!=row['state']:
                (RUN/'state-conflict.json').write_text(json.dumps(dict(name=row['name'],before=row['state'],after=snapshot(a)),indent=2)+'\n')
                raise RuntimeError('Unrelated actor changed: '+row['name'])
        if not levels.save_current_level(): raise RuntimeError('Copied layer save failed')
        copied.append(target)
    target=DEST+'/Bastion_Dutch_Pilot'
    if not levels.new_level(target): raise RuntimeError('Pilot map failed')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for p in copied:
        if not unreal.EditorLevelUtils.add_level_to_world(world,p,unreal.LevelStreamingAlwaysLoaded): raise RuntimeError('Attach failed')
    unreal.GameplayStatics.flush_level_streaming(world)
    if not levels.set_current_level_by_name('Bastion_Dutch_Pilot'): raise RuntimeError('Wrong current level')
    bindings={r['id']:r for r in models['houses']};added=[]
    for row in architecture['houses']:
        a=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*row['position']))
        a.set_actor_label(row['publicInterior']['name'] if row['publicInterior'] else row['id'])
        a.set_folder_path('Dutch Bastion/Cinderbank')
        a.static_mesh_component.set_static_mesh(unreal.load_asset(bindings[row['id']]['mesh']))
        a.static_mesh_component.set_collision_profile_name('BlockAll')
        a.tags=['WarDutchBastion','WarCapitalBuilding','WarWorldObject_'+row['actorId'],'WarModelSha256_'+bindings[row['id']]['sha256']]
        furnishing=[]
        if row['publicInterior']:
            a.tags=list(a.tags)+['WarCapitalInterior'];furnishing=furnish(a,row)
        added.append(dict(id=row['actorId'],actor=a.get_name(),state=snapshot(a),furnishing=furnishing))
    start=actors.spawn_actor_from_class(unreal.PlayerStart,unreal.Vector(-5480,-9120,110))
    start.tags=['WarDutchProofStart'];start.set_actor_label('Dutch block isolated review start')
    if not levels.save_current_level(): raise RuntimeError('Pilot save failed')
    baseline()
    data=dict(revision=revision,map=target,layers=copied,removed=removed,added=added,relocated=relocated,
              preservedActorCount=len(preserved),sourcePackagesUnchanged=True,
              packageHashes={p:sha(package_file(p)) for p in copied+[target]},
              acceptance=dict(visual=False,traversal=False,citywide=False,release=False))
    receipt.write_text(json.dumps(data,indent=2)+'\n');(OUT/'current.json').write_text(json.dumps(dict(revision=revision,map=target),indent=2)+'\n')
    unreal.log('WAR_DUTCH_PILOT='+target)
    return data


def render():
    data=json.loads((RUN/'pilot.json').read_text())
    if not levels.load_level(data['map']): raise RuntimeError('Missing pilot')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
    c=capture.capture_component2d;c.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1600,1000,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    c.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR;c.capture_every_frame=False;c.capture_on_movement=False
    c.always_persist_rendering_state=True;c.fov_angle=68;c.post_process_blend_weight=0
    views=[('aerial',(-8000,-14000,5500),(-2200,-9100,700)),
           ('canal',(450,-11900,200),(-50,-7800,850)),
           ('street',(-5800,-11300,180),(-3500,-10800,650)),
           ('court',(-2900,-9300,200),(-2000,-7500,650))]
    for name,eye,target in views:
        eye=unreal.Vector(*eye);target=unreal.Vector(*target)
        capture.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,target),False,True)
        for _ in range(12): unreal.WarImportLibrary.prepare_world_preview_frame(world);c.capture_scene()
        unreal.RenderingLibrary.export_render_target(world,c.texture_target,str(RUN),name+'.png')
    unreal.log('WAR_DUTCH_RENDERED='+str(RUN))


def proof_config():
    data=json.loads((RUN/'pilot.json').read_text())
    for p,h in data['packageHashes'].items():
        if sha(package_file(p))!=h: raise RuntimeError('Pilot changed before proof')
    views=[dict(id=n,eye=e,target=t) for n,e,t in [
        ('aerial',[-8000,-14000,5500],[-2200,-9100,700]),
        ('canal',[450,-11900,200],[-50,-7800,850]),
        ('street',[-5800,-11300,180],[-3500,-10800,650]),
        ('court',[-3850,-9550,200],[-2300,-8000,650])]]
    routes=[]
    for r in architecture['houses']:
        if not r['publicInterior']: continue
        e=r['entrance'];d=r['direction']
        point=lambda distance:[e[0]+d[0]*distance,e[1]+d[1]*distance,e[2]+2]
        lot=next(l for b in plan['blocks'] for l in b['lots'] if l['id']==r['id'])
        centre=[sum(p[1] for p in lot['polygon'])*25,sum(p[0] for p in lot['polygon'])*25,e[2]+2]
        routes.append(dict(id=r['id'],points=[point(-160),point(80),centre,point(80),point(-160)]))
        views.append(dict(id=r['id'],eye=[*point(130)[:2],e[2]+175],target=[*centre[:2],e[2]+145]))
    opening=plan['blocks'][0]['openings'][0]['polygon']
    a,b,c,d=opening
    mid=lambda p,q:[(p[1]+q[1])*50,(p[0]+q[0])*50,height((p[0]+q[0])/2,(p[1]+q[1])/2)*100+3]
    front=mid(a,b);rear=mid(c,d);v=[rear[i]-front[i] for i in (0,1)];length=math.hypot(*v)
    outside=[front[i]-v[i]/length*150 for i in (0,1)]+[front[2]]
    routes.append(dict(id='courtyard_passage',points=[outside,front,rear,front,outside]))
    config=dict(map=data['map'],signature=architecture['geometrySignature'],views=views,routes=routes)
    (CONTENT/'Migration/dutch-bastion-proof.json').write_text(json.dumps(config,indent=2)+'\n')
    (RUN/'proof-config.json').write_text(json.dumps(config,indent=2)+'\n')


def survey():
    data=json.loads((RUN/'pilot.json').read_text())
    if not levels.load_level(data['map']): raise RuntimeError('Pilot missing')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    config=json.loads((RUN/'proof-config.json').read_text());hits=[]
    for route in config['routes']:
        for a,b in zip(route['points'],route['points'][1:]):
            start=unreal.Vector(*a)+unreal.Vector(0,0,105);end=unreal.Vector(*b)+unreal.Vector(0,0,105)
            hit=unreal.SystemLibrary.capsule_trace_single(world,start,end,42,96,
                unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,True)
            if hit: hits.append(dict(route=route['id'],hit=str(hit.to_tuple())))
    (RUN/'capsule-survey.json').write_text(json.dumps(hits,indent=2)+'\n')


if __name__=='__main__':
    if Path(unreal.Paths.project_dir()).resolve()!=ROOT/'unreal/AegisWar': raise RuntimeError('Use AegisWar')
    stage=os.environ.get('WAR_DUTCH_STAGE','pilot')
    if stage=='baseline': baseline()
    elif stage=='assets': build_assets()
    elif stage=='pilot': build_pilot()
    elif stage=='render': render()
    elif stage=='proof-config': proof_config()
    elif stage=='survey': survey()
    else: raise RuntimeError('Unknown Dutch Bastion stage')
