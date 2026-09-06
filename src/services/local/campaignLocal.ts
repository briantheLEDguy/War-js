import {
  CAMPAIGN_BATTLE_OBJECTIVE_INFLUENCE,
  CAMPAIGN_BATTLEFIELD_SWEEP_INFLUENCE,
  CAMPAIGN_OBJECTIVE_CAPTURE_XP,
  CAMPAIGN_OBJECTIVE_DEFENSE_COOLDOWN_MS,
  CAMPAIGN_OBJECTIVE_DEFENSE_INFLUENCE,
  CAMPAIGN_OBJECTIVE_DEFENSE_XP,
  CAMPAIGN_OBJECTIVES_BY_ZONE,
  CAMPAIGN_ZONE_BY_ID,
  campaignObjectiveCaptureEligibility,
  campaignObjectiveDefenseEligibility,
  campaignKeepCaptureReward,
  campaignZoneInfluence,
  buildCampaignSnapshot,
  defaultCampaignZoneControl,
  defaultCampaignObjectiveControl,
  isRvrKeepZone,
  objectiveKey,
  type CampaignClaimResult,
  type CampaignClaimReward,
  type CampaignObjectiveControlState,
  type CampaignObjectiveDefenseState,
  type CampaignRealm,
  type CampaignSnapshot,
  type CampaignZoneControlState,
  type CampaignZoneInfluenceState,
} from '../../data/campaign';
import type { CampaignService, Unsubscribe } from '../types';

interface StoredCampaignState {
  version?: number;
  zoneControl: CampaignZoneControlState;
  objectiveControl: CampaignObjectiveControlState;
  influence?: CampaignZoneInfluenceState;
  defenseReadyAt?: CampaignObjectiveDefenseState;
}

interface Subscription {
  cb: (snapshot: CampaignSnapshot) => void;
  currentZoneId?: string | null;
}

const STORAGE_KEY = 'war-js:campaign-state:aegis-riftbound-v1';
const STORAGE_VERSION = 3;

export class CampaignLocal implements CampaignService {
  private zoneControl: CampaignZoneControlState = {};
  private objectiveControl: CampaignObjectiveControlState = {};
  private influence: CampaignZoneInfluenceState = {};
  private defenseReadyAt: CampaignObjectiveDefenseState = {};
  private subs = new Set<Subscription>();

  constructor() {
    this.load();
  }

  async getSnapshot(currentZoneId?: string | null): Promise<CampaignSnapshot> {
    return this.snapshot(currentZoneId);
  }

  subscribeSnapshot(
    cb: (snapshot: CampaignSnapshot) => void,
    currentZoneId?: string | null,
  ): Unsubscribe {
    const sub = { cb, currentZoneId };
    this.subs.add(sub);
    cb(this.snapshot(currentZoneId));
    return () => this.subs.delete(sub);
  }

  async claimObjective(
    zoneId: string,
    objectiveId: string,
    realm: CampaignRealm,
  ): Promise<CampaignClaimResult> {
    const objectives = CAMPAIGN_OBJECTIVES_BY_ZONE[zoneId] ?? [];
    const objective = objectives.find((entry) => entry.id === objectiveId);
    if (!objective) {
      throw new Error(`Unknown campaign objective "${zoneId}:${objectiveId}".`);
    }

    const controlledObjectives = objectives.map((entry) => ({
      ...entry,
      control: this.objectiveControl[objectiveKey(zoneId, entry.id)]
        ?? defaultCampaignObjectiveControl(zoneId, entry.id),
    }));
    const currentObjective = controlledObjectives.find((entry) => entry.id === objectiveId)!;
    const influence = campaignZoneInfluence(zoneId, this.influence);
    const eligibility = campaignObjectiveCaptureEligibility(
      controlledObjectives,
      currentObjective,
      realm,
      influence,
    );
    if (!eligibility.capturable) {
      throw new Error(eligibility.reason ?? `Objective "${objectiveId}" cannot be captured.`);
    }

    const reward: CampaignClaimReward = objective.type === 'keep' && isRvrKeepZone(zoneId)
      ? campaignKeepCaptureReward(zoneId)
      : {
          xp: objective.type === 'battle_objective' ? CAMPAIGN_OBJECTIVE_CAPTURE_XP : 0,
          influence: objective.type === 'battle_objective' ? CAMPAIGN_BATTLE_OBJECTIVE_INFLUENCE : 0,
        };

    const battleObjectives = objectives.filter((entry) => entry.type === 'battle_objective');
    const controlledBattleObjectivesBefore = controlledObjectives
      .filter((entry) => entry.type === 'battle_objective' && entry.control === realm)
      .length;

    this.objectiveControl[objectiveKey(zoneId, objectiveId)] = realm;

    if (
      objective.type === 'battle_objective' &&
      battleObjectives.length > 0 &&
      controlledBattleObjectivesBefore < battleObjectives.length &&
      battleObjectives.every((entry) =>
        (this.objectiveControl[objectiveKey(zoneId, entry.id)]
          ?? defaultCampaignObjectiveControl(zoneId, entry.id)) === realm,
      )
    ) {
      reward.influence += CAMPAIGN_BATTLEFIELD_SWEEP_INFLUENCE;
    }

    if (reward.influence > 0) {
      const entry = this.influence[zoneId] ?? {};
      this.influence[zoneId] = {
        ...entry,
        [realm]: Math.max(0, Math.floor(entry[realm] ?? 0)) + reward.influence,
      };
    }

    const previousZoneControl = this.zoneControl[zoneId] ?? defaultCampaignZoneControl(zoneId);
    if (objective.type === 'keep' && isRvrKeepZone(zoneId)) {
      this.zoneControl[zoneId] = realm;
    } else if (CAMPAIGN_ZONE_BY_ID[zoneId]?.nodeRole !== 'battlefield') {
      const allControlled = objectives.every((entry) =>
        (this.objectiveControl[objectiveKey(zoneId, entry.id)]
          ?? defaultCampaignZoneControl(zoneId)) === realm,
      );
      if (allControlled) this.zoneControl[zoneId] = realm;
    }

    this.persist();
    this.broadcast();
    const snapshot = this.snapshot();
    const active = snapshot.zones.find((entry) => entry.id === zoneId);
    const updated = active?.objectives.find((entry) => entry.id === objectiveId);
    if (!updated) throw new Error(`Captured objective "${zoneId}:${objectiveId}" disappeared from snapshot.`);
    return {
      activity: 'capture',
      snapshot,
      zoneId,
      objectiveId,
      realm,
      objective: updated,
      reward,
      zoneControlChanged: (this.zoneControl[zoneId] ?? defaultCampaignZoneControl(zoneId)) !== previousZoneControl,
    };
  }

