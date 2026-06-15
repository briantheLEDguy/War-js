import { useEffect, useMemo, useState } from 'react';
import type { Game } from '../../game/Game';
import { useGameStore } from '../../state/gameStore';
import {
  formatDistance,
  questNpcStatus,
  resolveTrackedQuests,
  type DistanceContext,
} from './objectiveHudData';
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

  const tracked = useMemo(
    () => resolveTrackedQuests({
      progresses: quests,
      npcs,
      enemies,
      playerPosition,
    }),
    [quests, npcs, enemies, playerPosition],
  );

  const availableQuestGivers = useMemo(
    () => npcs
      .filter((npc) => npc.role === 'questgiver')
      .map((npc) => ({
        npc,
        status: questNpcStatus(npc.id, quests, character),
        distance: playerPosition
          ? Math.hypot(npc.position.x - playerPosition.x, npc.position.z - playerPosition.z)
          : undefined,
      }))
      .filter((entry) => entry.status.offerCount > 0 || entry.status.readyCount > 0)
      .sort((a, b) => (a.distance ?? Number.MAX_SAFE_INTEGER) - (b.distance ?? Number.MAX_SAFE_INTEGER))
      .slice(0, 2),
    [character, npcs, playerPosition, quests],
  );

  return (
    <aside
      ref={panelRef}
      className={`objective-tracker${dragClassName}`}
      style={dragStyle}
      aria-label="Tracked objectives"
    >
      <div className="objective-tracker-header draggable-window-handle" {...dragHandleProps}>
        <span>Objectives</span>
        <b>{tracked.length}</b>
      </div>

      {tracked.length > 0 ? (
        <div className="objective-tracker-list">
          {tracked.slice(0, 3).map((quest) => (
            <section className={`objective-card${quest.ready ? ' ready' : ''}`} key={quest.questId}>
              <div className="objective-title-row">
                <h3>{quest.title}</h3>
                <span>{quest.ready ? 'Ready' : 'Active'}</span>
              </div>
              {quest.ready && quest.turnIn ? (
                <p className="objective-context">Turn in: {contextText(quest.turnIn)}</p>
              ) : null}
              <ul>
                {quest.rows.map((row) => (
                  <li className={row.complete ? 'done' : ''} key={row.id}>
                    <span>{row.description}</span>
                    <strong>{row.current}/{row.required}</strong>
                    {!row.complete && row.context ? <em>{contextText(row.context)}</em> : null}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      ) : (
        <div className="objective-empty">
          <span>No tracked quests</span>
          {availableQuestGivers.length > 0 ? (
            <ul>
              {availableQuestGivers.map(({ npc, status, distance }) => (
                <li key={npc.id}>
                  <b>{status.readyCount > 0 ? 'Turn-in' : 'Quest'}</b>
                  <span>{npc.name}</span>
                  {distance !== undefined ? <em>{formatDistance(distance)}</em> : null}
                </li>
              ))}
            </ul>
          ) : (
            <p>Quest givers appear on the minimap when work is available.</p>
          )}
        </div>
      )}
    </aside>
  );
}

function contextText(context: DistanceContext): string {
  const distance = formatDistance(context.distance);
  return distance ? `${context.label} - ${distance}` : context.label;
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
