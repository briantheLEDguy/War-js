import { useEffect, useState } from 'react';
import { QUESTS_BY_ID } from '../../data/quests';
import type { CharacterState, QuestProgress } from '../../services/types';
import type { EnemyState } from '../../state/gameStore';
import type { NpcState } from '../../world/NpcSpawner';
import type { CraftingStationSpawn, ZoneTrigger } from '../../world/ZoneLoader';
import { distance2d, formatDistance, questNpcStatus } from './objectiveHudData';

export type MarkerToggle = 'quests' | 'npcs' | 'crafting' | 'resources' | 'enemies' | 'exits';

export interface MapMarker {
  id: string;
  kind: MarkerToggle | 'player';
  label?: string;
  detail?: string;
  position: { x: number; y?: number; z: number };
  color: string;
  shape: 'circle' | 'square' | 'diamond' | 'triangle' | 'glyph';
  glyph?: string;
  priority?: boolean;
  edgeLabel?: string;
}

export interface ZoneExitMarker {
  id: string;
  label: string;
  targetZoneId: string;
  position: { x: number; z: number };
}

export interface CraftingMarker {
  id: string;
  label: string;
  kind: CraftingStationSpawn['kind'];
  position: { x: number; y: number; z: number };
}

export interface ResourceMarker {
  id: string;
  label: string;
  kind: string;
  available: boolean;
  position: { x: number; y: number; z: number };
}

export const DEFAULT_VISIBLE: Record<MarkerToggle, boolean> = {
  quests: true,
  npcs: true,
  crafting: true,
  resources: true,
  enemies: true,
  exits: true,
};

export const MAP_MARKER_LEGEND: Array<{ key: MarkerToggle; label: string; color: string }> = [
  { key: 'quests', label: 'Quests', color: '#ffd84a' },
  { key: 'npcs', label: 'NPCs', color: '#79b8ff' },
  { key: 'crafting', label: 'Craft', color: '#8fe08f' },
  { key: 'resources', label: 'Resources', color: '#a8d26f' },
  { key: 'enemies', label: 'Foes', color: '#d14a3a' },
  { key: 'exits', label: 'Exits', color: '#84a7ff' },
];