  async defendObjective(
    zoneId: string,
    objectiveId: string,
    realm: CampaignRealm,
  ): Promise<CampaignClaimResult> {
    const objective = CAMPAIGN_OBJECTIVES_BY_ZONE[zoneId]?.find((entry) => entry.id === objectiveId);
    if (!objective) throw new Error(`Unknown campaign objective "${zoneId}:${objectiveId}".`);
    const key = objectiveKey(zoneId, objectiveId);
    const nowMs = Date.now();
    const eligibility = campaignObjectiveDefenseEligibility(zoneId, {
      ...objective,
      control: this.objectiveControl[key] ?? defaultCampaignObjectiveControl(zoneId, objectiveId),
      defenseReadyAt: this.defenseReadyAt[key] ?? {},
    }, realm, nowMs);
    if (!eligibility.defendable) throw new Error(eligibility.reason ?? 'Objective cannot be defended.');

    const reward: CampaignClaimReward = {
      xp: CAMPAIGN_OBJECTIVE_DEFENSE_XP,
      influence: CAMPAIGN_OBJECTIVE_DEFENSE_INFLUENCE,
    };
    const influence = this.influence[zoneId] ?? {};
    this.influence[zoneId] = {
      ...influence,
      [realm]: Math.max(0, Math.floor(influence[realm] ?? 0)) + reward.influence,
    };
    // Reserve the realm cooldown before broadcasting, including reentrant subscriber calls.
    this.defenseReadyAt[key] = {
      ...this.defenseReadyAt[key],
      [realm]: nowMs + CAMPAIGN_OBJECTIVE_DEFENSE_COOLDOWN_MS,
    };
    this.persist();
    this.broadcast();
    const snapshot = this.snapshot();
    const updated = snapshot.zones.find((zone) => zone.id === zoneId)?.objectives
      .find((entry) => entry.id === objectiveId);
    if (!updated) throw new Error(`Defended objective "${zoneId}:${objectiveId}" disappeared from snapshot.`);
    return {
      activity: 'defend',
      snapshot,
      zoneId,
      objectiveId,
      realm,
      objective: updated,
      reward,
      zoneControlChanged: false,
    };
  }

  async resetCampaign(): Promise<CampaignSnapshot> {
    this.zoneControl = {};
    this.objectiveControl = {};
    this.influence = {};
    this.defenseReadyAt = {};
    this.persist();
    this.broadcast();
    return this.snapshot();
  }

  private load(): void {
    if (typeof localStorage === 'undefined') return;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as Partial<StoredCampaignState>;
      this.zoneControl = parsed.zoneControl ?? {};
      this.objectiveControl = parsed.objectiveControl ?? {};
      this.influence = parsed.influence ?? {};
      this.defenseReadyAt = parsed.defenseReadyAt ?? {};
    } catch {
      this.zoneControl = {};
      this.objectiveControl = {};
      this.influence = {};
      this.defenseReadyAt = {};
    }
  }

  private persist(): void {
    if (typeof localStorage === 'undefined') return;
    try {
      const state: StoredCampaignState = {
        version: STORAGE_VERSION,
        zoneControl: this.zoneControl,
        objectiveControl: this.objectiveControl,
        influence: this.influence,
        defenseReadyAt: this.defenseReadyAt,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* local persistence is optional */
    }
  }

  private broadcast(): void {
    for (const sub of this.subs) {
      sub.cb(this.snapshot(sub.currentZoneId));
    }
  }

  private snapshot(currentZoneId?: string | null): CampaignSnapshot {
    return buildCampaignSnapshot(
      currentZoneId,
      this.zoneControl,
      this.objectiveControl,
      this.influence,
      this.defenseReadyAt,
    );
  }
}
