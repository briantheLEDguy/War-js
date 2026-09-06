import { useEffect, useMemo, useState } from 'react';
import type { Game } from '../../game/Game';
import { campaignZoneName } from '../../data/campaign';
import { useGameStore } from '../../state/gameStore';
import {
  formatDistance,
  resolveTrackedQuests,
} from './objectiveHudData';
import { useZoneExitMarkers } from './mapData';
import { resolveQuestNavigation } from './questNavigation';
import { CampaignActivityCard, CampaignRewardCard } from './CampaignActivityCard';
import { useDraggableWindow } from './useDraggableWindow';

interface Props {
  game: Game | null;
}

interface PlayerSnapshot {
  x: number;
  z: number;
}

export function ObjectiveTracker({ game }: Props) {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLElement>();
  const quests = useGameStore((state) => state.quests);
  const npcs = useGameStore((state) => state.npcs);
  const enemies = useGameStore((state) => state.enemies);
  const character = useGameStore((state) => state.character);
  const playerPosition = usePlayerPosition(game, character?.position ?? null);
  const exits = useZoneExitMarkers(character?.zoneId ?? null);
  const navigation = resolveQuestNavigation({
    character, progresses: quests, npcs, enemies, exits,
    playerPosition: playerPosition ?? { x: 0, z: 0 },
  });

  const tracked = useMemo(
    () => resolveTrackedQuests({
      progresses: quests,
      npcs,
      enemies,
      playerPosition,
      zoneId: character?.zoneId,
      character,
    }),
    [quests, npcs, enemies, playerPosition, character],
  );
  const focused = tracked.find((quest) => quest.questId === navigation?.quest.id);
  const campaign = game?.campaignActivity;
  const showCampaign = campaign && (!navigation || (campaign.focus && campaign.focus.distance <= campaign.focus.objective.captureRadius));

  function showRoute() {
    if (!navigation) return;
    const store = useGameStore.getState();
    store.setWorldMapZoneId(navigation.zoneId);
    store.setWorldMapLevel(navigation.zoneId === character?.zoneId ? 'zone' : 'route');
    store.setWorldMapOpen(true);
  }

  return (
    <aside
      ref={panelRef}
      className={`objective-tracker${dragClassName}`}
      style={dragStyle}
      aria-label="Tracked objectives"
    >
      <div className="objective-tracker-header draggable-window-handle" {...dragHandleProps}>
        <span>{showCampaign ? 'Your campaign' : 'Your expedition'}</span>
        <b>{showCampaign ? 'Solo objectives' : navigation?.stage === 'turnin' ? 'Reward ready' : navigation?.stage === 'offer' ? 'Next mission' : 'In progress'}</b>
      </div>
      <CampaignRewardCard />
      {showCampaign ? <CampaignActivityCard campaign={campaign} /> : navigation ? (
        <section className={`objective-card${navigation.stage === 'turnin' ? ' ready' : ''}`}>
          <div className="objective-title-row"><h3>{navigation.quest.title}</h3></div>
          <p className="expedition-destination">{campaignZoneName(navigation.zoneId)}</p>
          <p className="expedition-next-action">
            <span>{navigation.label}</span>
            {navigation.distance !== undefined && <strong>{formatDistance(navigation.distance)}</strong>}
          </p>
          {focused && navigation.stage === 'active' && (
            <ul>
              {focused.rows.map((row) => (
                <li className={row.complete ? 'done' : ''} key={row.id}>
                  <span>{row.description}</span><strong>{row.current}/{row.required}</strong>
                </li>
              ))}
            </ul>
          )}
          <div className="expedition-actions">
            <button type="button" onClick={showRoute}>Show route</button>
            <button type="button" onClick={() => useGameStore.getState().toggleQuestLog()}>Quest log{tracked.length > 1 ? ` (${tracked.length})` : ''}</button>
          </div>
          <p className="expedition-reward">
            Reward: {navigation.quest.reward.xp} XP · {navigation.quest.reward.gold} gold
            {(navigation.quest.reward.items ?? []).map((item) => <span key={item.key}>{item.name}</span>)}
          </p>
        </section>
      ) : (
        <div className="objective-empty">
          <span>No active expedition</span>
          <p>Explore the campaign atlas or visit a field officer for your next assignment.</p>
        </div>
      )}
    </aside>
  );
}

function usePlayerPosition(
  game: Game | null,
  fallback: PlayerSnapshot | null,
): PlayerSnapshot | null {
  const [position, setPosition] = useState<PlayerSnapshot | null>(() => fallback);

  useEffect(() => {
    if (!game) {
      setPosition(fallback);
      return;
    }

    let raf = 0;
    let lastUpdate = 0;
    const loop = (now: number) => {
      if (now - lastUpdate > 300) {
        lastUpdate = now;
        const playerPos = game.playerPos;
        setPosition({ x: playerPos.x, z: playerPos.z });
      }
      raf = requestAnimationFrame(loop);
    };

    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [fallback, game]);

  return position;
}
