import type { QuestDefinition } from '../services/types';

/**
 * Static catalog of all quests in the game. Quests form a linear chain via
 * `prereqQuestId`; completing one unlocks the next. The early chain sends an
 * Aegis recruit from Bastion of Aegis toward Dawnline Expanse
 * and escalates through campaign raiders, objective guards, and a field commander.
 */
export const QUESTS: QuestDefinition[] = [
  {
    id: 'dawnline-01-scouting',
    title: 'Scouts of the Dawnline',
    description:
      'The Aegis marshal has dispatched you toward Dawnline Expanse to investigate Riftbound pressure. Venture through the gate and break the raider camp beyond the wall.',
    minLevel: 1,
    giverNpcId: 'quest-1',
    objectives: [
      {
        id: 'kill-raiders',
        description: 'Slay Campaign Raiders',
        killTarget: 'Campaign Raider',
        required: 4,
      },
    ],
    reward: {
      xp: 150,
      gold: 8,
      items: [
        {
          key: 'sword_recruit',
          name: 'Aegis Recruit Sword',
          qty: 1,
          kind: 'weapon',
          equipSlot: 'mainHand',
          strengthRoll: { min: 1, max: 3 },
        },
      ],
    },
  },
  {
    id: 'dawnline-02-guards',
    title: 'The Objective Guards',
    description:
      'Riftbound guards are anchoring the field standards. Drive them away before the front line collapses.',
    minLevel: 1,
    giverNpcId: 'quest-1',
    prereqQuestId: 'dawnline-01-scouting',
    objectives: [
      {
        id: 'kill-guards',
        description: 'Slay Objective Guards',
        killTarget: 'Objective Guard',
        required: 2,
      },
      {
        id: 'kill-raiders-2',
        description: 'Thin the ranks of the raiders',
        killTarget: 'Campaign Raider',
        required: 3,
      },
    ],
    reward: {
      xp: 260,
      gold: 15,
      items: [
        {
          key: 'armor_chain',
          name: 'Aegis Chain Hauberk',
          qty: 1,
          kind: 'armor',
          equipSlot: 'chest',
          strengthRoll: { min: 2, max: 5 },
        },
      ],
    },
  },
  {
    id: 'dawnline-03-captain',
    title: 'The Field Captain',
    description:
      'A field captain has taken command of the raiders near the keep. Bring the captain down.',
    minLevel: 2,
    giverNpcId: 'quest-1',
    prereqQuestId: 'dawnline-02-guards',
    objectives: [
      {
        id: 'kill-captain',
        description: 'Slay the field captain',
        killTarget: 'Objective Guard',
        required: 1,
      },
    ],
    reward: {
      xp: 400,
      gold: 25,
      items: [
        {
          key: 'shield_steel',
          name: 'Steel-Rimmed Shield',
          qty: 1,
          kind: 'armor',
          equipSlot: 'offHand',
          strengthRoll: { min: 2, max: 4 },
        },
      ],
    },
  },
  {
    id: 'dawnline-04-keep',
    title: 'Break the Keep Line',
    description:
      'The Dawnline keep is the field anchor. Clear its guards and open the road deeper into the campaign.',
    minLevel: 3,
    giverNpcId: 'quest-1',
    prereqQuestId: 'dawnline-03-captain',
    objectives: [
      {
        id: 'kill-keep-guards',
        description: 'Slay keep guards',
        killTarget: 'Objective Guard',
        required: 1,
      },
    ],
    reward: {
      xp: 650,
      gold: 60,
      items: [
        {
          key: 'helm_reikguard',
          name: 'Aegis Helm',
          qty: 1,
          kind: 'armor',
          equipSlot: 'head',
          strengthRoll: { min: 3, max: 7 },
        },
        {
          key: 'sword_veteran',
          name: "Veteran's Greatsword",
          qty: 1,
          kind: 'weapon',
          equipSlot: 'mainHand',
          strengthRoll: { min: 4, max: 9 },
        },
      ],
    },
  },
];

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
