"""Apply Bastion's citywide architecture to guarded copies of owned layers."""
import importlib.util
import json
import math
import os
import inspect
import re
from pathlib import Path
import sys
import unreal

sys.path.insert(0,str(Path(__file__).parent))
spec=importlib.util.spec_from_file_location('dutch_native',Path(__file__).with_name('native-dutch-bastion.py'))
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
from dutch_bastion import ROOT, OUT, digest, native_mesh
from world_actor_state import snapshot
from dutch_city_ground import paving_height, data as ground_data


def configure():
    plan=json.loads((OUT/'city-plan.json').read_text())
    architecture=json.loads((OUT/'city-architecture.json').read_text())
    placement=json.loads((OUT/'city-placement.json').read_text())
    overlap=json.loads((OUT/'overlap-audit.json').read_text())
    if overlap.get('geometrySignature')!=architecture['geometrySignature'] or not overlap.get('passed') or overlap.get('failures'):
        raise RuntimeError('Finished mesh overlap audit is missing or stale')
    if plan['groundSignature']!=ground_data()['signature']: raise RuntimeError('Stale city grading')
    if architecture['planSignature']!=digest(plan) or placement['planSignature']!=digest(plan): raise RuntimeError('Stale city input')
    if architecture['pending'] or placement['conflicts'] or any(not r.get('geometryResolved') for r in plan['pendingBlocks']):
        raise RuntimeError('Unresolved city geometry or ownership')
    if plan['publicVenues']['pending'] or plan['streetReview']['pending']: raise RuntimeError('Unresolved access')
    if architecture['geometrySignature']!=digest(architecture['houses']): raise RuntimeError('Edited architecture manifest')
    n.plan=plan;n.architecture=dict(houses=architecture['houses']+placement['surfaces'])
    n.architecture['geometrySignature']=digest(n.architecture['houses'])
    n.revision=digest(dict(plan=digest(plan),geometry=n.architecture['geometrySignature'],placement=digest(placement),nativeRevision=3))[:12]
    n.DEST='/Game/WorldRebuild/DutchBastion_'+n.revision;n.RUN=OUT/n.revision;n.RUN.mkdir(exist_ok=True)
    for name,value in (('source-architecture.json',architecture),('source-placement.json',placement),('source-plan.json',plan),('source-overlap-audit.json',overlap)):
        target=n.RUN/name
        if target.exists() and digest(json.loads(target.read_text()))!=digest(value): raise RuntimeError('Edited revision input: '+name)
        if not target.exists(): target.write_text(json.dumps(value,separators=(',',':'))+'\n')
    recipe=dict(material=digest(inspect.getsource(n.material)),mesh=digest(inspect.getsource(native_mesh)),importerRevision=2)
    recipe_path=n.RUN/'asset-recipe.json'
    if recipe_path.exists() and json.loads(recipe_path.read_text())!=recipe: raise RuntimeError('Native asset recipe changed')
    recipe_path.write_text(json.dumps(recipe,indent=2)+'\n')
    return plan,architecture,placement


