import { xpForLevel } from '../../game/QuestLogic';
import { useGameStore } from '../../state/gameStore';
import { useDraggableWindow } from './useDraggableWindow';

export function PlayerFrame() {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLDivElement>();
  const c = useGameStore((s) => s.character);
  const abilityResource = useGameStore((s) => s.abilityResource);
  const effects = useGameStore((s) => s.playerStatusEffects);
  if (!c) return null;
  const hpPct = c.health / c.maxHealth;
  const mpPct = c.mana / c.maxMana;
  const resourcePct = abilityResource
    ? abilityResource.current / abilityResource.max
    : 0;
  const xpNeed = xpForLevel(c.level);
  const xpPct = Math.min(1, c.xp / xpNeed);
  return (
    <div ref={panelRef} className={`panel player-frame${dragClassName}`} style={dragStyle}>
      <div className="unit-name draggable-window-handle" {...dragHandleProps}>
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
      {abilityResource && (
        <div className="bar ability-resource-bar">
          <div className="fill ability-resource" style={{ transform: `scaleX(${resourcePct})` }} />
          <div className="label">
            {abilityResource.label} {abilityResource.current} / {abilityResource.max}
          </div>
        </div>
      )}
      <div className="bar xp-bar" title={`${c.xp} / ${xpNeed} XP`}>
        <div className="fill xp" style={{ transform: `scaleX(${xpPct})` }} />
      </div>
      <div className="unit-stats">
        <span title="Strength">STR {c.strength}</span>
        <span title="Gold" className="gold-pill">{c.gold}g</span>
      </div>
      {effects.length > 0 && <div className="player-effect-strip" aria-label="Active effects">
        {effects.slice(0, 3).map((effect) => <span key={effect.id} title={effect.label}>{effect.label}</span>)}
        {effects.length > 3 && <span title={effects.slice(3).map((effect) => effect.label).join(', ')}>+{effects.length - 3}</span>}
      </div>}
    </div>
  );
}
