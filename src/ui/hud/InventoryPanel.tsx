import { useMemo, useState } from 'react';
import {
  EQUIP_SLOT_LABELS,
  EQUIP_SLOT_ORDER,
  getConsumableEffect,
  INVENTORY_CAPACITY,
  resolveInventoryItem,
} from '../../data/items';
import { equipFromInventory, getEquippedGear, isInventoryItemEquipped } from '../../game/Equipment';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';
import {
  DEFAULT_INVENTORY_FILTERS,
  filterAndSortInventoryItems,
  getEquipmentComparisonLines,
  isDefaultInventoryFilters,
  type InventoryFilters,
  type InventoryKindFilter,
  type InventoryMaterialFilter,
  type InventorySortMode,
} from './inventoryCraftingQoL';
import { useDraggableWindow } from './useDraggableWindow';

const KIND_FILTERS: Array<{ value: InventoryKindFilter; label: string }> = [
  { value: 'all', label: 'All types' },
  { value: 'equipment', label: 'Equipment' },
  { value: 'weapon', label: 'Weapons' },
  { value: 'armor', label: 'Armor' },
  { value: 'consumable', label: 'Consumables' },
  { value: 'material', label: 'Materials' },
  { value: 'seed', label: 'Seeds' },
];

const MATERIAL_FILTERS: Array<{ value: InventoryMaterialFilter; label: string }> = [
  { value: 'all', label: 'All uses' },
  { value: 'apothecary', label: 'Apothecary' },
  { value: 'talisman_making', label: 'Talisman' },
  { value: 'cultivation', label: 'Cultivation' },
  { value: 'salvage', label: 'Salvage mats' },
];

const SORT_MODES: Array<{ value: InventorySortMode; label: string }> = [
  { value: 'slot', label: 'Slot order' },
  { value: 'name', label: 'Name' },
  { value: 'kind', label: 'Type' },
  { value: 'quantity', label: 'Quantity' },
  { value: 'strength', label: 'Strength' },
];

export function InventoryPanel() {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLDivElement>();
  const inventory        = useGameStore((s) => s.inventory);
  const character        = useGameStore((s) => s.character);
  const updateCharacter  = useGameStore((s) => s.updateCharacter);
  const removeInventoryQty = useGameStore((s) => s.removeInventoryQty);
  const appendChat       = useGameStore((s) => s.appendChat);
  const [hoverSlot, setHoverSlot] = useState<number | null>(null);
  const [filters, setFilters] = useState<InventoryFilters>(DEFAULT_INVENTORY_FILTERS);

  const slots = useMemo(
    () => Array.from({ length: INVENTORY_CAPACITY }, (_, i) =>
      inventory.find((it) => it.slot === i),
    ),
    [inventory],
  );
  const visibleItems = useMemo(
    () => filterAndSortInventoryItems(inventory, filters),
    [filters, inventory],
  );
  const defaultFilters = isDefaultInventoryFilters(filters);
  const displayEntries = useMemo(
    () => defaultFilters
      ? slots.map((item, slot) => ({ item, slot }))
      : visibleItems.map((item) => ({ item, slot: item.slot })),
    [defaultFilters, slots, visibleItems],
  );
  const occupied = inventory.length;
  const shown = defaultFilters ? occupied : visibleItems.length;
  const usedEquipSlots = useMemo(
    () => EQUIP_SLOT_ORDER.filter((slot) =>
      inventory.some((rawItem) => resolveInventoryItem(rawItem).equipSlot === slot),
    ),
    [inventory],
  );

  function setFilter<K extends keyof InventoryFilters>(key: K, value: InventoryFilters[K]) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

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
    <div ref={panelRef} className={`panel inventory${dragClassName}`} style={dragStyle}>
      <div className="inventory-header draggable-window-handle" {...dragHandleProps}>
        <h2>Inventory</h2>
        <div className="inventory-capacity">
          <strong>{occupied}</strong><span>/{INVENTORY_CAPACITY} occupied</span>
        </div>
      </div>
      <progress
        className="inventory-capacity-track"
        value={occupied}
        max={INVENTORY_CAPACITY}
        aria-label="Inventory capacity"
      />

      <div className="inventory-controls">
        <input
          type="search"
          value={filters.search}
          aria-label="Search inventory"
          placeholder="Search packs..."
          onChange={(e) => setFilter('search', e.target.value)}
        />
        <select
          value={filters.kind}
          aria-label="Filter by item type"
          onChange={(e) => setFilter('kind', e.target.value as InventoryKindFilter)}
        >
          {KIND_FILTERS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <select
          value={filters.equipSlot}
          aria-label="Filter by equipment slot"
          onChange={(e) => setFilter('equipSlot', e.target.value as InventoryFilters['equipSlot'])}
        >
          <option value="all">All slots</option>
          {usedEquipSlots.map((slot) => (
            <option key={slot} value={slot}>{EQUIP_SLOT_LABELS[slot]}</option>
          ))}
        </select>
        <select
          value={filters.material}
          aria-label="Filter by material use"
          onChange={(e) => setFilter('material', e.target.value as InventoryMaterialFilter)}
        >
          {MATERIAL_FILTERS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <select
          value={filters.sort}
          aria-label="Sort inventory"
          onChange={(e) => setFilter('sort', e.target.value as InventorySortMode)}
        >
          {SORT_MODES.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </div>

      <div className="inventory-filter-status">
        <span>{shown} stack{shown === 1 ? '' : 's'} shown</span>
        {!defaultFilters && (
          <button type="button" onClick={() => setFilters(DEFAULT_INVENTORY_FILTERS)}>
            Clear
          </button>
        )}
      </div>

      {displayEntries.length === 0 ? (
        <div className="inventory-empty-state">No inventory stacks match these filters.</div>
      ) : (
        <div className={`inv-grid${defaultFilters ? '' : ' filtered'}`}>
        {displayEntries.map(({ item: it, slot: i }) => {
          const item = it ? resolveInventoryItem(it) : null;
          const effect = item ? getConsumableEffect(item.key) : undefined;
          const canEquip =
            !!item?.equipSlot && (item.kind === 'weapon' || item.kind === 'armor');
          const equipped = it ? isInventoryItemEquipped(it, character?.equipment) : false;
          const equippedGear =
            item?.equipSlot && character ? getEquippedGear(character, item.equipSlot, inventory) : null;
          const comparisonLines = item
            ? getEquipmentComparisonLines(item, equippedGear, EQUIP_SLOT_LABELS)
            : [];
          const tooltipLines = item
            ? [
                item.name,
                item.kind ? item.kind.replace('_', ' ') : null,
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
                ...comparisonLines,
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
              onMouseEnter={() => setHoverSlot(i)}
              onMouseLeave={() => setHoverSlot((h) => (h === i ? null : h))}
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
                  {hoverSlot === i && (
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
      )}
      <p className="inv-hint">Click or right-click gear to equip. Double-click consumables.</p>
    </div>
  );
}
