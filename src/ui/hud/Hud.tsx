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
  const debugOpen = useGameStore((s) => s.debugOpen);
  const inventoryOpen = useGameStore((s) => s.inventoryOpen);

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
    </div>
  );
}
