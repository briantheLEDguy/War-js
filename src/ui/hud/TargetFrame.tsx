import { useGameStore } from '../../state/gameStore';

export function TargetFrame() {
  const targetId = useGameStore((s) => s.targetId);
  const enemies = useGameStore((s) => s.enemies);
  const target = enemies.find((e) => e.id === targetId);
  if (!target || !target.alive) return null;
  const pct = target.health / target.maxHealth;
  return (
    <div className="panel target-frame">
      <div className="unit-name">
        <span>{target.name}</span>
        <span className="unit-level">Lv {target.level}</span>
      </div>
      <div className="bar">
        <div className="fill health" style={{ transform: `scaleX(${pct})` }} />
        <div className="label">{target.health} / {target.maxHealth}</div>
      </div>
    </div>
  );
}
