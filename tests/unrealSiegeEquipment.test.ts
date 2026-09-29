import { describe, expect, it } from 'vitest';
import { validateSiegeEquipment } from '../scripts/unreal/siege-equipment-proof';

const proof = () => ({ passed: true, checkpoints: 3, stoppedWithoutEscort: true, stoppedWithoutCrew: true, ramStrikeAdvanced: true,
  overlapRecoveredWithoutDamage: true,
  vehicles: [{ travelCm: 25000 }, { travelCm: 24300 }] });
describe('native siege equipment evidence', () => {
  it('requires both engines to complete the route and stop when unsupported', () => {
    expect(() => validateSiegeEquipment(proof())).not.toThrow();
    for (const mutation of [{ checkpoints: 2 }, { stoppedWithoutEscort: false }, { stoppedWithoutCrew: false }, { ramStrikeAdvanced: false },
      { overlapRecoveredWithoutDamage: false }, { overlapRecoveredWithoutDamage: undefined },
      { vehicles: [{ travelCm: 25000 }] }, { vehicles: [{ travelCm: 25000 }, { travelCm: 50 }] }]) {
      expect(() => validateSiegeEquipment({ ...proof(), ...mutation })).toThrow();
    }
  });
  it('rejects absent and non-finite evidence', () => {
    expect(() => validateSiegeEquipment(null)).toThrow();
    expect(() => validateSiegeEquipment({ ...proof(), vehicles: [{ travelCm: NaN }, { travelCm: 25000 }] })).toThrow();
  });
});
