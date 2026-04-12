import { useState } from 'react';
import { useGameStore } from '../../state/gameStore';

const ICONS: Record<string, string> = {
  sword_iron: '\u2694',
  shield_wood: '\u{1F6E1}',
  potion_health: '\u{1F9EA}',
  potion_mana: '\u{1F9EA}',
  bread: '\u{1F35E}',
};

const GRID_SIZE = 16;

export function InventoryPanel() {
  const inventory = useGameStore((s) => s.inventory);
  const [hover, setHover] = useState<number | null>(null);

  const slots = Array.from({ length: GRID_SIZE }, (_, i) =>
    inventory.find((it) => it.slot === i),
  );

  return (
    <div className="panel inventory">
      <h2>Inventory</h2>
      <div className="inv-grid">
        {slots.map((it, i) => (
          <div
            key={i}
            className={`inv-slot ${it ? '' : 'empty'}`}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover((h) => (h === i ? null : h))}
          >
            {it && (
              <>
                <span>{ICONS[it.key] ?? '\u25CB'}</span>
                {it.qty > 1 && <span className="qty">{it.qty}</span>}
                {hover === i && <div className="inv-tooltip">{it.name}</div>}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
