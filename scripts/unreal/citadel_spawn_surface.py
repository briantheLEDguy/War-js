"""Signed spawn footprints; native floor and capsule checks remain mandatory."""
import math
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def relocation_witness(file, baseline):
    """An explicit overlay move binds actual unchanged paving and complete native paths."""
    path = Path(file).resolve()
    path.relative_to((ROOT/'artifacts/unreal/citadel-reference').resolve())
    report = json.loads(path.read_text())
    baseline_file = (ROOT/baseline['file']).resolve()
    baseline_file.relative_to((ROOT/'artifacts/unreal/aegis-citadel').resolve())
    if (report.get('schemaVersion') != 1 or report.get('packagesUnchanged') is not True or
            report.get('diagnosticOnly') is not True or report.get('traversalApproved') is not False or
            report.get('visualApproved') is not False or report.get('protectionRadiusCm') != 750 or
            report.get('spawnsCm') != baseline['battlefield']['team_spawns'][:2] or
            report.get('baselineSha256') != hashlib.sha256(baseline_file.read_bytes()).hexdigest() or
            any(report.get('packageHashes', {}).get(p) != h for p, h in baseline['packageHashes'].items())):
        raise ValueError('Spawn relocation needs an unchanged native source and exact original baseline.')
    pads = report.get('spawnPadCandidates', [])
    if not pads:
        raise ValueError('Native survey found no complete replacement spawn footprint.')
    pad = pads[0]
    convoy = next((row for row in report.get('paths', []) if row.get('kind')=='direct'), {})
    segments = convoy.get('segments', [])
    actual = segments[0] if len(segments)==1 else {}
    points = actual.get('pointsCm', [])
    if (actual.get('valid') is not True or actual.get('partial') is not False or len(points)<2 or
            any(not isinstance(p,list) or len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v)
                for v in p) for p in points) or
            math.dist(points[0],baseline['battlefield']['objectives'][1])>100 or
            math.dist(points[-1],baseline['battlefield']['objectives'][2])>100):
        raise ValueError('Spawn relocation needs the complete actual convoy path on the unchanged city.')
    def distance(point,a,b):
        delta=[b[i]-a[i] for i in range(3)];squared=sum(v*v for v in delta)
        t=max(0,min(1,sum((point[i]-a[i])*delta[i] for i in range(3))/squared)) if squared else 0
        return math.dist(point,[a[i]+t*delta[i] for i in range(3)])
    measured=min(distance(pad['pointCm'],a,b) for a,b in zip(points,points[1:]))
    if (abs(measured-pad['minimumConvoyCentrePathDistanceCm'])>.01 or measured<1300 or
            pad.get('diagnosticFootprintComplete') is not True or pad.get('widthCm')!=600 or
            any(math.dist(pad['pointCm'],p)<1450 for p in
                baseline['battlefield']['objectives']+baseline['battlefield']['optional_objectives'])):
        raise ValueError('Spawn survey clearance does not match its actual convoy path and objective separation.')
    original = json.loads(baseline_file.read_text())
    actors = {(package,row['actor']):row['state'] for package,rows in original['actors'].items() for row in rows}
    copies = {package:report['map'].rsplit('/',1)[0]+'/Layers/RetainedCity_'+str(index)
        for index,package in enumerate(baseline['city']['sceneryLevels'])}
    surface = dict(schemaVersion=1,index=0,point=pad['pointCm'],widthCm=pad['widthCm'],
        groundGradient=pad['groundGradient'],capsuleRadiusCm=42,capsuleHalfHeightCm=96,diagnosticOnly=True,
        samples=[])
    for sample in pad['samples']:
        source = dict(sample['source'])
        original = source.get('originalActorPackage')
        name = source.get('originalActorName')
        state = actors.get((original,name), {})
        state_hash = hashlib.sha256(json.dumps(state,sort_keys=True,separators=(',', ':')).encode()).hexdigest()
        copied = source.get('actorPackage', '')
        actor_path = copied+'.'+copied.rsplit('/',1)[-1]+':PersistentLevel.'+str(name)
        components = [component for component in state.get('components', [])
            if source.get('componentPath')==actor_path+'.'+component.get('name', '')
            and component.get('class')=='StaticMeshComponent'
            and component.get('mesh', '').split('.')[0]==source.get('meshPackage')]
        if (original not in baseline['packageHashes'] or not name or
                state_hash != source.get('actorStateSha256') or len(components)!=1 or
                copied != copies.get(original) or
                copied not in report['packageHashes'] or source.get('actorPath')!=actor_path):
            raise ValueError('Relocated spawn support is not part of the preserved city.')
        source['surveyActorPackage']=copied
        source['surveyActorPath']=actor_path
        source['surveyComponentPath']=source['componentPath']
        source['actorPackage'] = original
        source['actorPath']=original+'.'+original.rsplit('/',1)[-1]+':PersistentLevel.'+name
        source['componentPath']=source['actorPath']+'.'+components[0]['name']
        surface['samples'].append(dict(x=sample['x'],y=sample['y'],floor=sample['pointCm'],
            normal=sample['normal'],capsuleClear=sample['capsuleClear'],source=source))
    result = dict(schemaVersion=1,index=0,fromPoint=report['spawnsCm'][0],point=pad['pointCm'],
        protectionRadiusCm=750,minimumConvoyCentrePathDistanceCm=pad['minimumConvoyCentrePathDistanceCm'],
        characterPathToOriginalSpawn=pad['characterPathToOriginalSpawn'],
        characterPathToCheckpoint=pad['characterPathToCheckpoint'],measuredSurface=surface,
        survey=dict(file=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            map=report['map'],revision=report['revision'],baselineSha256=report['baselineSha256']),
        rationale='Move only the lower defender spawn overlay clear of the convoy; retain paving, city actors, objectives and protection rules.',
        freshNativeReplayRequired=True,nativeTraversalApproved=False)
    _validate_relocation(result,baseline)
    return result