def build_city():
    plan,architecture,placement=configure();baseline=n.baseline();models=n.build_assets()
    receipt=n.RUN/'city.json'
    if receipt.exists():
        data=json.loads(receipt.read_text())
        for package,sha in data['packageHashes'].items():
            if n.sha(n.package_file(package))!=sha: raise RuntimeError('Preserve changed city revision')
        for package,sha in data.get('visualHashes',{}).items():
            if n.sha(n.package_file(package,'.uasset'))!=sha: raise RuntimeError('Preserve edited city material/model')
        unreal.log('WAR_DUTCH_CITY_ALREADY_BUILT');return data
    changes=[];copies={}
    for kind,source in baseline['levels'].items():
        target=n.DEST+'/Layers/'+kind
        if n.assets.does_asset_exist(target): raise RuntimeError('Unreceipted copied layer: '+target)
        if not n.assets.duplicate_asset(source,target) or not n.levels.load_level(target): raise RuntimeError('Cannot copy source capital')
        current={a.get_name():a for a in n.actors.get_all_level_actors() if a.get_outer().get_path_name().split('.')[0]==target}
        expected={r['name']:r['state'] for r in baseline['actors'][kind]}
        for name,state in expected.items():
            if name not in current or snapshot(current[name])!=state: raise RuntimeError('Copied source actor differs: '+name)
        actions=[r for r in placement['actions'] if r['layer']==kind]
        for action in actions:
            actor=current[action['name']]
            if snapshot(actor)!=action['before']: raise RuntimeError('Actor changed after survey: '+action['name'])
            change=dict(action=action['action'],layer=kind,name=action['name'],before=snapshot(actor))
            if action['action'] in ('remove_owned_house','remove_owned_street'):
                if not n.actors.destroy_actor(actor): raise RuntimeError('Cannot remove owned house')
            else:
                children=list(actor.get_attached_actors());change['childrenBefore']={a.get_name():snapshot(a) for a in children}
                actor.set_actor_location(unreal.Vector(*action['location']),False,True);change['after']=snapshot(actor)
                change['childrenAfter']={a.get_name():snapshot(a) for a in children}
            changes.append(change)
        changed={r['name'] for r in actions}
        changed.update(name for r in changes if r['layer']==kind for name in r.get('childrenAfter',{}))
        for name,state in expected.items():
            if name not in changed and snapshot(current[name])!=state: raise RuntimeError('Unrelated actor changed: '+name)
        (n.RUN/'city-copy-journal.json').write_text(json.dumps(dict(sourceHashes=baseline['hashes'],changes=changes),indent=2)+'\n')
        if not n.levels.save_current_level(): raise RuntimeError('Copy save failed')
        copies[kind]=target
    geometry=n.DEST+'/Layers/Bastion_Dutch_Geometry'
    if not n.levels.new_level(geometry): raise RuntimeError('Cannot create city architecture layer')
    bindings={r['id']:r for r in models['houses']};added=[]
    for row in n.architecture['houses']:
        actor=n.actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*row['position']))
        actor.set_actor_label(row['publicInterior']['name'] if row['publicInterior'] else row['district'].replace('_',' ').title()+' Dutch '+('paving' if row.get('surface') else 'house')+' '+row['id'])
        actor.set_folder_path('Dutch Bastion/'+row['district'])
        actor.static_mesh_component.set_static_mesh(unreal.load_asset(bindings[row['id']]['mesh']))
        actor.static_mesh_component.set_collision_profile_name('BlockAll')
        actor.tags=['WarDutchBastion','WarCityStreet' if row.get('surface') else 'WarCapitalBuilding',
                    'WarWorldObject_'+row['actorId'],'WarModelSha256_'+bindings[row['id']]['sha256']]
        furnishing=[]
        if row['publicInterior']:
            actor.tags=list(actor.tags)+['WarCapitalInterior'];furnishing=n.furnish(actor,row)
        added.append(dict(id=row['actorId'],actor=actor.get_name(),state=snapshot(actor),furnishing=furnishing))
    # Reproduce actual GM additions, preserving the original draft byte-for-byte.
    draft=json.loads((ROOT/'unreal/AegisWar/Saved/WorldEdit/crownward-draft.json').read_text())
    original={r['id']:r for r in json.loads(draft['baseline'])['objects']}
    for row in draft['objects']:
        if row==original.get(row['id']): continue
        if row['id'] in original: raise RuntimeError('Existing GM edit needs explicit reconciliation: '+row['id'])
        mesh_path,sha=row['sourceIdentity'].rsplit(':',1);transform=row['transform'];mesh=unreal.load_asset(mesh_path)
        if not isinstance(mesh,unreal.StaticMesh): raise RuntimeError('Missing GM draft mesh')
        actor=n.actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*transform[:3]))
        rotation=unreal.Quat(*transform[3:7]).rotator()
        actor.set_actor_rotation(rotation,False);actor.set_actor_scale3d(unreal.Vector(*transform[7:10]))
        actor.static_mesh_component.set_static_mesh(mesh);actor.static_mesh_component.set_collision_profile_name('BlockAll')
        actor.tags=['WarWorldObject_'+row['id'],'WarModelSha256_'+sha]
        actor.set_actor_hidden_in_game(row['hidden']);added.append(dict(id=row['id'],actor=actor.get_name(),state=snapshot(actor),preservedGmDraft=True))
    # Dense streets need readable blue-grey fill beneath the retained dusk sun.
    # This light belongs to the capital layer and unloads with that zone.
    fill=n.actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,15000),unreal.Rotator(pitch=-45,yaw=55))
    fill.set_actor_label('Bastion overcast street fill')
    fill.light_component.set_editor_property('intensity',3500)
    fill.light_component.set_editor_property('cast_shadows',False)
    fill.light_component.set_editor_property('atmosphere_sun_light',False)
    fill.light_component.set_editor_property('forward_shading_priority',0)
    fill.light_component.set_editor_property('use_temperature',False)
    fill.light_component.set_editor_property('light_color',unreal.Color(173,192,218,255))
    fill.tags=['WarDutchBastion','WarWorldObject_dutch_bastion_overcast_fill']
    added.append(dict(id='dutch_bastion_overcast_fill',actor=fill.get_name(),state=snapshot(fill)))
    if not n.levels.save_current_level(): raise RuntimeError('City geometry save failed')
    target=n.DEST+'/Bastion_Dutch_City'
    if not n.levels.new_level(target): raise RuntimeError('Cannot create city review root')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for package in list(copies.values())+[geometry]:
        if not unreal.EditorLevelUtils.add_level_to_world(world,package,unreal.LevelStreamingAlwaysLoaded): raise RuntimeError('Cannot attach city layer')
    unreal.GameplayStatics.flush_level_streaming(world)
    n.levels.set_current_level_by_name('Bastion_Dutch_City')
    start=n.actors.spawn_actor_from_class(unreal.PlayerStart,unreal.Vector(-13600,0,110))
    start.tags=['WarDutchProofStart']
    if not n.levels.save_current_level(): raise RuntimeError('City root save failed')
    n.baseline()
    packages=list(copies.values())+[geometry,target]
    registry=unreal.AssetRegistryHelpers.get_asset_registry();pending=[];visual_hashes={}
    for actor in added:
        for state in [actor['state'],*[f['state'] for f in actor.get('furnishing',[])]]:
            for component in state['components']:
                pending.extend(p.split('.')[0] for p in [component.get('mesh'),*component.get('materials',[])] if p)
    while pending:
        package=pending.pop()
        if not package.startswith('/Game/') or package in visual_hashes: continue
        file=n.package_file(package,'.uasset')
        if not file.exists(): raise RuntimeError('Missing city visual dependency: '+package)
        visual_hashes[package]=n.sha(file)
        pending.extend(str(p) for p in registry.get_dependencies(package,unreal.AssetRegistryDependencyOptions()))
    data=dict(revision=n.revision,map=target,layers=copies,geometryLayer=geometry,changes=changes,added=added,
              packageHashes={p:n.sha(n.package_file(p)) for p in packages},sourceHashes=baseline['hashes'],
              visualHashes=visual_hashes,
              coverage=placement['coverage'],acceptance=dict(visual=False,traversal=False,release=False))
    receipt.write_text(json.dumps(data,indent=2)+'\n')
    (OUT/'city-current.json').write_text(json.dumps(dict(revision=n.revision,map=target),indent=2)+'\n')
    unreal.log('WAR_DUTCH_CITY_BUILT='+target)
    return data


