import { createHash } from 'node:crypto';

export type CitadelSurfacePoint = [number,number,number];
export interface CitadelRouteSurfaceProfile {
  schemaVersion:1; routeId:string; kind:'world_x_piecewise_linear'; meshId:'stairs_and_balconies';
  knotsCm:[number,number][];
  boundaryPolicy:'closed_profile_domain_shared_boundaries_same_height';
  construction:'continuous_paved_fan_ramp';
}
type Route = {id:string;points:CitadelSurfacePoint[];width:number};
export type CitadelSurfaceProofRoute = {id:string;points:CitadelSurfacePoint[];clearWidthCm:number;surfaceProfile?:CitadelRouteSurfaceProfile};
const finite=(v:unknown):v is number => typeof v==='number' && Number.isFinite(v) && Math.abs(v)<=1_000_000;
const point=(v:any):v is CitadelSurfacePoint => Array.isArray(v) && v.length===3 && v.every(finite);
const fields=['schemaVersion','routeId','kind','meshId','knotsCm','boundaryPolicy','construction'];
const exact=(v:any,wanted:string[]) => v && typeof v==='object' && !Array.isArray(v)
  && Object.keys(v).sort().join(',')===[...wanted].sort().join(',');
function fail(reason:string):never { throw new Error('Invalid signed citadel route surface: '+reason); }

export function validateCitadelSurfaceProfile(value:unknown): asserts value is CitadelRouteSurfaceProfile {
  const v=value as CitadelRouteSurfaceProfile;
  if (!exact(v,fields) || v.schemaVersion!==1 || !/^[a-z0-9_]{1,80}$/.test(v.routeId)
    || v.kind!=='world_x_piecewise_linear' || v.meshId!=='stairs_and_balconies'
    || v.boundaryPolicy!=='closed_profile_domain_shared_boundaries_same_height' || v.construction!=='continuous_paved_fan_ramp'
    || !Array.isArray(v.knotsCm) || v.knotsCm.length<2 || v.knotsCm.length>64
    || v.knotsCm.some(k => !Array.isArray(k) || k.length!==2 || !k.every(finite))) fail('schema, identity or knots');
  for (let i=1;i<v.knotsCm.length;i++) {
    const [x,z]=v.knotsCm[i], [beforeX,beforeZ]=v.knotsCm[i-1];
    if (x<=beforeX || 1/Math.hypot(1,(z-beforeZ)/(x-beforeX))<.7) fail('nonmonotonic X or unwalkable authored slope');
  }
}

/** A lateral lane uses its actual world X, never a centerline elevation guess. */
export function citadelSurfaceHeight(profile:CitadelRouteSurfaceProfile,x:number):number {
  const knots=profile.knotsCm;
  if (!finite(x) || x<knots[0][0] || x>knots.at(-1)![0]) fail('sample escaped the closed profile domain');
  for (let i=1;i<knots.length;i++) if (x<=knots[i][0]) {
    const a=knots[i-1],b=knots[i]; return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0]);
  }
  return knots.at(-1)![1];
}

export function validateCitadelRouteSurfaceProfiles(values:unknown,routes:Route[]):Map<string,CitadelRouteSurfaceProfile> {
  if (values===undefined) return new Map();
  if (!Array.isArray(values) || values.length>16) fail('bounded profile list');
  const result=new Map<string,CitadelRouteSurfaceProfile>();
  for (const value of values) {
    validateCitadelSurfaceProfile(value);
    const route=routes.find(r => r.id===value.routeId);
    if (!route || result.has(value.routeId) || !finite(route.width) || route.width<600 || route.points.length<2
      || route.points.some(p => !point(p) || Math.abs(p[2]-citadelSurfaceHeight(value,p[0]))>.01)) fail('route identity or centerline height');
    for (let i=1;i<route.points.length;i++) {
      const a=route.points[i-1],b=route.points[i],dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy);
      if (length<1) fail('physical route segment');
      // Bind the whole floor footprint, including the actual capsule's outer edge.
      for (const p of [a,b]) for (const side of [-1,1]) citadelSurfaceHeight(value,p[0]-dy/length*side*route.width/2);
    }
    result.set(value.routeId,value);
  }
  return result;
}

export function citadelRouteWidthSeed(route:CitadelSurfaceProofRoute,segment:number,alpha:number,lane:number,radius:number):CitadelSurfacePoint {
  const a=route.points[segment],b=route.points[segment+1];
  if (!a || !b || !Number.isFinite(alpha) || alpha<0 || alpha>1 || !Number.isFinite(lane) || Math.abs(lane)>1
    || !Number.isFinite(radius) || radius<42 || route.clearWidthCm<=2*radius) fail('walking sample parameters');
  const dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy),offset=lane*(route.clearWidthCm/2-radius);
  if (length<1) fail('walking segment');
  const x=a[0]+dx*alpha-dy/length*offset,y=a[1]+dy*alpha+dx/length*offset;
  return [x,y,route.surfaceProfile ? citadelSurfaceHeight(route.surfaceProfile,x) : a[2]+(b[2]-a[2])*alpha];
}

export function validateCitadelSurfaceReport(setup:any,routes:CitadelSurfaceProofRoute[]):void {
  const expected=routes.filter(r => r.surfaceProfile).map(r => ({id:r.id,surfaceProfile:r.surfaceProfile}));
  for (const row of expected) {
    validateCitadelSurfaceProfile(row.surfaceProfile);
    if (row.id!==row.surfaceProfile!.routeId+':forward' && row.id!==row.surfaceProfile!.routeId+':reverse') fail('profile belongs to another proof route');
  }
  if (expected.length && (setup.surfaceSamplingMethod!=='signed_world_x_piecewise_linear_per_lane_and_movement_step'
      || !same(setup.surfaceProfiles,expected))
    || !expected.length && (setup.surfaceProfiles!==undefined && !same(setup.surfaceProfiles,[])
      || setup.surfaceSamplingMethod!==undefined && setup.surfaceSamplingMethod!=='signed_world_x_piecewise_linear_per_lane_and_movement_step'))
    fail('native sampling method or exact profile witnesses');
}

