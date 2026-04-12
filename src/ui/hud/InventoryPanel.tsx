import { useState } from 'react';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';

const ICONS: Record<string, string> = {
  sword_iron:    '\u2694',
  shield_wood:   '\u{1F6E1}',
  potion_health: '\u{1F9EA}',
  potion_mana:   '\u{1F9EA}',
  bread:         '\u{1F35E}',
};

/** Items the player can double-click to consume. */
const CONSUMABLE: Record<string, { hp?: number; mp?: number; label: string }> = {
  potion_health: { hp: 50,  label: 'Restores 50 HP' },
  potion_mana:   { mp: 50,  label: 'Restores 50 Mana' },
  bread:         { hp: 20,  label: 'Restores 20 HP' },
};

const GRID_SIZE = 16;

export function InventoryPanel() {
  const inventory        = useGameStore((s) => s.inventory);
  const character        = useGameStore((s) => s.character);
  const updateCharacter  = useGameStore((s) => s.updateCharacter);
  const removeInventoryQty = useGameStore((s) => s.removeInventoryQty);
  const appendChat       = useGameStore((s) => s.appendChat);
  const [hover, setHover] = useState<number | null>(null);

  const slots = Array.from({ length: GRID_SIZE }, (_, i) =>
    inventory.find((it) => it.slot === i),
  );

  function useItem(slotIndex: number) {
    const item = slots[slotIndex];
    if (!item || !character) return;
    const effect = CONSUMABLE[item.key];
    if (!effect) return;

    // Apply effect
    const patch: { health?: number; mana?: number } = {};
    if (effect.hp) patch.health = Math.min(character.maxHealth, character.health + effect.hp);
    if (effect.mp) patch.mana   = Math.min(character.maxMana,   character.mana   + effect.mp);
    updateCharacter(patch);

    // Consume one from stack
    removeInventoryQty(slotIndex, 1);

    // Persist (use latest inventory from store after removal)
    const latestInv = useGameStore.getState().inventory;
    void services.inventory.update(character.id, latestInv).catch(() => {});

    appendChat({
      id: `use-${Date.now()}`,
      channel: 'system',
      from: 'System',
      body: `You used: ${item.name}`,
      timestamp: Date.now(),
    });
  }

  return (
    <div className="panel inventory">
      <h2>Inventory</h2>
      <div className="inv-grid">
        {slots.map((it, i) => {
          const effect = it ? CONSUMABLE[it.key] : undefined;
          const tooltipLines = it
            ? [it.name, effect ? `${effect.label} (double-click)` : null]
                .filter(Boolean)
                .join('\n')
            : null;
          return (
            <div
              key={i}
              className={`inv-slot ${it ? '' : 'empty'}`}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover((h) => (h === i ? null : h))}
              onDoubleClick={() => useItem(i)}
            >
              {it && (
                <>
                  <span>{ICONS[it.key] ?? '\u25CB'}</span>
                  {it.qty > 1 && <span className="qty">{it.qty}</span>}
                  {hover === i && (
                    <div className="inv-tooltip">
                      {tooltipLines?.split('\n').map((line, j) => (
                        <div key={j}>{line}</div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
      <p className="inv-hint">Double-click a consumable to use it.</p>
    </div>
  );
}