def proof_config(quick=False,write=True):
    plan,architecture,placement=configure();data=json.loads((n.RUN/'city.json').read_text())
    for p,h in data['packageHashes'].items():
        if n.sha(n.package_file(p))!=h: raise RuntimeError('City changed before proof')
    for p,h in data.get('visualHashes',{}).items():
        if n.sha(n.package_file(p,'.uasset'))!=h: raise RuntimeError('City visual dependency changed before proof')
    rows={r['id']:r for r in architecture['houses']}
    views=[dict(id='whole_city',eye=[-22000,-21500,24000],target=[-1000,0,1800])];routes=[]
    def street_camera(entrance):
        p=(entrance[1]/100,entrance[0]/100);choices=[]
        for street in plan['streets']:
            for a,b in zip(street['points'],street['points'][1:]):
                vector=[b[i]-a[i] for i in (0,1)];square=sum(v*v for v in vector)
                if square<1e-9: continue
                t=max(0,min(1,sum((p[i]-a[i])*vector[i] for i in (0,1))/square))
                q=[a[i]+t*vector[i] for i in (0,1)]
                choices.append((math.dist(p,q),q,vector,t))
        _,q,vector,t=min(choices,key=lambda c:c[0]);length=math.hypot(*vector)
        sign=-1 if t>.5 else 1
        distance=min(8,length*(t if sign<0 else 1-t))
        target=[q[i]+sign*vector[i]/length*distance for i in (0,1)]
        h=paving_height(*q)*100
        return [q[1]*100,q[0]*100,h+180],[target[1]*100,target[0]*100,paving_height(*target)*100+240]
    seen=set()
    for block in plan['blocks']:
        points=block['boundary'];cx=sum(p[0] for p in points)/len(points);cz=sum(p[1] for p in points)/len(points)
        if not quick:
            span=max(max(p[i] for p in points)-min(p[i] for p in points) for i in (0,1))
            views.append(dict(id=block['id']+'_aerial',eye=[cz*100-1800,cx*100-2300,paving_height(cx,cz)*100+max(6500,span*145)],
                              target=[cz*100,cx*100,paving_height(cx,cz)*100+600]))
        eligible=[rows[l['id']] for l in block['lots'] if rows[l['id']]['width']>=5]
        if not eligible: continue
        row=min(eligible,key=lambda r:(r['foundationRelief'],r['id']));e=row['entrance'];d=row['direction']
        if not quick or block['district'] not in seen:
            seen.add(block['district'])
            eye,target=street_camera(e)
            views.append(dict(id=block['id']+'_street',eye=eye,target=target))
        if not quick:
            for opening in block['openings']:
                if 'centreline' in opening: line=opening['centreline']
                else:
                    a,b,c,z=opening['polygon'];line=[[(a[i]+b[i])/2 for i in (0,1)],[(c[i]+z[i])/2 for i in (0,1)]]
                routes.append(dict(id=opening['id'],points=[[z*100,x*100,paving_height(x,z)*100+4] for x,z in line]))
    for row in architecture['houses']:
        if not row['publicInterior']: continue
        lot=next(l for b in plan['blocks'] for l in b['lots'] if l['id']==row['id'])
        e=row['entrance'];d=row['direction'];centre=[sum(p[1] for p in lot['polygon'])/len(lot['polygon'])*100,
            sum(p[0] for p in lot['polygon'])/len(lot['polygon'])*100,e[2]+2]
        def point(t):
            x,y=e[0]+d[0]*t,e[1]+d[1]*t
            return [x,y,paving_height(y/100,x/100)*100+4 if t<0 else e[2]+2]
        views.append(dict(id=row['id']+'_interior',eye=[*point(110)[:2],e[2]+175],target=[*centre[:2],e[2]+145]))
        if not quick:
            views.append(dict(id=row['id']+'_floor_detail',eye=[*point(110)[:2],e[2]+175],
                              target=[*centre[:2],e[2]+10]))
        routes.append(dict(id=row['id'],points=[point(-150),point(80),centre,point(80),point(-150)]))
    if not quick:
        for block in plan['blocks']:
            row=max((rows[l['id']] for l in block['lots']),key=lambda r:(r.get('clippedTriangles',0),r['id']))
            a,b=row['frame'];length=math.dist(a,b);dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length
            x,z=a[0]+dx*.1,a[1]+dy*.1;ex,ez=x+dy*2.5-dx*.9,z-dx*2.5-dy*.9
            views.append(dict(id=row['id']+'_corner_detail',
                              eye=[ez*100,ex*100,max(paving_height(ex,ez)*100+200,row['position'][2]+340)],
                              target=[z*100,x*100,row['position'][2]+290]))
    for street in plan['streets']:
        if quick and street['id'] not in ('sable_market','cinder_crescent','crownwatch_merchant_rise'): continue
        samples=[];length=0;part=0
        for a,b in zip(street['points'],street['points'][1:]):
            count=max(1,math.ceil(math.dist(a,b)/1.5))
            for i in range(count):
                x=a[0]+(b[0]-a[0])*i/count;z=a[1]+(b[1]-a[1])*i/count
                samples.append([z*100,x*100,paving_height(x,z)*100+4]);length+=math.dist(a,b)/count
                if length>=55 and len(samples)>1:
                    routes.append(dict(id=street['id']+'_'+str(part),points=samples));part+=1;samples=[samples[-1]];length=0
        x,z=street['points'][-1];samples.append([z*100,x*100,paving_height(x,z)*100+4])
        if len(samples)>1: routes.append(dict(id=street['id']+'_'+str(part),points=samples))
    config=dict(map=data['map'],signature=n.architecture['geometrySignature'],views=views,routes=routes,
                viewSettleSeconds=3,scope='city_quick' if quick else 'whole_city')
    if write:
        (n.CONTENT/'Migration/dutch-bastion-proof.json').write_text(json.dumps(config,indent=2)+'\n')
        (n.RUN/'proof-config.json').write_text(json.dumps(config,indent=2)+'\n')
    unreal.log(f'WAR_DUTCH_CITY_PROOF_CONFIG={len(views)} views, {len(routes)} routes')
    return config


