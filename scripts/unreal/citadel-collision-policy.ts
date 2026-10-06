/** Audit the unchanged native character capsule; profile names alone are insufficient. */
export function validateCitadelCapsulePolicy(p: any): void {
  const responses=(v:any)=>Array.isArray(v) && v.length===64
    && v.every((r:any,i:number)=>r===(i===8 ? 0 : 2));
  if (p?.version!==1 || p.source!=='native_AWarCharacter_class_default_capsule_v1'
    || p.characterClass!=='/Script/AegisWar.WarCharacter' || p.classDefaultClass!==p.characterClass
    || p.profile!=='Custom' || p.classDefaultProfile!=='Custom'
    || p.collisionEnabled!==3 || p.classDefaultCollisionEnabled!==3
    || p.objectChannel!==2 || p.classDefaultObjectChannel!==2
    || !responses(p.responses) || !responses(p.classDefaultResponses)
    || p.matchesClassDefault!==true || p.simulatingPhysics!==false || p.classDefaultSimulatingPhysics!==false)
    throw new Error('Complete unchanged native character capsule collision policy is required.');
}

/** Dimensions and walking limits must remain native throughout the entire proof. */
export function validateCitadelCapsuleKinematics(p:any):void {
  const near=(v:any,n:number,tolerance=1e-10)=>typeof v==='number' && Number.isFinite(v) && Math.abs(v-n)<=tolerance;
  const vector=(v:any,expected:number[])=>Array.isArray(v) && v.length===3 && v.every((n:any,i:number)=>near(n,expected[i]));
  if (p?.version!==1 || p.source!=='native_AWarCharacter_class_default_kinematics_v1'
    || p.capsuleRadiusCm!==42 || p.classDefaultRadiusCm!==42 || p.scaledRadiusCm!==42
    || p.capsuleHalfHeightCm!==96 || p.classDefaultHalfHeightCm!==96 || p.scaledHalfHeightCm!==96
    || !vector(p.componentScale,[1,1,1]) || !vector(p.capsuleAxis,[0,0,1])
    || p.maxStepHeightCm!==45 || p.classDefaultMaxStepHeightCm!==45
    || !near(p.walkableFloorZ,.71,1e-7) || p.classDefaultWalkableFloorZ!==0.7099999785423279
    || !near(p.walkableFloorZ,p.classDefaultWalkableFloorZ,1e-7) || p.capturedRuntimeValuesPinned!==true
    || p.gravityScale!==1 || p.classDefaultGravityScale!==1 || !vector(p.gravityDirection,[0,0,-1])
    || p.updatedComponentIsCapsule!==true || p.matchesClassDefault!==true)
    throw new Error('Complete unchanged native capsule geometry and walking policy is required.');
}
