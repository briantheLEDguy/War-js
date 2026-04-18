import type { QuestDefinition } from '../services/types';

/**
 * Static catalog of all quests in the game. Quests form a linear chain via
 * `prereqQuestId`; completing one unlocks the next. The early chain sends an
 * Empire recruit out through Altdorf's south gate to the Reikland encampment
 * and escalates through goblin raiders, ogres, and a warboss.
 *
 * Names and placements are kept plausible for a WAR Empire chapter — raider
 * goblins, an ogre thug, and a warboss are faithful to Reikland's invaders.
 */
export const QUESTS: QuestDefinition[] = [
  {
    id: 'reikland-01-scouting',
    title: 'Scouts of the Reikwald',
    description:
      'Wilhelm Krupp has dispatched you to the Reikwald to investigate greenskin sightings. Venture through the south gate and slay the Goblin Raiders camped beyond the wall.',
    minLevel: 1,
    giverNpcId: 'quest-1',
    objectives: [
      {
        id: 'kill-raiders',
        description: 'Slay Goblin Raiders',
        killTarget: 'Goblin Raider',
        required: 4,
      },
    ],
    reward: {
      xp: 150,
      gold: 8,
      items: [
        {
          key: 'sword_recruit',
          name: 'Reikguard Recruit Sword',
          qty: 1,
          kind: 'weapon',
          equipSlot: 'mainHand',
          strengthRoll: { min: 1, max: 3 },
        },
      ],
    },
  },
  {
    id: 'reikland-02-shamans',
    title: 'The Twisted Shamans',
    description:
      "Night Goblin Shamans are inciting the raiders. Put them to the sword before they summon something fouler.",
    minLevel: 1,
    giverNpcId: 'quest-1',
    prereqQuestId: 'reikland-01-scouting',
    objectives: [
      {
        id: 'kill-shamans',
        description: 'Slay Night Goblin Shamans',
        killTarget: 'Night Goblin Shaman',
        required: 2,
      },
      {
        id: 'kill-raiders-2',
        description: 'Thin the ranks of the raiders',
        killTarget: 'Goblin Raider',
        required: 3,
      },
    ],
    reward: {
      xp: 260,
      gold: 15,
      items: [
        {
          key: 'armor_chain',
          name: 'Reikguard Chain Hauberk',
          qty: 1,
          kind: 'armor',
          equipSlot: 'chest',
          strengthRoll: { min: 2, max: 5 },
        },
      ],
    },
  },
  {
    id: 'reikland-03-ogre',
    title: 'The Ogre Thug',
    description:
      'A hulking ogre has joined the raiders and bullies Sigmar\u2019s patrols. Bring him down.',
    minLevel: 2,
    giverNpcId: 'quest-1',
    prereqQuestId: 'reikland-02-shamans',
    objectives: [
      {
        id: 'kill-ogre',
        description: "Slay Grulg the Ogre Thug",
        killTarget: 'Grulg the Ogre Thug',
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
    id: 'reikland-04-warboss',
    title: 'Break the Warboss',
    description:
      'The greenskin warband is led by Warboss Gorfang. End him and the raiders will scatter.',
    minLevel: 3,
    giverNpcId: 'quest-1',
    prereqQuestId: 'reikland-03-ogre',
    objectives: [
      {
        id: 'kill-warboss',
        description: 'Slay Warboss Gorfang',
        killTarget: 'Warboss Gorfang',
        required: 1,
      },
    ],
    reward: {
      xp: 650,
      gold: 60,
      items: [
        {
          key: 'helm_reikguard',
          name: 'Reikguard Helm',
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
