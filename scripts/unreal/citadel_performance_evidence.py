"""Portable, read-only rendered performance evidence verification."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

PRESERVED_CITY=dict(path='/Game/Cities/Shared/aegis_capital/City',
    revision='6ffd751f94efa5aa261779a6853262a6ca5128376c7a65a369e69943de9f6a2f')
QUALITY=('ViewDistance','AntiAliasing','Shadow','GlobalIllumination','Reflection','PostProcess','Texture','Effects','Foliage','Shading','Landscape')
FLAGS=('productionAdmission','steamAdmission','humanPlaytest','visualApproval','releaseAcceptance','referenceHardwareCertified')


def performance_package_file(root,package,engine_root=None):
    """Resolve original Engine content through the configured toolchain only."""
    if isinstance(package,str) and package.startswith('/Game/'):
        from shared_city_sources import package_file
        return package_file(root,package)
    if not isinstance(package,str) or not re.fullmatch(r'/Engine/[A-Za-z0-9_/-]+',package):
        raise ValueError('Invalid baseline native package identity.')
    if any(part in ('','.','..') for part in package[8:].split('/')):
        raise ValueError('Invalid baseline Engine package path.')
    configured=engine_root or os.environ.get('UNREAL_ENGINE_ROOT')
    if not configured and sys.platform=='win32':
        default=Path('C:/Program Files/Epic Games/UE_5.8')
        if default.is_dir():configured=default
    if not configured:raise ValueError('Actual configured Unreal Engine content root is unavailable.')
    content=(Path(configured)/'Engine/Content').resolve()
    base=(content/package[8:]).resolve()
    try:base.relative_to(content)
    except ValueError:raise ValueError('Baseline Engine package escaped configured Content root.') from None
    candidates=[base.with_suffix(extension) for extension in ('.uasset','.umap') if base.with_suffix(extension).is_file()]
    if len(candidates)!=1:raise ValueError('Baseline Engine package is missing or ambiguous.')
    # A linked package file cannot redirect verification outside its Content root.
    try:candidates[0].resolve().relative_to(content)
    except ValueError:raise ValueError('Baseline Engine package escaped configured Content root.') from None
    return candidates[0]


def baseline_package_ownership(source):
    """Only the new private overlay is owned; original Engine dependencies stay input."""
    signature=source.get('signature');owned=source.get('packageHashes');inputs=source.get('sourceHashes');dependencies=source.get('dependencyHashes')
    if (not isinstance(signature,str) or not re.fullmatch('[a-f0-9]{64}',signature)
            or not all(isinstance(value,dict) and value for value in (owned,inputs,dependencies))):
        raise ValueError('Baseline package ownership is missing.')
    prefix='/Game/WorldRebuild/AegisCitadel_'+signature[:12]+'/'
    if (source.get('map')!=prefix+'PerformanceBaseline' or source['map'] not in owned
            or any(not isinstance(name,str) or not name.startswith(prefix) or name in inputs or name in dependencies for name in owned)):
        raise ValueError('Baseline overlay ownership escaped its private namespace.')


def finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def point(value):
    return isinstance(value,list) and len(value)==3 and all(finite(v) for v in value)


def settings_valid(value):
    return (isinstance(value,dict) and value.get('resolution')==[1920,1080] and value.get('screenPercentage')==100
        and value.get('maxFps')==0 and value.get('vSync')==0 and value.get('frameSmoothing') is False
        and value.get('engineFixedFrameRate') is False and value.get('fappFixedTimeStep') is False
        and value.get('worldTimeDilation')==1 and value.get('dynamicResolutionMode')==0 and value.get('rendered') is True
        and isinstance(value.get('rhi'),str) and value['rhi'] and 'null' not in value['rhi'].lower()
        and all(type(value.get('quality',{}).get('sg.'+key+'Quality')) is int
            and 0<=value['quality']['sg.'+key+'Quality']<=4 for key in QUALITY))


def roster(report):
    rows=report.get('roster');payload=report.get('rosterCanonical')
    if (not isinstance(rows,list) or len(rows)!=36 or report.get('statsMode') not in ('normal','normalized')
            or any(sum(r.get('realm')==realm for r in rows)!=18 for realm in ('aegis','riftbound'))
            or not isinstance(payload,str) or len(payload)>100_000
            or hashlib.sha256(payload.encode()).hexdigest()!=report.get('rosterSha256')):
        raise ValueError('Actual canonical 18-per-realm roster and digest are required.')
    keys=('realm','careerId','visualAsset','combatLevel','equipmentSignature')
    for row in rows:
        if (not isinstance(row.get('careerId'),str) or not row['careerId']
                or not isinstance(row.get('visualAsset'),str) or not row['visualAsset'].startswith('/Game/')
                or type(row.get('combatLevel')) is not int or not 1<=row['combatLevel']<=40
                or not re.fullmatch('[a-f0-9]{64}',str(row.get('equipmentSignature')))):
            raise ValueError('Actual character model, level and equipment identity is missing.')
    normalized=sorted((json.dumps({key:row[key] for key in keys},sort_keys=True) for row in rows))
    if sorted(json.dumps(json.loads(line),sort_keys=True) for line in payload.split('\n'))!=normalized:
        raise ValueError('Roster canonical digest describes different characters.')
    return normalized


def progress_state_valid(row):
    stage=row.get('stage');claims=row.get('mainClaims');optional=row.get('optionalClaims')
    allowed=(0,1,3,7,15) if stage==0 else (15,31,47,63,127) if stage==1 else (127,)
    times=row.get('milestoneSeconds');phase=row.get('phase')
    return (type(stage) is int and stage in (0,1,2) and phase in ('active','transition')
        and type(claims) is int and claims in allowed and type(optional) is int and 0<=optional<8
        and optional & ~((1 << (stage+1))-1)==0
        and finite(row.get('elapsedSeconds')) and 0<=row['elapsedSeconds']<=3001
        and all(finite(row.get(k)) and row[k]>=0 for k in ('stageRemainingSeconds','transitionRemainingSeconds','overtimeRemainingSeconds'))
        and row['stageRemainingSeconds']<=840 and row['transitionRemainingSeconds']<=60 and row['overtimeRemainingSeconds']<=120
        and (stage<2 and claims==(15 if stage==0 else 127) and row['stageRemainingSeconds']==0 and row['overtimeRemainingSeconds']==0
            if phase=='transition' else row['transitionRemainingSeconds']==0 and (row['stageRemainingSeconds']>0 or row['overtimeRemainingSeconds']>0))
        and isinstance(times,list) and len(times)<=7 and all(finite(t) and 0<t<=row['elapsedSeconds']
            and (i==0 or t>=times[i-1]) for i,t in enumerate(times)))


def earned_progression(report,raw,config):
    """Validate observed ordinary captures and gates without granting gameplay acceptance."""
    proof=report.get('baselineProgression',{});observations=proof.get('observations')
    if (config.get('fixtureMode')!='earned_progression' or config.get('isolatedStageWindows') is not False
            or report.get('fixtureMode')!='earned_progression' or report.get('isolatedStageWindows') is not False
            or report.get('earnedProgressionObserved') is not True or proof.get('version')!=1
            or proof.get('startedStage')!=0 or proof.get('startedMainClaims')!=0 or proof.get('startedOptionalClaims')!=0
            or proof.get('settledStage')!=2 or proof.get('settledMainClaims')!=127 or proof.get('commanderVictory') is not False
            or not isinstance(observations,list) or not 10<=len(observations)<=4096):
        raise ValueError('Baseline requires actual earned progression from an empty ordinary stage-zero round.')
    previous=None;gate_ids=None;starts={};transitions={}
    for row in observations:
        if (not progress_state_valid(row) or row.get('siegeElapsedSeconds')!=row['elapsedSeconds']
                or row.get('resultCount')!=0 or row.get('commanderVictory') is not False
                or previous and (row['elapsedSeconds']<previous['elapsedSeconds']
                or not previous['stage']<=row['stage']<=previous['stage']+1
                or row['mainClaims'] & previous['mainClaims']!=previous['mainClaims']
                or row['optionalClaims'] & previous['optionalClaims']!=previous['optionalClaims']
                or row['milestoneSeconds'][:len(previous['milestoneSeconds'])]!=previous['milestoneSeconds'])):
            raise ValueError('Earned baseline claims, clocks or milestone history were reset or substituted.')
        if len(row['milestoneSeconds'])!=row['mainClaims'].bit_count():
            raise ValueError('Every earned main capture requires its actual milestone time.')
        gates=row.get('gates');ids=[]
        if not isinstance(gates,list) or len(gates)!=2 or {g.get('stageIndex') for g in gates}!={0,1}:
            raise ValueError('Both actual preserved gate assemblies need observed state.')
        for index in (0,1):
            gate=next(g for g in gates if g['stageIndex']==index);expected=bool(row['mainClaims'] & (8 if index==0 else 64))
            components=gate.get('components')
            if (not isinstance(gate.get('id'),str) or not gate['id'].startswith(config['map']+'.')
                    or gate.get('open') is not expected or gate.get('hidden') is not expected or gate.get('collisionEnabled') is not (not expected)
                    or not isinstance(components,list) or not 0<len(components)<=256
                    or len({c.get('id') for c in components})!=len(components)
                    or any(not isinstance(c.get('id'),str) or not c['id'].startswith(gate['id']+'.')
                           or any(type(c.get(k)) is not bool for k in ('collisionEnabled','hiddenInGame','visible')) for c in components)):
                raise ValueError('Actual baseline gates differ from earned breach/center claims.')
            ids.append(gate['id'])
        if len(set(ids))!=2 or gate_ids and ids!=gate_ids:raise ValueError('Baseline gate identities changed during progression.')
        gate_ids=ids
        if row['phase']=='transition' and row['stage'] not in transitions:transitions[row['stage']]=row['elapsedSeconds']
        if row['phase']=='active' and row['stage'] not in starts:
            if row['stage']>0 and (row['stage']-1 not in transitions or row['elapsedSeconds']-transitions[row['stage']-1]<59.9
                    or row['mainClaims']!=(15 if row['stage']==1 else 127)):
                raise ValueError('Baseline stages must follow earned captures and ordinary sixty-second transitions.')
            starts[row['stage']]=row['elapsedSeconds']
        previous=row
    initial=observations[0]
    if (initial['stage']!=0 or initial['phase']!='active' or initial['mainClaims']!=0 or initial['optionalClaims']!=0
            or initial['elapsedSeconds']>.001 or abs(initial['stageRemainingSeconds']-840)>.001
            or previous['stage']!=2 or previous['phase']!='active' or previous['mainClaims']!=127
            or len(starts)!=3 or len(transitions)!=2
            or any(not any(r['mainClaims']==mask for r in observations) for mask in (1,3,7,15,63,127))):
        raise ValueError('Baseline did not observe all ordinary stages and earned milestone boundaries.')
    for row in raw['frames']:
        state=dict(row,elapsedSeconds=row.get('siegeElapsedSeconds'))
        if not progress_state_valid(state) or len(row['milestoneSeconds'])!=row['mainClaims'].bit_count():
            raise ValueError('Raw baseline frames require actual siege claims, clocks and capture times.')
        observed=next((r for r in reversed(observations) if r['elapsedSeconds']<=row['siegeElapsedSeconds']+.001),None)
        if (not observed or any(row[k]!=observed[k] for k in ('stage','phase','mainClaims','optionalClaims','milestoneSeconds'))
                or row['stage']==2 and row['mainClaims']!=127):
            raise ValueError('Raw baseline exposure differs from observed earned progression.')


def performance_proof(report,raw,config,enforce_budget=True):
    setup=config.get('performance',{});hardware=report.get('hardware',{});cameras=setup.get('cameras',[])
    if (setup.get('version')!=1 or setup.get('settleSeconds')!=10 or setup.get('minWindowSeconds')!=60
            or len(cameras)!=3 or {c.get('stage') for c in cameras}!={0,1,2}
            or any(not point(c.get('eye')) or not point(c.get('target')) or math.dist(c['eye'],c['target'])<100
                   or c.get('fieldOfView')!=68 or len(c.get('positions',[]))!=36 or not all(point(p) for p in c['positions']) for c in cameras)
            or report.get('schemaVersion')!=1 or report.get('passed') is not True or report.get('performanceOnly') is not True
            or report.get('proofOnly') is not True or any(report.get(k)!=config.get(k) for k in ('map','mapSha256','cityRevision','signature'))
            or any(report.get(k) is not False for k in FLAGS) or report.get('bindings')!=setup
            or not settings_valid(report.get('settings')) or Path(report['settings'].get('gameUserSettingsIni','')).resolve()!=Path(setup.get('settingsPath','')).resolve()
            or any(not isinstance(hardware.get(k),str) or not 0<len(hardware[k])<=2048
                   for k in ('cpu','gpu','adapter','driverVersion','os','engineVersion'))
            or not re.match(r'^5\.8\.2(?:[-+]|$)',hardware.get('engineVersion',''))
            or type(hardware.get('physicalMemoryBytes')) is not int or hardware['physicalMemoryBytes']<=0
            or raw.get('schemaVersion')!=1 or raw.get('complete') is not True
            or not isinstance(raw.get('frames'),list) or not 0<len(raw['frames'])<=1_000_000
            or report.get('frames',{}).get('count')!=len(raw['frames']) or len(report.get('windows',[]))!=3):
        raise ValueError('Rendered performance proof is incomplete, differently bound, capped or lacks actual frames.')
    if config.get('performanceBaseline'):
        if (report.get('performanceBaseline') is not True or report.get('isolatedStageWindows') is not False
                or report.get('statsMode')!='normalized' or any(report.get('sourceCity',{}).get(k)!=v for k,v in PRESERVED_CITY.items())
                or any(report.get(k) is not False for k in ('progressionAcceptance','victoryAcceptance','conquestAcceptance','routeAcceptance','fullSiegeAdmission'))):
            raise ValueError('Preserved-city baseline is exposure only; gameplay/admission is unverified.')
        earned_progression(report,raw,config)
    roster(report)
    for index,row in enumerate(raw['frames']):
        previous=raw['frames'][index-1] if index else None
        if (row.get('index')!=index or previous and (row['stage']<previous['stage']
                or row['elapsedSeconds']<=previous['elapsedSeconds']
                or abs(row['frameMs']-(row['elapsedSeconds']-previous['elapsedSeconds'])*1000)>1)):
            raise ValueError('Raw frame sequence omits wall time or substitutes stage exposure.')
    positions=report.get('formationPositions',[]);by_id={(r.get('stage'),r.get('index')):r for r in positions}
    if len(positions)!=108 or len(by_id)!=108:raise ValueError('All 108 actual formation witnesses are required.')
    for camera in cameras:
        for index,p in enumerate(camera['positions']):
            witness=by_id.get((camera['stage'],index),{})
            if (witness.get('point')!=p or not point(witness.get('actualFloor')) or abs(witness['actualFloor'][2]-p[2])>25
                    or not finite(witness.get('floorNormalZ')) or not math.sqrt(.5)<=witness['floorNormalZ']<=1.001
                    or witness.get('capsuleRadiusCm')!=42 or witness.get('capsuleHalfHeightCm')!=96 or witness.get('captureRadiusCm')!=650
                    or any(witness.get(k) is not True for k in ('floorClear','capsuleClear','navigation','captureExclusion'))
                    or not finite(witness.get('minimumCaptureDistanceCm')) or witness['minimumCaptureDistanceCm']<700):
                raise ValueError('Actual formation floor/capsule/navigation/capture exclusion is unverified.')
    windows=[]
    if any(f.get('stage') not in (0,1,2) for f in raw['frames']):raise ValueError('Unexpected performance stage.')
    for camera in cameras:
        stage=camera['stage'];rows=[f for f in raw['frames'] if f['stage']==stage];previous=None;run=[];longest=[]
        direction=[camera['target'][i]-camera['eye'][i] for i in range(3)];magnitude=math.sqrt(sum(v*v for v in direction))
        for row in rows:
            counts=('drawCalls','primitives','aegisEnrolled','riftboundEnrolled','alive','dead','respawning','avatars','modelReady','visible',
                    'projected','recentlyRendered','unoccluded','streamingRequests')
            if (not finite(row.get('elapsedSeconds')) or not finite(row.get('stageElapsedSeconds')) or row['stageElapsedSeconds']<0
                    or type(row.get('index')) is not int or row['index']<0 or not finite(row.get('frameMs')) or row['frameMs']<=0
                    or any(not finite(row.get(k)) or row[k]<0 for k in ('gameThreadMs','renderThreadMs','rhiThreadMs','gpuMs','physicalMiB'))
                    or any(type(row.get(k)) is not int or row[k]<0 for k in counts)
                    or any(type(row.get(k)) is not bool for k in ('eligible','cameraMatches','encounterActive','leasePaused','preparing','benchmarkOrders','settled'))
                    or row.get('phase') not in ('active','transition','finished','waiting')
                    or not settings_valid(row.get('settings')) or row['settings']!=report['settings']
                    or not point(row.get('cameraEye')) or not point(row.get('cameraDirection')) or not finite(row.get('cameraFov'))
                    or previous and (row['elapsedSeconds']<=previous['elapsedSeconds'] or row['index']<=previous['index']
                       or abs(row['frameMs']-(row['elapsedSeconds']-previous['elapsedSeconds'])*1000)>1)):
                raise ValueError('Malformed or discontinuous actual frame/camera/settings evidence.')
            previous=row
            if (row['aegisEnrolled']>18 or row['riftboundEnrolled']>18 or any(row[k]>36 for k in counts[4:-1])
                    or row['visible']>min(row['projected'],row['recentlyRendered'],row['unoccluded'],row['modelReady'],row['avatars'])):
                raise ValueError('Impossible actual crowd counts.')
            camera_matches=(all(abs(v-camera['eye'][i])<=1 for i,v in enumerate(row['cameraEye']))
                and all(abs(v-direction[i]/magnitude)<=.0001 for i,v in enumerate(row['cameraDirection']))
                and abs(row['cameraFov']-camera['fieldOfView'])<=.01)
            active=row['phase']=='active' and not row['leasePaused'] and not row['preparing']
            if row['cameraMatches'] and not camera_matches or row['encounterActive']!=active:
                raise ValueError('Actual camera/activity contradicts native witnesses.')
            eligible=(active and row['cameraMatches'] and camera_matches and row['stageElapsedSeconds']>=10
                and row['aegisEnrolled']==18 and row['riftboundEnrolled']==18 and row['alive']+row['dead']==36
                and all(row[k]==36 for k in ('avatars','modelReady','visible','projected','recentlyRendered','unoccluded'))
                and row['streamingRequests']==0 and row.get('rosterSha256')==report['rosterSha256'] and row.get('statsMode')==report['statsMode']
                and all(row[k]>0 for k in ('gameThreadMs','renderThreadMs','gpuMs')))
            if row['settled']!=(row['stageElapsedSeconds']>=10) or row['eligible']!=eligible:
                raise ValueError('Eligible crowd exposure differs from actual phase/population/rendering.')
            if eligible:run.append(row)
            else:run=[]
            if run and (not longest or run[-1]['elapsedSeconds']-run[0]['elapsedSeconds']>longest[-1]['elapsedSeconds']-longest[0]['elapsedSeconds']):longest=run
        seconds=longest[-1]['elapsedSeconds']-longest[0]['elapsedSeconds'] if len(longest)>1 else 0
        if seconds+.000001<60:raise ValueError('No continuous settled visible36 exposure at stage '+str(stage))
        claimed=next((w for w in report['windows'] if w.get('stage')==stage),{})
        if (claimed.get('startElapsedSeconds')!=longest[0]['elapsedSeconds'] or claimed.get('endElapsedSeconds')!=longest[-1]['elapsedSeconds']
                or claimed.get('frameCount')!=len(longest) or claimed.get('settleSeconds')!=10):
            raise ValueError('Window receipt differs from actual raw frames.')
        times=sorted(f['frameMs'] for f in longest);fps=(len(longest)-1)/seconds;p95=times[min(len(times)-1,math.floor(len(times)*.95))]
        if enforce_budget and (fps+.000001<60 or p95>16.7+.000001):raise ValueError('Absolute crowded60FPS/p95 budget failed.')
        windows.append(dict(stage=stage,seconds=seconds,frames=len(longest),fps=fps,p95FrameMs=p95))
    return windows


def baseline_comparison(candidate,baseline,comparison):
    settings=lambda value:{k:v for k,v in value.items() if k!='gameUserSettingsIni'}
    if (comparison.get('schemaVersion')!=1 or comparison.get('sourceCity')!=PRESERVED_CITY
            or baseline.get('cityRevision')!=PRESERVED_CITY['revision'] or any(baseline.get('sourceCity',{}).get(k)!=v for k,v in PRESERVED_CITY.items())
            or candidate['hardware']!=baseline['hardware'] or settings(candidate['settings'])!=settings(baseline['settings'])
            or candidate['statsMode']!=baseline['statsMode'] or roster(candidate)!=roster(baseline)
            or comparison.get('candidateCityRevision')!=candidate['cityRevision'] or comparison.get('candidateSignature')!=candidate['signature']
            or comparison.get('baselineMap')!=baseline['map'] or comparison.get('baselineMapSha256')!=baseline['mapSha256']
            or len(comparison.get('stages',[]))!=3 or {r.get('stage') for r in comparison['stages']}!={0,1,2}
            or any(candidate['bindings'].get(k)!=baseline['bindings'].get(k) for k in ('settingsSha256','binarySha256','sourceHashes','configHashes'))):
        raise ValueError('A real comparable preserved-city baseline is required; matched booleans cannot replace it.')
    for stage in comparison['stages']:
        if (stage.get('candidateCamera')!=next(c for c in candidate['bindings']['cameras'] if c['stage']==stage['stage'])
                or stage.get('baselineCamera')!=next(c for c in baseline['bindings']['cameras'] if c['stage']==stage['stage'])
                or any(not isinstance(stage.get(k),str) or not stage[k].strip() for k in ('floorAndAnchorMapping','architectureDifference'))):
            raise ValueError('Actual baseline floor/anchor/camera differences must be disclosed.')


def performance_evidence(root,binding,plan,city,confined,digest,read):
    def load_bound(row):
        file=confined(root,row.get('path'))
        if digest(file)!=row.get('sha256'):raise ValueError('Actual performance evidence file changed.')
        return file,read(file)
    def load_run(row,baseline=False):
        file,report=load_bound(row);config_file,config=load_bound(row.get('config',{}));frames_file,frames=load_bound(row.get('frames',{}))
        if (report.get('configSha256')!=digest(config_file) or report.get('frames',{}).get('sha256')!=digest(frames_file)
                or Path(report.get('frames',{}).get('path','')).resolve()!=Path(config.get('performance',{}).get('settingsPath','')).parent.resolve()/'performance-frames.json'):
            raise ValueError('Native report is not bound to the actual setup/flushed frames.')
        setup=config['performance']
        for filename,expected in [(setup['settingsPath'],setup['settingsSha256']),(setup['binaryPath'],setup['binarySha256']),
                (setup['blueprintPath'],setup['blueprintSha256']),*setup['sourceHashes'].items(),*setup['configHashes'].items()]:
            if digest(Path(filename))!=expected:raise ValueError('Performance source/settings/native binary changed.')
        source=read(Path(setup['blueprintPath']))
        if source.get('signature')!=config.get('signature'):raise ValueError('Performance source signature differs.')
        if baseline:
            baseline_package_ownership(source)
            payload=source.get('signaturePayload')
            keys=('fixtureMode','sourceCity','sourceHashes','dependencyHashes','objectives','optionalObjectives','teamSpawns','performanceFormations')
            published=next(c for c in read(root/'artifacts/unreal/shared-cities/current.json')['cities'] if c['id']=='aegis_capital')
            if (not isinstance(payload,str) or hashlib.sha256(payload.encode()).hexdigest()!=source['signature']
                    or json.loads(payload)!={k:source[k] for k in keys} or source.get('sourceCity')!=PRESERVED_CITY
                    or source.get('performanceBaseline') is not True or source.get('isolatedStageWindows') is not False
                    or source.get('fixtureMode')!='earned_progression' or config.get('fixtureMode')!='earned_progression'
                    or source.get('map')!=config['map'] or source.get('packageHashes',{}).get(config['map'])!=config['mapSha256']
                    or source.get('geometrySignature')!=PRESERVED_CITY['revision'] or source.get('nativeImported') is not True
                    or source.get('sourceHashesUnchanged') is not True
                    or source.get('stageBaselineRecipeSha256')!=digest(root/'scripts/unreal/stage-citadel-performance-baseline.py')
                    or published['definition']!=PRESERVED_CITY['path'] or published['revision']!=PRESERVED_CITY['revision']
                    or any(source['sourceHashes'].get(k)!=v for k,v in published['packageHashes'].items())
                    or source['dependencyHashes']!=published['dependencyHashes']
                    or report.get('baselinePackageHashes')!=source['packageHashes']
                    or report.get('baselineSourceHashes')!=source['sourceHashes']
                    or report.get('baselineDependencyHashes')!=source['dependencyHashes']):
                raise ValueError('Actual baseline manifest/source dependency identity is missing or stale.')
            for hashes in (source['sourceHashes'],source['dependencyHashes'],source['packageHashes']):
                for package,expected in hashes.items():
                    if digest(performance_package_file(root,package))!=expected:raise ValueError('Preserved baseline content changed.')
        for camera in setup['cameras']:
            formation=next((f for f in source.get('performanceFormations',[]) if f.get('stage')==camera['stage']),{})
            if (formation.get('positions')!=camera['positions'] or formation.get('minimumCaptureGapCm')!=50
                    or formation.get('camera')!=dict(eye=camera['eye'],target=camera['target'],horizontalFovDegrees=camera['fieldOfView'])):
                raise ValueError('Performance orders/camera differ from signed actual source.')
        if bool(config.get('performanceBaseline'))!=baseline:raise ValueError('Baseline and candidate exposure modes cannot be interchanged.')
        return report,config,performance_proof(report,frames,config,not baseline)
    report,config,windows=load_run(binding)
    if report['cityRevision']!=city['city']['revision'] or report['signature']!=plan['signature']:
        raise ValueError('Rendered candidate performance belongs to another scenery revision.')
    baseline,baseline_config,baseline_windows=load_run(binding.get('baseline',{}),True)
    _,comparison=load_bound(binding.get('baseline',{}).get('comparison',{}))
    baseline_comparison(report,baseline,comparison)
    return report,dict(candidate=windows,baseline=baseline_windows)
