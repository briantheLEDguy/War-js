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
  const fallbacks = useGameStore((s) => s.assetFallbacks);
  const gmBuildMode = useGameStore((s) => s.gmBuildMode);
  const px = game?.playerPos.x ?? 0;
  const py = game?.playerPos.y ?? 0;
  const pz = game?.playerPos.z ?? 0;
  const zone = game?.zoneName ?? '?';

  return (
    <div
      ref={panelRef}
      className={`debug draggable-window-handle${dragClassName}`}
      style={dragStyle}
      {...dragHandleProps}
    >
      {`FPS:        ${fps}
Zone:       ${zone}
Pos:        ${px.toFixed(2)}, ${py.toFixed(2)}, ${pz.toFixed(2)}
Backend:    ${services.backend}
GM Build:   ${gmBuildMode ? 'on' : 'off'}
Fallbacks:  ${fallbacks}`}
    </div>
  );
}
