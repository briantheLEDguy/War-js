import {expect,it} from 'vitest';
import {readFileSync} from 'node:fs';
import type {ZoneDefinition} from '../shared/world/ZoneDefinition';
import type {TerrainSurface} from '../shared/terrainSurface';
import {redesignT1} from '../scripts/unreal/t1-layouts';
import {battlefieldLandscape} from '../scripts/unreal/t1-battlefield-landscape';
import {landformFirst,translateAssemblyElevation} from '../scripts/unreal/t1-landform-first';
import {relocateTerrainAnchors,reconcileTerrainArrivals} from '../scripts/unreal/t1-terrain-anchor-revision';
import {createOrvrGridHeightSampler} from '../shared/orvrTerrain';

function fixture(id='sunmeadow_march') {
 const base=battlefieldLandscape(redesignT1(JSON.parse(readFileSync('public/assets/maps/'+id+'.json','utf8')) as ZoneDefinition));
 const surface:TerrainSurface={bounds:base.spatial!.bounds,segmentsX:base.spatial!.terrainGrid.segmentsX,segmentsZ:base.spatial!.terrainGrid.segmentsZ,edgeFade:20,samples:Array((base.spatial!.terrainGrid.segmentsX+1)*(base.spatial!.terrainGrid.segmentsZ+1)).fill(45)};
 const original=landformFirst(base,surface).zone,terrain=structuredClone(original.orvrLayout!.terrain);
 terrain.naturalField!.surface!.samples=terrain.naturalField!.surface!.samples.map(h=>h+15);
 for(const pad of terrain.flattenAreas){pad.height+=15;if(pad.y!==undefined)pad.y+=15;}
 for(const c of terrain.clearCorridors)for(const p of c.points)p.y=(p.y??c.height)+15;
 return {original,terrain};
}
for(const id of ['sunmeadow_march','cinderfen_outskirts'])it('revises '+id+' anchors and complete keeps once while retaining rules, offsets and originals',()=>{
 const {original,terrain}=fixture(id);original.npcs![0].heightMode='absolute';original.npcs![0].y=48;original.props.push({id:'absolute_probe',kind:'rock',x:0,z:0,y:47,heightMode:'absolute'},{id:'relative_probe',kind:'rock',x:0,z:0,y:2});
 const before=structuredClone(original),controls=structuredClone(terrain),r=relocateTerrainAnchors(original,terrain),zone=r.zone;
 expect(original).toEqual(before);expect(terrain).toEqual(controls);expect(zone.orvrLayout!.keeps).toEqual(original.orvrLayout!.keeps.map(k=>translateAssemblyElevation(k,15)));
 expect(zone.orvrLayout!.stagingCamps.map(c=>c.y)).toEqual([60,60]);expect(zone.orvrLayout!.battlefieldObjectives.every(o=>o.y===60)).toBe(true);
 expect(zone.rvrObjectives!.every(o=>o.y===60)).toBe(true);expect(zone.npcs![0].y).toBe(63);expect(zone.npcs!.slice(1)).toEqual(original.npcs!.slice(1).map(n=>n.heightMode==='absolute'&&n.y!==undefined?{...n,y:n.y+15}:n));
 expect(zone.props.find(p=>p.id==='absolute_probe')!.y).toBe(62);expect(zone.props.find(p=>p.id==='relative_probe')!.y).toBe(2);
 for(const keep of original.orvrLayout!.keeps)for(const p of original.props.filter(p=>p.id===keep.objectiveId||p.id?.startsWith(keep.objectiveId+'_')))expect(zone.props.find(n=>n.id===p.id)!.y).toBeCloseTo(p.y!+15,10);
 expect(zone.zoneTriggers!.map(t=>({id:t.id,target:t.targetZoneId,targetSpawn:t.targetSpawn}))).toEqual(original.zoneTriggers!.map(t=>({id:t.id,target:t.targetZoneId,targetSpawn:t.targetSpawn})));
 const height=createOrvrGridHeightSampler(terrain,zone.size,zone.segments,zone.spatial);
 for(const trigger of zone.zoneTriggers!){expect(trigger.y).toBeCloseTo(height(trigger.x,trigger.z),5);expect(trigger.arrivalPoint!.y).toBeCloseTo(height(trigger.arrivalPoint!.x,trigger.arrivalPoint!.z),5);}
 expect(zone.orvrLayout!.caravanRoutes.map(c=>({...c,points:c.points.map(p=>({...p,y:0}))}))).toEqual(original.orvrLayout!.caravanRoutes.map(c=>({...c,points:c.points.map(p=>({...p,y:0}))})));
 expect(r.maximumBoundaryErrorMetres).toBe(0);expect(r.requiresReciprocalArrivals).toBe(true);expect(r.nativeIntegrated||r.routeGradesAccepted||r.fullAssemblyRelocationAccepted||r.appearanceApproved).toBe(false);
});
it('rejects changed grids, foundations, missing corridors, malformed native frames and unqualified keep props',()=>{
 const {original,terrain}=fixture();const grid=structuredClone(terrain);grid.naturalField!.surface!.bounds.maxX+=1;expect(()=>relocateTerrainAnchors(original,grid)).toThrow('sampling grid');
 const seam=structuredClone(terrain);seam.naturalField!.baseHeight+=1;expect(()=>relocateTerrainAnchors(original,seam)).toThrow('distant-terrain seams');
 const moved=structuredClone(terrain);moved.flattenAreas[0].x+=1;expect(()=>relocateTerrainAnchors(original,moved)).toThrow('foundation identities');
 const missing=structuredClone(terrain);missing.clearCorridors.pop();expect(()=>relocateTerrainAnchors(original,missing)).toThrow('retained ground corridors');
 const bad=structuredClone(terrain);bad.clearCorridors[0].points[0].y=NaN;expect(()=>relocateTerrainAnchors(original,bad)).toThrow('ground corridors');
 const keep=original.orvrLayout!.keeps[0],prop=original.props.find(p=>p.id?.startsWith(keep.objectiveId+'_'))!;prop.heightMode=undefined;
 expect(()=>relocateTerrainAnchors(original,terrain)).toThrow('absolute prop frames');
 const frame={id:prop.id!,x:prop.x,z:prop.z,y:10};expect(relocateTerrainAnchors(original,terrain,[frame]).zone.props.find(p=>p.id===prop.id)!.y).toBe(25);
 expect(()=>relocateTerrainAnchors(original,terrain,[{...frame,x:frame.x+1}])).toThrow('native keep prop frame');
});
it('updates every incoming landing from its unique revised reciprocal while preserving graph and input maps',()=>{
 const {original,terrain}=fixture(),zone=relocateTerrainAnchors(original,terrain).zone,trigger=zone.zoneTriggers![0],origin:ZoneDefinition={...structuredClone(original),id:trigger.targetZoneId,zoneTriggers:[{id:'return',label:'Return',x:0,z:0,radius:5,targetZoneId:zone.id,targetSpawn:{x:1,y:2,z:3}}]};
 const maps=[zone,origin],before=structuredClone(maps),r=reconcileTerrainArrivals(maps,[zone.id]);expect(maps).toEqual(before);expect(r[1].zoneTriggers![0].targetSpawn).toEqual(trigger.arrivalPoint);
 const broken=structuredClone(maps);broken[0].zoneTriggers![0].arrivalPoint!.y-=5;expect(()=>reconcileTerrainArrivals(broken,[zone.id])).toThrow('terrain support');
 const ambiguous=structuredClone(maps);ambiguous[0].zoneTriggers!.push(structuredClone(ambiguous[0].zoneTriggers![0]));expect(()=>reconcileTerrainArrivals(ambiguous,[zone.id])).toThrow('unique connected');
 expect(()=>reconcileTerrainArrivals(maps,['brightfen_approach'])).toThrow('Invalid terrain arrival');
});
