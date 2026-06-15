import { useEffect, useMemo, useState } from 'react';
import {
  CRAFTING_PROFESSIONS,
  CRAFTING_RECIPES,
  CULTIVATION_SLOT_COUNT,
  CULTIVATION_SEEDS,
  getProfessionProgress,
  getSalvageOutputs,
  inventoryQty,
  professionLabel,
  type CraftingItemStack,
  type CraftingRecipe,
  type CraftingRewardItem,
} from '../../data/crafting';
import { getItemDefinition, resolveInventoryItem } from '../../data/items';
import {
  craftRecipe,
  harvestCultivationSlot,
  plantCultivationSeed,
  salvageInventorySlot,
} from '../../game/CraftingLogic';
import type { CraftingProfessionId, CraftingStationKind, InventoryItem } from '../../services/types';
import { useGameStore } from '../../state/gameStore';
import {
  countCraftableRecipes,
  filterRecipeAvailability,
  getCultivationReadyCount,
  getRecipeAvailability,
  type RecipeAvailability,
  type RecipeFilterMode,
} from './inventoryCraftingQoL';
import { useDraggableWindow } from './useDraggableWindow';

type CraftingTab = 'apothecary' | 'talisman_making' | 'cultivation' | 'salvage' | 'progress';

const TAB_LABELS: Record<CraftingTab, string> = {
  apothecary: 'Apothecary',
  talisman_making: 'Talismans',
  cultivation: 'Cultivation',
  salvage: 'Salvage',
  progress: 'Progress',
};

const RECIPE_FILTERS: Array<{ value: RecipeFilterMode; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'craftable', label: 'Craftable' },
  { value: 'missing', label: 'Missing mats' },
  { value: 'rank', label: 'Rank gated' },
];