export function buildMarkers(input: {
  character: CharacterState | null;
  craftingStations: CraftingMarker[];
  enemies: EnemyState[];
  exits: ZoneExitMarker[];
  npcs: NpcState[];
  playerPosition: { x: number; z: number };
  quests: QuestProgress[];
  resourceNodes: ResourceMarker[];
  visible: Record<MarkerToggle, boolean>;
}): MapMarker[] {
  const activeKillTargets = activeQuestKillTargets(input.quests);
  const markers: MapMarker[] = [];

  if (input.visible.exits) {
    for (const exit of input.exits) {
      const distance = distance2d(input.playerPosition, exit.position);
      markers.push({
        id: `exit-${exit.id}`,
        kind: 'exits',
        label: exit.label,
        detail: exit.targetZoneId,
        position: exit.position,
        color: '#84a7ff',
        shape: 'triangle',
        priority: true,
        edgeLabel: formatDistance(distance),
      });
    }
  }

  for (const npc of input.npcs) {
    const status = questNpcStatus(npc.id, input.quests, input.character);
    const distance = distance2d(input.playerPosition, npc.position);
    if (input.visible.quests && status.readyCount > 0) {
      markers.push({
        id: `quest-turnin-${npc.id}`,
        kind: 'quests',
        label: npc.name,
        detail: npc.title ?? 'Quest turn-in',
        position: npc.position,
        color: '#ffd84a',
        shape: 'glyph',
        glyph: '?',
        priority: true,
        edgeLabel: formatDistance(distance),
      });
      continue;
    }
    if (input.visible.quests && status.offerCount > 0) {
      markers.push({
        id: `quest-offer-${npc.id}`,
        kind: 'quests',
        label: npc.name,
        detail: npc.title ?? 'Quest available',
        position: npc.position,
        color: '#f0d880',
        shape: 'glyph',
        glyph: '!',
        priority: true,
        edgeLabel: formatDistance(distance),
      });
      continue;
    }
    if (!input.visible.npcs) continue;
    markers.push({
      id: `npc-${npc.id}`,
      kind: 'npcs',
      label: npc.name,
      detail: npc.title ?? roleLabel(npc.role),
      position: npc.position,
      color: npcRoleColor(npc.role),
      shape: npc.role === 'guard' ? 'triangle' : 'circle',
      glyph: npcRoleGlyph(npc.role),
    });
  }

  if (input.visible.crafting) {
    for (const station of input.craftingStations) {
      const distance = distance2d(input.playerPosition, station.position);
      markers.push({
        id: `craft-${station.id}`,
        kind: 'crafting',
        label: station.label,
        detail: roleLabel(station.kind),
        position: station.position,
        color: '#8fe08f',
        shape: 'square',
        priority: true,
        edgeLabel: formatDistance(distance),
      });
    }
  }

  if (input.visible.resources) {
    for (const node of input.resourceNodes) {
      if (!node.available) continue;
      const distance = distance2d(input.playerPosition, node.position);
      markers.push({
        id: `resource-${node.id}`,
        kind: 'resources',
        label: node.label,
        detail: roleLabel(node.kind),
        position: node.position,
        color: '#a8d26f',
        shape: 'diamond',
        priority: true,
        edgeLabel: formatDistance(distance),
      });
    }
  }

  if (input.visible.enemies) {
    for (const enemy of input.enemies) {
      if (!enemy.alive) continue;
      const priority = activeKillTargets.has(enemy.name);
      markers.push({
        id: `enemy-${enemy.id}`,
        kind: 'enemies',
        label: enemy.name,
        detail: `Level ${enemy.level}`,
        position: enemy.position,
        color: priority ? '#ff705d' : '#d14a3a',
        shape: 'circle',
        priority,
        edgeLabel: priority ? formatDistance(distance2d(input.playerPosition, enemy.position)) : undefined,
      });
    }
  }

  return markers.sort((a, b) => Number(a.priority) - Number(b.priority));
}

export function npcRoleColor(role: string): string {
  switch (role) {
    case 'trainer': return '#9dd6ff';
    case 'vendor': return '#79b8ff';
    case 'banker': return '#8fe08f';
    case 'guard': return '#c6c0ad';
    case 'questgiver': return '#d4b060';
    default: return 'rgba(140, 165, 190, 0.72)';
  }
}

export function npcRoleGlyph(role: string): string | undefined {
  switch (role) {
    case 'trainer': return 'T';
    case 'vendor': return 'V';
    case 'banker': return 'B';
    case 'questgiver': return 'Q';
    default: return undefined;
  }
}

export function useZoneExitMarkers(zoneId: string | null): ZoneExitMarker[] {
  const [markers, setMarkers] = useState<ZoneExitMarker[]>([]);

  useEffect(() => {
    if (!zoneId) {
      setMarkers([]);
      return;
    }

    let cancelled = false;
    async function loadMarkers() {
      try {
        const response = await fetch(`${import.meta.env.BASE_URL}assets/maps/${zoneId}.json`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const zone = await response.json() as { zoneTriggers?: ZoneTrigger[] };
        if (cancelled) return;
        setMarkers((zone.zoneTriggers ?? []).map((trigger) => ({
          id: trigger.id,
          label: trigger.label,
          targetZoneId: trigger.targetZoneId,
          position: { x: trigger.x, z: trigger.z },
        })));
      } catch {
        if (!cancelled) setMarkers([]);
      }
    }

    void loadMarkers();
    return () => {
      cancelled = true;
    };
  }, [zoneId]);

  return markers;
}

function activeQuestKillTargets(quests: QuestProgress[]): Set<string> {
  const targets = new Set<string>();
  for (const progress of quests) {
    if (progress.status !== 'active') continue;
    const definition = QUESTS_BY_ID[progress.questId];
    if (!definition) continue;
    for (const objective of definition.objectives) {
      const current = progress.counters[objective.id] ?? 0;
      if (objective.killTarget && current < objective.required) {
        targets.add(objective.killTarget);
      }
    }
  }
  return targets;
}

function roleLabel(value: string): string {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}
