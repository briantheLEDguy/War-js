"""Guarded campaign-shell revision; source worlds and other zone layers stay intact."""
import copy
import json
import shutil
import hashlib


def campaign_candidate(n, city):
    import unreal
    from world_actor_state import snapshot
    directory=n.ROOT/'artifacts/unreal/world-portals'
    receipt_path=n.RUN/'campaign.json'
    if receipt_path.exists():
        receipt=json.loads(receipt_path.read_text())
        for p,h in receipt['packageHashes'].items():
            if n.sha(n.package_file(p))!=h: raise RuntimeError('Changed campaign candidate: '+p)
        return receipt
    build=json.loads((directory/'build.json').read_text())
    manifest=json.loads((directory/build['partitionManifest']).read_text())
    capital=next(z for z in manifest['zones'] if z['id']=='aegis_capital')
    if capital['levels']!=n.baseline()['levels']:
        # A follow-up revision may replace an already activated Dutch city.
        # Verify that receipt and every saved dependency before using its shell.
        previous=n.OUT/capital.get('dutchRevision','')/'campaign.json'
        if not previous.exists(): raise RuntimeError('Capital routing changed after survey')
        prior=json.loads(previous.read_text())
        if not prior.get('activated') or prior['manifest']!=manifest:
            raise RuntimeError('Active city differs from its activation receipt')
        for package,expected in prior['packageHashes'].items():
            if n.sha(n.package_file(package))!=expected: raise RuntimeError('Preserve edited active city: '+package)
        prior_city=json.loads((previous.parent/'city.json').read_text())
        for package,expected in prior_city['packageHashes'].items():
            if n.sha(n.package_file(package))!=expected: raise RuntimeError('Preserve edited active city layer: '+package)
        for package,expected in prior_city['visualHashes'].items():
            if n.sha(n.package_file(package,'.uasset'))!=expected: raise RuntimeError('Preserve edited active city asset: '+package)
        draft=n.ROOT/'unreal/AegisWar/Saved/WorldEdit'/('DutchBastion_'+capital['dutchRevision'])/'draft.json'
        if draft.exists():
            document=json.loads(draft.read_text());baseline=json.loads(document['baseline'])['objects']
            if document['objects']!=baseline: raise RuntimeError('Reconcile the active city GM draft before replacing its layers')
    sources={p:n.sha(n.package_file(p)) for p in set(manifest['packageHashes'])|{build['map']}}
    if sources[build['map']]!=manifest['mainSha256'] or sources[build['layer']]!=manifest['packageHashes'][build['layer']]:
        raise RuntimeError('Campaign shell changed; reconcile edits before activation')
    backup=n.RUN/'activation-backup';backup.mkdir(exist_ok=True)
    for file in (directory/'build.json',directory/build['partitionManifest'],n.ROOT/'unreal/AegisWar/Config/DefaultEngine.ini'):
        target=backup/file.name
        if target.exists() and target.read_bytes()!=file.read_bytes(): raise RuntimeError('Activation inputs changed')
        shutil.copy2(file,target)
    (backup/'source-hashes.json').write_text(json.dumps(sources,indent=2)+'\n')
    replacements=list(city['layers'].values())+[city['geometryLayer']]
    routing=n.DEST+'/CampaignRouting_v3';target=n.DEST+'/Bastion_Campaign_v3'
    for package in (routing,target):
        if n.assets.does_asset_exist(package): raise RuntimeError('Unreceipted campaign package: '+package)
    if not n.assets.duplicate_asset(build['layer'],routing) or not n.levels.load_level(routing):
        raise RuntimeError('Cannot copy routing layer')
    actors=n.actors.get_all_level_actors()
    before={a.get_name():snapshot(a) for a in actors}
    anchors=[a for a in actors if isinstance(a,unreal.WarZoneAnchor)]
    anchor=next(a for a in anchors if str(a.get_editor_property('zone_id'))=='aegis_capital')
    if sorted(map(str,anchor.get_editor_property('content_levels')))!=sorted(capital['levels'].values()):
        raise RuntimeError('Unexpected capital anchor bindings')
    anchor.set_editor_property('content_levels',replacements)
    if before!={a.get_name():snapshot(a) for a in actors}: raise RuntimeError('Unrelated routing actor state changed')
    if not n.levels.save_current_level(): raise RuntimeError('Cannot save routing candidate')
    if not n.assets.duplicate_asset(build['map'],target) or not n.levels.load_level(target):
        raise RuntimeError('Cannot copy campaign shell')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    root=lambda: {a.get_name():snapshot(a) for a in n.actors.get_all_level_actors()
                  if a.get_outer().get_path_name().split('.')[0]==target}
    initial=root()
    for package in [build['layer'],*capital['levels'].values()]:
        stream=unreal.GameplayStatics.get_streaming_level(world,package)
        if not stream: raise RuntimeError('Missing original campaign attachment: '+package)
        unreal.GameplayStatics.flush_level_streaming(world)
        if not unreal.EditorLevelUtils.remove_level_from_world(stream.get_loaded_level()):
            raise RuntimeError('Cannot detach copied source binding')
    if not unreal.EditorLevelUtils.add_level_to_world(world,routing,unreal.LevelStreamingAlwaysLoaded):
        raise RuntimeError('Cannot attach new campaign routing')
    for package in replacements:
        stream=unreal.EditorLevelUtils.add_level_to_world(world,package,unreal.LevelStreamingDynamic)
        if not stream: raise RuntimeError('Cannot attach capital revision')
        stream.set_editor_property('initially_loaded',False);stream.set_editor_property('initially_visible',False)
    unreal.GameplayStatics.flush_level_streaming(world)
    actors=n.actors.get_all_level_actors()
    if sorted(str(a.get_editor_property('route_id')) for a in actors if isinstance(a,unreal.WarZonePortal))!=sorted(build['portals']):
        raise RuntimeError('Campaign portal identities changed')
    if sorted(str(a.get_editor_property('zone_id')) for a in actors if isinstance(a,unreal.WarZoneAnchor))!=sorted(build['zones']):
        raise RuntimeError('Campaign zone identities changed')
    if root()!=initial: raise RuntimeError('Persistent authored actors changed')
    for zone in manifest['zones']:
        for package in replacements if zone['id']=='aegis_capital' else zone['levels'].values():
            if not unreal.GameplayStatics.get_streaming_level(world,package): raise RuntimeError('Lost zone attachment: '+package)
    if not n.levels.set_current_level_by_name(target.rsplit('/',1)[1]) or not n.levels.save_current_level():
        raise RuntimeError('Cannot save revised campaign shell')
    for p,h in sources.items():
        if n.sha(n.package_file(p))!=h: raise RuntimeError('A source world changed: '+p)
    n.baseline()
    candidate=copy.deepcopy(manifest)
    revised=next(z for z in candidate['zones'] if z['id']=='aegis_capital')
    revised['levels']={**city['layers'],'architecture':city['geometryLayer']}
    revised['actorCount']=sum(len(rows) for rows in n.baseline()['actors'].values())-sum(c['action'] in ('remove_owned_house','remove_owned_street') for c in city['changes'])+len(city['added'])+sum(len(a.get('furnishing',[])) for a in city['added'])
    revised['dutchRevision']=n.revision
    revised['acceptance'].update(visual='pending',traversal='pending',release='blocked')
    candidate.update(layer=routing,mainMap=target,mainSha256=n.sha(n.package_file(target)))
    for p in [build['layer'],*capital['levels'].values()]: candidate['packageHashes'].pop(p,None)
    for p in [routing,*replacements]: candidate['packageHashes'][p]=n.sha(n.package_file(p))
    revised_build=copy.deepcopy(build)
    revised_build.update(map=target,layer=routing,capitalSha256After=candidate['mainSha256'],runtimeTraversalVerified=False,dutchRevision=n.revision)
    result=dict(map=target,layer=routing,sourceHashes=sources,packageHashes={p:n.sha(n.package_file(p)) for p in [target,routing,*replacements]},
                manifest=candidate,build=revised_build,activated=False)
    receipt_path.write_text(json.dumps(result,indent=2)+'\n')
    unreal.log('WAR_DUTCH_CAMPAIGN_CANDIDATE='+target)
    return result