def route_survey():
    config=proof_config(write=False)
    if not n.levels.load_level(config['map']): raise RuntimeError('Missing city survey map')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    unreal.WarImportLibrary.prepare_preview_frame(None)
    failures=[];samples=0
    for route in config['routes']:
        for index,point in enumerate(route['points']):
            samples+=1;p=unreal.Vector(*point)
            hit=unreal.SystemLibrary.line_trace_single(world,p+unreal.Vector(0,0,100),p-unreal.Vector(0,0,1500),
                unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,True)
            if not hit:
                failures.append(dict(route=route['id'],index=index,point=point,reason='missing_floor'));continue
            values=hit.to_tuple();floor=values[5];normal=values[7]
            if abs(floor.z-p.z)>40 or normal.z<.65:
                failures.append(dict(route=route['id'],index=index,point=point,floor=floor.z,normal=normal.z,
                                     actor=values[9].get_name() if values[9] else None))
    (n.RUN/'route-ground-survey.json').write_text(json.dumps(dict(map=config['map'],samples=samples,failures=failures),indent=2)+'\n')
    unreal.log(f'WAR_DUTCH_ROUTE_GROUND={samples} samples, {len(failures)} discrepancies')
    if failures: raise RuntimeError('Native route ground survey failed; inspect route-ground-survey.json')


