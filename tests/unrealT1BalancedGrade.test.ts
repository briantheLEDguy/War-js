import {expect,it} from 'vitest';
import {balancedTerrainNetwork} from '../scripts/unreal/t1-balanced-grade';
import {gradeTerrainNetwork} from '../scripts/unreal/t1-grade-network';

it('shares a known valley conflict between cut and fill without relaxing the grade',()=>{
 const routes=[{id:'valley',points:[{x:0,z:0},{x:10,z:0},{x:20,z:0}]}],field=(x:number)=>Math.abs(x-10)*2,options={spacing:10,maximumGrade:.1,neighbourDistance:20};
 const r=balancedTerrainNetwork(routes,[],field,options);
 expect(r.routes[0].points.map(p=>p.y)).toEqual([10.5,9.5,10.5]);
 expect(r.maximumCutMetres).toBe(9.5);expect(r.maximumFillMetres).toBe(9.5);
 expect(r.oneSidedMaximumCutMetres).toBe(19);expect(r.maximumCentreGrade).toBe(.1);
 expect(gradeTerrainNetwork(routes,[],field,options).routes[0].points.map(p=>p.y)).toEqual([1,0,1]);
 expect(r.fullWidthAccepted||r.nativeVerified||r.appearanceApproved).toBe(false);
});
it('leaves already feasible ground unchanged including both height-range limits',()=>{
 const routes=[{id:'ground',points:[{x:0,z:0},{x:40,z:0}]}];
 for(const value of [-100,0,350]){
  const r=balancedTerrainNetwork(routes,[],()=>value);expect(r.routes[0].points.every(p=>p.y===value)).toBe(true);
  expect(r.maximumCutMetres+r.maximumFillMetres).toBe(0);
 }
});
it('retains shared flat footings, metadata and input data while sampling each node once',()=>{
 const routes=[{id:'east',points:[{x:-24,z:0},{x:0,z:0},{x:24,z:0}]},{id:'north',points:[{x:0,z:-24},{x:0,z:0},{x:0,z:24}]}];
 const pads=[{id:'court',x:0,z:0,y:100,height:100,radius:13,feather:20,preserveFooting:true}],original=structuredClone({routes,pads});let calls=0;
 const r=balancedTerrainNetwork(routes,pads,(x,z)=>{calls++;return 20+Math.abs(x)+Math.abs(z);});
 expect({routes,pads}).toEqual(original);expect(calls).toBe(r.nodeCount);expect(r.pads[0].preserveFooting).toBe(true);
 expect(r.pads[0].y).toBe(r.pads[0].height);
 for(const route of r.routes)for(const p of route.points.filter(p=>Math.hypot(p.x,p.z)<=21))expect(p.y).toBe(r.pads[0].height);
});
it('is deterministic, height-translation invariant and preserves nearby-route slope constraints',()=>{
 const routes=[{id:'advance',points:[{x:-60,z:0},{x:-20,z:30},{x:40,z:35},{x:70,z:-10}]},{id:'flank',points:[{x:-55,z:16},{x:0,z:50},{x:65,z:5}]}],field=(x:number,z:number)=>50+20*Math.sin(x/30)+10*Math.cos(z/20);
 const r=balancedTerrainNetwork(routes,[],field),shift=balancedTerrainNetwork(routes,[],(x,z)=>field(x,z)+10),points=r.routes.flatMap(p=>p.points);
 expect(balancedTerrainNetwork(routes,[],field)).toEqual(r);
 r.routes.forEach((route,i)=>route.points.forEach((p,j)=>expect(shift.routes[i].points[j].y).toBeCloseTo(p.y!+10,10)));
 for(const a of points)for(const b of points)if(Math.hypot(a.x-b.x,a.z-b.z)<80)expect(Math.abs(a.y!-b.y!)).toBeLessThanOrEqual(.09*Math.hypot(a.x-b.x,a.z-b.z)+1e-10);
});
it('inherits bounded geometry, field and inventory validation',()=>{
 const route={id:'route',points:[{x:0,z:0},{x:10,z:0}]};
 for(const value of [NaN,Infinity,351,-101])expect(()=>balancedTerrainNetwork([route],[],()=>value)).toThrow('source height');
 expect(()=>balancedTerrainNetwork([route],[],()=>0,{maximumGrade:.19})).toThrow('Invalid bounded');
 expect(()=>balancedTerrainNetwork(Array(129).fill(route),[],()=>0)).toThrow('Invalid bounded');
});
