import {describe,expect,it} from 'vitest';
import {createOrvrGridHeightSampler,orvrHeightAt,type OrvrTerrainControls} from '../shared/orvrTerrain';
const controls=():OrvrTerrainControls=>({sourceVersion:'balanced-test',gradedRoutes:true,landforms:[],flattenAreas:[],clearCorridors:[
 {id:'crossing-a',points:[{x:-100,z:0,y:10},{x:100,z:0,y:10}],radius:10,feather:30,height:0},
 {id:'crossing-b',points:[{x:0,z:-100,y:30},{x:0,z:100,y:30}],radius:10,feather:30,height:0},
]});
describe('balanced corridor grading',()=>{
 it('retains legacy overlap behavior when omitted or explicitly false',()=>{
  const terrain=controls();expect(orvrHeightAt(terrain,0,0)).toBe(20);
  terrain.clearCorridors[0].points=Array.from({length:41},(_,i)=>({x:-100+i*5,z:0,y:10}));
  const old=orvrHeightAt(terrain,0,0);expect(old).toBeLessThan(13);
  expect(orvrHeightAt({...terrain,balancedCorridors:false},0,0)).toBe(old);
 });
 it('prevents flat-route subdivision from outweighing a crossing route',()=>{
  const terrain={...controls(),balancedCorridors:true},copy=structuredClone(terrain);
  const points=[[0,0],[7,5],[20,12],[-30,14],[33,-18],[70,0]];
  const before=points.map(([x,z])=>orvrHeightAt(terrain,x,z));
  terrain.clearCorridors[0].points=Array.from({length:81},(_,i)=>({x:-100+i*2.5,z:0,y:10}));
  points.forEach(([x,z],i)=>expect(orvrHeightAt(terrain,x,z)).toBeCloseTo(before[i],12));
  expect(copy.clearCorridors[0].points).toHaveLength(2);expect(before[0]).toBe(20);
 });
 it('remains continuous across the bisector of unequal-slope adjacent segments',()=>{
  const terrain=controls();terrain.balancedCorridors=true;terrain.clearCorridors=[{
   id:'bend',points:[{x:-100,z:0,y:0},{x:0,z:0,y:10},{x:0,z:100,y:40}],radius:15,feather:30,height:0,
  }];
  const a=orvrHeightAt(terrain,-10-.00001,10),b=orvrHeightAt(terrain,-10+.00001,10);
  expect(Math.abs(a-b)).toBeLessThan(.00001);
  // Selecting only the nearest segment jumps between different projected elevations here.
  expect(a).toBeGreaterThan(9);expect(a).toBeLessThan(13);
 });
 it('is compact at corridor edges and does not change ungraded priority controls',()=>{
  const terrain={...controls(),balancedCorridors:true};
  for(const p of [[50,50],[101,101],[-200,0],[0,-200]])expect(orvrHeightAt(terrain,...p as [number,number])).toBe(0);
  expect(Math.abs(orvrHeightAt(terrain,60,40-.0001))).toBeLessThan(1e-8);
  const ungraded={...terrain,gradedRoutes:false};
  for(const [x,z] of [[0,0],[15,6],[39,0]])expect(orvrHeightAt(ungraded,x,z)).toBe(orvrHeightAt({...ungraded,balancedCorridors:false},x,z));
 });
 it('serializes the opt-in and uses native float triangle vertices in a rectangular grid',()=>{
  const terrain={...controls(),balancedCorridors:true};terrain.clearCorridors[0].points[1].y=18;
  const restored=JSON.parse(JSON.stringify(terrain));
  const spatial={bounds:{minX:-30,maxX:30,minZ:-20,maxZ:20},terrainGrid:{segmentsX:3,segmentsZ:2},playableOutline:[{x:-30,z:-20},{x:30,z:-20},{x:30,z:20},{x:-30,z:20}]};
  const h=createOrvrGridHeightSampler(restored,60,3,spatial),v=(x:number,z:number)=>Math.fround(orvrHeightAt(terrain,x,z));
  expect(h(-25,-16)).toBeCloseTo(v(-30,-20)+.25*(v(-10,-20)-v(-30,-20))+.2*(v(-30,0)-v(-30,-20)),7);
  expect(h(-15,-4)).toBeCloseTo(v(-10,0)+.25*(v(-30,0)-v(-10,0))+.2*(v(-10,-20)-v(-10,0)),7);
 });
});
