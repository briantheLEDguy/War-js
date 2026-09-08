import type { Game } from '../../game/Game';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';
import { useDraggableWindow } from './useDraggableWindow';

interface Props {
  game: Game | null;
}

export function DebugOverlay({ game }: Props) {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLDivElement>();
  const fps = useGameStore((s) => s.fps);
  const frameLimit = useGameStore((s) => s.settings.frameRateLimit);
  const fallbacks = useGameStore((s) => s.assetFallbacks);
  const gmBuildMode = useGameStore((s) => s.gmBuildMode);
  const px = game?.playerPos.x ?? 0;
  const py = game?.playerPos.y ?? 0;
  const pz = game?.playerPos.z ?? 0;
  const zone = game?.zoneName ?? '?';
  const sample = game?.performanceSample;

  return (
    <div
      ref={panelRef}
      className={`debug draggable-window-handle${dragClassName}`}
      style={dragStyle}
      {...dragHandleProps}
    >
      {`FPS:        ${fps}
Limit:      ${frameLimit} FPS
Frame:      ${(game?.frameMs ?? 0).toFixed(1)} ms
3D scale:   ${Math.round((game?.renderScale ?? 1) * 100)}%
Zone:       ${zone}
Pos:        ${px.toFixed(2)}, ${py.toFixed(2)}, ${pz.toFixed(2)}
Backend:    ${services.backend}
GM Build:   ${gmBuildMode ? 'on' : 'off'}
Fallbacks:  ${fallbacks}${sample ? `
Simulation: ${sample.simulationMs.toFixed(1)} ms
Camera:     ${sample.cameraMs.toFixed(1)} ms
CPU submit: ${sample.submissionMs.toFixed(1)} ms (not GPU)
Main draws: ${sample.calls}
Triangles:  ${sample.triangles.toLocaleString()}
Programs:   ${sample.programs}` : ''}`}
    </div>
  );
}
