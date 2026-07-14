import { type ReactNode, type SVGProps } from 'react';
import { canUseGmTools } from '../../editor/gmAuth';
import type { Game } from '../../game/Game';
import { useGameStore } from '../../state/gameStore';
import { ChatPanel } from './ChatPanel';
import { CampaignMapPanel } from './CampaignMapPanel';
import { CharacterSheetPanel } from './CharacterSheetPanel';
import { CraftingPanel } from './CraftingPanel';
import { DebugOverlay } from './DebugOverlay';
import { FloatingDamageLayer } from './FloatingDamageLayer';
import { GmPanel } from './GmPanel';
import { GuidedTasksPanel } from './GuidedTasksPanel';
import { Hotbar } from './Hotbar';
import { InteractionFeedback } from './InteractionFeedback';
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
import { useDraggableWindow } from './useDraggableWindow';

interface Props {
  game: Game | null;
  onLogout: () => void;
}

export function Hud({ game, onLogout }: Props) {
  const debugOpen    = useGameStore((s) => s.debugOpen);
  const inventoryOpen = useGameStore((s) => s.inventoryOpen);
  const characterSheetOpen = useGameStore((s) => s.characterSheetOpen);
  const questLogOpen = useGameStore((s) => s.questLogOpen);
  const activeQuestDialogNpcId = useGameStore((s) => s.activeQuestDialogNpcId);
  const playerDead   = useGameStore((s) => s.playerDead);
  const wikiOpen = useGameStore((s) => s.wikiOpen);
  const worldMapOpen = useGameStore((s) => s.worldMapOpen);
  const worldMapLevel = useGameStore((s) => s.worldMapLevel);
  const settingsOpen = useGameStore((s) => s.settingsOpen);
  const gmMenuOpen = useGameStore((s) => s.gmMenuOpen);
  const user = useGameStore((s) => s.user);
  const toggleWiki = useGameStore((s) => s.toggleWiki);
  const toggleWorldMap = useGameStore((s) => s.toggleWorldMap);
  const openCampaignMap = useGameStore((s) => s.openCampaignMap);
  const toggleSettings = useGameStore((s) => s.toggleSettings);
  const toggleGmMenu = useGameStore((s) => s.toggleGmMenu);
  const gmBuildMode = useGameStore((s) => s.gmBuildMode);
  const gmToolsAvailable = canUseGmTools(user);

  function handleRespawn() {
    useGameStore.getState().setPendingRespawn(true);
  }

  return (
    <div className="hud">
      <PlayerFrame />
      <TargetFrame />
      <GuidedTasksPanel />
      <CampaignMapPanel game={game} />
      <div className="hud-control-bar" role="toolbar" aria-label="Game actions">
        <HudActionButton label="Exit to Login" onClick={onLogout}>
          <ExitIcon />
        </HudActionButton>
        <HudActionButton label="Settings" active={settingsOpen} onClick={toggleSettings}>
          <SettingsIcon />
        </HudActionButton>
        <HudActionButton label="Guide" active={wikiOpen} onClick={toggleWiki}>
          <GuideIcon />
        </HudActionButton>
        <HudActionButton label="Map" active={worldMapOpen} onClick={toggleWorldMap}>
          <MapIcon />
        </HudActionButton>
        <HudActionButton label="Campaign" active={worldMapOpen && worldMapLevel === 'campaign'} onClick={openCampaignMap}>
          <CampaignIcon />
        </HudActionButton>
        {gmToolsAvailable && (
          <HudActionButton label="GM Tools" active={gmMenuOpen} onClick={toggleGmMenu}>
            <GmIcon />
          </HudActionButton>
        )}
      </div>
      <Hotbar />
      <InteractionFeedback />
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
      <GmPanel game={game} />
      {gmBuildMode && <WorldEditorModeStrip />}
      {gmBuildMode && <WorldEditorPanel game={game} />}

      {playerDead && (
        <div className="death-overlay">
          <DeathPanel onRespawn={handleRespawn} />
        </div>
      )}
    </div>
  );
}

