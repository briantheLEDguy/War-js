/** Offline cut/fill grading; full-width terrain, native movement and appearance need separate qualification. */
import {gradeTerrainNetwork,type TerrainGradeRoute,type TerrainGradeOptions} from './t1-grade-network';

type Pads=Parameters<typeof gradeTerrainNetwork>[1];

/** Midpoint of feasible lower/upper envelopes avoids excavating every conflict into the lower route. */
export function balancedTerrainNetwork(routes:TerrainGradeRoute[],pads:Pads,field:(x:number,z:number)=>number,options:TerrainGradeOptions={}) {
 // Reflection maps the existing admitted [-100,350] height range onto itself.
 const reflection=250,samples=new Map<string,number>();
 const height=(x:number,z:number)=>{
  const key=x.toFixed(5)+','+z.toFixed(5);
  if(!samples.has(key))samples.set(key,field(x,z));
  return samples.get(key)!;
 };
 const lower=gradeTerrainNetwork(routes,pads,height,options);
 const reflected=gradeTerrainNetwork(routes,pads,(x,z)=>reflection-height(x,z),options);
 if(lower.nodeCount!==reflected.nodeCount||lower.edgeCount!==reflected.edgeCount)throw new Error('Balanced terrain grade graphs differ');
 const result=structuredClone(lower);let maximumCutMetres=0,maximumFillMetres=0;
 const midpoint=(x:number,z:number,a:number,b:number)=>{
  const y=(a+reflection-b)/2,delta=height(x,z)-y;
  maximumCutMetres=Math.max(maximumCutMetres,delta);maximumFillMetres=Math.max(maximumFillMetres,-delta);return y;
 };
 result.routes.forEach((r,i)=>r.points.forEach((p,j)=>p.y=midpoint(p.x,p.z,p.y!,reflected.routes[i].points[j].y!)));
 result.pads.forEach((p,i)=>{p.height=midpoint(p.x,p.z,p.height,reflected.pads[i].height);if(p.y!==undefined)p.y=p.height;});
 return {...result,policy:'balanced-envelope' as const,maximumCutMetres,maximumFillMetres,
  oneSidedMaximumCutMetres:lower.maximumCutMetres,oneSidedMaximumFillMetres:reflected.maximumCutMetres};
}
