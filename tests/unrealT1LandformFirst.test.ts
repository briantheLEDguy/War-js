import {expect,it} from 'vitest';
import {readFileSync} from 'node:fs';
import type {ZoneDefinition} from '../shared/world/ZoneDefinition';
import type {TerrainSurface} from '../shared/terrainSurface';
import {redesignT1} from '../scripts/unreal/t1-layouts';
import {battlefieldLandscape} from '../scripts/unreal/t1-battlefield-landscape';
import {landformFirst,translateAssemblyElevation} from '../scripts/unreal/t1-landform-first';
import {reconcilePocketGrounding} from '../scripts/unreal/t1-pocket-grounding';
import type {LandscapePocket} from '../scripts/unreal/t1-landscape-pockets';
import {createOrvrGridHeightSampler} from '../shared/orvrTerrain';

const baseline=(id='sunmeadow_march')=>battlefieldLandscape(redesignT1(JSON.parse(readFileSync('public/assets/maps/'+id+'.json','utf8')) as ZoneDefinition));
const flat=(zone:ZoneDefinition,height=45):TerrainSurface=>({bounds:zone.spatial!.bounds,segmentsX:zone.spatial!.terrainGrid.segmentsX,segmentsZ:zone.spatial!.terrainGrid.segmentsZ,edgeFade:20,samples:Array((zone.spatial!.terrainGrid.segmentsX+1)*(zone.spatial!.terrainGrid.segmentsZ+1)).fill(height)});
it('translates every fitted assembly position exactly once without changing relative offsets or dimensions',()=>{
 const a={x:1,z:2,y:8,height:40,gate:{x:3,z:4,y:9,width:6},slots:[{x:5,z:6,y:12,operatorPosition:{x:7,z:8,y:15}}],local:{height:3,y:2}};
 expect(translateAssemblyElevation(a,20)).toEqual({x:1,z:2,y:28,height:40,gate:{x:3,z:4,y:29,width:6},slots:[{x:5,z:6,y:32,operatorPosition:{x:7,z:8,y:35}}],local:{height:3,y:2}});
 expect(a.gate.y).toBe(9);expect(()=>translateAssemblyElevation(a,NaN)).toThrow('assembly elevation');
});
for(const id of ['sunmeadow_march','cinderfen_outskirts'])it('grades '+id+' foundations as complete retained assemblies and preserves horizontal identities',()=>{
 const original=baseline(id),copy=structuredClone(original),surface=flat(original),r=landformFirst(original,surface),zone=r.zone;
 expect(original).toEqual(copy);expect(zone.paths!.map(p=>p.id)).toEqual(original.paths!.map(p=>p.id));
 expect(zone.orvrLayout!.keeps).toEqual(original.orvrLayout!.keeps.map(k=>translateAssemblyElevation(k,45-k.y!)));
 expect(zone.orvrLayout!.stagingCamps.map(c=>({...c,y:0}))).toEqual(original.orvrLayout!.stagingCamps.map(c=>({...c,y:0})));
 expect(zone.orvrLayout!.battlefieldObjectives.map(c=>({...c,y:0}))).toEqual(original.orvrLayout!.battlefieldObjectives.map(c=>({...c,y:0})));
 expect(zone.orvrLayout!.caravanRoutes.map(r=>({id:r.id,realm:r.realm,destination:r.destinationKeepId}))).toEqual(original.orvrLayout!.caravanRoutes.map(r=>({id:r.id,realm:r.realm,destination:r.destinationKeepId})));
 expect(zone.npcs).toEqual(original.npcs);expect(zone.enemies).toEqual(original.enemies);expect(zone.resourceNodes).toEqual(original.resourceNodes);
 expect(zone.orvrLayout!.terrain.landforms).toEqual([]);expect(Math.max(...r.grades.map(g=>g.maximumGrade))).toBeLessThan(.001);
 const pads=zone.orvrLayout!.terrain.flattenAreas.filter(a=>a.id==='village'||a.id==='arrival_court'||a.id.startsWith(id+'_village_'));
 expect(pads.length).toBeGreaterThan(1);expect(pads.every(p=>p.height===45)).toBe(true);
 expect(zone.zoneTriggers!.map(t=>t.targetZoneId)).toEqual(original.zoneTriggers!.map(t=>t.targetZoneId));
 expect(r.nativeBuilt||r.appearanceApproved||r.drivingAccepted||r.fullAssemblyRelocationAccepted).toBe(false);
 expect(()=>landformFirst(zone,surface)).toThrow('Preserve existing');
});
it('closes a reopened cosmetic basin, preserves its depth and leaves the original source untouched',()=>{
 const original=baseline(),zone=structuredClone(original),terrain=zone.orvrLayout!.terrain;terrain.naturalField!.surface=flat(zone);terrain.landforms=[];
 const id=zone.id+'_pocket_test',point={x:0,z:0},area={id,...point,radius:9,feather:52,height:60,preserveFooting:true};
 terrain.flattenAreas=[area];terrain.clearCorridors=[{id:id+'_approach',radius:6,feather:30,height:0,points:[{x:100,z:0,y:45},{x:0,z:0,y:60}]}];
 const pocket:LandscapePocket={id,label:'Test pool',purpose:'Cosmetic basin',...point,radius:9,bedY:60,waterY:60.45,approach:[{x:100,z:0,y:45},{x:0,z:0,y:60}],cosmeticWater:true,gameplayAccepted:false},copy=structuredClone(zone);
 const r=reconcilePocketGrounding(zone,[pocket]),height=createOrvrGridHeightSampler(r.zone.orvrLayout!.terrain,r.zone.size,r.zone.segments,r.zone.spatial);
 expect(zone).toEqual(copy);expect(r.basins[0].iterations).toBeGreaterThan(0);expect(r.basins[0].minimumRimAboveWater).toBeGreaterThanOrEqual(.1);
 expect(r.pockets[0].waterY-r.pockets[0].bedY).toBeCloseTo(.45,12);expect(r.pockets[0].bedY).toBeCloseTo(height(0,0),12);
 expect(r.pockets[0].approach).toEqual(r.zone.orvrLayout!.terrain.clearCorridors[0].points);
 expect(pocket.bedY).toBe(60);expect(r.nativeVerified||r.appearanceApproved).toBe(false);
 expect(()=>reconcilePocketGrounding(zone,[{...pocket,radius:50}])).toThrow('Invalid retained');
 expect(()=>reconcilePocketGrounding(zone,[{...pocket,waterY:64}])).toThrow('Invalid retained');
 expect(()=>reconcilePocketGrounding(zone,[{...pocket,id:'missing'}])).toThrow('Invalid retained');
});
it('rejects unadmitted regions and malformed retained approaches before authoring',()=>{
 expect(()=>landformFirst({id:'brightfen_approach'} as ZoneDefinition,{} as TerrainSurface)).toThrow('first-pair');
 const original=baseline();expect(()=>landformFirst(original,flat(original),{support:[{id:'bad',width:1,points:[{x:0,z:0},{x:10,z:0}]}]})).toThrow('population approach');
});