export function CraftingPanel() {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLDivElement>();
  const inventory = useGameStore((s) => s.inventory);
  const craftingState = useGameStore((s) => s.craftingState);
  const craftingOpen = useGameStore((s) => s.craftingOpen);
  const station = useGameStore((s) => s.activeCraftingStation);
  const closeCrafting = useGameStore((s) => s.closeCrafting);
  const [activeTab, setActiveTab] = useState<CraftingTab>('apothecary');
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!station) return;
    if (station.kind === 'apothecary') setActiveTab('apothecary');
    else if (station.kind === 'talisman_making') setActiveTab('talisman_making');
    else if (station.kind === 'cultivation') setActiveTab('cultivation');
    else if (station.kind === 'salvage') setActiveTab('salvage');
  }, [station]);

  useEffect(() => {
    if (!craftingOpen) return undefined;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [craftingOpen]);

  const salvageItems = useMemo(
    () => inventory
      .map(resolveInventoryItem)
      .filter((item) => getSalvageOutputs(item).length > 0),
    [inventory],
  );

  if (!craftingOpen || !station) return null;

  const stationAllows = (kind: CraftingStationKind): boolean =>
    station.kind === 'general' || station.kind === kind;

  return (
    <div ref={panelRef} className={`panel crafting-panel${dragClassName}`} style={dragStyle}>
      <div className="crafting-header draggable-window-handle" {...dragHandleProps}>
        <div>
          <h2>Crafting</h2>
          <div className="crafting-station">{station.label}</div>
        </div>
        <button className="quest-close" type="button" onClick={closeCrafting}>Close</button>
      </div>

      <div className="crafting-tabs">
        {(Object.keys(TAB_LABELS) as CraftingTab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            className={activeTab === tab ? 'active' : ''}
            onClick={() => setActiveTab(tab)}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {activeTab === 'apothecary' && (
        <RecipeList
          professionId="apothecary"
          stationAllowed={stationAllows('apothecary')}
          inventory={inventory}
        />
      )}
      {activeTab === 'talisman_making' && (
        <RecipeList
          professionId="talisman_making"
          stationAllowed={stationAllows('talisman_making')}
          inventory={inventory}
        />
      )}
      {activeTab === 'cultivation' && (
        <CultivationView
          inventory={inventory}
          now={now}
          stationAllowed={stationAllows('cultivation')}
        />
      )}
      {activeTab === 'salvage' && (
        <SalvageView
          items={salvageItems}
          stationAllowed={stationAllows('salvage')}
        />
      )}
      {activeTab === 'progress' && <ProgressView />}
    </div>
  );
}

function RecipeList({
  professionId,
  stationAllowed,
  inventory,
}: {
  professionId: Extract<CraftingProfessionId, 'apothecary' | 'talisman_making'>;
  stationAllowed: boolean;
  inventory: InventoryItem[];
}) {
  const craftingState = useGameStore((s) => s.craftingState);
  const [recipeFilter, setRecipeFilter] = useState<RecipeFilterMode>('all');
  const progress = getProfessionProgress(craftingState, professionId);
  const recipes = CRAFTING_RECIPES.filter((recipe) => recipe.professionId === professionId);
  const availability = useMemo(
    () => recipes.map((recipe) =>
      getRecipeAvailability(recipe, inventory, progress.rank, stationAllowed),
    ),
    [inventory, progress.rank, recipes, stationAllowed],
  );
  const visibleRecipes = useMemo(
    () => filterRecipeAvailability(availability, recipeFilter),
    [availability, recipeFilter],
  );
  const craftableCount = countCraftableRecipes(availability);

  return (
    <div className="crafting-content">
      <div className="crafting-profession-row">
        <span>{professionLabel(professionId)}</span>
        <div className="crafting-row-metrics">
          <strong>Rank {progress.rank}</strong>
          <span>{craftableCount}/{recipes.length} craftable</span>
        </div>
      </div>

      <div className="crafting-filter-row" role="group" aria-label={`${professionLabel(professionId)} recipe filter`}>
        {RECIPE_FILTERS.map((filter) => (
          <button
            type="button"
            key={filter.value}
            className={recipeFilter === filter.value ? 'active' : ''}
            onClick={() => setRecipeFilter(filter.value)}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {visibleRecipes.length === 0 && (
        <div className="crafting-empty">No recipes match this filter.</div>
      )}
      {visibleRecipes.map((entry) => {
        const { recipe } = entry;
        return (
          <div className={`crafting-recipe${entry.canCraft ? '' : ' disabled'}`} key={recipe.id}>
            <div className="crafting-recipe-main">
              <div>
                <div className="crafting-recipe-name">{recipe.name}</div>
                <div className="crafting-recipe-summary">{recipe.summary}</div>
              </div>
              <button
                type="button"
                disabled={!entry.canCraft}
                onClick={() => craftRecipe(recipe.id)}
              >
                Craft
              </button>
            </div>
            <RecipeMeta recipe={recipe} inventory={inventory} availability={entry} />
          </div>
        );
      })}
    </div>
  );
}

function RecipeMeta({
  recipe,
  inventory,
  availability,
}: {
  recipe: CraftingRecipe;
  inventory: InventoryItem[];
  availability: RecipeAvailability;
}) {
  const deficitSummary = availability.missingInputs
    .map((input) => `${itemName(input.key)} x${input.missing}`)
    .join(', ');

  return (
    <>
      <div className="crafting-meta">
        <div>
          <span>Needs</span>
          <ItemStackList stacks={recipe.inputs} inventory={inventory} />
        </div>
        <div>
          <span>Makes</span>
          <RewardList rewards={recipe.outputs} />
        </div>
        <div className={availability.enoughRank ? '' : 'missing'}>
          <span>Rank</span>
          <strong>{recipe.minRank}</strong>
        </div>
      </div>
      {deficitSummary && (
        <div className="crafting-deficit">Missing: {deficitSummary}</div>
      )}
      {!availability.enoughRank && (
        <div className="crafting-deficit">Requires rank {recipe.minRank}.</div>
      )}
      {!availability.stationAllowed && (
        <div className="crafting-deficit">This station cannot craft this recipe.</div>
      )}
    </>
  );
}

function CultivationView({
  inventory,
  now,
  stationAllowed,
}: {
  inventory: InventoryItem[];
  now: number;
  stationAllowed: boolean;
}) {
  const craftingState = useGameStore((s) => s.craftingState);
  const slots = craftingState.cultivationSlots;
  const hasSoil = inventoryQty(inventory, 'craft_fertile_soil') > 0;
  const soilQty = inventoryQty(inventory, 'craft_fertile_soil');
  const readyCount = getCultivationReadyCount(slots, now);

  return (
    <div className="crafting-content">
      <div className="crafting-summary-row">
        <span>Plots <strong>{slots.length}/{CULTIVATION_SLOT_COUNT}</strong></span>
        <span className={readyCount > 0 ? 'ready' : ''}>Ready <strong>{readyCount}</strong></span>
        <span>Soil <strong>{soilQty}</strong></span>
      </div>

      <div className="cultivation-slots">
        {slots.length === 0 && <div className="crafting-empty">No active plots.</div>}
        {slots.map((slot) => {
          const seed = CULTIVATION_SEEDS.find((entry) => entry.seedKey === slot.seedKey);
          const ready = slot.readyAt <= now;
          return (
            <div className={`cultivation-slot${ready ? ' ready' : ''}`} key={slot.id}>
              <div>
                <div className="crafting-recipe-name">{seed?.name ?? slot.seedKey}</div>
                <div className="crafting-recipe-summary">
                  {ready ? 'Ready to harvest' : `${formatDuration(slot.readyAt - now)} remaining`}
                </div>
              </div>
              <button type="button" disabled={!ready} onClick={() => harvestCultivationSlot(slot.id)}>
                Harvest
              </button>
            </div>
          );
        })}
      </div>

      <div className="seed-list">
        {CULTIVATION_SEEDS.map((seed) => {
          const qty = inventoryQty(inventory, seed.seedKey);
          const disabled = !stationAllowed || qty <= 0 || slots.length >= 3;
          return (
            <div className={`crafting-recipe${disabled ? ' disabled' : ''}`} key={seed.seedKey}>
              <div className="crafting-recipe-main">
                <div>
                  <div className="crafting-recipe-name">{seed.name}</div>
                  <div className="crafting-recipe-summary">
                    Owned {qty} - {formatDuration(seed.durationMs)}
                  </div>
                </div>
                <div className="crafting-button-pair">
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => plantCultivationSeed(seed.seedKey, false)}
                  >
                    Plant
                  </button>
                  <button
                    type="button"
                    disabled={disabled || !hasSoil}
                    onClick={() => plantCultivationSeed(seed.seedKey, true)}
                  >
                    Soil
                  </button>
                </div>
              </div>
              <RewardList rewards={[...seed.outputs, ...(seed.bonusOutputs ?? [])]} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SalvageView({
  items,
  stationAllowed,
}: {
  items: InventoryItem[];
  stationAllowed: boolean;
}) {
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const selectedItem = selectedSlot === null
    ? null
    : items.find((item) => item.slot === selectedSlot) ?? null;
  const selectedRewards = selectedItem ? getSalvageOutputs(selectedItem) : [];

  useEffect(() => {
    if (selectedSlot === null) return;
    if (!items.some((item) => item.slot === selectedSlot)) setSelectedSlot(null);
  }, [items, selectedSlot]);

  return (
    <div className="crafting-content">
      <div className={`salvage-preview${selectedItem ? ' selected' : ''}`}>
        {selectedItem ? (
          <>
            <div>
              <div className="crafting-recipe-name">
                {selectedItem.icon} {selectedItem.name}
              </div>
              <div className="crafting-recipe-summary">
                Review outputs before breaking this item down.
              </div>
              <RewardList rewards={selectedRewards} />
            </div>
            <button
              type="button"
              disabled={!stationAllowed}
              onClick={() => {
                salvageInventorySlot(selectedItem.slot);
                setSelectedSlot(null);
              }}
            >
              Salvage Selected
            </button>
          </>
        ) : (
          <div className="crafting-recipe-summary">
            Select equipment below to preview salvage outputs before destroying it.
          </div>
        )}
      </div>
      {items.length === 0 && <div className="crafting-empty">No salvageable equipment.</div>}
      {items.map((item) => {
        const rewards = getSalvageOutputs(item);
        const selected = selectedSlot === item.slot;
        return (
          <div className={`crafting-recipe salvage-option${selected ? ' selected' : ''}`} key={`${item.slot}-${item.key}`}>
            <div className="crafting-recipe-main">
              <div>
                <div className="crafting-recipe-name">{item.icon} {item.name}</div>
                <div className="crafting-recipe-summary">
                  {item.affix?.strengthBonus ? `+${item.affix.strengthBonus} Strength` : 'Equipment'}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedSlot(item.slot)}
              >
                {selected ? 'Selected' : 'Select'}
              </button>
            </div>
            <RewardList rewards={rewards} />
          </div>
        );
      })}
    </div>
  );
}

function ProgressView() {
  const craftingState = useGameStore((s) => s.craftingState);

  return (
    <div className="crafting-content">
      {CRAFTING_PROFESSIONS.map((profession) => {
        const progress = getProfessionProgress(craftingState, profession.id);
        const pct = Math.min(100, progress.xp % 100);
        return (
          <div className="crafting-progress-row" key={profession.id}>
            <div>
              <div className="crafting-recipe-name">{profession.label}</div>
              <div className="crafting-recipe-summary">{profession.description}</div>
            </div>
            <div className="crafting-progress-meter">
              <span>Rank {progress.rank}</span>
              <div className="crafting-progress-track">
                <div style={{ width: `${pct}%` }} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ItemStackList({
  stacks,
  inventory,
}: {
  stacks: CraftingItemStack[];
  inventory: InventoryItem[];
}) {
  return (
    <div className="crafting-stack-list">
      {stacks.map((stack) => {
        const owned = inventoryQty(inventory, stack.key);
        const missing = owned < stack.qty;
        return (
          <span className={missing ? 'missing' : ''} key={stack.key}>
            {itemName(stack.key)} {owned}/{stack.qty}
          </span>
        );
      })}
    </div>
  );
}

function RewardList({ rewards }: { rewards: CraftingRewardItem[] }) {
  return (
    <div className="crafting-stack-list">
      {rewards.map((reward) => (
        <span key={`${reward.key}-${reward.qty}`}>
          {itemName(reward.key)} x{reward.qty}
          {reward.strengthRoll ? ` (+${reward.strengthRoll.min}-${reward.strengthRoll.max} Strength)` : ''}
        </span>
      ))}
    </div>
  );
}

function itemName(key: string): string {
  return getItemDefinition(key)?.name ?? key;
}

function formatDuration(ms: number): string {
  const seconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return minutes > 0 ? `${minutes}m ${rest}s` : `${rest}s`;
}
