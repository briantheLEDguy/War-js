import { useMemo } from 'react';
import {
  acceptQuest,
  questsInProgressFor,
  questsOfferedBy,
  questsReadyToTurnIn,
  turnInQuest,
} from '../../game/QuestLogic';
import { useGameStore } from '../../state/gameStore';

/**
 * Dialog shown when the player presses E near a quest-giver. Lists turn-ins
 * first, then new offers, then active (in-progress) quests with live counters.
 */
export function QuestDialog() {
  const activeNpcId = useGameStore((s) => s.activeQuestDialogNpcId);
  const close = () => useGameStore.getState().setActiveQuestDialogNpcId(null);

  const npcs = useGameStore((s) => s.npcs);
  const character = useGameStore((s) => s.character);
  const quests = useGameStore((s) => s.quests);

  const npc = useMemo(
    () => npcs.find((n) => n.id === activeNpcId) ?? null,
    [npcs, activeNpcId],
  );

  if (!activeNpcId || !npc) return null;

  const turnIns = questsReadyToTurnIn(activeNpcId, quests);
  const offers = questsOfferedBy(activeNpcId, quests, character);
  const active = questsInProgressFor(activeNpcId, quests);

  return (
    <div className="dialog-overlay" onClick={close}>
      <div className="panel quest-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="quest-log-header">
          <h2>{npc.name}</h2>
          <button className="quest-close" onClick={close}>
            Leave
          </button>
        </div>
        {npc.title && <div className="quest-npc-title">{npc.title}</div>}

        {turnIns.length === 0 && offers.length === 0 && active.length === 0 && (
          <p className="quest-empty">This one has no work for you today.</p>
        )}

        {turnIns.length > 0 && (
          <>
            <h3>Reward Awaits</h3>
            {turnIns.map(({ definition }) => (
              <div className="quest-offer" key={definition.id}>
                <div className="quest-title">{definition.title}</div>
                <div className="quest-reward">
                  +{definition.reward.xp} XP, +{definition.reward.gold} gold
                  {definition.reward.items?.map((r) => `, ${r.name}`).join('')}
                </div>
                <button
                  onClick={() => {
                    turnInQuest(definition.id);
                  }}
                >
                  Complete
                </button>
              </div>
            ))}
          </>
        )}

        {offers.length > 0 && (
          <>
            <h3>Available</h3>
            {offers.map((def) => (
              <div className="quest-offer" key={def.id}>
                <div className="quest-title">{def.title}</div>
                <div className="quest-desc">{def.description}</div>
                <ul className="quest-objectives">
                  {def.objectives.map((o) => (
                    <li key={o.id}>
                      {o.description}: 0 / {o.required}
                    </li>
                  ))}
                </ul>
                <div className="quest-reward">
                  Reward: +{def.reward.xp} XP, +{def.reward.gold} gold
                  {def.reward.items?.map((r) => `, ${r.name}`).join('')}
                </div>
                <button
                  onClick={() => {
                    acceptQuest(def.id);
                  }}
                >
                  Accept
                </button>
              </div>
            ))}
          </>
        )}

        {active.length > 0 && (
          <>
            <h3>In Progress</h3>
            {active.map(({ progress, definition }) => (
              <div className="quest-offer faded" key={definition.id}>
                <div className="quest-title">{definition.title}</div>
                <ul className="quest-objectives">
                  {definition.objectives.map((o) => {
                    const cur = progress.counters[o.id] ?? 0;
                    const done = cur >= o.required;
                    return (
                      <li key={o.id} className={done ? 'objective-done' : ''}>
                        {o.description}: {cur} / {o.required}
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

