import { QUESTS_BY_ID } from '../../data/quests';
import { useGameStore } from '../../state/gameStore';
import type { QuestProgress } from '../../services/types';

/** Quest log — toggled with L. Shows active and completed quests with progress. */
export function QuestLogPanel() {
  const quests = useGameStore((s) => s.quests);
  const toggle = useGameStore((s) => s.toggleQuestLog);

  const active = quests.filter(
    (q) => q.status === 'active' || q.status === 'ready_to_turn_in',
  );
  const completed = quests.filter((q) => q.status === 'completed');

  return (
    <div className="panel quest-log">
      <div className="quest-log-header">
        <h2>Quest Log</h2>
        <button className="quest-close" onClick={toggle}>
          Close
        </button>
      </div>

      <h3>Active ({active.length})</h3>
      {active.length === 0 ? (
        <p className="quest-empty">No active quests. Find a quest-giver in town (look for golden markers) and press E to interact.</p>
      ) : (
        <ul className="quest-list">
          {active.map((p) => (
            <QuestEntry key={p.questId} progress={p} />
          ))}
        </ul>
      )}

      {completed.length > 0 && (
        <>
          <h3>Completed ({completed.length})</h3>
          <ul className="quest-list faded">
            {completed.map((p) => {
              const def = QUESTS_BY_ID[p.questId];
              if (!def) return null;
              return (
                <li key={p.questId}>
                  <div className="quest-title">{def.title}</div>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}

function QuestEntry({ progress }: { progress: QuestProgress }) {
  const def = QUESTS_BY_ID[progress.questId];
  if (!def) return null;
  const ready = progress.status === 'ready_to_turn_in';

  return (
    <li className={ready ? 'ready' : ''}>
      <div className="quest-title">
        {def.title}
        {ready && <span className="quest-ready-tag"> Ready!</span>}
      </div>
      <div className="quest-desc">{def.description}</div>
      <ul className="quest-objectives">
        {def.objectives.map((o) => {
          const cur = progress.counters[o.id] ?? 0;
          const done = cur >= o.required;
          return (
            <li key={o.id} className={done ? 'objective-done' : ''}>
              {o.description}: {cur} / {o.required}
            </li>
          );
        })}
      </ul>
      <div className="quest-reward">
        Reward: +{def.reward.xp} XP, +{def.reward.gold} gold
        {def.reward.items
          ? def.reward.items.map((r) => `, ${r.name}`).join('')
          : ''}
      </div>
    </li>
  );
}
