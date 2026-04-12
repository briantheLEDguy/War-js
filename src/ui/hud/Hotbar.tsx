import { useGameStore } from '../../state/gameStore';

interface Ability {
  slot: number;
  key: string;
  icon: string;
  name: string;
}

const ABILITIES: Ability[] = [
  { slot: 0, key: '1', icon: '\u2694', name: 'Autoattack' },
  { slot: 1, key: '2', icon: '\u26A1', name: 'Placeholder' },
  { slot: 2, key: '3', icon: '\u2728', name: 'Placeholder' },
  { slot: 3, key: '4', icon: '\u2695', name: 'Placeholder' },
];

export function Hotbar() {
  const cooldowns = useGameStore((s) => s.hotbarCooldowns);
  return (
    <div className="hotbar">
      {ABILITIES.map((a) => {
        const cd = cooldowns[a.slot] ?? 0;
        return (
          <div key={a.slot} className="hotbar-slot" title={a.name}>
            <span>{a.icon}</span>
            <span className="key">{a.key}</span>
            {cd > 0 && <div className="cd-overlay">{cd.toFixed(1)}</div>}
          </div>
        );
      })}
    </div>
  );
}
