/** Offline centre-line grading; full-width terrain and native movement require separate qualification. */
import type {TerrainPoint,OrvrTerrainControls} from '../../shared/orvrTerrain';

export interface TerrainGradeRoute {id:string;points:TerrainPoint[]}
export interface TerrainGradeOptions {spacing?:number;maximumGrade?:number;neighbourDistance?:number;padBuffer?:number}
type Pad=OrvrTerrainControls['flattenAreas'][number];
type Node={x:number;z:number;raw:number;height:number;edges:Map<number,number>};

/** Greatest network height envelope below the sampled landform, with shared junctions and nearby-road constraints. */
export function gradeTerrainNetwork(routes:TerrainGradeRoute[],pads:Pad[],field:(x:number,z:number)=>number,options:TerrainGradeOptions={}) {
 const spacing=options.spacing??12,grade=options.maximumGrade??.09,near=options.neighbourDistance??80,buffer=options.padBuffer??8;
 const point=(p:TerrainPoint)=>p&&[p.x,p.z].every(v=>Number.isFinite(v)&&Math.abs(v)<=10000);
 if(![spacing,grade,near,buffer].every(Number.isFinite)||spacing<4||spacing>20||grade<.02||grade>.18||near<20||near>120||buffer<0||buffer>16
  ||!Array.isArray(routes)||!routes.length||routes.length>128||!Array.isArray(pads)||pads.length>128
  ||routes.some(r=>!r.id||!Array.isArray(r.points)||r.points.length<2||r.points.length>4096||r.points.some((p,i)=>!point(p)||i>0&&Math.hypot(p.x-r.points[i-1].x,p.z-r.points[i-1].z)<.001))
  ||pads.some(p=>!p.id||!point(p)||!Number.isFinite(p.radius)||p.radius<1||p.radius>200))throw new Error('Invalid bounded terrain grade network');
 const result=structuredClone(routes),footings=structuredClone(pads),nodes:Node[]=[],lookup=new Map<string,number>();let edges=0;
 const at=(p:TerrainPoint)=>{
  const key=p.x.toFixed(5)+','+p.z.toFixed(5),existing=lookup.get(key);if(existing!==undefined)return existing;
  if(nodes.length>=12000)throw new Error('Terrain grade node inventory exceeded');
  const raw=field(p.x,p.z);if(!Number.isFinite(raw)||raw< -100||raw>350)throw new Error('Invalid terrain grade source height');
  const index=nodes.length;lookup.set(key,index);nodes.push({x:p.x,z:p.z,raw,height:raw,edges:new Map()});return index;
 };
 const connect=(a:number,b:number,cost:number)=>{
  if(a===b)return;const old=nodes[a].edges.get(b);if(old!==undefined&&old<=cost)return;
  if(old===undefined&&++edges>750000)throw new Error('Terrain grade edge inventory exceeded');
  nodes[a].edges.set(b,cost);nodes[b].edges.set(a,cost);
 };
 const memberships:number[][]=[];
 for(const route of result){
  const dense:TerrainPoint[]=[];
  for(let i=1;i<route.points.length;i++){
   const a=route.points[i-1],b=route.points[i],count=Math.ceil(Math.hypot(b.x-a.x,b.z-a.z)/spacing);
   if(dense.length+count>12000)throw new Error('Terrain grade node inventory exceeded');
   for(let j=0;j<count;j++)dense.push(j?{x:a.x+(b.x-a.x)*j/count,z:a.z+(b.z-a.z)*j/count}:{...a});
  }
  dense.push({...route.points[route.points.length-1]});route.points=dense;const ids=dense.map(at);memberships.push(ids);
  for(let i=1;i<ids.length;i++)connect(ids[i-1],ids[i],Math.hypot(dense[i].x-dense[i-1].x,dense[i].z-dense[i-1].z)*grade);
 }
 // Flat foundations join every sampled route or other footing inside their reserved area.
 const padIds=footings.map(at);
 for(let i=0;i<footings.length;i++)for(let j=0;j<nodes.length;j++)if(Math.hypot(nodes[j].x-footings[i].x,nodes[j].z-footings[i].z)<=footings[i].radius+buffer)connect(padIds[i],j,0);
 // Hash local neighbours instead of building a quadratic all-pairs graph.
 const buckets=new Map<string,number[]>();
 for(let i=0;i<nodes.length;i++){
  const n=nodes[i],bx=Math.floor(n.x/near),bz=Math.floor(n.z/near);
  for(let dx=-1;dx<=1;dx++)for(let dz=-1;dz<=1;dz++)for(const j of buckets.get((bx+dx)+','+(bz+dz))??[]){
   const distance=Math.hypot(n.x-nodes[j].x,n.z-nodes[j].z);if(distance<near)connect(i,j,distance*grade);
  }
  const key=bx+','+bz;if(!buckets.has(key))buckets.set(key,[]);buckets.get(key)!.push(i);
 }
 const heap:Array<[number,number]>=[];
 const push=(item:[number,number])=>{heap.push(item);let i=heap.length-1;while(i){const p=(i-1)>>1;if(heap[p][0]<=item[0])break;heap[i]=heap[p];i=p;}heap[i]=item;};
 const pop=()=>{const first=heap[0],last=heap.pop()!;if(heap.length){let i=0;while(i*2+1<heap.length){let c=i*2+1;if(c+1<heap.length&&heap[c+1][0]<heap[c][0])c++;if(last[0]<=heap[c][0])break;heap[i]=heap[c];i=c;}heap[i]=last;}return first;};
 nodes.forEach((n,i)=>push([n.height,i]));
 while(heap.length){const [height,i]=pop();if(height!==nodes[i].height)continue;for(const [j,cost] of nodes[i].edges)if(height+cost<nodes[j].height){nodes[j].height=height+cost;push([nodes[j].height,j]);}}
 result.forEach((r,i)=>r.points.forEach((p,j)=>p.y=nodes[memberships[i][j]].height));
 footings.forEach((p,i)=>{p.height=nodes[padIds[i]].height;if(p.y!==undefined)p.y=p.height;});
 return {routes:result,pads:footings,nodeCount:nodes.length,edgeCount:edges,maximumCutMetres:Math.max(...nodes.map(n=>n.raw-n.height)),
  maximumCentreGrade:grade,fullWidthAccepted:false,nativeVerified:false,appearanceApproved:false};
}
