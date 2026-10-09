import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { battlefieldLandscape, offRoadLinks } from '../scripts/unreal/t1-battlefield-landscape';
import { landscapePockets } from '../scripts/unreal/t1-landscape-pockets';
import { createOrvrGridHeightSampler } from '../shared/orvrTerrain';
import { battlefieldGrades } from '../scripts/unreal/t1-battlefield-grades';

for (const id of ['sunmeadow_march','cinderfen_outskirts']) it(id+' reserves shallow walkable pockets without moving gameplay anchors',()=>{
  const source=battlefieldLandscape(redesignT1(JSON.parse(readFileSync('public/assets/maps/'+id+'.json','utf8')) as ZoneDefinition)),before=JSON.stringify(source);
  const {zone,pockets}=landscapePockets(source);
  expect(JSON.stringify(source)).toBe(before);expect(pockets).toHaveLength(id==='sunmeadow_march'?2:4);
  expect(zone.orvrLayout!.keeps).toEqual(source.orvrLayout!.keeps);expect(zone.resourceNodes).toEqual(source.resourceNodes);expect(zone.zoneTriggers).toEqual(source.zoneTriggers);
  const h=createOrvrGridHeightSampler(zone.orvrLayout!.terrain,zone.size,zone.segments,zone.spatial);
  for(const p of pockets){
    expect(p.waterY-p.bedY).toBeCloseTo(.45);expect(h(p.x,p.z)).toBeCloseTo(p.bedY,4);
    expect(p.gameplayAccepted).toBe(false);
    if(p.cosmeticWater) for(let i=0;i<64;i++) expect(h(p.x+Math.cos(i*Math.PI/32)*(p.radius+60),p.z+Math.sin(i*Math.PI/32)*(p.radius+60))).toBeGreaterThanOrEqual(p.waterY+.08);
    expect(battlefieldGrades([{id:p.id,width:6,points:p.approach}],h)[0].maximumGrade).toBeLessThan(.22);
  }
  expect(Math.max(...battlefieldGrades([...zone.paths!,...offRoadLinks(id)],h).map(p=>p.maximumGrade))).toBeLessThan(.22);
});
