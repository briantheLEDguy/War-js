import {expect,it} from 'vitest';
import {gradeTerrainNetwork} from '../scripts/unreal/t1-grade-network';

it('finds the bounded envelope below a known valley without raising the source',()=>{
 const r=gradeTerrainNetwork([{id:'valley',points:[{x:0,z:0},{x:10,z:0},{x:20,z:0}]}],[],x=>Math.abs(x-10)*2,{spacing:10,maximumGrade:.1,neighbourDistance:20});
 expect(r.routes[0].points.map(p=>p.y)).toEqual([1,0,1]);expect(r.maximumCutMetres).toBe(19);
 expect(r.fullWidthAccepted||r.nativeVerified||r.appearanceApproved).toBe(false);
});
it('constrains nearby long roads without requiring an explicit shared junction',()=>{
 const routes=[{id:'low',points:[{x:0,z:0},{x:120,z:0}]},{id:'high',points:[{x:0,z:10},{x:120,z:10}]}],copy=structuredClone(routes);
 const r=gradeTerrainNetwork(routes,[],(_x,z)=>z*2,{spacing:12,maximumGrade:.1});
 expect(routes).toEqual(copy);expect(r.routes[0].points).toHaveLength(11);
 for(const p of r.routes[1].points)expect(p.y).toBeCloseTo(1,12);
 expect(r.nodeCount).toBe(22);expect(r.edgeCount).toBeGreaterThan(20);
});
it('shares intersections and flat foundations while preserving route and pad metadata',()=>{
 const routes=[{id:'east',points:[{x:-24,z:0},{x:0,z:0},{x:24,z:0}]},{id:'north',points:[{x:0,z:-24},{x:0,z:0},{x:0,z:24}]}];
 const pads=[{id:'court',x:0,z:0,height:100,radius:13,feather:20,preserveFooting:true}],copy=structuredClone(pads);
 const r=gradeTerrainNetwork(routes,pads,(x,z)=>20+Math.abs(x)+Math.abs(z));
 expect(pads).toEqual(copy);expect(r.pads[0].height).toBe(20);expect(r.pads[0].preserveFooting).toBe(true);
 for(const route of r.routes)for(const p of route.points.filter(p=>Math.hypot(p.x,p.z)<=21))expect(p.y).toBe(20);
 expect(r.routes.map(p=>p.id)).toEqual(['east','north']);
});
it('is deterministic and bounds every sampled road edge and nearby-road height difference',()=>{
 const routes=[{id:'curve',points:[{x:-60,z:0},{x:-20,z:30},{x:40,z:35},{x:70,z:-10}]},{id:'flank',points:[{x:-55,z:16},{x:0,z:50},{x:65,z:5}]}],field=(x:number,z:number)=>50+20*Math.sin(x/30)+10*Math.cos(z/20);
 const r=gradeTerrainNetwork(routes,[],field),points=r.routes.flatMap(p=>p.points);
 expect(gradeTerrainNetwork(routes,[],field)).toEqual(r);
 for(const p of points)expect(p.y!).toBeLessThanOrEqual(field(p.x,p.z)+1e-10);
 for(const a of points)for(const b of points)if(Math.hypot(a.x-b.x,a.z-b.z)<80)expect(Math.abs(a.y!-b.y!)).toBeLessThanOrEqual(.09*Math.hypot(a.x-b.x,a.z-b.z)+1e-10);
});
it('rejects malformed controls, geometry, fields and excessive admitted inventories',()=>{
 const route={id:'route',points:[{x:0,z:0},{x:10,z:0}]};
 for(const options of [{spacing:3},{spacing:21},{maximumGrade:.19},{neighbourDistance:121},{padBuffer:-1}])expect(()=>gradeTerrainNetwork([route],[],()=>0,options)).toThrow('Invalid bounded');
 for(const points of [[{x:0,z:0},{x:0,z:0}],[{x:0,z:0},{x:NaN,z:0}],[{x:0,z:0},{x:10001,z:0}]])expect(()=>gradeTerrainNetwork([{...route,points}],[],()=>0)).toThrow('Invalid bounded');
 for(const height of [NaN,Infinity,351,-101])expect(()=>gradeTerrainNetwork([route],[],()=>height)).toThrow('source height');
 expect(()=>gradeTerrainNetwork(Array(129).fill(route),[],()=>0)).toThrow('Invalid bounded');
 expect(()=>gradeTerrainNetwork([{id:'huge',points:[{x:-10000,z:-10000},{x:10000,z:10000},{x:-10000,z:10000}]}],[],()=>0,{spacing:4})).toThrow('node inventory');
});
