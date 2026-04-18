import { QUESTS_BY_ID, questsByGiver, questsByTurnIn } from '../data/quests';
import { services } from '../services';
import type {
  CharacterState,
  InventoryItem,
  QuestDefinition,
  QuestProgress,
  QuestRewardItem,
} from '../services/types';
import { useGameStore } from '../state/gameStore';

/** Level-up curve. Raised from PlayerFrame to share a single source of truth. */
export function xpForLevel(level: number): number {
  return 100 + level * 150;
}

/** Quest progress with the static definition resolved. */
export interface ResolvedQuest {
  progress: QuestProgress;
  definition: QuestDefinition;
}

/** Quests the NPC is offering this character right now (status filter). */
export function questsOfferedBy(
  npcId: string,
  progresses: QuestProgress[],
  character: CharacterState | null,
): QuestDefinition[] {
  if (!character) return [];
  const byId = new Map(progresses.map((p) => [p.questId, p] as const));
  return questsByGiver(npcId).filter((q) => {
    if (character.level < q.minLevel) return false;
    if (q.prereqQuestId) {
      const pre = byId.get(q.prereqQuestId);
      if (!pre || pre.status !== 'completed') return false;
    }
    const own = byId.get(q.id);
    return !own || own.status === 'available';
  });
}

/** Quests this NPC can hand rewards for (player already finished all steps). */
export function questsReadyToTurnIn(
  npcId: string,
  progresses: QuestProgress[],
): ResolvedQuest[] {
  const byId = new Map(progresses.map((p) => [p.questId, p] as const));
  const out: ResolvedQuest[] = [];
  for (const q of questsByTurnIn(npcId)) {
    const p = byId.get(q.id);
    if (p && p.status === 'ready_to_turn_in') {
      out.push({ progress: p, definition: q });
    }
  }
  return out;
}

/** Quests currently active that this NPC started (shown as "in progress"). */
export function questsInProgressFor(
  npcId: string,
  progresses: QuestProgress[],
): ResolvedQuest[] {
  const byId = new Map(progresses.map((p) => [p.questId, p] as const));
  const out: ResolvedQuest[] = [];
  for (const q of questsByGiver(npcId)) {
    const p = byId.get(q.id);
    if (p && p.status === 'active') out.push({ progress: p, definition: q });
  }
  return out;
}

/** Accept a quest — moves it to status=active with zeroed counters. */
export function acceptQuest(questId: string): void {
  const def = QUESTS_BY_ID[questId];
  if (!def) return;
  const store = useGameStore.getState();
  const character = store.character;
  if (!character) return;

  const counters: Record<string, number> = {};
  for (const o of def.objectives) counters[o.id] = 0;

  const progress: QuestProgress = {
    questId,
    status: 'active',
    counters,
  };
  store.upsertQuest(progress);
  void services.quests.update(character.id, useGameStore.getState().quests).catch(() => {});

  store.appendChat({
    id: `quest-accept-${Date.now()}`,
    channel: 'system',
    from: 'System',
    body: `Quest accepted: ${def.title}`,
    timestamp: Date.now(),
  });
}

/**
 * Called from Combat.killEnemy when an enemy dies — walks the active quests
 * and increments any objective that matches the enemy's name. Flips a quest
 * to `ready_to_turn_in` once every objective reaches its required count.
 */
export function registerEnemyKill(enemyName: string): void {
  const store = useGameStore.getState();
  const { quests, character } = store;
  if (!character) return;

  let changed = false;
  for (const p of quests) {
    if (p.status !== 'active') continue;
    const def = QUESTS_BY_ID[p.questId];
    if (!def) continue;

    const counters = { ...p.counters };
    let touched = false;
    for (const obj of def.objectives) {
      if (obj.killTarget && obj.killTarget === enemyName) {
        const cur = counters[obj.id] ?? 0;
        if (cur < obj.required) {
          counters[obj.id] = cur + 1;
          touched = true;
        }
      }
    }
    if (!touched) continue;

    const complete = def.objectives.every(
      (o) => (counters[o.id] ?? 0) >= o.required,
    );

    const next: QuestProgress = {
      questId: p.questId,
      status: complete ? 'ready_to_turn_in' : 'active',
      counters,
    };
    store.upsertQuest(next);
    changed = true;

    if (complete) {
      store.appendChat({
        id: `quest-ready-${Date.now()}-${p.questId}`,
        channel: 'system',
        from: 'System',
        body: `Quest ready to turn in: ${def.title}`,
        timestamp: Date.now(),
      });
    }
  }

  if (changed) {
    void services.quests
      .update(character.id, useGameStore.getState().quests)
      .catch(() => {});
  }
}

/** Roll a random strength bonus within [min,max] inclusive. */
function rollStrength(reward: QuestRewardItem): number | undefined {
  if (!reward.strengthRoll) return undefined;
  const { min, max } = reward.strengthRoll;
  return min + Math.floor(Math.random() * (max - min + 1));
}

/** Build an InventoryItem from a QuestRewardItem, rolling affixes. */
export function buildRewardItem(reward: QuestRewardItem): Omit<InventoryItem, 'slot'> {
  const strengthBonus = rollStrength(reward);
  const affix = strengthBonus !== undefined ? { strengthBonus } : undefined;
  return {
    key: reward.key,
    name: reward.name,
    qty: reward.qty,
    kind: reward.kind,
    equipSlot: reward.equipSlot,
    affix,
  };
}

