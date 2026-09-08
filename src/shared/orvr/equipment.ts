import type { EquipmentState, Position } from './protocol';

/** Engine damage originates at its visual position; occupants remain at its authored controls. */
export function equipmentOperatorPosition(equipment: Pick<EquipmentState, 'position' | 'operatorPosition'>): Position {
  return equipment.operatorPosition ?? equipment.position;
}