def detail_config():
    config=proof_config(write=False)
    requested=json.loads((n.RUN/'detail-view-ids.json').read_text())
    views={v['id']:v for v in config['views']}
    if not requested or len(set(requested))!=len(requested) or any(v not in views for v in requested):
        raise RuntimeError('Supplemental review requires unique known view identities')
    overrides=n.RUN/'detail-camera-overrides.json'
    if overrides.exists():
        for key,camera in json.loads(overrides.read_text()).items():
            if key not in requested or set(camera)!={'eye','target'} or any(
                    not isinstance(p,list) or len(p)!=3 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in p)
                    for p in camera.values()):
                raise RuntimeError('Invalid supplemental camera override')
            views[key]={**views[key],**camera}
    config.update(views=[views[v] for v in requested],routes=[],scope='city_details')
    (n.CONTENT/'Migration/dutch-bastion-proof.json').write_text(json.dumps(config,indent=2)+'\n')
    (n.RUN/'proof-config.json').write_text(json.dumps(config,indent=2)+'\n')


def collision_survey():
    current=json.loads((OUT/'city-current.json').read_text())
    if not n.levels.load_level(current['map']): raise RuntimeError('Missing diagnostic world')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    pattern=r'WAR_DUTCH_ROUTE_BLOCKED=(\S+) feet=X=([-\d.]+) Y=([-\d.]+) Z=([-\d.]+) target=X=([-\d.]+) Y=([-\d.]+) Z=([-\d.]+)'
    results=[]
    for match in re.finditer(pattern,(OUT/'proof.log').read_text(errors='replace')):
        key,*values=match.groups();values=list(map(float,values))
        start=unreal.Vector(*values[:3])+unreal.Vector(0,0,96)
        end=unreal.Vector(*values[3:])+unreal.Vector(0,0,96)
        hits=unreal.SystemLibrary.capsule_trace_multi(world,start,end,42,96,unreal.TraceTypeQuery.ECC_VISIBILITY,
            False,[],unreal.DrawDebugTrace.NONE,True)
        rows=[]
        for hit in hits or []:
            actor=hit.to_tuple()[9]
            if actor: rows.append(dict(name=actor.get_name(),label=actor.get_actor_label(),state=snapshot(actor)))
        results.append(dict(route=key,feet=values[:3],target=values[3:],hits=rows))
    (OUT/current['revision']/'collision-survey.json').write_text(json.dumps(results,indent=2)+'\n')


