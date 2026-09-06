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
    <div ref={panelRef} className={`panel target-frame${target.keepEncounter ? ' commander' : ''}${dragClassName}`} style={dragStyle}>
      <div className="unit-name draggable-window-handle" {...dragHandleProps}>
        <span>{target.name}</span>
        <span className="unit-level">Lv {target.level}</span>
      </div>
      {target.keepEncounter && <div className="commander-phase">Keep commander · {target.keepEncounter.phase === 'enraged' ? 'Last stand' : 'Hold the courtyard'}</div>}
      <div className="bar">
        <div className="fill health" style={{ transform: `scaleX(${pct})` }} />
        <div className="label">{target.health} / {target.maxHealth}</div>
      </div>
      {target.activeCast && (
        <div className="enemy-cast">
          <div className="enemy-cast-bar" role="progressbar" aria-label={target.activeCast.label}
            aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(target.activeCast.progress * 100)}>
            <div className="enemy-cast-fill" style={{ transform: `scaleX(${target.activeCast.progress})` }} />
            <span className="enemy-cast-label">{target.activeCast.label}</span>
          </div>
          <p className="enemy-cast-cue">{target.activeCast.responseCue}</p>
        </div>
      )}
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
