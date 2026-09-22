import type { EquipmentState, Position } from './protocol';

/** Literal approved ram crew origins in the engine's +Y-up, +Z-forward frame. */
export const RAM_OPERATOR_SEATS = [
  { offset: { x: -.71, y: .91, z: .185 }, facing: Math.PI / 2, key: 'left' },
  { offset: { x: .71, y: .91, z: .185 }, facing: -Math.PI / 2, key: 'right' },
] as const;

export function equipmentFacing(equipment: Pick<EquipmentState, 'position' | 'facing' | 'lastOperation'>): number {
  if (Number.isFinite(equipment.facing)) return equipment.facing!;
  const target = equipment.lastOperation?.target;
  return target ? Math.atan2(target.x - equipment.position.x, target.z - equipment.position.z) : 0;
}

export function equipmentLocalPosition(equipment: Pick<EquipmentState, 'position' | 'facing' | 'lastOperation'>, offset: Position): Position {
  const yaw = equipmentFacing(equipment), c = Math.cos(yaw), s = Math.sin(yaw);
  return { x: equipment.position.x + offset.x * c + offset.z * s, y: equipment.position.y + offset.y,
    z: equipment.position.z - offset.x * s + offset.z * c };
}

/** Preserve valid physical seats while repairing partial legacy records and dropping stale occupants. */
export function equipmentOperatorSeats(equipment: Pick<EquipmentState, 'kind' | 'operators' | 'operatorSeats'>): Partial<Record<string, 0 | 1>> {
  const seats: Partial<Record<string, 0 | 1>> = {};
  if (equipment.kind !== 'ram') return seats;
  const operators = [...new Set(equipment.operators)].slice(0, 2), occupied = new Set<number>();
  for (const id of operators) {
    const seat = equipment.operatorSeats?.[id];
    if ((seat === 0 || seat === 1) && !occupied.has(seat)) { seats[id] = seat; occupied.add(seat); }
  }
  for (const id of operators) if (seats[id] === undefined) {
    const seat = occupied.has(0) ? 1 : 0;
    seats[id] = seat; occupied.add(seat);
  }
  return seats;
}

export function equipmentOperatorSeat(equipment: Pick<EquipmentState, 'kind' | 'operators' | 'operatorSeats'>, playerId: string): 0 | 1 | undefined {
  return equipmentOperatorSeats(equipment)[playerId];
}

/** Engine damage originates at its visual position; occupants remain at its authored controls. */
export function equipmentOperatorPosition(equipment: Pick<EquipmentState, 'position' | 'operatorPosition'>
  & Partial<Pick<EquipmentState, 'kind' | 'operators' | 'operatorSeats' | 'facing' | 'lastOperation'>>, playerId?: string): Position {
  const index = playerId && equipment.operators ? equipment.operators.indexOf(playerId) : -1;
  if (equipment.kind === 'ram' && (index === 0 || index === 1)) {
    const seat = equipmentOperatorSeat({ ...equipment, kind: 'ram', operators: equipment.operators! }, playerId!)!;
    return equipmentLocalPosition(equipment, RAM_OPERATOR_SEATS[seat].offset);
  }
  return equipment.operatorPosition ?? equipment.position;
}
