import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { widenVehicleGatePassages } from '../scripts/unreal/t1-vehicle-passages';
import { mapPropNavigation } from '../server/mapNavigation';

for (const id of ['sunmeadow_march', 'cinderfen_outskirts']) it(id+' aligns vehicle gate openings, source collision and retained assemblies', () => {
  const zone = redesignT1(JSON.parse(readFileSync('public/assets/maps/'+id+'.json', 'utf8')) as ZoneDefinition);
  const before = structuredClone(zone);
  widenVehicleGatePassages(zone);
  for (const keep of zone.orvrLayout!.keeps) {
    expect(zone.paths!.find(p => p.id === keep.objectiveId+'_approach')!.width).toBe(8);
    for (const gate of keep.gates) {
      expect(gate.width).toBe(7.5);
      const oldGate = before.orvrLayout!.keeps.flatMap(k => k.gates).find(g => g.id === gate.id)!;
      expect({...gate, width:oldGate.width}).toEqual(oldGate);
      for (const propId of [gate.propId, keep.objectiveId+'_'+gate.stage+'_gatehouse']) {
        const prop = zone.props!.find(p => p.id === propId)!, old = before.props!.find(p => p.id === propId)!;
        expect({...prop, scaleX:undefined}).toEqual({...old, scaleX:undefined});
        expect(prop.scaleX).toBe(1.25);
        const boxes = mapPropNavigation([prop], () => 12).collision;
        const oldBoxes = mapPropNavigation([old], () => 12).collision;
        boxes.forEach((box,i) => {
          expect(box.footprint!.width).toBeCloseTo(oldBoxes[i].footprint!.width*1.25);
          expect(box.footprint!.depth).toBe(oldBoxes[i].footprint!.depth);
          expect(box.minY).toBe(oldBoxes[i].minY); expect(box.maxY).toBe(oldBoxes[i].maxY);
        });
        if (propId === gate.propId) expect(boxes[0].footprint!.width).toBe(7.5);
      }
    }
  }
  expect(zone.zoneTriggers).toEqual(before.zoneTriggers);
  expect(zone.resourceNodes).toEqual(before.resourceNodes);
});

it('rejects later batches and modified gate assemblies', () => {
  const source = redesignT1(JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json','utf8')) as ZoneDefinition);
  const later = structuredClone(source); later.id='brightfen_approach';
  expect(() => widenVehicleGatePassages(later)).toThrow('first terrain batch');
  const leaves = source.props!.find(p => p.id === source.orvrLayout!.keeps[0].gates[0].propId)!;
  leaves.scaleZ=2;
  expect(() => widenVehicleGatePassages(source)).toThrow('unmodified model-space');
});