function DeathPanel({ onRespawn }: { onRespawn: () => void }) {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLDivElement>({ draggedPosition: 'fixed' });

  return (
    <div
      ref={panelRef}
      className={`death-panel draggable-window-handle${dragClassName}`}
      style={dragStyle}
      {...dragHandleProps}
    >
      <h2>You have fallen!</h2>
      <p>Your journey is not yet over.</p>
      <button onClick={onRespawn}>Return to Life</button>
    </div>
  );
}

interface HudActionButtonProps {
  label: string;
  active?: boolean;
  onClick: () => void;
  children: ReactNode;
}

function HudActionButton({ label, active, onClick, children }: HudActionButtonProps) {
  return (
    <button
      type="button"
      className={`hud-icon-btn${active ? ' active' : ''}`}
      onClick={onClick}
      aria-label={label}
      aria-pressed={active}
      data-tooltip={label}
      title={label}
    >
      {children}
    </button>
  );
}

type HudIconProps = SVGProps<SVGSVGElement>;

function ExitIcon(props: HudIconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" {...props}>
      <path d="M10 7V5a2 2 0 0 1 2-2h7v18h-7a2 2 0 0 1-2-2v-2" />
      <path d="M15 12H3" />
      <path d="m7 8-4 4 4 4" />
    </svg>
  );
}

function SettingsIcon(props: HudIconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" {...props}>
      <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" />
      <path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.04.04a2.15 2.15 0 0 1-3.04 3.04l-.04-.04a1.8 1.8 0 0 0-1.98-.36 1.8 1.8 0 0 0-1.1 1.65V21a2.15 2.15 0 0 1-4.3 0v-.06a1.8 1.8 0 0 0-1.1-1.65 1.8 1.8 0 0 0-1.98.36l-.04.04a2.15 2.15 0 0 1-3.04-3.04l.04-.04A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-1.65-1.1H3a2.15 2.15 0 0 1 0-4.3h.06A1.8 1.8 0 0 0 4.71 8.5a1.8 1.8 0 0 0-.36-1.98l-.04-.04a2.15 2.15 0 0 1 3.04-3.04l.04.04a1.8 1.8 0 0 0 1.98.36A1.8 1.8 0 0 0 10.46 2h.08a2.15 2.15 0 0 1 4.3 0v.06a1.8 1.8 0 0 0 1.1 1.65 1.8 1.8 0 0 0 1.98-.36l.04-.04a2.15 2.15 0 0 1 3.04 3.04l-.04.04a1.8 1.8 0 0 0-.36 1.98 1.8 1.8 0 0 0 1.65 1.1H21a2.15 2.15 0 0 1 0 4.3h-.06A1.8 1.8 0 0 0 19.4 15Z" />
    </svg>
  );
}

function GuideIcon(props: HudIconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" {...props}>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15Z" />
      <path d="M8 7h8" />
      <path d="M8 11h6" />
    </svg>
  );
}

function MapIcon(props: HudIconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" {...props}>
      <path d="m9 18-6 3V6l6-3 6 3 6-3v15l-6 3-6-3Z" />
      <path d="M9 3v15" />
      <path d="M15 6v15" />
    </svg>
  );
}

function CampaignIcon(props: HudIconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" {...props}>
      <path d="M12 3 4 6v6c0 4.6 3.2 7.8 8 9 4.8-1.2 8-4.4 8-9V6l-8-3Z" />
      <path d="M12 8v8" />
      <path d="M8.5 11.5h7" />
    </svg>
  );
}

function GmIcon(props: HudIconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" {...props}>
      <path d="m5 19 10-10" />
      <path d="m14 4 6 6" />
      <path d="m13 5 6 6" />
      <path d="M5 5v4" />
      <path d="M3 7h4" />
      <path d="M19 15v4" />
      <path d="M17 17h4" />
    </svg>
  );
}
