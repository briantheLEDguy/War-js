import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { describe, expect, test } from 'vitest';
// @ts-expect-error Authoring source is native ESM shared with the generator.
import { addAegisPeople, civicPlacementClear } from '../scripts/campaign/aegis-people.mjs';
const zone=JSON.parse(readFileSync('public/assets/maps/aegis_capital.json','utf8'));
const cast=zone.npcs.filter((n: {id:string})=>n.id.startsWith('aegis_people_'));
describe('Aegis civic cast integration',()=>{
  test('places all seven roles in clear, stable city destinations',()=>{
    expect(cast).toHaveLength(15);
    expect(new Set(cast.map((n: any)=>n.characterProfileKey)).size).toBe(7);
    for(const npc of cast){
      expect(civicPlacementClear(zone,npc.x,npc.z),npc.id).toBe(true);
      expect(npc.role).toBe('ambient');
      if(npc.id.includes('hall_')) {expect(npc.z).toBeGreaterThan(214);expect(npc.z).toBeLessThan(237);}
      if(npc.characterProfileKey.endsWith('_child')) expect(cast.some((a:any)=>a.characterProfileKey.endsWith('_female')&&Math.hypot(a.x-npc.x,a.z-npc.z)<5)).toBe(true);
    }
    const copy=structuredClone(zone);addAegisPeople(copy);
    expect(copy.npcs).toEqual(zone.npcs);
    const other={id:'riftspire_capital',npcs:[]};addAegisPeople(other);expect(other.npcs).toEqual([]);
  });
  test('resolves the installed reviewed models and idle-only custom rig',()=>{
    const index=JSON.parse(readFileSync('public/assets/models/asset-index.json','utf8'));
    for(const key of new Set<string>(cast.map((n:any)=>n.characterProfileKey))){
      const entry=index.characterProfiles[key];expect(entry.runtimeReady).toBe(true);expect(entry.skeletonId).toBe('aegis_people_v1');
      const data=readFileSync('public/assets/models/'+entry.model);
      expect(createHash('sha256').update(data).digest('hex')).toBe(entry.modelSha256);
      const gltf=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)).toString());
      expect(gltf.animations.map((a:any)=>a.name)).toEqual(['idle']);expect(gltf.skins).toHaveLength(1);
    }
  });
});
