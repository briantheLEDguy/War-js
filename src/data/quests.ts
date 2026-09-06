import type { CampaignRealm } from './campaign';
import { playerRealmForRace, type PlayableRace } from './careers';
import type { CharacterState, QuestDefinition, QuestProgress } from '../services/types';

interface ExpeditionRoute {
  realm: CampaignRealm;
  questPrefix: string;
  capitalZoneId: string;
  dispatchNpcId: string;
  fieldZoneId: string;
  fieldName: string;
  shortName: string;
  officerName: string;
  captainName: string;
  enemyKeepGuard: string;
  nextZoneName: string;
}

/** Aegis quest and objective IDs remain stable so existing saves keep their progress. */
export const QUESTS: QuestDefinition[] = [
  ...expeditionQuests({
    realm: 'aegis',
    questPrefix: 'dawnline',
    capitalZoneId: 'aegis_capital',
    dispatchNpcId: 'quest-1',
    fieldZoneId: 'brightfen_approach',
    fieldName: 'Brightfen Approach',
    shortName: 'Brightfen',
    officerName: 'Ari Vell',
    captainName: 'Brightfen Field Captain',
    enemyKeepGuard: 'Riftbound Keep Guard',
    nextZoneName: 'Glassriver Ford',
  }),
  ...expeditionQuests({
    realm: 'riftbound',
    questPrefix: 'cinderfen',
    capitalZoneId: 'riftspire_capital',
    dispatchNpcId: 'riftspire_dispatch',
    fieldZoneId: 'cinderfen_outskirts',
    fieldName: 'Cinderfen Outskirts',
    shortName: 'Cinderfen',
    officerName: 'Dren Voss',
    captainName: 'Cinderfen Field Captain',
    enemyKeepGuard: 'Aegis Keep Guard',
    nextZoneName: 'Bleakroot Causeway',
  }),
];

function expeditionQuests(route: ExpeditionRoute): QuestDefinition[] {
  const fieldOfficerId = `${route.fieldZoneId}_dispatch`;
  const fieldHandoff = {
    realm: route.realm,
    giverNpcId: fieldOfficerId,
    giverZoneId: route.fieldZoneId,
    turninNpcId: fieldOfficerId,
    turninZoneId: route.fieldZoneId,
  };
  const scoutingId = `${route.questPrefix}-01-scouting`;
  const guardsId = `${route.questPrefix}-02-guards`;
  const captainId = `${route.questPrefix}-03-captain`;
  return [
    {
      ...fieldHandoff,
      id: scoutingId,
      title: `Scouts of ${route.shortName}`,
      description: `Take the capital gate marked ${route.fieldName}, a Tier 1 frontier. Defeat four Campaign Raiders there, then report to ${route.officerName} at the field camp. Your first expedition stays in this zone.`,
      minLevel: 1,
      giverNpcId: route.dispatchNpcId,
      giverZoneId: route.capitalZoneId,
      objectives: [{
        id: 'kill-raiders',
        description: `Defeat Campaign Raiders in ${route.fieldName}`,
        killTarget: 'Campaign Raider',
        zoneId: route.fieldZoneId,
        required: 4,
      }],
      reward: {
        xp: 150,
        gold: 8,
        items: [{ key: 'potion_health', name: 'Health Potion', qty: 3 }],
      },
    },
    {
      ...fieldHandoff,
      id: guardsId,
      title: `The ${route.shortName} Standards`,
      description: `Clear the guards and raiders around the field standards in ${route.fieldName}. Return to ${route.officerName} at the camp for supplies.`,
      minLevel: 1,
      prereqQuestId: scoutingId,
      objectives: [
        { id: 'kill-guards', description: 'Defeat Objective Guards', killTarget: 'Objective Guard', zoneId: route.fieldZoneId, required: 2 },
        { id: 'kill-raiders-2', description: 'Defeat Campaign Raiders', killTarget: 'Campaign Raider', zoneId: route.fieldZoneId, required: 3 },
      ],
      reward: {
        xp: 260,
        gold: 15,
        items: [
          { key: 'potion_mana', name: 'Mana Potion', qty: 3 },
          { key: 'bread', name: 'Hunk of Bread', qty: 2 },
        ],
      },
    },
    {
      ...fieldHandoff,
      id: captainId,
      title: `The ${route.shortName} Captain`,
      description: `The ${route.captainName} commands the raiders behind the keeps. Defeat this captain in ${route.fieldName}, then return to ${route.officerName}.`,
      minLevel: 2,
      prereqQuestId: guardsId,
      objectives: [{
        id: 'kill-captain',
        description: `Defeat the ${route.captainName}`,
        killTarget: route.captainName,
        zoneId: route.fieldZoneId,
        required: 1,
      }],
      reward: {
        xp: 400,
        gold: 25,
        items: [
          { key: 'potion_health', name: 'Health Potion', qty: 3 },
          { key: 'potion_mana', name: 'Mana Potion', qty: 3 },
        ],
      },
    },
    {
      ...fieldHandoff,
      id: `${route.questPrefix}-04-keep`,
      title: `Finish the ${route.shortName} Expedition`,
      description: `Defeat a ${route.enemyKeepGuard} in ${route.fieldName}, then return to ${route.officerName} for your expedition amulet. This completes your first expedition. ${route.nextZoneName} is the next Tier 2 route when you are ready.`,
      minLevel: 3,
      prereqQuestId: captainId,
      objectives: [{
        id: 'kill-keep-guards',
        description: `Defeat a ${route.enemyKeepGuard}`,
        killTarget: route.enemyKeepGuard,
        zoneId: route.fieldZoneId,
        required: 1,
      }],
      reward: {
        xp: 650,
        gold: 60,
        items: [{
          key: 'jewel_amulet_bloodglass',
          name: `${route.shortName} Expedition Amulet`,
          qty: 1,
          kind: 'armor',
          equipSlot: 'neck',
          strengthRoll: { min: 3, max: 7 },
        }],
      },
    },
  ];
}