it('keeps source collision props rigid with the keep instead of independently following changed terrain',()=>{
 const original=baseline(),before=createOrvrGridHeightSampler(original.orvrLayout!.terrain,original.size,original.segments,original.spatial);
 const keep=original.orvrLayout!.keeps[0];original.props!.push({id:keep.objectiveId+'_offset_probe',kind:'building',x:keep.x+70,z:keep.z,y:2});
 const r=landformFirst(original,flat(original)),moved=r.zone.orvrLayout!.keeps.find(k=>k.objectiveId===keep.objectiveId)!;
 const props=r.zone.props!.filter(p=>p.id===keep.objectiveId||p.id?.startsWith(keep.objectiveId+'_'));
 expect(props.length).toBeGreaterThan(20);
 for(const p of props){const old=original.props!.find(o=>o.id===p.id)!,gate=keep.gates.find(g=>g.propId===p.id),postern=keep.postern&&[keep.postern.propId,keep.postern.propId.replace(/_outside$/,'_inside')].includes(p.id??'')?keep.postern:undefined;expect(p.heightMode).toBe('absolute');expect(p.y).toBeCloseTo((postern?postern.outside.y+(old.y??0):gate?(gate.y??keep.y??0)+(old.y??0):(old.heightMode==='absolute'?0:before(old.x,old.z))+(old.y??0))+moved.y!-keep.y!,10);}
 expect(original.props!.at(-1)!.heightMode).toBeUndefined();
});

it('uses a qualified native prop frame while keeping its horizontal position and complete keep translation',()=>{
 const original=baseline(),keep=original.orvrLayout!.keeps[0],prop=original.props!.find(p=>p.id?.startsWith(keep.objectiveId+'_'))!;
 const frame={id:prop.id!,x:prop.x,z:prop.z,y:12.345},r=landformFirst(original,flat(original),{keepFrames:[frame]});
 expect(r.zone.props!.find(p=>p.id===prop.id)!.y).toBeCloseTo(frame.y+45-keep.y!,10);
 expect(()=>landformFirst(original,flat(original),{keepFrames:[{...frame,x:frame.x+1}]})).toThrow('native keep prop frame');
});
