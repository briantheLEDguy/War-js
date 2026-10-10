/** Shared-edge authoring geometry. Curves are proposals until terrain and native traversal are verified. */
import type { TerrainPoint } from '../../shared/orvrTerrain';

export interface RouteCurve { start: TerrainPoint; end: TerrainPoint; points: TerrainPoint[] }
export interface RouteMove { from: TerrainPoint; to: TerrainPoint }
export interface NetworkRoute { id: string; points: TerrainPoint[] }
const key = (p: TerrainPoint) => `${p.x},${p.z}`;
export const routeEdgeKey = (a: TerrainPoint,b: TerrainPoint) => [key(a),key(b)].sort().join('|');
const unit = (x: number,z: number) => { const d=Math.hypot(x,z);return {x:x/d,z:z/d}; };
const finite = (p: TerrainPoint) => Number.isFinite(p.x) && Number.isFinite(p.z) && (p.y===undefined || Number.isFinite(p.y));

/** Construct each undirected edge once so supplies and opposing route directions share exact ground. */
export function curveRouteNetwork<T extends NetworkRoute>(routes: T[],moves: RouteMove[],frozenEdges: string[]=[],spacing=20) {
  if (!routes.length || routes.length>64 || !Number.isFinite(spacing) || spacing<2 || spacing>40
    || moves.length>256 || new Set(routes.map(r=>r.id)).size!==routes.length) throw new Error('Invalid route network inventory');
  const nodes=new Map<string,TerrainPoint>(),adjacency=new Map<string,Set<string>>(),edges=new Map<string,[TerrainPoint,TerrainPoint]>();
  for (const route of routes) {
    if (!route.id || route.points.length<2 || route.points.length>4096 || route.points.some(p=>!finite(p))) throw new Error('Invalid route network points');
    for (const p of route.points) {
      const prior=nodes.get(key(p));
      if (prior && Math.abs((prior.y??0)-(p.y??0))>.01) throw new Error('Route junction elevations differ');
      nodes.set(key(p),{...p});if(!adjacency.has(key(p)))adjacency.set(key(p),new Set());
    }
    for (let i=1;i<route.points.length;i++) {
      let a=route.points[i-1],b=route.points[i];
      if (Math.hypot(a.x-b.x,a.z-b.z)<.001) throw new Error('Zero-length route edge');
      adjacency.get(key(a))!.add(key(b));adjacency.get(key(b))!.add(key(a));
      if(key(a)>key(b))[a,b]=[b,a];edges.set(routeEdgeKey(a,b),[a,b]);
    }
  }
  if(nodes.size>4096 || edges.size>4096)throw new Error('Route network exceeds bounded graph');
  const relocation=new Map<string,TerrainPoint>(),frozen=new Set(frozenEdges);
  for(const move of moves) {
    if(!finite(move.from)||!finite(move.to)||!nodes.has(key(move.from))||relocation.has(key(move.from)))throw new Error('Invalid route node relocation');
    relocation.set(key(move.from),{...nodes.get(key(move.from))!,...move.to});
  }
  const at=(p:TerrainPoint)=>relocation.get(key(p))??p;
  if(new Set([...nodes.values()].map(p=>key(at(p)))).size!==nodes.size)throw new Error('Relocation merges distinct junctions');
  for(const id of frozen) {
    const edge=edges.get(id);if(!edge)throw new Error('Frozen route edge is absent');
    if(edge.some(p=>key(at(p))!==key(p)||(at(p).y??0)!==(p.y??0)))throw new Error('Frozen route edge cannot move');
  }
  const tangent=(a:TerrainPoint,b:TerrainPoint)=>{
    const p=at(a),q=at(b),direct=unit(q.x-p.x,q.z-p.z);
    const others=[...adjacency.get(key(a))!].filter(k=>k!==key(b)).map(k=>at(nodes.get(k)!));
    if(!others.length)return direct;
    const back=others.map(r=>unit(r.x-p.x,r.z-p.z)).sort((r,s)=>(r.x*direct.x+r.z*direct.z)-(s.x*direct.x+s.z*direct.z))[0];
    return back.x*direct.x+back.z*direct.z<-.25?unit(direct.x-back.x,direct.z-back.z):direct;
  };
  const curves:RouteCurve[]=[];let count=0;
  for(const [id,[a,b]] of edges) {
    const p=at(a),q=at(b),length=Math.hypot(q.x-p.x,q.z-p.z);
    if(length<.001)throw new Error('Relocation collapses an edge');
    let points:TerrainPoint[];
    if(frozen.has(id))points=[{...p},{...q}];
    else {
      const ta=tangent(a,b),tb=tangent(b,a),handle=Math.min(length*.3,55),steps=Math.ceil(length/spacing);
      if(steps>2048)throw new Error('Route edge exceeds sampling budget');
      const c={x:p.x+ta.x*handle,z:p.z+ta.z*handle},d={x:q.x+tb.x*handle,z:q.z+tb.z*handle};
      points=Array.from({length:steps+1},(_,i)=>{const t=i/steps,u=1-t;return {x:u**3*p.x+3*u*u*t*c.x+3*u*t*t*d.x+t**3*q.x,z:u**3*p.z+3*u*u*t*c.z+3*u*t*t*d.z+t**3*q.z,y:(p.y??0)+((q.y??0)-(p.y??0))*t};});
      points[0]={...p};points[steps]={...q};
    }
    count+=points.length;if(count>20000)throw new Error('Route curves exceed sampling budget');
    curves.push({start:{...a},end:{...b},points});
  }
  return {curves,routes:routes.map(route=>({...route,points:mapRouteEdges(route.points,curves)}))};
}

/** Apply qualified shared edges; unrelated segments retain their existing coordinates. */
export function mapRouteEdges(points: TerrainPoint[],curves: RouteCurve[]): TerrainPoint[] {
  const edges=new Map(curves.map(c=>[routeEdgeKey(c.start,c.end),c]));const result:TerrainPoint[]=[];
  for(let i=1;i<points.length;i++) {
    const a=points[i-1],b=points[i],curve=edges.get(routeEdgeKey(a,b));
    const next=curve?(key(a)===key(curve.start)?curve.points:[...curve.points].reverse()):[a,b];
    result.push(...(result.length?next.slice(1):next).map(p=>({...p})));
  }
  return result;
}

/** Move a branch join by its source-edge parameter, preserving its authored vertical control. */
export function projectRouteJoin(point: TerrainPoint,curves: RouteCurve[],maximumDistance=12): TerrainPoint {
  if(!finite(point)||!Number.isFinite(maximumDistance)||maximumDistance<0||maximumDistance>100)throw new Error('Invalid route join projection');
  let best=maximumDistance,result={...point};
  for(const curve of curves) {
    const a=curve.start,b=curve.end,dx=b.x-a.x,dz=b.z-a.z;
    const t=Math.max(0,Math.min(1,((point.x-a.x)*dx+(point.z-a.z)*dz)/(dx*dx+dz*dz)));
    const distance=Math.hypot(point.x-a.x-t*dx,point.z-a.z-t*dz);if(distance>=best)continue;
    const f=t*(curve.points.length-1),i=Math.min(curve.points.length-2,Math.floor(f)),u=f-i,p=curve.points[i],q=curve.points[i+1];
    result={...point,x:p.x+(q.x-p.x)*u,z:p.z+(q.z-p.z)*u};best=distance;
  }
  return result;
}
