import { useGameStore } from '../../state/gameStore';
import { BUILD_MODE_TOOL_CYCLE, buildModeToolLabel } from '../../world/editor/WorldEditorModes';
import type { WorldEditorTool } from '../../world/editor/WorldEditorRuntime';

export function WorldEditorModeStrip() {
  const tool = useGameStore((s) => s.worldEditorTool);
  const activeInCycle = BUILD_MODE_TOOL_CYCLE.some((entry) => entry.tool === tool);

  return (
    <div className="world-editor-mode-strip" aria-live="polite">
      {BUILD_MODE_TOOL_CYCLE.map((entry) => (
        <div
          key={entry.tool}
          className={`world-editor-mode-icon${tool === entry.tool ? ' active' : ''}`}
          title={entry.label}
        >
          <span>{entry.icon}</span>
        </div>
      ))}
      {!activeInCycle && (
        <div className="world-editor-mode-context active">
          <span>{toolIcon(tool)}</span>
          <strong>{buildModeToolLabel(tool)}</strong>
        </div>
      )}
    </div>
  );
}

function toolIcon(tool: WorldEditorTool): string {
  if (tool === 'paint_material') return 'P';
  if (tool === 'stamp_prefab') return 'B';
  if (tool === 'select') return '>';
  if (tool === 'move') return 'M';
  if (tool === 'rotate') return 'R';
  if (tool === 'collider') return 'C';
  if (tool === 'walkable_surface') return 'W';
  if (tool === 'ruler') return '|';
  if (tool === 'voxel_smooth') return '~';
  if (tool === 'voxel_flatten') return '=';
  if (tool === 'voxel_roughen') return '^';
  return '?';
}