def activate(n, city):
    """Publish only the reviewed candidate; interrupted writes are resumable."""
    candidate=campaign_candidate(n,city)
    review=json.loads((n.RUN/'review.json').read_text())
    proof_dir=n.RUN/'game-proof'
    proof=json.loads((proof_dir/'report.json').read_text(encoding='utf-8-sig'))
    config=json.loads((proof_dir/'config.json').read_text())
    ground=json.loads((n.RUN/'route-ground-survey.json').read_text())
    if ground.get('map')!=city['map'] or ground.get('failures') or ground.get('samples')!=sum(len(r['points']) for r in config['routes']):
        raise RuntimeError('Native route ground evidence is incomplete')
    if (review.get('revision')!=n.revision or not all(review.get(k) is True for k in ('visual','traversal','performance'))
            or review.get('unfinished') or config.get('scope')!='whole_city' or not proof['passed']
            or proof.get('routeFailures') or proof['signature']!=n.architecture['geometrySignature']
            or proof['map']!=city['map'] or proof['routesWalked']!=len(config['routes']) or proof['views']!=len(config['views'])):
        raise RuntimeError('Full native city acceptance is incomplete')
    network_path=(n.ROOT/review['networkEvidence']).resolve();network_path.relative_to(n.ROOT.resolve())
    network=json.loads(network_path.read_text())
    if network.get('map')!=candidate['map'] or not network.get('passed') or not network.get('twoClientStreaming'):
        raise RuntimeError('Candidate campaign streaming has not passed')
    if any(network.get('packageHashes',{}).get(p)!=h for p,h in candidate['packageHashes'].items()):
        raise RuntimeError('Network evidence does not match the candidate packages')
    performance_views=[]
    for scope in ('performance_city','performance_baseline'):
        directory=n.RUN/scope
        measurement=json.loads((directory/'report.json').read_text(encoding='utf-8-sig'))
        setup=json.loads((directory/'config.json').read_text())
        expected_map=city['map'] if scope=='performance_city' else n.DEST+'/Baseline_Comparison'
        if (setup.get('scope')!=scope or setup.get('map')!=expected_map or measurement.get('map')!=expected_map
                or not measurement.get('passed') or measurement.get('signature')!=n.architecture['geometrySignature']
                or measurement.get('frameLimit')!=0 or measurement.get('vSync')!=0
                or measurement.get('views')!=len(setup['views']) or setup['routes']
                or not measurement.get('frameSamples') or not measurement.get('viewPerformance')):
            raise RuntimeError('Matched uncapped performance evidence is incomplete: '+scope)
        performance_views.append(setup['views'])
    if performance_views[0]!=performance_views[1]: raise RuntimeError('Performance cameras differ')
    for p,h in city['packageHashes'].items():
        if n.sha(n.package_file(p))!=h: raise RuntimeError('Changed reviewed city package: '+p)
    if not city.get('visualHashes'): raise RuntimeError('Missing model/material preservation evidence')
    for p,h in city['visualHashes'].items():
        if n.sha(n.package_file(p,'.uasset'))!=h: raise RuntimeError('Changed reviewed visual dependency: '+p)
    for p,h in candidate['sourceHashes'].items():
        if n.sha(n.package_file(p))!=h: raise RuntimeError('Source world changed before activation: '+p)
    n.baseline()
    directory=n.ROOT/'artifacts/unreal/world-portals';backup=n.RUN/'activation-backup'
    original=json.loads((backup/'build.json').read_text())
    from dutch_city_revision import merge_manifest
    manifest_path=directory/original['partitionManifest']
    live_manifest_bytes=manifest_path.read_bytes()
    build_path=directory/'build.json';live_build_bytes=build_path.read_bytes()
    candidate['build']=merge_manifest(original,candidate['build'],json.loads(live_build_bytes),'build')
    manifest=merge_manifest(json.loads((backup/manifest_path.name).read_bytes()),candidate['manifest'],json.loads(live_manifest_bytes))
    candidate['manifest']=manifest
    capital=next(z for z in manifest['zones'] if z['id']=='aegis_capital')
    capital['dutchArchitectureReview']=dict(visual=True,traversal=True,performance=True,revision=n.revision)
    # The wider zone/gameplay/release fields remain independent acceptance gates.
    settings=(backup/'DefaultEngine.ini').read_bytes()
    for key in (b'GameDefaultMap=',b'EditorStartupMap='):
        old=key+original['map'].encode();new=key+candidate['map'].encode()
        if settings.count(old)!=1: raise RuntimeError('Unexpected startup configuration')
        settings=settings.replace(old,new)
    outputs={directory/'build.json':(json.dumps(candidate['build'],indent=2)+'\n').encode(),
             directory/original['partitionManifest']:(json.dumps(manifest,indent=2)+'\n').encode(),
             n.ROOT/'unreal/AegisWar/Config/DefaultEngine.ini':settings}
    journal=[]
    for path,contents in outputs.items():
        before=(backup/path.name).read_bytes();current=path.read_bytes()
        if path in (manifest_path,build_path):
            expected=live_manifest_bytes if path==manifest_path else live_build_bytes
            if current!=expected: raise RuntimeError('Campaign review changed during activation')
            # Keep the concurrent review state separately from the immutable
            # original backup; three-way merging above rejects conflicts.
            (backup/('review-state-'+path.stem+'-'+hashlib.sha256(current).hexdigest()+'.json')).write_bytes(current)
            before=current
        elif current not in (before,contents): raise RuntimeError('Preserve changed activation input: '+str(path))
        journal.append(dict(path=path.relative_to(n.ROOT).as_posix(),before=hashlib.sha256(before).hexdigest(),after=hashlib.sha256(contents).hexdigest()))
    (n.RUN/'activation-journal.json').write_text(json.dumps(journal,indent=2)+'\n')
    for path,contents in outputs.items():
        temporary=path.with_name(path.name+'.dutch.tmp');temporary.write_bytes(contents);temporary.replace(path)
    candidate['activated']=True;candidate['review']=review
    (n.RUN/'campaign.json').write_text(json.dumps(candidate,indent=2)+'\n')
    from dutch_city_revision import export_revision
    export_revision()
    print('Activated Dutch Bastion campaign revision '+n.revision)
