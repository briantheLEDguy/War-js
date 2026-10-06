"""Portable frame evidence fixtures; no native Content or process is used."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/unreal'))
from citadel_performance_evidence import performance_package_file,performance_proof,performance_evidence,baseline_comparison,baseline_package_ownership,PRESERVED_CITY,QUALITY

sha=lambda value:hashlib.sha256(value.encode()).hexdigest()


def fixture(frame_ms=1000/60):
    cameras=[dict(stage=stage,eye=[0,0,3000],target=[0,0,0],fieldOfView=68,
        positions=[[i*300,3000,0] for i in range(36)]) for stage in range(3)]
    setup=dict(version=1,cameras=cameras,settleSeconds=10,minWindowSeconds=60,settingsPath='private/benchmark.ini',
        settingsSha256=sha('settings'),binaryPath='private/native.dll',binarySha256=sha('binary'),sourceHashes={'source.cpp':sha('source')},
        configHashes={'normal.ini':sha('normal')},blueprintPath='blueprint.json',blueprintSha256=sha('blueprint'))
    config=dict(map='/Game/Private/SiegeCandidate',cityRevision=sha('city'),signature=sha('signature'),mapSha256=sha('map'),performance=setup)
    settings=dict(resolution=[1920,1080],screenPercentage=100,maxFps=0,vSync=0,frameSmoothing=False,engineFixedFrameRate=False,
        fappFixedTimeStep=False,worldTimeDilation=1,dynamicResolutionMode=0,rendered=True,rhi='D3D12',gameUserSettingsIni=setup['settingsPath'],
        quality={'sg.'+key+'Quality':3 for key in QUALITY})
    roster=[dict(realm='aegis' if i<18 else 'riftbound',careerId='sunfire_templar',combatLevel=20,
        visualAsset='/Game/Visuals/Fixture',equipmentSignature=sha('equipment')) for i in range(36)]
    canonical='\n'.join(sorted(json.dumps(r,sort_keys=True) for r in roster));roster_sha=sha(canonical)
    frames=[];windows=[]
    for stage in range(3):
        count=int(60000/frame_ms+.5)+1
        for i in range(count):
            frames.append(dict(stage=stage,index=len(frames),elapsedSeconds=stage*200+10+i*frame_ms/1000,stageElapsedSeconds=10+i*frame_ms/1000,
                frameMs=140000 if i==0 and stage>0 else frame_ms,gameThreadMs=3,renderThreadMs=4,rhiThreadMs=1,gpuMs=5,drawCalls=100,primitives=1000000,physicalMiB=1000,
                aegisEnrolled=18,riftboundEnrolled=18,alive=35,dead=1,respawning=0,avatars=36,modelReady=36,visible=36,
                projected=36,recentlyRendered=36,unoccluded=36,streamingRequests=0,rosterSha256=roster_sha,statsMode='normalized',
                benchmarkOrders=True,settled=True,eligible=True,settings=settings,cameraEye=[0,0,3000],cameraDirection=[0,0,-1],cameraFov=68,
                cameraMatches=True,phase='active',encounterActive=True,leasePaused=False,preparing=False))
        rows=frames[-count:]
        windows.append(dict(stage=stage,startElapsedSeconds=rows[0]['elapsedSeconds'],endElapsedSeconds=rows[-1]['elapsedSeconds'],frameCount=count,settleSeconds=10))
    report=dict(schemaVersion=1,passed=True,performanceOnly=True,proofOnly=True,**config,configSha256=sha('config'),
        productionAdmission=False,steamAdmission=False,humanPlaytest=False,visualApproval=False,releaseAcceptance=False,referenceHardwareCertified=False,
        bindings=setup,settings=settings,roster=roster,rosterCanonical=canonical,rosterSha256=roster_sha,statsMode='normalized',
        hardware=dict(cpu='cpu',gpu='gpu',adapter='adapter',driverVersion='driver',os='Windows',engineVersion='5.8.2-123+++UE5',physicalMemoryBytes=32_000_000_000),
        windows=windows,frames=dict(count=len(frames),sha256=sha('raw')),formationPositions=[
            dict(stage=c['stage'],index=i,point=p,actualFloor=p,floorNormalZ=1,capsuleRadiusCm=42,capsuleHalfHeightCm=96,floorClear=True,
                capsuleClear=True,navigation=True,captureExclusion=True,captureRadiusCm=650,minimumCaptureDistanceCm=1000)
            for c in cameras for i,p in enumerate(c['positions'])])
    return report,dict(schemaVersion=1,complete=True,frames=frames),config


def earned_fixture():
    report,raw,config=fixture();times=[110,180,250,290,460,460,500]
    config.update(performanceBaseline=True,isolatedStageWindows=False,fixtureMode='earned_progression',cityRevision=PRESERVED_CITY['revision'])
    report.update(config,sourceCity=PRESERVED_CITY.copy(),earnedProgressionObserved=True,
        progressionAcceptance=False,victoryAcceptance=False,conquestAcceptance=False,routeAcceptance=False,fullSiegeAdmission=False)
    def observation(stage,phase,claims,elapsed,count):
        gates=[]
        for index in (0,1):
            opened=bool(claims & (8 if index==0 else 64));identity=config['map']+'.PersistentLevel.Gate'+str(index)
            gates.append(dict(id=identity,stageIndex=index,open=opened,hidden=opened,collisionEnabled=not opened,
                components=[dict(id=identity+'.Leaf',collisionEnabled=True,hiddenInGame=False,visible=True)]))
        return dict(stage=stage,phase=phase,mainClaims=claims,optionalClaims=0,elapsedSeconds=elapsed,siegeElapsedSeconds=elapsed,
            resultCount=0,commanderVictory=False,milestoneSeconds=times[:count],stageRemainingSeconds=840-elapsed+(0,350,560)[stage] if phase=='active' else 0,
            transitionRemainingSeconds=60 if phase=='transition' else 0,overtimeRemainingSeconds=0,gates=gates)
    observations=[observation(0,'active',0,0,0),observation(0,'active',1,110,1),observation(0,'active',3,180,2),
        observation(0,'active',7,250,3),observation(0,'transition',15,290,4),observation(1,'active',15,350,4),
        observation(1,'active',31,460,5),observation(1,'active',63,460,6),observation(1,'transition',127,500,7),
        observation(2,'active',127,560,7),observation(2,'active',127,630,7)]
    report['baselineProgression']=dict(version=1,startedStage=0,startedMainClaims=0,startedOptionalClaims=0,
        observations=observations,settledStage=2,settledMainClaims=127,commanderVictory=False)
    for index,row in enumerate(raw['frames']):
        stage=row['stage'];row['elapsedSeconds']+=(0,150,160)[stage]
        row.update(observation(stage,'active',(0,15,127)[stage],row['elapsedSeconds'],(0,4,7)[stage]))
        if index:row['frameMs']=(row['elapsedSeconds']-raw['frames'][index-1]['elapsedSeconds'])*1000
    report['windows']=[dict(stage=stage,startElapsedSeconds=rows[0]['elapsedSeconds'],endElapsedSeconds=rows[-1]['elapsedSeconds'],
        frameCount=len(rows),settleSeconds=10) for stage in range(3) for rows in [[r for r in raw['frames'] if r['stage']==stage]]]
    return report,raw,config


class PerformanceTests(unittest.TestCase):
    def test_baseline_engine_dependencies_can_never_be_owned_overlay_packages(self):
        signature='a'*64;prefix='/Game/WorldRebuild/AegisCitadel_'+signature[:12]+'/'
        source=dict(signature=signature,map=prefix+'PerformanceBaseline',packageHashes={prefix+'PerformanceBaseline':'b'*64},
            sourceHashes={'/Engine/PreservedInput':'c'*64},dependencyHashes={'/Game/Original':'d'*64})
        baseline_package_ownership(source)
        for name in ('/Engine/PreservedInput','/Engine/Other','/Game/Original','/Game/Escape'):
            changed=copy.deepcopy(source);changed['packageHashes'][name]='e'*64
            with self.assertRaisesRegex(ValueError,'ownership'):baseline_package_ownership(changed)

    def test_baseline_requires_real_earned_captures_gates_and_no_commander_result(self):
        report,raw,config=earned_fixture();self.assertEqual(len(performance_proof(report,raw,config,False)),3)
        mutations=(lambda r,f,c:c.update(isolatedStageWindows=True),
            lambda r,f,c:r['baselineProgression'].update(startedStage=2),
            lambda r,f,c:r['baselineProgression']['observations'][6]['milestoneSeconds'].__setitem__(0,111),
            lambda r,f,c:r['baselineProgression']['observations'][0]['gates'][0].update(open=True),
            lambda r,f,c:r['baselineProgression']['observations'][9].update(elapsedSeconds=550,siegeElapsedSeconds=550),
            lambda r,f,c:r['baselineProgression'].update(commanderVictory=True),
            lambda r,f,c:f['frames'][-1].update(mainClaims=255),
            lambda r,f,c:r.update(fullSiegeAdmission=True))
        for mutate in mutations:
            report,raw,config=earned_fixture();mutate(report,raw,config)
            with self.assertRaises(ValueError):performance_proof(report,raw,config,False)

    def test_engine_package_resolver_uses_actual_configured_content_and_rejects_escapes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);engine=root/'actual-engine';content=engine/'Engine/Content';file=content/'Materials/Test.uasset'
            file.parent.mkdir(parents=True);file.write_bytes(b'PORTABLE TEST PACKAGE ONLY')
            with mock.patch.dict('os.environ',{'UNREAL_ENGINE_ROOT':str(engine)}):
                self.assertEqual(performance_package_file(root,'/Engine/Materials/Test'),file)
                self.assertEqual(hashlib.sha256(performance_package_file(root,'/Engine/Materials/Test').read_bytes()).hexdigest(),
                                 hashlib.sha256(b'PORTABLE TEST PACKAGE ONLY').hexdigest())
                for package in ('/Engine/../outside','/Engine//Materials/Test','/Engine/Materials/Test.uasset',
                                '/Engine/C:/outside','/Script/Engine','/Engine/Materials/Missing'):
                    with self.assertRaises(ValueError):performance_package_file(root,package)
                file.with_suffix('.umap').write_bytes(b'AMBIGUOUS PORTABLE TEST PACKAGE')
                with self.assertRaisesRegex(ValueError,'ambiguous'):performance_package_file(root,'/Engine/Materials/Test')
    def test_true_exposure_derives_absolute_budget_and_preserves_actual_deaths(self):
        report,raw,config=fixture();result=performance_proof(report,raw,config)
        self.assertEqual(len(result),3);self.assertAlmostEqual(result[0]['fps'],60)
        report,raw,config=fixture(20)
        with self.assertRaisesRegex(ValueError,'budget'):performance_proof(report,raw,config)
        performance_proof(report,raw,config,False)

    def test_actual_occlusion_pause_gap_equipment_and_missing_floor_fail(self):
        for field,value in (('unoccluded',35),('leasePaused',True),('elapsedSeconds',45),('cameraEye',[0,0,4000])):
            report,raw,config=fixture();raw['frames'][1800][field]=value
            with self.assertRaises(ValueError):performance_proof(report,raw,config)
        report,raw,config=fixture();report['roster'][0]['combatLevel']=1
        with self.assertRaisesRegex(ValueError,'Roster'):performance_proof(report,raw,config)
        report,raw,config=fixture();report['formationPositions'][0]['capsuleClear']=False
        with self.assertRaisesRegex(ValueError,'formation'):performance_proof(report,raw,config)

    def test_explicit_baseline_comparison_requires_real_preserved_identity_and_mapping(self):
        candidate,_,_=fixture();baseline=copy.deepcopy(candidate)
        baseline.update(cityRevision=PRESERVED_CITY['revision'],sourceCity=PRESERVED_CITY.copy(),map='/Game/Private/PerformanceBaseline')
        baseline['settings']['gameUserSettingsIni']='baseline/benchmark.ini';baseline['bindings']['settingsPath']='baseline/benchmark.ini'
        comparison=dict(schemaVersion=1,sourceCity=PRESERVED_CITY.copy(),candidateCityRevision=candidate['cityRevision'],
            candidateSignature=candidate['signature'],baselineMap=baseline['map'],baselineMapSha256=baseline['mapSha256'],stages=[
                dict(stage=s,candidateCamera=candidate['bindings']['cameras'][s],baselineCamera=baseline['bindings']['cameras'][s],
                    floorAndAnchorMapping='Actual original floor mapping',architectureDifference='Camera height follows original physical floor') for s in range(3)])
        baseline_comparison(candidate,baseline,comparison)
        with self.assertRaises(ValueError):baseline_comparison(candidate,baseline,dict(matchedBaseline=True))
        comparison['stages'][2]['architectureDifference']=''
        with self.assertRaisesRegex(ValueError,'disclosed'):baseline_comparison(candidate,baseline,comparison)

    def test_publication_requires_actual_config_frames_and_separate_baseline_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);report,raw,config=fixture();setup=config['performance']
            write=lambda file,value:file.write_text(json.dumps(value),encoding='utf-8')
            digest=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
            for key in ('settings','binary','blueprint'):
                file=root/(key+'.txt');file.write_text('PORTABLE TEST SOURCE ONLY',encoding='utf-8')
                setup[key+'Path']=str(file);setup[key+'Sha256']=digest(file)
            report['settings']['gameUserSettingsIni']=setup['settingsPath']
            source_file=root/'source.cpp';source_file.write_text('PORTABLE TEST SOURCE ONLY',encoding='utf-8')
            setup['sourceHashes']={str(source_file):digest(source_file)};setup['configHashes']=setup['sourceHashes'].copy()
            blueprint=dict(signature=config['signature'],performanceFormations=[dict(stage=c['stage'],positions=c['positions'],minimumCaptureGapCm=50,
                camera=dict(eye=c['eye'],target=c['target'],horizontalFovDegrees=c['fieldOfView'])) for c in setup['cameras']])
            write(Path(setup['blueprintPath']),blueprint);setup['blueprintSha256']=digest(Path(setup['blueprintPath']))
            frames_file=root/'performance-frames.json';write(frames_file,raw)
            config_file=root/'config.json';write(config_file,config)
            report['configSha256']=digest(config_file);report['frames'].update(path=str(frames_file),sha256=digest(frames_file))
            report_file=root/'performance-report.json';write(report_file,report)
            bound=lambda file:dict(path=file.name,sha256=digest(file))
            binding=dict(**bound(report_file),config=bound(config_file),frames=bound(frames_file))
            def confined(base,relative):
                if not isinstance(relative,str) or not relative:raise ValueError('Missing actual baseline binding')
                file=(base/relative).resolve();file.relative_to(base.resolve());return file
            read=lambda file:json.loads(file.read_text(encoding='utf-8'))
            args=(root,binding,dict(signature=config['signature']),dict(city=dict(revision=config['cityRevision'])),confined,digest,read)
            with self.assertRaisesRegex(ValueError,'baseline binding'):performance_evidence(*args)
            frames_file.write_text(frames_file.read_text()+' ',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'file changed'):performance_evidence(*args)


if __name__=='__main__':unittest.main()
