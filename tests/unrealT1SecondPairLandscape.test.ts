import {readFileSync} from 'node:fs';
import {expect,it} from 'vitest';
import type {ZoneDefinition} from '../shared/world/ZoneDefinition';
import {redesignT1} from '../scripts/unreal/t1-layouts';
import {secondPairField,secondPairLandscape} from '../scripts/unreal/t1-second-pair-landscape';
import {createOrvrGridHeightSampler} from '../shared/orvrTerrain';
import {terrainFieldHeight,validateTerrainField} from '../shared/terrainField';
import {battlefieldGrades} from '../scripts/unreal/t1-battlefield-grades';

for(const id of ['brightfen_approach','ashen_steppe'])it(id+' has distinct source geology and retains full-width gentle routes and gameplay identities',()=>{
 const source=redesignT1(JSON.parse(readFileSync('public/assets/maps/'+id+'.json','utf8')) as ZoneDefinition),before=JSON.stringify(source);
 const zone=secondPairLandscape(source),h=createOrvrGridHeightSampler(zone.orvrLayout!.terrain,zone.size,zone.segments,zone.spatial);
 expect(JSON.stringify(source)).toBe(before);expect(zone.orvrLayout!.keeps).toEqual(source.orvrLayout!.keeps);
 expect(zone.orvrLayout!.caravanRoutes).toEqual(source.orvrLayout!.caravanRoutes);expect(zone.rvrObjectives).toEqual(source.rvrObjectives);
 expect(zone.npcs).toEqual(source.npcs);expect(zone.enemies).toEqual(source.enemies);expect(zone.resourceNodes).toEqual(source.resourceNodes);
 expect(Math.max(...battlefieldGrades(zone.paths!,h).map(r=>r.maximumGrade))).toBeLessThan(.22);
 for(const t of zone.zoneTriggers!)expect(t.arrivalPoint!.y).toBe(h(t.arrivalPoint!.x,t.arrivalPoint!.z));
});
it('island channels and layered plateaus have different sections rather than recolored hills',()=>{
 const fen=secondPairField('brightfen_approach'),ash=secondPairField('ashen_steppe');validateTerrainField(fen);validateTerrainField(ash);
 expect(terrainFieldHeight(fen,-425,-180)).toBeLessThan(terrainFieldHeight(fen,-650,-155));
 expect(terrainFieldHeight(ash,225,425)).toBeGreaterThan(100);
 expect(terrainFieldHeight(ash,105,80)).toBeLessThan(35);
 expect(()=>secondPairField('sunmeadow_march')).toThrow();
});
