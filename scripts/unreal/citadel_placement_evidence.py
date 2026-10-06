"""Audit route-only live overlap accounting and complete projection certificates."""
import math
from citadel_separation_certificate import audit_separating_plane


def validate_route_placement_overlaps(e, movement_steps, radius, half_height):
    def require(condition):
        if not condition: raise ValueError('Incomplete or inconsistent native route placement overlap evidence')
    integer=lambda v:type(v) is int and v>=0
    finite=lambda v:type(v) in (int,float) and math.isfinite(v)
    vector=lambda v:isinstance(v,list) and len(v)==3 and all(finite(x) for x in v)
    require(movement_steps is None or integer(movement_steps))
    require(isinstance(e,dict) and all(integer(e.get(k)) for k in ('queries','rawClear','separated','blocked','unresolved','rawBlockingHits')))
    require(e['queries']==sum(e[k] for k in ('rawClear','separated','blocked','unresolved')))
    require(isinstance(e.get('contacts'),list) and len(e['contacts'])==sum(e[k] for k in ('separated','blocked','unresolved')))
    require(e['queries']>=(2 if movement_steps is None else 2+movement_steps*3 if movement_steps else 0))
    require(e.get('lastDisposition') in ('raw_clear','all_raw_contacts_proven_separated') if e['queries'] else e.get('lastDisposition')=='unused')
    counts=dict(separated=0,blocked=0,unresolved=0);raw_hits=0
    for record in e['contacts']:
        require(isinstance(record,dict))
        query,decision=record.get('query',{}),record.get('resolution',{})
        require(isinstance(query,dict) and isinstance(decision,dict))
        q=query.get('quaternion')
        require(vector(query.get('center')) and isinstance(q,list) and len(q)==4 and all(finite(x) for x in q)
            and abs(sum(x*x for x in q)-1)<=1e-10 and query.get('radiusCm')==radius and finite(radius) and radius>=42
            and query.get('halfHeightCm')==half_height and finite(half_height) and half_height>=max(96,radius)
            and query.get('role') in ('seed_probe','floor_adjusted','native_movement_pose'))
        require(decision.get('diagnosticOnly') is True and decision.get('admissionGranted') is False and decision.get('capsuleInputValid') is True)
        require(all(integer(decision.get(k)) for k in ('rawBlockingHitCount','uniqueBlockingBodyCount','resolvedSeparatedBodyCount','blockedBodyCount','unresolvedBodyCount')))
        require(0<decision['uniqueBlockingBodyCount']<=decision['rawBlockingHitCount'])
        require(decision['uniqueBlockingBodyCount']==sum(decision[k] for k in ('resolvedSeparatedBodyCount','blockedBodyCount','unresolvedBodyCount')))
        require(isinstance(decision.get('perBodyDecisions'),list) and len(decision['perBodyDecisions'])==decision['uniqueBlockingBodyCount'])
        body_counts=dict(separated=0,blocked=0,unresolved=0)
        for body in decision['perBodyDecisions']:
            require(isinstance(body,dict) and body.get('decision') in body_counts)
            body_counts[body['decision']]+=1
        require(integer(decision.get('inconsistentDuplicateCount'))
            and body_counts['separated']==decision['resolvedSeparatedBodyCount']
            and body_counts['blocked']==decision['blockedBodyCount']
            and body_counts['unresolved']==decision['unresolvedBodyCount'])
        if decision.get('proposalDecision')=='blocked':require(body_counts['blocked']>0)
        elif decision.get('proposalDecision')=='unresolved':
            require(body_counts['blocked']==0 and (body_counts['unresolved']>0 or decision['inconsistentDuplicateCount']>0))
        raw_hits+=decision['rawBlockingHitCount']
        if decision.get('proposalDecision')=='all_raw_contacts_proven_separated':
            counts['separated']+=1
            require(decision['blockedBodyCount']==decision['unresolvedBodyCount']==0
                and integer(decision.get('inconsistentDuplicateCount')) and decision['inconsistentDuplicateCount']==0)
            distance=half_height-radius
            axis=[2*(q[0]*q[2]+q[1]*q[3])*distance,2*(q[1]*q[2]-q[0]*q[3])*distance,(1-2*(q[0]*q[0]+q[1]*q[1]))*distance]
            for body in decision['perBodyDecisions']:
                require(isinstance(body,dict))
                w=body.get('liveWitness',{})
                require(isinstance(w,dict))
                require(body.get('originalBodyBindingVerified') is True and body.get('decision')=='separated'
                    and type(w.get('schemaVersion')) is int and w['schemaVersion']==2 and w.get('source')=='live_physics_shape_geometry_under_execute_read'
                    and all(w.get(k) is True for k in ('readLockEntered','complete','staticSingleBodyPolicySupported','separatedContactDiagnostic'))
                    and w.get('sameReadLockMtdBlocking') is False and w.get('admissionGranted') is False
                    and w.get('capsuleRadiusCm')==radius and vector(w.get('capsuleAxisStart')) and vector(w.get('capsuleAxisEnd')))
                require(all(abs(w['capsuleAxisStart'][i]-query['center'][i]+axis[i])<=1e-8
                    and abs(w['capsuleAxisEnd'][i]-query['center'][i]-axis[i])<=1e-8 for i in range(3)))
                require(isinstance(w.get('shapes'),list) and integer(w.get('liveShapeCount')) and len(w['shapes'])==w['liveShapeCount']
                    and all(isinstance(s,dict) and type(s.get('selected')) is bool and integer(s.get('shapeIndex'))
                        and s['shapeIndex']<w['liveShapeCount'] for s in w['shapes'])
                    and len({s['shapeIndex'] for s in w['shapes']})==w['liveShapeCount'])
                selected=[s for s in w['shapes'] if s['selected']]
                require(bool(selected) and integer(w.get('selectedShapeCount')) and len(selected)==w['selectedShapeCount'])
                for shape in selected:
                    require(all(shape.get(k) is True for k in ('boundToQueriedBody','queryShape','rigidUnitSeparationPolicySupported','affineQueryBoundsVerified','triangleWitnessComplete','finiteTriangles'))
                        and finite(shape.get('collisionMarginCm')) and shape['collisionMarginCm']==0 and shape.get('truncated') is False
                        and isinstance(shape.get('triangles'),list) and bool(shape['triangles'])
                        and integer(shape.get('candidateTriangleCount')) and len(shape['triangles'])==shape['candidateTriangleCount']
                        and integer(shape.get('liveCookedTriangleCount')) and shape['liveCookedTriangleCount']>=shape['candidateTriangleCount'])
                    seen=set()
                    for triangle in shape['triangles']:
                        require(isinstance(triangle,dict))
                        identity=triangle.get('internalTriangle')
                        require(integer(identity) and identity<shape['liveCookedTriangleCount'] and identity not in seen and triangle.get('finite') is True)
                        seen.add(identity)
                        audit=audit_separating_plane(w['capsuleAxisStart'],w['capsuleAxisEnd'],radius,triangle['worldVertices'],triangle)
                        require(audit['fullCapsuleSeparated'])
        else:
            require(query.get('role')=='seed_probe')
            if decision.get('proposalDecision')=='blocked':counts['blocked']+=1
            elif decision.get('proposalDecision')=='unresolved':counts['unresolved']+=1
            else:require(False)
    require(raw_hits==e['rawBlockingHits'] and all(e[k]==v for k,v in counts.items()))
