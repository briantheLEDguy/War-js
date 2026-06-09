import type { WorldEditorTool } from './WorldEditorRuntime';

export interface BuildModeCycleEntry {
  tool: WorldEditorTool;
  label: string;
  icon: string;
}

export const BUILD_MODE_TOOL_CYCLE: BuildModeCycleEntry[] = [
  { tool: 'voxel_add', label: 'Add', icon: '+' },
  { tool: 'voxel_subtract', label: 'Subtract', icon: '-' },
  { tool: 'fill_erase', label: 'Erase', icon: 'E' },
  { tool: 'scale', label: 'Scale', icon: 'S' },
];

export function cycleBuildModeTool(current: WorldEditorTool, direction: number): WorldEditorTool {
  const currentIndex = BUILD_MODE_TOOL_CYCLE.findIndex((entry) => entry.tool === current);
  const start = currentIndex >= 0 ? currentIndex : -1;
  const nextIndex = (start + direction + BUILD_MODE_TOOL_CYCLE.length) % BUILD_MODE_TOOL_CYCLE.length;
  return BUILD_MODE_TOOL_CYCLE[nextIndex].tool;
}

export function buildModeToolLabel(tool: WorldEditorTool): string {
  return BUILD_MODE_TOOL_CYCLE.find((entry) => entry.tool === tool)?.label ?? tool.replaceAll('_', ' ');
}