def _validate_relocation(row, baseline):
    if (row.get('schemaVersion') != 1 or row.get('index') != 0 or
            row.get('fromPoint') != baseline['battlefield']['team_spawns'][0] or
            row.get('point') != row.get('measuredSurface', {}).get('point') or
            row.get('protectionRadiusCm') != 750 or
            type(row.get('minimumConvoyCentrePathDistanceCm')) not in (int,float) or
            not math.isfinite(row['minimumConvoyCentrePathDistanceCm']) or
            row['minimumConvoyCentrePathDistanceCm'] < 1300 or
            row.get('freshNativeReplayRequired') is not True or row.get('nativeTraversalApproved') is not False):
        raise ValueError('Spawn overlay relocation lacks convoy standoff or preserved protection rules.')
    for key, end in (('characterPathToOriginalSpawn',row['fromPoint']),
                     ('characterPathToCheckpoint',baseline['battlefield']['objectives'][2])):
        path = row.get(key, {});points = path.get('pointsCm', [])
        if (path.get('valid') is not True or path.get('partial') is not False or len(points) < 2 or
                any(not isinstance(p,list) or len(p)!=3 or
                    any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in points) or
                math.dist(points[0],row['point']) > 100 or math.dist(points[-1],end) > 100):
            raise ValueError('Spawn relocation requires complete actual character navigation to the preserved approach.')


def gradient(row, recipe_version):
    value = row.get('groundGradient', [0, 0])
    if (recipe_version >= 6 and 'groundGradient' not in row or
            not isinstance(value, list) or len(value) != 2 or
            any(type(v) not in (int, float) or not math.isfinite(v) for v in value) or
            math.hypot(*value) > 1 or row['index'] >= 2 and value != [0, 0]):
        raise ValueError('Spawn surface requires a finite walkable ground gradient; upper pads stay flat.')
    return value


def seed(point, x, y, edge, slope):
    dx, dy = x * edge / 2, y * edge / 2
    return [point[0] + dx, point[1] + dy, point[2] + slope[0] * dx + slope[1] * dy]


def validate_retained_surfaces(baseline, approaches, relocations=None, recipe_version=6):
    """Bind both lower footprints to the unchanged native scene, never an old map guess."""
    rows = baseline.get('spawnPadSurfaces', [])
    if len(rows) != 2 or {row.get('index') for row in rows} != {0, 1}:
        raise ValueError('Both retained spawn surfaces require a fresh native survey.')
    if relocations:
        if recipe_version < 11 or len(relocations) != 1:
            raise ValueError('Only the versioned lower defender overlay relocation is supported.')
        relocation = relocations[0]
        expected = relocation_witness(ROOT/relocation['survey']['file'],baseline)
        if relocation != expected:
            raise ValueError('Spawn relocation differs from its exact native survey.')
        rows = [relocation['measuredSurface'] if row['index']==0 else row for row in rows]
    hashes = baseline['packageHashes']
    for row in rows:
        pad = next(p for p in approaches if p['index'] == row['index'])
        slope = gradient(pad, 6)
        samples = row.get('samples', [])
        if (row.get('schemaVersion') != 1 or row.get('point') != pad['points'][0] or
                row.get('widthCm') != pad['widthCm'] or row.get('groundGradient') != slope or
                row.get('capsuleRadiusCm') != 42 or row.get('capsuleHalfHeightCm') != 96 or
                row.get('diagnosticOnly') is not True or len(samples) != 25 or
                {(s.get('x'), s.get('y')) for s in samples} !=
                {(x, y) for x in range(-2, 3) for y in range(-2, 3)}):
            raise ValueError('Retained spawn surface differs from its exact measured footprint.')
        for sample in samples:
            source = sample.get('source', {})
            floor, normal = sample.get('floor'), sample.get('normal')
            expected = seed(row['point'], sample['x'], sample['y'], row['widthCm']/2-42, slope)
            if (source.get('meshPackage') not in hashes or
                    source.get('meshSha256') != hashes[source['meshPackage']] or
                    source.get('actorPackage') not in hashes or not source.get('actorPath') or
                    not source.get('componentPath') or not source.get('actorStateSha256') or
                    not isinstance(floor, list) or len(floor) != 3 or
                    not isinstance(normal, list) or len(normal) != 3 or
                    any(type(v) not in (int, float) or not math.isfinite(v) for v in floor + normal) or
                    normal[2] < math.sqrt(.5) or sample.get('capsuleClear') is not True or
                    math.dist(floor[:2], expected[:2]) > .01 or abs(floor[2]-expected[2]) > 25 or
                    any(abs(-normal[i]/normal[2]-slope[i]) > .001 for i in range(2))):
                raise ValueError('Retained native spawn survey lacks unchanged source, support or capsule clearance.')
