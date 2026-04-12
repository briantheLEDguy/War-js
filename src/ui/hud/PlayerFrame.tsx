import { useGameStore } from '../../state/gameStore';

function xpForLevel(level: number) {
  return 100 + level * 150;
}

export function PlayerFrame() {
  const c = useGameStore((s) => s.character);
  if (!c) return null;
  const hpPct = c.health / c.maxHealth;
  const mpPct = c.mana / c.maxMana;
  const xpNeed = xpForLevel(c.level);
  const xpPct = Math.min(1, c.xp / xpNeed);
  return (
    <div className="panel player-frame">
      <div className="unit-name">
        <span>{c.name}</span>
        <span className="unit-level">Lv {c.level} {c.className}</span>
      </div>
      <div className="bar">
        <div className="fill health" style={{ transform: `scaleX(${hpPct})` }} />
        <div className="label">{c.health} / {c.maxHealth}</div>
      </div>
      <div className="bar">
        <div className="fill mana" style={{ transform: `scaleX(${mpPct})` }} />
        <div className="label">{c.mana} / {c.maxMana}</div>
      </div>
      <div className="bar xp-bar" title={`${c.xp} / ${xpNeed} XP`}>
        <div className="fill xp" style={{ transform: `scaleX(${xpPct})` }} />
      </div>
    </div>
  );
}
