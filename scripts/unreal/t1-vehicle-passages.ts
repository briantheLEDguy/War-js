import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';

/** Retain the original six-metre minimum while admitting the 3.2m-radius convoy profile. */
export function widenVehicleGatePassages(zone: ZoneDefinition): void {
  if (!['sunmeadow_march', 'cinderfen_outskirts'].includes(zone.id) || !zone.orvrLayout || !zone.props || !zone.paths) throw new Error('Vehicle passages require the first terrain batch');
  const props = new Map(zone.props.map(p => [p.id, p]));
  for (const keep of zone.orvrLayout.keeps) {
    const approach = zone.paths.find(p => p.id === keep.objectiveId + '_approach');
    if (!approach || approach.width !== 6 || keep.gates.length !== 2) throw new Error('Unexpected retained keep passage');
    for (const gate of keep.gates) {
      const leaves = props.get(gate.propId), house = props.get(keep.objectiveId + '_' + gate.stage + '_gatehouse');
      if (!leaves || !house || gate.width !== 6 || leaves.colliderSpace !== 'model' || house.colliderSpace !== 'model'
          || !house.kind.endsWith('_gatehouse') || !leaves.kind.endsWith('_gate_leaves')
          || [house, leaves].some(p => p.scaleX !== undefined || p.scaleY !== undefined || p.scaleZ !== undefined || p.scale !== 1)) {
        throw new Error('Gate adaptation requires unmodified model-space house and leaf assemblies');
      }
      // Intrinsic colliders and animation pivots stay in their original model frame.
      // Shared authority and native authoring apply the same lateral scale.
      house.scaleX = 1.25; leaves.scaleX = 1.25; gate.width = 7.5;
    }
    approach.width = 8;
  }
}
