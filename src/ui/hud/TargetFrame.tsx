import { useGameStore } from '../../state/gameStore';
import { useDraggableWindow } from './useDraggableWindow';

export function TargetFrame() {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLDivElement>();
  const targetId = useGameStore((s) => s.targetId);
  const enemies = useGameStore((s) => s.enemies);
  const target = enemies.find((e) => e.id === targetId);
  if (!target || !target.alive) return null;
  const pct = target.health / target.maxHealth;
  return (
    <div ref={panelRef} className={`panel target-frame${dragClassName}`} style={dragStyle}>
      <div className="unit-name draggable-window-handle" {...dragHandleProps}>
        <span>{target.name}</span>
        <span className="unit-level">Lv {target.level}</span>
      </div>
      <div className="bar">
        <div className="fill health" style={{ transform: `scaleX(${pct})` }} />
        <div className="label">{target.health} / {target.maxHealth}</div>
      </div>
      {target.statusEffects && target.statusEffects.length > 0 && (
        <div className="target-status-row">
          {target.statusEffects.slice(0, 5).map((effect) => (
            <span key={effect.id} className={`target-status status-${effect.kind}`}>
              {effect.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
