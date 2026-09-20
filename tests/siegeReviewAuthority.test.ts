import { describe, expect, it } from 'vitest';
import { createSiegeReviewAuthority } from '../authoring/blender/orvr-frontier/siege-review-authority';
import { equipmentOperatorPosition, equipmentOperatorSeat } from '../src/shared/orvr';

describe('siege browser review authority fixture', () => {
  it.each(['ram', 'catapult', 'oil'] as const)('boards the %s outside solid gates and accepts its operation', kind => {
    const fixture = createSiegeReviewAuthority(kind);
    expect(fixture.machine.operators).toEqual(kind === 'ram' ? ['driver', 'crew'] : ['driver']);
    expect(fixture.operate().ok).toBe(true);
    expect(fixture.machine.lastOperation?.at).toBe(10);
    expect(fixture.operate().code).toBe('equipment_cooldown');
  });

  it('drives, turns and leaves the other crew member on the same side when the driver dismounts', () => {
    const f = createSiegeReviewAuthority('ram'), start = { ...f.machine.position };
    f.advance(.4, { x: 1, z: 0 });
    expect(f.machine.position.x - start.x).toBeCloseTo(1);
    expect(f.machine.facing).toBeCloseTo(Math.PI / 2);
    for (const id of f.machine.operators) expect(f.state.players[id].position).toEqual(equipmentOperatorPosition(f.machine, id));
    expect(f.command('driver', { type: 'leaveEquipment' }).ok).toBe(true);
    expect(equipmentOperatorSeat(f.machine, 'crew')).toBe(1);
    f.advance(.2, { x: 0, z: -1 });
    expect(f.machine.facing).toBeCloseTo(Math.PI);
    expect(f.command('driver', { type: 'board', equipmentId: f.machine.id }).ok).toBe(true);
    expect(equipmentOperatorSeat(f.machine, 'driver')).toBe(0);
    expect(f.operate().ok).toBe(true);
  });
});
