import {expect,it} from 'vitest';
import {readFileSync} from 'node:fs';
import type {ZoneDefinition} from '../shared/world/ZoneDefinition';
import {redesignT1} from '../scripts/unreal/t1-layouts';
import {battlefieldLandscape} from '../scripts/unreal/t1-battlefield-landscape';
import {landscapePockets} from '../scripts/unreal/t1-landscape-pockets';
import {localTerrainTransitions} from '../scripts/unreal/t1-local-terrain-transitions';
import {tacticalSpurs} from '../scripts/unreal/t1-tactical-spurs';
import {sunmeadowRouteReflow} from '../scripts/unreal/t1-sunmeadow-route-reflow';
import {createOrvrGridHeightSampler} from '../shared/orvrTerrain';

it('reflows public synthetic Sunmeadow controls with full-width grades and complete retained assemblies',()=>{
 const base=JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json','utf8')) as ZoneDefinition;
 const original=tacticalSpurs(localTerrainTransitions(landscapePockets(battlefieldLandscape(redesignT1(base))).zone).zone).zone,copy=structuredClone(original);
 const result=sunmeadowRouteReflow(original),zone=result.zone,layout=zone.orvrLayout!;
 expect(original).toEqual(copy);expect(layout.terrain.balancedCorridors).toBe(true);
 expect(layout.keeps).toEqual(original.orvrLayout!.keeps);expect(layout.stagingCamps).toEqual(original.orvrLayout!.stagingCamps);
 expect(zone.spawnPoint).toEqual(original.spawnPoint);expect(zone.zoneTriggers).toEqual(original.zoneTriggers);
 expect(zone.paths![0]).toEqual(original.paths![0]);expect(zone.paths!.map(p=>p.id)).toEqual(original.paths!.map(p=>p.id));
 expect(zone.paths!.map(p=>p.width)).toEqual(original.paths!.map(p=>p.width));
 expect(zone.paths![2].points.some(p=>p.x===310&&p.z===-300)).toBe(true);
 expect(Math.max(...result.grades.map(g=>g.maximumGrade))).toBeLessThan(.22);
 expect(layout.caravanRoutes).toHaveLength(6);
 for(const route of layout.caravanRoutes){expect(route.lengthMetres).toBeGreaterThanOrEqual(350);expect(route.lengthMetres).toBeLessThanOrEqual(750);expect(route.width).toBe(12);}
 const h=createOrvrGridHeightSampler(layout.terrain,zone.size,zone.segments,zone.spatial);
 for(const objective of layout.battlefieldObjectives){const old=original.orvrLayout!.battlefieldObjectives.find(p=>p.objectiveId===objective.objectiveId)!;expect({...objective,y:old.y}).toEqual(old);expect(objective.y).toBe(h(objective.x,objective.z));}
 const before=createOrvrGridHeightSampler(original.orvrLayout!.terrain,original.size,original.segments,original.spatial);
 for(const prop of zone.props??[])if(prop.heightMode==='absolute'){const old=original.props!.find(p=>p.id===prop.id)!;expect(prop.y).toBeCloseTo((old.y??0)+h(prop.x,prop.z)-before(prop.x,prop.z),8);}
 expect(result.nativeBuilt).toBe(false);expect(result.drivingAccepted).toBe(false);expect(result.appearanceApproved).toBe(false);
 expect(()=>sunmeadowRouteReflow(zone)).toThrow('Preserve existing balanced');
});
it('refuses other regions and incomplete source controls',()=>{
 for(const zone of [{id:'cinderfen_outskirts'},{id:'sunmeadow_march',paths:[]}])expect(()=>sunmeadowRouteReflow(zone as ZoneDefinition)).toThrow('explicit Sunmeadow');
});
