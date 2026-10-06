/** Validate route-only placement receipts; saved evidence never authorizes movement. */
const finite = (v: any): v is number => typeof v === 'number' && Number.isFinite(v);
const vector = (v: any) => Array.isArray(v) && v.length === 3 && v.every(finite);
const dot = (a: number[], b: number[]) => a.reduce((sum, v, i) => sum + v * b[i], 0);
const subtract = (a: number[], b: number[]) => a.map((v, i) => v - b[i]);
const integer = (v: any) => Number.isSafeInteger(v) && v >= 0;
const fail = (): never => { throw new Error('Incomplete or inconsistent native route placement overlap evidence.'); };

function separatedWitness(w: any, query: any): void {
  if (w?.schemaVersion !== 2 || w.source !== 'live_physics_shape_geometry_under_execute_read'
    || w.readLockEntered !== true || w.complete !== true || w.staticSingleBodyPolicySupported !== true
    || w.sameReadLockMtdBlocking !== false || w.separatedContactDiagnostic !== true || w.admissionGranted !== false
    || !vector(w.capsuleAxisStart) || !vector(w.capsuleAxisEnd) || w.capsuleRadiusCm !== query.radiusCm
    || !integer(w.liveShapeCount) || !Array.isArray(w.shapes) || w.shapes.length !== w.liveShapeCount) fail();
  const q=query.quaternion, distance=query.halfHeightCm-query.radiusCm;
  const axis=[2*(q[0]*q[2]+q[1]*q[3]),2*(q[1]*q[2]-q[0]*q[3]),1-2*(q[0]*q[0]+q[1]*q[1])].map(v=>v*distance);
  if (w.capsuleAxisStart.some((v:number,i:number)=>Math.abs(v-query.center[i]+axis[i])>1e-8)
    || w.capsuleAxisEnd.some((v:number,i:number)=>Math.abs(v-query.center[i]-axis[i])>1e-8)) fail();
  const shapeIds=new Set<number>();
  for (const shape of w.shapes) {
    if (!shape || typeof shape.selected!=='boolean' || !integer(shape.shapeIndex)
      || shape.shapeIndex>=w.liveShapeCount || shapeIds.has(shape.shapeIndex)) fail();
    shapeIds.add(shape.shapeIndex);
  }
  const shapes=w.shapes.filter((s:any)=>s.selected);
  if (!shapes.length || !integer(w.selectedShapeCount) || shapes.length!==w.selectedShapeCount) fail();
  for (const shape of shapes) {
    if (shape.boundToQueriedBody!==true || shape.queryShape!==true || shape.rigidUnitSeparationPolicySupported!==true
      || shape.collisionMarginCm!==0 || shape.affineQueryBoundsVerified!==true || shape.triangleWitnessComplete!==true
      || shape.truncated!==false || shape.finiteTriangles!==true || !Array.isArray(shape.triangles)
      || !integer(shape.candidateTriangleCount) || !integer(shape.liveCookedTriangleCount)
      || shape.liveCookedTriangleCount<shape.candidateTriangleCount
      || !shape.triangles.length || shape.triangles.length!==shape.candidateTriangleCount) fail();
    const seen=new Set<number>();
    for (const t of shape.triangles) {
      if (!integer(t.internalTriangle) || t.internalTriangle>=shape.liveCookedTriangleCount || seen.has(t.internalTriangle)
        || t.finite!==true || t.certificateVersion!==1 || t.guardPolicyVersion!==1 || t.projectionAxisRecorded!==true
        || t.fullCapsuleSeparationCertified!==true || !vector(t.separatingUnitAxis) || !vector(t.projectionOriginCm)
        || ['numericalGuardCm','separatingPlaneGapCm','gapTriangleAfterCapsuleCm','gapCapsuleAfterTriangleCm'].some(k=>!finite(t[k]))
        || !Array.isArray(t.worldVertices) || t.worldVertices.length!==3 || !t.worldVertices.every(vector)) fail();
      seen.add(t.internalTriangle);
      const n=t.separatingUnitAxis, norm=dot(n,n), origin=t.projectionOriginCm;
      if (Math.abs(norm-1)>1e-10 || !finite(t.separatingAxisSquaredLength) || Math.abs(t.separatingAxisSquaredLength-norm)>1e-12
        || origin.some((v:number,i:number)=>Math.abs(v-(w.capsuleAxisStart[i]+w.capsuleAxisEnd[i])/2)>1e-8)) fail();
      const p=[w.capsuleAxisStart,w.capsuleAxisEnd].map(v=>dot(subtract(v,origin),n));
      const support=query.radiusCm*Math.sqrt(norm), caps=[Math.min(...p)-support,Math.max(...p)+support];
      const vertices=t.worldVertices.map((v:number[])=>dot(subtract(v,origin),n));
      const triangle=[Math.min(...vertices),Math.max(...vertices)];
      for (const [recorded,actual] of [[t.capsuleProjectionCm,caps],[t.triangleProjectionCm,triangle]])
        if (!Array.isArray(recorded) || recorded.length!==2 || recorded.some((v:number,i:number)=>!finite(v) || Math.abs(v-actual[i])>1e-8)) fail();
      const above=triangle[0]-caps[1], below=caps[0]-triangle[1], gap=Math.max(above,below);
      const longest=Math.max(...t.worldVertices.map((v:number[],i:number)=>Math.hypot(...subtract(v,t.worldVertices[(i+1)%3]))));
      const u=subtract(t.worldVertices[1],t.worldVertices[0]),v=subtract(t.worldVertices[2],t.worldVertices[0]);
      const normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
      const magnitude=Math.max(query.radiusCm,...[w.capsuleAxisStart,w.capsuleAxisEnd,...t.worldVertices].flat().map(Math.abs));
      const guard=Math.max(.001,32*2**-23*(magnitude+longest+query.radiusCm+Math.hypot(...subtract(w.capsuleAxisEnd,w.capsuleAxisStart))));
      if (magnitude>1e6 || longest**2<=1e-12 || Math.hypot(...normal)<=longest**2*1e-6
        || t.numericalGuardCm<guard-1e-10 || gap<=t.numericalGuardCm
        || Math.abs(t.separatingPlaneGapCm-gap)>1e-8 || Math.abs(t.gapTriangleAfterCapsuleCm-above)>1e-8
        || Math.abs(t.gapCapsuleAfterTriangleCm-below)>1e-8
        || t.projectionGapDirection!==(above>=below ? 'triangle_above_capsule' : 'capsule_above_triangle')) fail();
    }
  }
}

