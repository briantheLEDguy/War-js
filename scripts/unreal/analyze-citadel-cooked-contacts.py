"""Inspect complete live cooked-triangle witnesses without granting admission."""
import argparse
import json
import math
from pathlib import Path
from citadel_capsule_distance import capsule_triangle_clearance
from citadel_separation_certificate import audit_separating_plane


def analyze(witness):
    if (witness.get('schemaVersion')!=2 or witness.get('source')!='live_physics_shape_geometry_under_execute_read'
            or witness.get('diagnosticOnly') is not True or witness.get('complete') is not True
            or witness.get('readLockEntered') is not True):
        raise ValueError('A complete read-locked live-shape witness is required')
    shapes=witness['shapes'];selected=[row for row in shapes if row['selected']]
    if len(shapes)!=witness['liveShapeCount'] or len(selected)!=witness['selectedShapeCount'] or not selected:
        raise ValueError('Live shape coverage is incomplete')
    gaps=[];degenerate=0
    for shape in selected:
        triangles=shape.get('triangles',[])
        if (shape.get('triangleWitnessComplete') is not True or shape.get('truncated') is not False
                or shape.get('finiteTriangles') is not True or len(triangles)!=shape.get('candidateTriangleCount')
                or shape.get('affineQueryBoundsVerified') is not True
                or not shape['boundToQueriedBody'] or not shape['queryShape']):
            raise ValueError('Selected cooked shape coverage is incomplete')
        # Exported margins must be disclosed; do not reinterpret a margin-bearing
        # shape as an unexpanded triangle surface.
        margin=shape['collisionMarginCm']
        if not math.isfinite(margin) or margin!=0:raise ValueError('Nonzero or invalid live collision margin is unresolved')
        ids=set()
        for triangle in triangles:
            identity=triangle['internalTriangle']
            area=triangle['areaCm2']
            if (type(identity) is not int or identity<0 or identity>=shape['liveCookedTriangleCount']
                    or identity in ids or triangle['finite'] is not True or type(area) not in (int,float)
                    or not math.isfinite(area) or area<0):raise ValueError('Invalid or duplicate cooked triangle')
            ids.add(identity)
            gap=capsule_triangle_clearance(witness['capsuleAxisStart'],witness['capsuleAxisEnd'],
                witness['capsuleRadiusCm'],triangle['worldVertices'])
            degenerate+=triangle['areaCm2']==0
            row=dict(shapeIndex=shape['shapeIndex'],internalTriangle=identity,
                externalFace=triangle['externalFace'],surfaceGapCm=gap,areaCm2=triangle['areaCm2'])
            if 'projectionAxisRecorded' in triangle and triangle['projectionAxisRecorded']:
                row['projectionAudit']=audit_separating_plane(witness['capsuleAxisStart'],
                    witness['capsuleAxisEnd'],witness['capsuleRadiusCm'],triangle['worldVertices'],triangle)
            elif triangle.get('fullCapsuleSeparationCertified') is True:
                row['projectionAuditUnavailable']=True
            gaps.append(row)
    if not gaps:raise ValueError('No candidate cooked faces; transform/coverage remains unresolved')
    gaps.sort(key=lambda row:row['surfaceGapCm'])
    return dict(diagnosticOnly=True,minimumCandidateSurfaceGapCm=gaps[0]['surfaceGapCm'],
        candidateTriangles=len(gaps),degenerateTriangles=degenerate,closestTriangles=gaps[:8],
        independentlyAuditedCertificates=sum('projectionAudit' in row for row in gaps),
        gapIsMinimumTranslationDistance=False,gapIsGlobalMeshClearance=False,admissionGranted=False)


def analyze_report(report):
    rows=[];seen=set()
    for sample in report['routeWidthSamples']:
        if sample['passed']:continue
        for field in ('failedSubstepDiagnostic','destinationDiagnostic'):
            contacts=sample.get(field,{}).get('capsuleContacts')
            if not contacts:continue
            for overlap in contacts['admissionQuery']['overlaps']:
                body=overlap.get('directBodyQuery')
                if not body:continue
                key=(tuple(contacts['center']),tuple(contacts['quaternion']),contacts['radiusCm'],contacts['halfHeightCm'],
                    overlap['component']['path'],body['overlapItemIndex'],body['instanceBodyIndex'])
                if key in seen:continue
                seen.add(key);row=dict(route=sample['id'],center=contacts['center'],
                    quaternion=contacts['quaternion'],radiusCm=contacts['radiusCm'],halfHeightCm=contacts['halfHeightCm'],
                    overlapItemIndex=body['overlapItemIndex'],instanceBodyIndex=body['instanceBodyIndex'],
                    component=overlap['component']['path'],withoutMTD=body['withoutMTD'],withMTD=body['withMTD'],
                    nativeMtdDistanceCm=body['mtdDistanceCm'])
                try:row['geometryDiagnostic']=analyze(body['cookedTriangleWitness'])
                except (KeyError,TypeError,ValueError) as error:row['unresolved']=str(error)
                rows.append(row)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=json.loads(args.report.read_text());rows=analyze_report(report)
    args.output.write_text(json.dumps(dict(diagnosticOnly=True,sourceReport=str(args.report),rows=rows,
        admissionGranted=False,visualApproval=False),indent=2)+'\n')
    print(json.dumps(dict(output=str(args.output),bodyPoses=len(rows),unresolved=sum('unresolved' in row for row in rows),admissionGranted=False)))


if __name__=='__main__':main()
