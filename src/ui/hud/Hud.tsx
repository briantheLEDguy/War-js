import type { Game } from '../../game/Game';
import { useGameStore } from '../../state/gameStore';
import { ChatPanel } from './ChatPanel';
import { CharacterSheetPanel } from './CharacterSheetPanel';
import { CraftingPanel } from './CraftingPanel';
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
import { SettingsPanel } from './SettingsPanel';
import { TargetFrame } from './TargetFrame';
import { TouchControls } from './TouchControls';
import { WikiPanel } from './WikiPanel';
import { WorldEditorModeStrip } from './WorldEditorModeStrip';
import { WorldEditorPanel } from './WorldEditorPanel';

interface Props {
  game: Game | null;
}

export function Hud({ game }: Props) {
  const debugOpen    = useGameStore((s) => s.debugOpen);
  const inventoryOpen = useGameStore((s) => s.inventoryOpen);
  const characterSheetOpen = useGameStore((s) => s.characterSheetOpen);
  const questLogOpen = useGameStore((s) => s.questLogOpen);
  const activeQuestDialogNpcId = useGameStore((s) => s.activeQuestDialogNpcId);
  const playerDead   = useGameStore((s) => s.playerDead);
  const wikiOpen = useGameStore((s) => s.wikiOpen);
  const settingsOpen = useGameStore((s) => s.settingsOpen);
  const toggleWiki = useGameStore((s) => s.toggleWiki);
  const toggleSettings = useGameStore((s) => s.toggleSettings);
  const gmBuildMode = useGameStore((s) => s.gmBuildMode);

  function handleRespawn() {
    useGameStore.getState().setPendingRespawn(true);
  }

  return (
    <div className="hud">
      <PlayerFrame />
      <TargetFrame />
      <button
        className={`guide-toggle-btn${wikiOpen ? ' active' : ''}`}
        type="button"
        onClick={toggleWiki}
        aria-pressed={wikiOpen}
      >
        Guide
      </button>
      <button
        className={`settings-toggle-btn${settingsOpen ? ' active' : ''}`}
        type="button"
        onClick={toggleSettings}
        aria-pressed={settingsOpen}
      >
        Settings
      </button>
      <Hotbar />
      <ChatPanel />
      <Minimap game={game} />
      {inventoryOpen && <InventoryPanel />}
      <CraftingPanel />
      {characterSheetOpen && <CharacterSheetPanel />}
      {questLogOpen && <QuestLogPanel />}
      {activeQuestDialogNpcId && <QuestDialog />}
      {debugOpen && <DebugOverlay game={game} />}
      {wikiOpen && <WikiPanel />}
      <NameplateLayer game={game} />
      <QuestMarkerLayer game={game} />
      <FloatingDamageLayer game={game} />
      <TouchControls game={game} />
      <SettingsPanel />
      {gmBuildMode && <WorldEditorModeStrip />}
      {gmBuildMode && <WorldEditorPanel game={game} />}

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
