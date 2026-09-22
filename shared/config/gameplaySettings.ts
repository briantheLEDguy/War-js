import { DEFAULT_VIEW_DISTANCE } from './viewDistance';
import { DEFAULT_KEYBINDINGS } from '../data/keybindings';
export type GuidedTaskId = 'move' | 'camera' | 'interact' | 'kill' | 'gather' | 'equip' | 'guide' | 'craft';
export type GuidedTaskProgress = Record<GuidedTaskId, boolean>;
export const DEFAULT_GAMEPLAY_SETTINGS = {
  invertCameraX: false,
  invertCameraY: false,
  mouseLookSensitivity: 1,
  touchLookSensitivity: 1,
  zoomSensitivity: 1,
  viewDistance: DEFAULT_VIEW_DISTANCE,
  renderResolution: 'auto',
  frameRateLimit: 30,
  keybindings: DEFAULT_KEYBINDINGS,
};
