import { useState } from 'react';
import { getConsumableEffect, INVENTORY_CAPACITY, resolveInventoryItem } from '../../data/items';
import { equipFromInventory, isInventoryItemEquipped } from '../../game/Equipment';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';

export function InventoryPanel() {
  const inventory        = useGameStore((s) => s.inventory);
  const character        = useGameStore((s) => s.character);
  const updateCharacter  = useGameStore((s) => s.updateCharacter);
  const removeInventoryQty = useGameStore((s) => s.removeInventoryQty);
  const appendChat       = useGameStore((s) => s.appendChat);
  const [hover, setHover] = useState<number | null>(null);

  const slots = Array.from({ length: INVENTORY_CAPACITY }, (_, i) =>
    inventory.find((it) => it.slot === i),
  );

  function activateItem(slotIndex: number) {
    const rawItem = slots[slotIndex];
    if (!rawItem || !character) return;

    const item = resolveInventoryItem(rawItem);
    const canEquip =
      !!item.equipSlot && (item.kind === 'weapon' || item.kind === 'armor');
    if (canEquip) {
      equipFromInventory(slotIndex);
      return;
    }

    const effect = getConsumableEffect(item.key);
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
          const item = it ? resolveInventoryItem(it) : null;
          const effect = item ? getConsumableEffect(item.key) : undefined;
          const canEquip =
            !!item?.equipSlot && (item.kind === 'weapon' || item.kind === 'armor');
          const equipped = it ? isInventoryItemEquipped(it, character?.equipment) : false;
          const tooltipLines = item
            ? [
                item.name,
                item.affix?.strengthBonus
                  ? `+${item.affix.strengthBonus} Strength`
                  : null,
                item.equipSlot
                  ? equipped
                    ? 'Equipped'
                    : 'Right-click to equip'
                  : effect
                    ? `${effect.label} (double-click)`
                    : null,
              ]
                .filter(Boolean)
                .join('\n')
            : null;
          return (
            <button
              type="button"
              key={i}
              className={`inv-slot ${it ? '' : 'empty'} ${equipped ? 'equipped' : ''}`}
              disabled={!it}
              aria-label={
                item
                  ? `${item.name}${equipped ? ' equipped' : ''}`
                  : `Empty inventory slot ${i + 1}`
              }
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover((h) => (h === i ? null : h))}
              onClick={() => {
                if (canEquip) equipFromInventory(i);
              }}
              onDoubleClick={() => activateItem(i)}
              onContextMenu={(e) => {
                if (!canEquip) return;
                e.preventDefault();
                equipFromInventory(i);
              }}
            >
              {item && (
                <>
                  <span>{item.icon ?? '\u25CB'}</span>
                  {item.qty > 1 && <span className="qty">{item.qty}</span>}
                  {hover === i && (
                    <div className="inv-tooltip">
                      {tooltipLines?.split('\n').map((line, j) => (
                        <div key={j}>{line}</div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </button>
          );
        })}
      </div>
      <p className="inv-hint">Click or right-click gear to equip. Double-click consumables.</p>
    </div>
  );
}
