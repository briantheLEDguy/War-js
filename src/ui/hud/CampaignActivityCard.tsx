import {
  CAMPAIGN_BATTLE_OBJECTIVE_INFLUENCE,
  CAMPAIGN_OBJECTIVE_CAPTURE_XP,
  CAMPAIGN_OBJECTIVE_DEFENSE_INFLUENCE,
  CAMPAIGN_OBJECTIVE_DEFENSE_XP,
  campaignKeepCaptureReward,
  isRvrKeepZone,
} from '../../data/campaign';
import { campaignRealmForCharacter } from '../../game/CampaignObjectiveLogic';
import { claimPendingCampaignReward } from '../../game/CampaignRewards';
import type { Game } from '../../game/Game';
import { useGameStore } from '../../state/gameStore';
import { formatDistance } from './objectiveHudData';

export function CampaignActivityCard({ campaign }: { campaign: NonNullable<Game['campaignActivity']> }) {
  const character = useGameStore((state) => state.character);
  if (!character) return null;
  const { zone, focus, progress } = campaign;
  const realm = campaignRealmForCharacter(character);
  const influence = zone.influence[realm];
  const controlled = zone.objectives.filter((objective) => objective.type === 'battle_objective' && objective.control === realm).length;
  const total = zone.objectives.filter((objective) => objective.type === 'battle_objective').length;
  const keepReward = campaignKeepCaptureReward(zone.id);
  const rewardHint = focus?.activity === 'defend'
    ? focus.objective.type === 'battle_objective' && isRvrKeepZone(zone.id)
      ? `Clear nearby enemies and hold the standard: +${CAMPAIGN_OBJECTIVE_DEFENSE_XP} XP, +${CAMPAIGN_OBJECTIVE_DEFENSE_INFLUENCE} influence.`
      : 'This objective cannot be defended.'
    : focus?.objective.type === 'keep' && isRvrKeepZone(zone.id)
      ? `Victory: ${keepReward.xp} XP, ${keepReward.gold} gold and a Victor’s Amulet.`
      : focus?.objective.type === 'battle_objective'
        ? `Clear nearby enemies and hold the point: +${CAMPAIGN_OBJECTIVE_CAPTURE_XP} XP, +${CAMPAIGN_BATTLE_OBJECTIVE_INFLUENCE} influence.`
        : 'Secure this objective for your realm.';
  function showMap() {
    const store = useGameStore.getState();
    store.setWorldMapZoneId(zone.id);
    store.setWorldMapLevel('zone');
    store.setWorldMapOpen(true);
  }
  return <section className="objective-card campaign-activity-card">
    <p className="expedition-destination">{zone.name}</p>
    <h3>{focus ? `${focus.activity === 'defend' ? 'Defend' : 'Capture'} ${focus.objective.label}` : 'Area secured'}</h3>
    {total > 0 && <p className="campaign-readiness">Standards {controlled}/{total} · Influence {influence}/{zone.influence.keepSiegeRequired}</p>}
    {focus && <>
      <p className="expedition-next-action"><span>{focus.blocker ?? (focus.distance > focus.objective.captureRadius
        ? 'Reach the marked objective' : `Hold this area for ${focus.holdMs / 1000} seconds`)}</span><strong>{formatDistance(focus.distance)}</strong></p>
      {progress > 0 && <progress className="campaign-hold-progress" aria-label="Objective secured" value={progress} max={1} />}
      {focus.commander && <p className="commander-status">
        {focus.commander.phase === 'locked' ? `Clear the approach to draw out ${focus.commander.name}.`
          : focus.commander.phase === 'defeated' ? 'Commander defeated. Hold the keep to claim your reward.'
          : focus.commander.phase === 'enraged' ? 'Last stand: faster attacks, unchanged warning time.'
          : 'Commander active. Dodge the cleave; move away for Siege Pulse.'}
      </p>}
      <p className="campaign-activity-hint">{rewardHint}</p>
    </>}
    {!focus && <p>Travel to the next front to continue your campaign.</p>}
    <div className="expedition-actions"><button type="button" onClick={showMap}>Show objectives</button></div>
  </section>;
}

export function CampaignRewardCard() {
  const notice = useGameStore((state) => state.campaignRewardNotice);
  const characterId = useGameStore((state) => state.character?.id);
  if (!notice || notice.characterId !== characterId) return null;
  return <section className="campaign-reward-card" aria-label="Campaign rewards" role="status">
    <strong>{notice.title}</strong>
    <p>+{notice.xp} XP{notice.gold > 0 && ` · +${notice.gold} gold`}{notice.influence > 0 && ` · +${notice.influence} influence`}</p>
    {notice.itemNames.map((name, index) => <p className="expedition-reward" key={`${name}-${index}`}>{name}</p>)}
    {notice.zoneControlChanged && <p>Territory secured for your realm.</p>}
    {notice.pendingItems.length > 0 ? <>
      <p>Free an inventory slot to collect your gear. Your gear is held until you collect it.</p>
      <button type="button" onClick={() => claimPendingCampaignReward(characterId!)}>Collect gear</button>
      <button type="button" onClick={() => useGameStore.getState().toggleInventory()}>Inventory</button>
    </> : <button type="button" onClick={() => useGameStore.getState().setCampaignRewardNotice(null)}>Continue</button>}
  </section>;
}