const semantic=(v:any):any => Array.isArray(v) ? v.map(semantic) : v && typeof v==='object'
  ? Object.fromEntries(Object.keys(v).sort().map(k => [k,semantic(v[k])])) : v;
const same=(a:any,b:any) => JSON.stringify(semantic(a))===JSON.stringify(semantic(b));
const orient=(a:CitadelSurfacePoint,b:CitadelSurfacePoint,c:CitadelSurfacePoint) => (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
function contains(triangle:CitadelSurfacePoint[],p:CitadelSurfacePoint):boolean {
  const scale=Math.max(1,...triangle.map((a,i) => Math.hypot(a[0]-triangle[(i+1)%3][0],a[1]-triangle[(i+1)%3][1])));
  return triangle.every((a,i) => orient(a,triangle[(i+1)%3],p)>=-1e-6*scale);
}

/** Source faces are independently bound; native clearance remains a separate mandatory proof. */
export function requireCitadelRouteSurfaceBindings(source:any,blueprint:any,meshes:Map<string,any>):void {
  const profiles=validateCitadelRouteSurfaceProfiles(blueprint.routeSurfaceProfiles,blueprint.routes ?? []);
  const bindings=source.surfaceBindings ?? [];
  if (!Array.isArray(bindings) || bindings.length!==profiles.size) fail('complete source surface bindings');
  const used=new Set<string>();
  for (const row of bindings) {
    if (!exact(row,['routeId','profilePayload','profileSha256','meshId','sourceMeshSha256','topTriangleIndices'])
      || !profiles.has(row.routeId) || used.has(row.routeId) || typeof row.profilePayload!=='string'
      || Buffer.byteLength(row.profilePayload,'utf8')>65_536
      || createHash('sha256').update(row.profilePayload).digest('hex')!==row.profileSha256) fail('source profile identity or raw payload SHA');
    used.add(row.routeId);const profile=profiles.get(row.routeId)!;
    let parsed:any;try { parsed=JSON.parse(row.profilePayload); } catch { fail('source profile payload JSON'); }
    validateCitadelSurfaceProfile(parsed);
    const asset=source.assets.find((a:any) => a.id===row.meshId),mesh=meshes.get(row.meshId);
    if (!same(parsed,profile) || row.meshId!==profile.meshId || !asset || row.sourceMeshSha256!==asset.sha256 || !mesh
      || !Array.isArray(row.topTriangleIndices) || !row.topTriangleIndices.length || row.topTriangleIndices.length>8192
      || new Set(row.topTriangleIndices).size!==row.topTriangleIndices.length) fail('actual floor mesh or source ordinals');
    const triangles:CitadelSurfacePoint[][]=[];const identities=new Set<string>();
    for (const index of row.topTriangleIndices) {
      if (!Number.isSafeInteger(index) || index<0 || index>=mesh.indices.length/3) fail('source triangle ordinal');
      const points:CitadelSurfacePoint[]=mesh.indices.slice(index*3,index*3+3).map((i:number) => mesh.positions[i]);
      if (points.length!==3 || points.some(p => !point(p) || Math.abs(p[2]-citadelSurfaceHeight(profile,p[0]))>.01)) fail('authored triangle does not follow h(worldX)');
      const [a,b,c]=points,ab=b.map((v,i) => v-a[i]),ac=c.map((v,i) => v-a[i]);
      const normal=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]];
      const minimum=Math.min(...points.map(p => p[0])),maximum=Math.max(...points.map(p => p[0]));
      if (normal[2]<=0 || normal[2]/Math.hypot(...normal)<.7 || profile.knotsCm.slice(1,-1).some(k => k[0]>minimum+.01 && k[0]<maximum-.01)) fail('floor winding/slope or unpartitioned knot seam');
      const identity=JSON.stringify(points.map(p => JSON.stringify(p)).sort());
      if (identities.has(identity)) fail('duplicate source floor face');identities.add(identity);triangles.push(points);
    }
    const route=blueprint.routes.find((r:any) => r.id===row.routeId),proof={id:route.id,points:route.points,clearWidthCm:route.width,surfaceProfile:profile};
    const previous=new Map<number,CitadelSurfacePoint>();
    const covered=(p:CitadelSurfacePoint) => { if (!triangles.some(t => contains(t,p))) fail('source floor omits a lane or turn sample'); };
    for (let segment=0;segment<proof.points.length-1;segment++) {
      const a=proof.points[segment],b=proof.points[segment+1],count=Math.max(1,Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/10));
      for (let sample=0;sample<=count;sample++) for (const lane of [-1,-.5,0,.5,1]) {
        const p=citadelRouteWidthSeed(proof,segment,sample/count,lane,42),before=previous.get(lane);
        if (before) { const steps=Math.max(1,Math.ceil(Math.hypot(p[0]-before[0],p[1]-before[1])/10));
          for (let i=1;i<steps;i++) { const x=before[0]+(p[0]-before[0])*i/steps;
            covered([x,before[1]+(p[1]-before[1])*i/steps,citadelSurfaceHeight(profile,x)]); } }
        covered(p);
        if (Math.abs(lane)===1) {
          const dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy),x=p[0]-dy/length*lane*42;
          covered([x,p[1]+dx/length*lane*42,citadelSurfaceHeight(profile,x)]);
        }
        previous.set(lane,p);
      }
    }
  }
}
