import { useGameStore } from '../../state/gameStore';

interface Ability {
  slot: number;
  key: string;
  icon: string;
  name: string;
  tooltip: string;
}

const ABILITIES: Ability[] = [
  { slot: 0, key: '1', icon: '\u2694',  name: 'Autoattack',   tooltip: 'Autoattack (melee, no cost)' },
  { slot: 1, key: '2', icon: '\u26A1',  name: 'Heavy Strike',  tooltip: 'Heavy Strike — 12-24 dmg, melee, 10 mana, 5s CD' },
  { slot: 2, key: '3', icon: '\u27B3',  name: 'Ranged Shot',   tooltip: 'Ranged Shot — 5-12 dmg, 10u range, 8 mana, 3s CD' },
  { slot: 3, key: '4', icon: '\u2764',  name: 'Bandage',       tooltip: 'Bandage — heal 35-50 HP, 15 mana, 10s CD' },
];

export function Hotbar() {
  const cooldowns = useGameStore((s) => s.hotbarCooldowns);
  const character = useGameStore((s) => s.character);

  return (
    <div className="hotbar">
      {ABILITIES.map((a) => {
        const cd = cooldowns[a.slot] ?? 0;
        const noMana =
          a.slot === 1 && (character?.mana ?? 0) < 10 ||
          a.slot === 2 && (character?.mana ?? 0) < 8  ||
          a.slot === 3 && (character?.mana ?? 0) < 15;
        return (
          <div
            key={a.slot}
            className={`hotbar-slot${noMana && cd <= 0 ? ' no-mana' : ''}`}
            title={a.tooltip}
          >
            <span>{a.icon}</span>
            <span className="key">{a.key}</span>
            {cd > 0 && <div className="cd-overlay">{cd.toFixed(1)}</div>}
          </div>
        );
      })}
    </div>
  );
}
