/** Conservative plan-view traffic/building envelope audit; exclusions are reported explicitly. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { composeSunmeadowEnvironment } from '../../../../scripts/campaign/sunmeadow-environment.mjs';
const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),root=path.resolve(work,'../../..');
const report=JSON.parse(await fs.readFile(path.join(work,'build-report.json'),'utf8'));const assets=new Map(report.map(a=>[a.asset_id,a]));
const zone=composeSunmeadowEnvironment(JSON.parse(await fs.readFile(path.join(root,'public/assets/maps/sunmeadow_march.json'),'utf8')),{architecture:true,nature:true,terrain:true});
const buildings=zone.props.filter(p=>/frontier_sunmeadow_(farmhouse|workshop|supply_post)$/.test(p.assetKey));
const local=(p,x,z)=>({x:(Math.cos(p.rotY??0)*(x-p.x)-Math.sin(p.rotY??0)*(z-p.z))/(p.scale??1),z:(Math.sin(p.rotY??0)*(x-p.x)+Math.cos(p.rotY??0)*(z-p.z))/(p.scale??1)});
const world=(p,x,z)=>({x:p.x+Math.cos(p.rotY??0)*x+Math.sin(p.rotY??0)*z,z:p.z-Math.sin(p.rotY??0)*x+Math.cos(p.rotY??0)*z});
const pointSegment=(p,a,b)=>{const dx=b.x-a.x,dz=b.z-a.z,t=Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.z-a.z)*dz)/(dx*dx+dz*dz||1)));return Math.hypot(p.x-a.x-t*dx,p.z-a.z-t*dz);};
const segmentDistance=(a,b,c,d)=>{
  const ux=b.x-a.x,uz=b.z-a.z,vx=d.x-c.x,vz=d.z-c.z,den=ux*vz-uz*vx;
  if(Math.abs(den)>1e-12){const dx=c.x-a.x,dz=c.z-a.z,t=(dx*vz-dz*vx)/den,u=(dx*uz-dz*ux)/den;if(t>=0&&t<=1&&u>=0&&u<=1)return 0;}
  return Math.min(pointSegment(a,c,d),pointSegment(b,c,d),pointSegment(c,a,b),pointSegment(d,a,b));
};
const roadOverlaps=[];
for(const building of buildings){
  const asset=assets.get(building.assetKey),b=asset.lods[0].bounds_z_up;
  for(const road of zone.paths){
    let distance=Infinity,nearest;
    const corners=[{x:b.minimum[0],z:-b.maximum[1]},{x:b.maximum[0],z:-b.maximum[1]},{x:b.maximum[0],z:-b.minimum[1]},{x:b.minimum[0],z:-b.minimum[1]}];
    const inside=p=>p.x>=b.minimum[0]&&p.x<=b.maximum[0]&&p.z>=-b.maximum[1]&&p.z<=-b.minimum[1];
    for(let i=1;i<road.points.length;i++){
      const start=local(building,road.points[i-1].x,road.points[i-1].z),end=local(building,road.points[i].x,road.points[i].z);
      const d=(inside(start)||inside(end)?0:Math.min(...corners.map((point,j)=>segmentDistance(start,end,point,corners[(j+1)%4]))))*(building.scale??1);
      if(d<distance){distance=d;nearest={start:road.points[i-1],end:road.points[i]};}
    }
    if(distance<road.width/2)roadOverlaps.push({building:building.id,road:road.id,distanceToMeasuredEnvelope:distance,roadHalfWidth:road.width/2,nearest});
  }
}
const axes=p=>[{x:Math.cos(p.rotY??0),z:-Math.sin(p.rotY??0)},{x:Math.sin(p.rotY??0),z:Math.cos(p.rotY??0)}];
const polygon=p=>{const b=assets.get(p.assetKey).lods[0].bounds_z_up;return[[b.minimum[0],-b.maximum[1]],[b.maximum[0],-b.maximum[1]],[b.maximum[0],-b.minimum[1]],[b.minimum[0],-b.minimum[1]]].map(([x,z])=>world(p,x,z));};
const intersects=(a,b)=>[...axes(a),...axes(b)].every(axis=>{const x=polygon(a).map(p=>p.x*axis.x+p.z*axis.z),y=polygon(b).map(p=>p.x*axis.x+p.z*axis.z);return Math.max(...x)>Math.min(...y)&&Math.max(...y)>Math.min(...x);});
const buildingOverlaps=[];
for(let i=0;i<buildings.length;i++)for(let j=i+1;j<buildings.length;j++)if(intersects(buildings[i],buildings[j]))buildingOverlaps.push([buildings[i].id,buildings[j].id]);
const output={roadOverlaps,buildingOverlaps,npcs:zone.npcs,stations:zone.craftingStations,method:'Conservative full LOD0 mesh envelope; exact segment-to-oriented-rectangle distance tests every authored road segment and full lane width. Gatehouses/walls excluded because their through-passages require per-surface checks. Roof-only overlaps require height review.'};
await fs.writeFile(path.join(work,'review/traffic_audit.json'),JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify({roadOverlaps,buildingOverlaps},null,2));
