import type { Game } from '../../game/Game';
import { useGameStore } from '../../state/gameStore';
import { ChatPanel } from './ChatPanel';
import { DebugOverlay } from './DebugOverlay';
import { FloatingDamageLayer } from './FloatingDamageLayer';
import { Hotbar } from './Hotbar';
import { InventoryPanel } from './InventoryPanel';
import { Minimap } from './Minimap';
import { NameplateLayer } from './NameplateLayer';
import { PlayerFrame } from './PlayerFrame';
import { TargetFrame } from './TargetFrame';

interface Props {
  game: Game | null;
}

export function Hud({ game }: Props) {
  const debugOpen    = useGameStore((s) => s.debugOpen);
  const inventoryOpen = useGameStore((s) => s.inventoryOpen);
  const playerDead   = useGameStore((s) => s.playerDead);

  function handleRespawn() {
    useGameStore.getState().setPendingRespawn(true);
  }

  return (
    <div className="hud">
      <PlayerFrame />
      <TargetFrame />
      <Hotbar />
      <ChatPanel />
      <Minimap game={game} />
      {inventoryOpen && <InventoryPanel />}
      {debugOpen && <DebugOverlay game={game} />}
      <NameplateLayer game={game} />
      <FloatingDamageLayer game={game} />

      {playerDead && (
        <div className="death-overlay">
          <div className="death-panel">
            <h2>You have fallen!</h2>
            <p>Your journey is not yet over.</p>
            <button onClick={handleRespawn}>Return to Life</button>
          </div>
        </div>
      )}
    </div>
  );
}