/** Availability is independent of location so the HUD can route to the quest giver. */
export function questAvailableToCharacter(
  quest: QuestDefinition,
  progresses: QuestProgress[],
  character: CharacterState | null,
): boolean {
  if (!character || character.level < quest.minLevel) return false;
  if (quest.realm && quest.realm !== playerRealmForRace(character.race)) return false;
  if (quest.prereqQuestId && !progresses.some((progress) =>
    progress.questId === quest.prereqQuestId && progress.status === 'completed',
  )) return false;
  const own = progresses.find((progress) => progress.questId === quest.id);
  return !own || own.status === 'available';
}

/** Old saves offered the Aegis chain to either realm; retain its progress on the equivalent route. */
export function migrateQuestProgressForRealm(
  progresses: QuestProgress[],
  race: PlayableRace,
): QuestProgress[] {
  const realm = playerRealmForRace(race);
  const statusRank: Record<QuestProgress['status'], number> = {
    available: 0, active: 1, ready_to_turn_in: 2, completed: 3,
  };
  const migrated = new Map<string, QuestProgress>();
  for (const progress of progresses) {
    const counterpartId = progress.questId.replace(/^dawnline-/, 'cinderfen-');
    const questId = realm === 'riftbound' && QUESTS_BY_ID[counterpartId]?.realm === realm
      ? counterpartId
      : progress.questId;
    const existing = migrated.get(questId);
    if (!existing) {
      migrated.set(questId, { ...progress, questId, counters: { ...progress.counters } });
      continue;
    }
    const counters = { ...existing.counters };
    for (const [objectiveId, count] of Object.entries(progress.counters)) {
      counters[objectiveId] = Math.max(counters[objectiveId] ?? 0, count);
    }
    migrated.set(questId, {
      questId,
      status: statusRank[progress.status] > statusRank[existing.status] ? progress.status : existing.status,
      counters,
    });
  }
  return [...migrated.values()].map((progress): QuestProgress => {
    const definition = QUESTS_BY_ID[progress.questId];
    const objectivesComplete = definition && definition.objectives.length > 0 &&
      definition.objectives.every((objective) =>
        (progress.counters[objective.id] ?? 0) >= objective.required,
      );
    // Complementary copies can finish a quest during the merge without another kill event.
    return progress.status === 'active' && objectivesComplete
      ? { ...progress, status: 'ready_to_turn_in' }
      : progress;
  });
}

/** O(1) lookup by quest id. */
export const QUESTS_BY_ID: Record<string, QuestDefinition> =
  Object.fromEntries(QUESTS.map((q) => [q.id, q]));

/** All quests offered by a given NPC (any status). */
export function questsByGiver(npcId: string): QuestDefinition[] {
  return QUESTS.filter((q) => q.giverNpcId === npcId);
}

/** All quests returned-to at a given NPC. Falls back to giver. */
export function questsByTurnIn(npcId: string): QuestDefinition[] {
  return QUESTS.filter((q) => (q.turninNpcId ?? q.giverNpcId) === npcId);
}
