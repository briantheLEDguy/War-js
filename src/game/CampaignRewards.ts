import type { CampaignClaimResult, CampaignClaimReward } from '../data/campaign';
import { services } from '../services';
import type { InventoryItem } from '../services/types';
import { useGameStore, type CampaignRewardNotice } from '../state/gameStore';
import { buildRewardItem, checkLevelUp } from './QuestLogic';
import { canFitRewardItems, placeRewardItems } from './RewardInventory';

const PENDING_REWARD_KEY = 'war-js:pending-campaign-reward:';
const settledResults = new WeakSet<CampaignClaimResult>();

/** A pure capacity check, including stack limits; it does not roll reward affixes. */
export function campaignRewardInventoryBlocker(
  reward: CampaignClaimReward,
  inventory: InventoryItem[],
): string | null {
  return !canFitRewardItems(reward.items ?? [], inventory)
    ? 'Make room in your inventory before claiming this objective reward.'
    : null;
}

/** Campaign control/influence have already been committed by the campaign service. */
export function settleCampaignReward(result: CampaignClaimResult, characterId: string): void {
  const store = useGameStore.getState();
  const character = store.character;
  if (!character || character.id !== characterId || settledResults.has(result)) return;
  settledResults.add(result);

  const previous = pendingNotice(characterId);
  const rolledItems = (result.reward.items ?? []).map(buildRewardItem);
  const placement = placeRewardItems([...(previous?.pendingItems ?? []), ...rolledItems], store.inventory);
  const notice: CampaignRewardNotice = {
    characterId,
    title: `${result.activity === 'defend' ? 'Defended' : 'Captured'} ${result.objective.label}`,
    zoneId: result.zoneId,
    xp: result.reward.xp,
    gold: result.reward.gold ?? 0,
    influence: result.reward.influence,
    itemNames: [...(previous?.pendingItems.map((item) => item.name) ?? []), ...rolledItems.map((item) => item.name)],
    zoneControlChanged: result.zoneControlChanged,
    pendingItems: placement.pendingItems,
  };
  store.setInventory(placement.inventory);
  store.updateCharacter({ xp: character.xp + notice.xp, gold: character.gold + notice.gold });
  checkLevelUp();
  store.setCampaignRewardNotice(notice);
  persistPendingNotice(notice);
  store.appendChat({
    id: `campaign-reward-${Date.now()}-${result.objectiveId}`,
    channel: 'system', from: 'System', timestamp: Date.now(),
    body: `${notice.title}: +${notice.xp} XP, +${notice.gold} gold, +${notice.influence} influence.${notice.itemNames.length ? ` ${notice.itemNames.join(', ')}.` : ''}${notice.zoneControlChanged ? ' Territory secured for your realm.' : ''}`,
  });

  const current = useGameStore.getState();
  void services.inventory.update(characterId, current.inventory).catch(() => {});
  if (current.character?.id === characterId) {
    const { xp, gold, level, maxHealth, maxMana, health, mana, strength } = current.character;
    void services.characters.save(characterId, {
      xp, gold, level, maxHealth, maxMana, health, mana, strength,
    }).catch(() => {});
  }
}

/** Collect held gear without replaying XP, gold, influence, or random rolls. */
export function claimPendingCampaignReward(characterId: string): boolean {
  const store = useGameStore.getState();
  if (store.character?.id !== characterId) return false;
  const notice = pendingNotice(characterId);
  if (!notice) return false;
  const placement = placeRewardItems(notice.pendingItems, store.inventory);
  const next = { ...notice, pendingItems: placement.pendingItems };
  store.setInventory(placement.inventory);
  store.setCampaignRewardNotice(next);
  persistPendingNotice(next);
  void services.inventory.update(characterId, placement.inventory).catch(() => {});
  return next.pendingItems.length === 0;
}

/** Called after the character and its inventory load; pending rewards survive logout/reload. */
export function restoreCampaignRewardNotice(characterId: string): void {
  const store = useGameStore.getState();
  if (store.character?.id !== characterId) return;
  const notice = pendingNotice(characterId);
  store.setCampaignRewardNotice(notice);
}

function pendingNotice(characterId: string): CampaignRewardNotice | null {
  const current = useGameStore.getState().campaignRewardNotice;
  if (current?.characterId === characterId && current.pendingItems.length > 0) return current;
  try {
    const raw = localStorage.getItem(`${PENDING_REWARD_KEY}${characterId}`);
    if (!raw) return null;
    const notice = JSON.parse(raw) as Partial<CampaignRewardNotice> | null;
    if (!notice || notice.characterId !== characterId || !Array.isArray(notice.pendingItems) || notice.pendingItems.length === 0) return null;
    if (typeof notice.title !== 'string' || typeof notice.zoneId !== 'string' || typeof notice.zoneControlChanged !== 'boolean') return null;
    if (![notice.xp, notice.gold, notice.influence].every((value) => typeof value === 'number' && Number.isFinite(value))) return null;
    if (!Array.isArray(notice.itemNames) || !notice.itemNames.every((name) => typeof name === 'string')) return null;
    if (!notice.pendingItems.every((item) => item && typeof item.key === 'string' && typeof item.name === 'string' && Number.isInteger(item.qty) && item.qty > 0)) return null;
    return notice as CampaignRewardNotice;
  } catch {
    return null;
  }
}

function persistPendingNotice(notice: CampaignRewardNotice): void {
  try {
    const key = `${PENDING_REWARD_KEY}${notice.characterId}`;
    if (notice.pendingItems.length > 0) localStorage.setItem(key, JSON.stringify(notice));
    else localStorage.removeItem(key);
  } catch {
    // The in-memory receipt still allows collection when local storage is unavailable.
  }
}