/**
 * Turn in a quest, apply rewards, and check for level-up. Caller must ensure
 * the quest is in status=ready_to_turn_in before calling.
 */
export function turnInQuest(questId: string): void {
  const store = useGameStore.getState();
  const character = store.character;
  if (!character) return;

  const def = QUESTS_BY_ID[questId];
  const p = store.quests.find((q) => q.questId === questId);
  if (!def || !p || p.status !== 'ready_to_turn_in') return;

  // Mark completed
  store.upsertQuest({ ...p, status: 'completed' });

  // Apply gold + xp
  const patch: Partial<CharacterState> = {
    xp: character.xp + def.reward.xp,
    gold: character.gold + def.reward.gold,
  };
  store.updateCharacter(patch);

  // Grant items
  if (def.reward.items) {
    for (const r of def.reward.items) {
      store.addInventoryItem(buildRewardItem(r));
    }
  }

  // Persist
  void services.inventory
    .update(character.id, useGameStore.getState().inventory)
    .catch(() => {});
  void services.quests
    .update(character.id, useGameStore.getState().quests)
    .catch(() => {});

  // Chat feedback
  const rewardParts = [
    `+${def.reward.xp} XP`,
    `+${def.reward.gold} gold`,
    ...(def.reward.items ?? []).map((r) => r.name),
  ];
  store.appendChat({
    id: `quest-complete-${Date.now()}`,
    channel: 'system',
    from: 'System',
    body: `Completed: ${def.title} (${rewardParts.join(', ')})`,
    timestamp: Date.now(),
  });

  // Check level-up
  checkLevelUp();

  // Save character snapshot
  const nowChar = useGameStore.getState().character;
  if (nowChar) {
    void services.characters
      .save(nowChar.id, {
        xp: nowChar.xp,
        gold: nowChar.gold,
        level: nowChar.level,
        maxHealth: nowChar.maxHealth,
        maxMana: nowChar.maxMana,
        health: nowChar.health,
        mana: nowChar.mana,
        strength: nowChar.strength,
      })
      .catch(() => {});
  }
}

/**
 * Consume accumulated XP and promote the character's level/stats as long as
 * the threshold is met. Handles multi-level-ups from a single big reward.
 */
export function checkLevelUp(): void {
  const store = useGameStore.getState();
  if (!store.character) return;
  let c: CharacterState = store.character;

  let leveled = false;
  while (c.xp >= xpForLevel(c.level)) {
    const remainder = c.xp - xpForLevel(c.level);
    const newLevel = c.level + 1;
    const newMaxHp = c.maxHealth + 20;
    const newMaxMp = c.maxMana + 10;
    const newStr = c.strength + 2;
    c = {
      ...c,
      level: newLevel,
      xp: remainder,
      strength: newStr,
      maxHealth: newMaxHp,
      maxMana: newMaxMp,
      health: newMaxHp,
      mana: newMaxMp,
    };
    leveled = true;
    store.appendChat({
      id: `level-up-${Date.now()}-${newLevel}`,
      channel: 'system',
      from: 'System',
      body: `You have reached level ${newLevel}!`,
      timestamp: Date.now(),
    });
  }
  if (leveled) {
    store.setCharacter(c);
  }
}

/** Equip an inventory item into its appropriate slot. Unstacks a single qty. */
export function equipFromInventory(slot: number): void {
  const store = useGameStore.getState();
  const character = store.character;
  if (!character) return;
  const item = store.inventory.find((i) => i.slot === slot);
  if (!item || !item.equipSlot) return;

  // Unequip any existing item in that slot back into inventory
  const prevKey = character.equipment?.[item.equipSlot];
  if (prevKey) {
    // Note: we don't currently track affixes for the previously equipped item
    // beyond what's in inventory — players can't unequip to identical slot yet.
  }

  const equipment = { ...(character.equipment ?? {}), [item.equipSlot]: item.key };
  // Strength from affix adds to character.strength while equipped. We track
  // this by recomputing strength from base (level*2 + 10) + sum of affixes.
  const baseStrength = 10 + (character.level - 1) * 2;
  let bonusStr = 0;
  for (const slotName of Object.keys(equipment) as Array<keyof typeof equipment>) {
    const k = equipment[slotName];
    if (!k) continue;
    // Find the currently-inventoried item with that key that will be worn.
    // The item being equipped right now might have a higher affix than a
    // prior one with the same key; prefer the in-hand item for this slot.
    if (slotName === item.equipSlot) {
      bonusStr += item.affix?.strengthBonus ?? 0;
    } else {
      const worn = store.inventory.find((i) => i.key === k);
      bonusStr += worn?.affix?.strengthBonus ?? 0;
    }
  }
  store.updateCharacter({
    equipment,
    strength: baseStrength + bonusStr,
  });

  store.appendChat({
    id: `equip-${Date.now()}`,
    channel: 'system',
    from: 'System',
    body: `Equipped: ${item.name}${
      item.affix ? ` (+${item.affix.strengthBonus} Strength)` : ''
    }`,
    timestamp: Date.now(),
  });

  if (character.id) {
    void services.characters.save(character.id, {
      equipment,
      strength: baseStrength + bonusStr,
    }).catch(() => {});
  }
}
