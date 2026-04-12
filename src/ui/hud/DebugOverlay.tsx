import type { Game } from '../../game/Game';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';

interface Props {
  game: Game | null;
}

export function DebugOverlay({ game }: Props) {
  const fps = useGameStore((s) => s.fps);
  const fallbacks = useGameStore((s) => s.assetFallbacks);
  const px = game?.playerPos.x ?? 0;
  const py = game?.playerPos.y ?? 0;
  const pz = game?.playerPos.z ?? 0;
  const zone = game?.zoneName ?? '?';

  return (
    <div className="debug">
      {`FPS:        ${fps}
Zone:       ${zone}
Pos:        ${px.toFixed(2)}, ${py.toFixed(2)}, ${pz.toFixed(2)}
Backend:    ${services.backend}
Fallbacks:  ${fallbacks}`}
    </div>
  );
}
