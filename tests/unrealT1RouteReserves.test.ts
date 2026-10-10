import {expect,it} from 'vitest';
import {detourRoundReserve} from '../scripts/unreal/t1-route-reserves';
import {distanceToSpatialSegment} from '../shared/worldSpatial';
it('routes tangent approaches and sampled arc chords outside the complete reserve',()=>{
 const source=[{x:-50,z:0,y:3},{x:50,z:0,y:7}],copy=structuredClone(source),centre={x:0,z:0},r=detourRoundReserve(source,centre,10);
 expect(source).toEqual(copy);expect(r.detouredSegments).toBe(1);expect(r.points[0]).toEqual(source[0]);expect(r.points.at(-1)).toEqual(source[1]);
 for(let i=1;i<r.points.length;i++)expect(distanceToSpatialSegment(centre,r.points[i-1],r.points[i])).toBeGreaterThanOrEqual(10-1e-10);
 expect(detourRoundReserve(source,centre,10)).toEqual(r);
});
it('chooses a contained alternate side and preserves clear routes',()=>{
 const source=[{x:-50,z:0},{x:50,z:0}],r=detourRoundReserve(source,{x:0,z:0},10,(a,b)=>a.z>=-1e-9&&b.z>=-1e-9);
 expect(r.points.every(p=>p.z>=-1e-9)).toBe(true);expect(()=>detourRoundReserve(source,{x:0,z:0},10,()=>false)).toThrow('contained');
 const clear=[{x:-50,z:20},{x:50,z:20}];expect(detourRoundReserve(clear,{x:0,z:0},10)).toEqual({points:clear,detouredSegments:0});
});
it('rejects malformed controls and routes whose endpoints occupy the reserve',()=>{
 for(const radius of [NaN,3,81])expect(()=>detourRoundReserve([{x:-50,z:0},{x:50,z:0}],{x:0,z:0},radius)).toThrow('bounded');
 expect(()=>detourRoundReserve([{x:0,z:0},{x:50,z:0}],{x:0,z:0},10)).toThrow('endpoint');
});
