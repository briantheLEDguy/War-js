"""Exact sampling and provenance guards for the private wing ground survey."""
import math
import re


def survey_points(version=2):
    if version not in (1,2):
        raise ValueError('Unknown wing-support sampling version')
    points={}
    for side in (-1,1):
        for x in (27000,28000,29000,30000,31000,32000,33000,34000,34400):
            for y in (6900,7450,8000,8550,9100):
                points.setdefault((x,side*y),[]).append('wing_'+str(side))
        towers=[(27450,850,9100),(33900,720,9100)]
        if version==2:towers.append((28600,1000,8900))
        for x,width,centre_y in towers:
            # Include the structural corner piers, which project beyond the body.
            half=max(width/2,width*.45+55)
            for dx in (-half,0,half):
                for dy in (-half,0,half):
                    points.setdefault((x+dx,side*centre_y+dy),[]).append('end_tower_'+str(side))
    return points


def checked_ground_summary(report):
    revision=report.get('revision','')
    prefix='/Game/WorldRebuild/AegisCitadel_'+revision
    if (report.get('schemaVersion')!=1 or not re.fullmatch('[a-f0-9]{12}',revision)
            or report.get('signature','')[:12]!=revision
            or not re.fullmatch('[a-f0-9]{64}',report.get('signature',''))
            or report.get('map')!=prefix+'/ReviewCandidate'
            or report.get('sourceAndCandidateHashesUnchanged') is not True
            or report.get('diagnosticOnly') is not True
            or report.get('groundContactApproved') is not False):
        raise ValueError('Exact private ground-survey provenance is required')
    hashes=report.get('packageHashes',{})
    if (not hashes or not all(isinstance(h,str) and re.fullmatch('[a-f0-9]{64}',h) for h in hashes.values())
            or not re.fullmatch('[a-f0-9]{64}',report.get('mapSha256',''))
            or hashes.get(report['map'])!=report.get('mapSha256')):
        raise ValueError('Ground survey map hash differs from its package closure')
    expected=survey_points(report.get('samplingVersion',1))
    rows=report.get('samples',[])
    actual={}
    finite=lambda p:isinstance(p,list) and len(p)==3 and all(type(v) in (int,float) and math.isfinite(v) for v in p)
    for row in rows:
        key=(row.get('xCm'),row.get('yCm'))
        p=row.get('pointCm')
        if (key not in expected or key in actual or row.get('regions')!=expected[key]
                or row.get('groundFound') is not True or not finite(p)
                or not finite(row.get('normal')) or any(abs(p[i]-key[i])>.05 for i in (0,1))
                or not -5000<=p[2]<=20000
                or not .98<=math.sqrt(sum(v*v for v in row['normal']))<=1.02
                or row.get('gapBelowCurrentEditFloorCm')!=max(0,2400-p[2])):
            raise ValueError('Ground contact is missing, duplicated or inconsistent at an exact footprint sample')
        actual[key]=row
    if set(actual)!=set(expected):
        raise ValueError('Every wing edge and projected tower-base sample is required')
    actors={r.get('actor'):r for r in report.get('groundActors',[])}
    if any(row.get('actor') not in actors or actors[row['actor']].get('package') not in hashes
           or not row.get('component') for row in rows):
        raise ValueError('A ground hit is outside the signed native package closure')
    heights=[row['pointCm'][2] for row in rows]
    return dict(samples=len(rows),minimumGroundZCm=min(heights),maximumGroundZCm=max(heights),
        samplesBelowCurrentEditFloor=sum(z<2400 for z in heights),
        maximumGapBelowCurrentEditFloorCm=max(max(0,2400-z) for z in heights),
        samplesAboveWingBase=sum(z>6010 for z in heights),
        continuousGroundContactProven=False,nativeFoundationApproved=False)