def performance_config(baseline=False):
    plan,architecture,placement=configure();city=json.loads((n.RUN/'city.json').read_text())
    target=city['map']
    if baseline:
        target=n.DEST+'/Baseline_Comparison'
        receipt=n.RUN/'comparison-baseline.json'
        if receipt.exists():
            if n.sha(n.package_file(target))!=json.loads(receipt.read_text())['sha256']: raise RuntimeError('Edited comparison baseline')
        else:
            if n.assets.does_asset_exist(target): raise RuntimeError('Unreceipted comparison world')
            if not n.levels.new_level(target): raise RuntimeError('Cannot create comparison world')
            world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            comparison_layers=n.baseline()['levels'];comparison_revision='original'
            predecessor=n.RUN/'activation-backup/zone-manifest.json'
            if predecessor.exists():
                capital=next(z for z in json.loads(predecessor.read_text())['zones'] if z['id']=='aegis_capital')
                comparison_layers=capital['levels'];comparison_revision=capital.get('dutchRevision','original')
            for package in comparison_layers.values():
                if not unreal.EditorLevelUtils.add_level_to_world(world,package,unreal.LevelStreamingAlwaysLoaded): raise RuntimeError('Cannot attach comparison source')
            n.levels.set_current_level_by_name('Baseline_Comparison')
            n.actors.spawn_actor_from_class(unreal.PlayerStart,unreal.Vector(-13600,0,110))
            if not n.levels.save_current_level(): raise RuntimeError('Cannot save comparison world')
            receipt.write_text(json.dumps(dict(map=target,sha256=n.sha(n.package_file(target)),
                                              sourceRevision=comparison_revision,sourceLayers=comparison_layers),indent=2)+'\n')
    views=[dict(id='whole_city',eye=[-22000,-21500,24000],target=[-1000,0,1800])]
    for area in plan['gatheringAreas']:
        points=area['polygon'];x=sum(p[0] for p in points)/len(points);z=sum(p[1] for p in points)/len(points)
        h=paving_height(x,z)*100
        views.append(dict(id=area['id'],eye=[z*100-1800,x*100-2300,h+4500],target=[z*100,x*100,h+600]))
    config=dict(map=target,signature=n.architecture['geometrySignature'],views=views,routes=[],
                scope='performance_baseline' if baseline else 'performance_city')
    (n.CONTENT/'Migration/dutch-bastion-proof.json').write_text(json.dumps(config,indent=2)+'\n')
    (n.RUN/'proof-config.json').write_text(json.dumps(config,indent=2)+'\n')


def source_survey():
    baseline=n.baseline();rows=[]
    for layer,package in baseline['levels'].items():
        if not n.levels.load_level(package): raise RuntimeError('Missing capital source')
        for actor in n.actors.get_all_level_actors():
            if actor.get_outer().get_path_name().split('.')[0]!=package: continue
            location=actor.get_actor_location()
            if not -16000<location.x<12800 or not -15000<location.y<15000: continue
            centre,extent=actor.get_actor_bounds(False)
            rows.append(dict(layer=layer,name=actor.get_name(),state=snapshot(actor),
                             bounds=[centre.x,centre.y,centre.z,extent.x,extent.y,extent.z],
                             parent=actor.get_attach_parent_actor().get_name() if actor.get_attach_parent_actor() else None))
    result=dict(sourceHashes=baseline['hashes'],actors=rows)
    target=OUT/'city-source-survey.json'
    if target.exists() and json.loads(target.read_text())!=result: raise RuntimeError('Source survey changed; preserve and reconcile')
    target.write_text(json.dumps(result,indent=2)+'\n')
    unreal.log('WAR_DUTCH_CITY_SURVEY='+str(len(rows)))


stage=os.environ.get('WAR_DUTCH_STAGE','city-survey')
if stage=='city-survey': source_survey()
elif stage=='city-assets': configure();n.build_assets()
elif stage=='city-build': build_city()
elif stage=='city-proof-config': proof_config()
elif stage=='city-review-config': proof_config(True)
elif stage=='city-detail-config': detail_config()
elif stage=='city-collision-survey': collision_survey()
elif stage=='city-performance-config': performance_config()
elif stage=='city-baseline-config': performance_config(True)
elif stage=='city-route-survey': route_survey()
elif stage=='city-world':
    configure()
    from dutch_city_activation import campaign_candidate
    campaign_candidate(n,json.loads((n.RUN/'city.json').read_text()))
elif stage=='city-apply':
    configure()
    from dutch_city_activation import activate
    activate(n,json.loads((n.RUN/'city.json').read_text()))
else: raise RuntimeError('Unknown city stage: '+stage)
