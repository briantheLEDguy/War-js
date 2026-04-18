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
import { QuestDialog } from './QuestDialog';
import { QuestLogPanel } from './QuestLogPanel';
import { QuestMarkerLayer } from './QuestMarkerLayer';
import { TargetFrame } from './TargetFrame';
import { TouchControls } from './TouchControls';

interface Props {
  game: Game | null;
}

export function Hud({ game }: Props) {
  const debugOpen    = useGameStore((s) => s.debugOpen);
  const inventoryOpen = useGameStore((s) => s.inventoryOpen);
  const questLogOpen = useGameStore((s) => s.questLogOpen);
  const activeQuestDialogNpcId = useGameStore((s) => s.activeQuestDialogNpcId);
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
      {questLogOpen && <QuestLogPanel />}
      {activeQuestDialogNpcId && <QuestDialog />}
      {debugOpen && <DebugOverlay game={game} />}
      <NameplateLayer game={game} />
      <QuestMarkerLayer game={game} />
      <FloatingDamageLayer game={game} />
      <TouchControls game={game} />

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
