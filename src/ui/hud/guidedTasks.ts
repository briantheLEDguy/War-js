import type { GuidedTaskId, GuidedTaskProgress } from '../../state/gameStore';

export interface GuidedTaskDefinition {
  id: GuidedTaskId;
  label: string;
  detail: string;
}

export const GUIDED_TASKS: GuidedTaskDefinition[] = [
  { id: 'move', label: 'Move', detail: 'Use WASD or touch movement.' },
  { id: 'camera', label: 'Look Around', detail: 'Drag or hold right mouse to adjust the camera.' },
  { id: 'interact', label: 'Interact', detail: 'Press E near quest givers, stations, or doors.' },
  { id: 'kill', label: 'Win a Fight', detail: 'Target an enemy and use your hotbar.' },
  { id: 'gather', label: 'Gather', detail: 'Harvest a valid defeated enemy corpse.' },
  { id: 'equip', label: 'Equip Gear', detail: 'Open inventory and equip a weapon or armor item.' },
  { id: 'guide', label: 'Open Guide', detail: 'Use H or the Guide button for game systems.' },
  { id: 'craft', label: 'Craft', detail: 'Use a crafting station to make or harvest an item.' },
];

export function guidedTaskCompletion(progress: GuidedTaskProgress): {
  completed: number;
  total: number;
  percent: number;
} {
  const total = GUIDED_TASKS.length;
  const completed = GUIDED_TASKS.filter((task) => progress[task.id]).length;
  return {
    completed,
    total,
    percent: total === 0 ? 100 : Math.round((completed / total) * 100),
  };
}
