import { describe, expect, it } from 'vitest';
import { countEditableCapital } from '../scripts/unreal/capital-scene-counts';

const actor = (id: string, hash = 'a'.repeat(64)) => ({
  tags: ['WarCapitalBuilding', `WarWorldObject_${id}`, `WarModelSha256_${hash}`],
  components: [{ class: 'StaticMeshComponent', mesh: '/Game/Reviewed/House.House' }],
});

describe('expanded capital acceptance totals', () => {
  it('counts reviewed material variants as distinct catalog templates', () => {
    expect(countEditableCapital([actor('one'), actor('two'), actor('three', 'b'.repeat(64)),
      { tags: ['WarCapitalExpansionV1'], components: [] }])).toEqual({ objects: 3, models: 2 });
  });
  it('rejects duplicates and missing provenance rather than weakening native acceptance', () => {
    expect(() => countEditableCapital([actor('one'), actor('one')])).toThrow();
    expect(() => countEditableCapital([actor('one', '')])).toThrow();
    expect(() => countEditableCapital([{ ...actor('one'), components: [] }])).toThrow();
  });
});