export function validateRoutePlacementOverlaps(e: any, movementSteps: number | null, radius: number, halfHeight: number): void {
  const keys=['queries','rawClear','separated','blocked','unresolved','rawBlockingHits'];
  if ((movementSteps!==null && !integer(movementSteps)) || !e || keys.some(k=>!integer(e[k])) || e.queries!==e.rawClear+e.separated+e.blocked+e.unresolved
    || !Array.isArray(e.contacts) || e.contacts.length!==e.separated+e.blocked+e.unresolved
    || e.queries<(movementSteps===null ? 2 : movementSteps ? 2+movementSteps*3 : 0)
    || (e.queries ? !['raw_clear','all_raw_contacts_proven_separated'].includes(e.lastDisposition) : e.lastDisposition!=='unused')) fail();
  let rawHits=0;
  const counts={separated:0,blocked:0,unresolved:0};
  for (const r of e.contacts) {
    const query=r.query, d=r.resolution;
    if (!query || !vector(query.center) || !Array.isArray(query.quaternion) || query.quaternion.length!==4
      || !query.quaternion.every(finite) || Math.abs(dot(query.quaternion,query.quaternion)-1)>1e-10
      || !finite(query.radiusCm) || query.radiusCm!==radius || radius<42 || !finite(query.halfHeightCm)
      || query.halfHeightCm!==halfHeight || halfHeight<96 || halfHeight<radius
      || !['seed_probe','floor_adjusted','native_movement_pose'].includes(query.role)
      || d?.diagnosticOnly!==true || d.admissionGranted!==false || d.capsuleInputValid!==true
      || !integer(d.rawBlockingHitCount) || d.rawBlockingHitCount<1 || !integer(d.uniqueBlockingBodyCount)
      || d.uniqueBlockingBodyCount<1 || d.uniqueBlockingBodyCount>d.rawBlockingHitCount
      || ['resolvedSeparatedBodyCount','blockedBodyCount','unresolvedBodyCount'].some(k=>!integer(d[k]))
      || d.uniqueBlockingBodyCount!==d.resolvedSeparatedBodyCount+d.blockedBodyCount+d.unresolvedBodyCount
      || !Array.isArray(d.perBodyDecisions) || d.perBodyDecisions.length!==d.uniqueBlockingBodyCount) fail();
    rawHits+=d.rawBlockingHitCount;
    const bodyCounts={separated:0,blocked:0,unresolved:0};
    for (const body of d.perBodyDecisions) {
      if (!body || !Object.hasOwn(bodyCounts,body.decision)) fail();
      ++bodyCounts[body.decision as keyof typeof bodyCounts];
    }
    if (!integer(d.inconsistentDuplicateCount) || bodyCounts.separated!==d.resolvedSeparatedBodyCount
      || bodyCounts.blocked!==d.blockedBodyCount || bodyCounts.unresolved!==d.unresolvedBodyCount
      || (d.proposalDecision==='blocked' && !bodyCounts.blocked)
      || (d.proposalDecision==='unresolved' && (bodyCounts.blocked || (!bodyCounts.unresolved && !d.inconsistentDuplicateCount)))) fail();
    if (d.proposalDecision==='all_raw_contacts_proven_separated') {
      ++counts.separated;
      if (d.blockedBodyCount || d.unresolvedBodyCount || d.inconsistentDuplicateCount!==0) fail();
      for (const body of d.perBodyDecisions) {
        if (body.originalBodyBindingVerified!==true || body.decision!=='separated') fail();
        separatedWitness(body.liveWitness,query);
      }
    } else {
      if (query.role!=='seed_probe') fail(); // rejected lift seeds may precede a valid swept floor placement
      if (d.proposalDecision==='blocked') ++counts.blocked;
      else if (d.proposalDecision==='unresolved') ++counts.unresolved;
      else fail();
    }
  }
  if (rawHits!==e.rawBlockingHits || Object.entries(counts).some(([k,v])=>e[k]!==v)) fail();
}
