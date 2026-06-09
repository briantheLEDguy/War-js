import { useEffect, useMemo, useState } from 'react';
import {
  CRAFTING_PROFESSIONS,
  CRAFTING_RECIPES,
  CULTIVATION_SEEDS,
  getProfessionProgress,
  getSalvageOutputs,
  hasIngredients,
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

type CraftingTab = 'apothecary' | 'talisman_making' | 'cultivation' | 'salvage' | 'progress';

const TAB_LABELS: Record<CraftingTab, string> = {
  apothecary: 'Apothecary',
  talisman_making: 'Talismans',
  cultivation: 'Cultivation',
  salvage: 'Salvage',
  progress: 'Progress',
};

export function CraftingPanel() {
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
    <div className="panel crafting-panel">
      <div className="crafting-header">
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
  const progress = getProfessionProgress(craftingState, professionId);
  const recipes = CRAFTING_RECIPES.filter((recipe) => recipe.professionId === professionId);

  return (
    <div className="crafting-content">
      <div className="crafting-profession-row">
        <span>{professionLabel(professionId)}</span>
        <strong>Rank {progress.rank}</strong>
      </div>
      {recipes.map((recipe) => {
        const enoughRank = progress.rank >= recipe.minRank;
        const enoughItems = hasIngredients(inventory, recipe.inputs);
        const disabled = !stationAllowed || !enoughRank || !enoughItems;
        return (
          <div className={`crafting-recipe${disabled ? ' disabled' : ''}`} key={recipe.id}>
            <div className="crafting-recipe-main">
              <div>
                <div className="crafting-recipe-name">{recipe.name}</div>
                <div className="crafting-recipe-summary">{recipe.summary}</div>
              </div>
              <button
                type="button"
                disabled={disabled}
                onClick={() => craftRecipe(recipe.id)}
              >
                Craft
              </button>
            </div>
            <RecipeMeta recipe={recipe} inventory={inventory} enoughRank={enoughRank} />
          </div>
        );
      })}
    </div>
  );
}

function RecipeMeta({
  recipe,
  inventory,
  enoughRank,
}: {
  recipe: CraftingRecipe;
  inventory: InventoryItem[];
  enoughRank: boolean;
}) {
  return (
    <div className="crafting-meta">
      <div>
        <span>Needs</span>
        <ItemStackList stacks={recipe.inputs} inventory={inventory} />
      </div>
      <div>
        <span>Makes</span>
        <RewardList rewards={recipe.outputs} />
      </div>
      <div className={enoughRank ? '' : 'missing'}>
        <span>Rank</span>
        <strong>{recipe.minRank}</strong>
      </div>
    </div>
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

  return (
    <div className="crafting-content">
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
  return (
    <div className="crafting-content">
      {items.length === 0 && <div className="crafting-empty">No salvageable equipment.</div>}
      {items.map((item) => {
        const rewards = getSalvageOutputs(item);
        return (
          <div className="crafting-recipe" key={`${item.slot}-${item.key}`}>
            <div className="crafting-recipe-main">
              <div>
                <div className="crafting-recipe-name">{item.icon} {item.name}</div>
                <div className="crafting-recipe-summary">
                  {item.affix?.strengthBonus ? `+${item.affix.strengthBonus} Strength` : 'Equipment'}
                </div>
              </div>
              <button
                type="button"
                disabled={!stationAllowed}
                onClick={() => salvageInventorySlot(item.slot)}
              >
                Salvage
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
