import { readdir, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import {
  CAMPAIGN_STATIC_VERSION,
  EDGES as CAMPAIGN_EDGES,
  NODES as CAMPAIGN_NODES,
} from './campaign/static-campaign-source.mjs';

const root = process.cwd();
const mapsDir = path.join(root, 'public', 'assets', 'maps');
const errors = [];
const parsedZones = new Map();
const PROFILE_KEY_RE = /^(npc|enemy)_[a-z0-9_]+$/;
const ASSET_KEY_RE = /^[a-z0-9_]+$/;

const files = (await readdir(mapsDir)).filter((file) => file.endsWith('.json'));

for (const file of files) {
  const fullPath = path.join(mapsDir, file);
  let zone;
  try {
    zone = JSON.parse(await readFile(fullPath, 'utf8'));
  } catch (err) {
    errors.push(`${file}: invalid JSON: ${err.message}`);
    continue;
  }

  if (!zone.id) errors.push(`${file}: missing zone id`);
  if (!zone.name) errors.push(`${file}: missing zone name`);
  if (zone.id) parsedZones.set(zone.id, { file, zone });
  if (!Number.isFinite(zone.size) || zone.size <= 0) errors.push(`${file}: invalid zone size`);
  if (!Number.isInteger(zone.segments) || zone.segments <= 0) errors.push(`${file}: invalid terrain segments`);

  validateArray(file, zone.props, 'props');
  validateArray(file, zone.enemies, 'enemies');
  validateArray(file, zone.npcs ?? [], 'npcs');
  validateArray(file, zone.paths ?? [], 'paths');
  validateArray(file, zone.biomeKits ?? [], 'biomeKits');
  validateArray(file, zone.zoneTriggers ?? [], 'zoneTriggers');
  validateArray(file, zone.resourceNodes ?? [], 'resourceNodes');
  validateArray(file, zone.rvrObjectives ?? [], 'rvrObjectives');
  validateWorldLife(file, zone);

  for (const [index, prop] of (zone.props ?? []).entries()) {
    validateFinite(file, `props[${index}].x`, prop.x);
    validateFinite(file, `props[${index}].z`, prop.z);
    if (prop.model && !/^[a-z0-9_\-./]+\.glb$/i.test(prop.model)) {
      errors.push(`${file}: props[${index}].model is not a fallback-safe GLB filename`);
    }
    if (prop.interaction) {
      if (!prop.interaction.id) errors.push(`${file}: props[${index}].interaction missing id`);
      if (prop.interaction.type !== 'gate' && prop.interaction.type !== 'house_portal') {
        errors.push(`${file}: props[${index}].interaction.type must be gate or house_portal`);
      }
      if (
        prop.interaction.type === 'house_portal' &&
        prop.interaction.interiorVariant !== 'small' &&
        prop.interaction.interiorVariant !== 'large'
      ) {
        errors.push(`${file}: props[${index}].interaction.interiorVariant must be small or large`);
      }
      validatePositive(file, `props[${index}].interaction.maxDistance`, prop.interaction.maxDistance ?? 1);
    }
    for (const [colliderIndex, collider] of (prop.colliders ?? []).entries()) {
      validatePositive(file, `props[${index}].colliders[${colliderIndex}].width`, collider.width);
      validatePositive(file, `props[${index}].colliders[${colliderIndex}].depth`, collider.depth);
      validateColliderVerticalBounds(file, `props[${index}].colliders[${colliderIndex}]`, collider);
      if (collider.blocksWhen && collider.blocksWhen !== 'always' && collider.blocksWhen !== 'closed') {
        errors.push(`${file}: props[${index}].colliders[${colliderIndex}].blocksWhen must be always or closed`);
      }
      if (collider.blocksWhen === 'closed' && !collider.interactionId) {
        errors.push(`${file}: props[${index}].colliders[${colliderIndex}] closes without interactionId`);
      }
    }
    for (const [surfaceIndex, surface] of (prop.walkableSurfaces ?? []).entries()) {
      validatePositive(file, `props[${index}].walkableSurfaces[${surfaceIndex}].width`, surface.width);
      validatePositive(file, `props[${index}].walkableSurfaces[${surfaceIndex}].depth`, surface.depth);
      if (surface.axis && surface.axis !== 'x' && surface.axis !== 'z') {
        errors.push(`${file}: props[${index}].walkableSurfaces[${surfaceIndex}].axis must be x or z`);
      }
    }
  }

  for (const [index, pathDef] of (zone.paths ?? []).entries()) {
    validatePositive(file, `paths[${index}].width`, pathDef.width);
    if (!Array.isArray(pathDef.points) || pathDef.points.length < 2) {
      errors.push(`${file}: paths[${index}] needs at least two points`);
    }
  }

  for (const [index, npc] of (zone.npcs ?? []).entries()) {
    if (!npc.id) errors.push(`${file}: npcs[${index}] missing id`);
    if (!npc.name) errors.push(`${file}: npcs[${index}] missing name`);
    validateFinite(file, `npcs[${index}].x`, npc.x);
    validateFinite(file, `npcs[${index}].z`, npc.z);
    validateProfileKey(file, `npcs[${index}].characterProfileKey`, npc.characterProfileKey);
    if (!npc.characterProfileKey && !npc.model) {
      errors.push(`${file}: npcs[${index}] missing characterProfileKey or model`);
    }
  }

  for (const [index, enemy] of (zone.enemies ?? []).entries()) {
    if (!enemy.id) errors.push(`${file}: enemies[${index}] missing id`);
    if (!enemy.name) errors.push(`${file}: enemies[${index}] missing name`);
    validateFinite(file, `enemies[${index}].x`, enemy.x);
    validateFinite(file, `enemies[${index}].z`, enemy.z);
    validateProfileKey(file, `enemies[${index}].characterProfileKey`, enemy.characterProfileKey);
    if (enemy.assetKey && !ASSET_KEY_RE.test(enemy.assetKey)) {
      errors.push(`${file}: enemies[${index}].assetKey is not a safe asset key`);
    }
    if (!enemy.characterProfileKey && !enemy.assetKey && !enemy.model) {
      errors.push(`${file}: enemies[${index}] missing characterProfileKey, assetKey, or model`);
    }
  }

  for (const [index, node] of (zone.resourceNodes ?? []).entries()) {
    if (!node.id) errors.push(`${file}: resourceNodes[${index}] missing id`);
    if (!node.label) errors.push(`${file}: resourceNodes[${index}] missing label`);
    if (!node.kind) errors.push(`${file}: resourceNodes[${index}] missing kind`);
    if (!node.professionId) errors.push(`${file}: resourceNodes[${index}] missing professionId`);
    validateFinite(file, `resourceNodes[${index}].x`, node.x);
    validateFinite(file, `resourceNodes[${index}].z`, node.z);
    validatePositive(file, `resourceNodes[${index}].radius`, node.radius ?? 1);
    validatePositive(file, `resourceNodes[${index}].xp`, node.xp);
    validatePositive(file, `resourceNodes[${index}].respawnSeconds`, node.respawnSeconds);
    validateArray(file, node.loot, `resourceNodes[${index}].loot`);
    for (const [lootIndex, loot] of (node.loot ?? []).entries()) {
      if (!loot.key) errors.push(`${file}: resourceNodes[${index}].loot[${lootIndex}] missing key`);
      validatePositive(file, `resourceNodes[${index}].loot[${lootIndex}].qty`, loot.qty);
      validatePositive(file, `resourceNodes[${index}].loot[${lootIndex}].chance`, loot.chance);
    }
  }
}

validateZoneTriggerTargets(parsedZones);
validateCampaignMaps(parsedZones);

if (errors.length > 0) {
  console.error(errors.join('\n'));
  process.exit(1);
}

console.log(`Validated ${files.length} zone map file(s) for world editing compatibility.`);

function validateArray(file, value, label) {
  if (!Array.isArray(value)) errors.push(`${file}: ${label} must be an array`);
}

function validateFinite(file, label, value) {
  if (!Number.isFinite(value)) errors.push(`${file}: ${label} must be finite`);
}

function validatePositive(file, label, value) {
  if (!Number.isFinite(value) || value <= 0) errors.push(`${file}: ${label} must be positive`);
}

function validateColliderVerticalBounds(file, label, collider) {
  if (collider.minY !== undefined && !Number.isFinite(collider.minY)) {
    errors.push(`${file}: ${label}.minY must be finite`);
  }
  if (collider.maxY !== undefined && !Number.isFinite(collider.maxY)) {
    errors.push(`${file}: ${label}.maxY must be finite`);
  }
  if (
    collider.minY !== undefined &&
    collider.maxY !== undefined &&
    Number.isFinite(collider.minY) &&
    Number.isFinite(collider.maxY) &&
    collider.minY > collider.maxY
  ) {
    errors.push(`${file}: ${label}.minY must be less than or equal to maxY`);
  }
}

function validateProfileKey(file, label, value) {
  if (value && !PROFILE_KEY_RE.test(value)) {
    errors.push(`${file}: ${label} is not a safe NPC/enemy profile key`);
  }
}

function validateZoneTriggerTargets(zonesById) {
  for (const { file, zone } of zonesById.values()) {
    for (const [index, trigger] of (zone.zoneTriggers ?? []).entries()) {
      if (!trigger.targetZoneId) {
        errors.push(`${file}: zoneTriggers[${index}] missing targetZoneId`);
        continue;
      }
      if (!zonesById.has(trigger.targetZoneId)) {
        errors.push(`${file}: zoneTriggers[${index}] targets missing zone ${trigger.targetZoneId}.json`);
      }
    }
  }
}

function validateCampaignMaps(zonesById) {
  const campaignIds = new Set(CAMPAIGN_NODES.map((node) => node.id));
  const missing = [...campaignIds].filter((zoneId) => !zonesById.has(zoneId));
  for (const zoneId of missing) errors.push(`campaign: missing generated map ${zoneId}.json`);

  for (const zoneId of campaignIds) {
    const entry = zonesById.get(zoneId);
    if (!entry) continue;
    const { file, zone } = entry;

    if (zone.staticMapVersion !== CAMPAIGN_STATIC_VERSION) {
      errors.push(`${file}: staticMapVersion must be ${CAMPAIGN_STATIC_VERSION}`);
    }
    if (!zone.staticMapHash) errors.push(`${file}: missing staticMapHash`);
    const actualHash = hashZone(zone);
    if (zone.staticMapHash && zone.staticMapHash !== actualHash) {
      errors.push(`${file}: staticMapHash ${zone.staticMapHash} does not match ${actualHash}`);
    }
    if (!zone.campaign) errors.push(`${file}: missing campaign metadata`);
    if (!zone.rvrObjectives?.length) errors.push(`${file}: missing rvrObjectives`);

    for (const [index, prop] of (zone.props ?? []).entries()) {
      if (!prop.id) errors.push(`${file}: campaign props[${index}] missing stable id`);
      validateFinite(file, `props[${index}].rotY`, prop.rotY);
      validatePositive(file, `props[${index}].scale`, prop.scale);
    }

    const propIds = new Set((zone.props ?? []).map((prop) => prop.id).filter(Boolean));
    for (const [index, node] of (zone.resourceNodes ?? []).entries()) {
      if (node.visualPropId && !propIds.has(node.visualPropId)) {
        errors.push(`${file}: resourceNodes[${index}].visualPropId ${node.visualPropId} does not match a prop id`);
      }
    }

    for (const [index, objective] of (zone.rvrObjectives ?? []).entries()) {
      if (!objective.id) errors.push(`${file}: rvrObjectives[${index}] missing id`);
      if (!objective.type) errors.push(`${file}: rvrObjectives[${index}] missing type`);
      if (!objective.label) errors.push(`${file}: rvrObjectives[${index}] missing label`);
      validateFinite(file, `rvrObjectives[${index}].x`, objective.x);
      validateFinite(file, `rvrObjectives[${index}].z`, objective.z);
      validatePositive(file, `rvrObjectives[${index}].captureRadius`, objective.captureRadius);
    }
  }

  for (const [from, to] of CAMPAIGN_EDGES) {
    validatePortalPair(zonesById, from, to);
    validatePortalPair(zonesById, to, from);
  }
}

function validatePortalPair(zonesById, from, to) {
  const fromEntry = zonesById.get(from);
  const toEntry = zonesById.get(to);
  if (!fromEntry || !toEntry) return;
  const trigger = (fromEntry.zone.zoneTriggers ?? []).find((entry) => entry.targetZoneId === to);
  if (!trigger) {
    errors.push(`${fromEntry.file}: missing portal to ${to}`);
    return;
  }
  if (!trigger.id) errors.push(`${fromEntry.file}: portal to ${to} missing id`);
  if (!trigger.label) errors.push(`${fromEntry.file}: portal to ${to} missing label`);
  validateFinite(fromEntry.file, `zoneTriggers[${trigger.id}].x`, trigger.x);
  validateFinite(fromEntry.file, `zoneTriggers[${trigger.id}].z`, trigger.z);
  validatePositive(fromEntry.file, `zoneTriggers[${trigger.id}].radius`, trigger.radius);
  if (!trigger.targetSpawn) errors.push(`${fromEntry.file}: portal to ${to} missing targetSpawn`);

  const reverse = (toEntry.zone.zoneTriggers ?? []).some((entry) => entry.targetZoneId === from);
  if (!reverse) errors.push(`${toEntry.file}: missing reverse portal to ${from}`);
}

function validateWorldLife(file, zone) {
  const life = zone.ambientLife;
  if (life === undefined) return;
  if (!life || !Array.isArray(life.actors) || !Array.isArray(life.emitters)) {
    errors.push(`${file}: ambientLife requires actors and emitters arrays`);
    return;
  }
  if (life.actors.length > 48) errors.push(`${file}: ambientLife exceeds the 48 actor budget`);
  if (life.emitters.length > 24) errors.push(`${file}: ambientLife exceeds the 24 emitter budget`);
  const ids = new Set();
  const point = (label, value) => {
    if (!value || !Number.isFinite(value.x) || !Number.isFinite(value.z)) {
      errors.push(`${file}: ${label} requires finite x/z`);
    } else if (Math.abs(value.x) > zone.size / 2 || Math.abs(value.z) > zone.size / 2) {
      errors.push(`${file}: ${label} is outside zone bounds`);
    }
  };
  const range = (label, value, min, max) => {
    if (value !== undefined && (!Number.isFinite(value) || value < min || value > max)) {
      errors.push(`${file}: ${label} must be between ${min} and ${max}`);
    }
  };
  for (const [index, actor] of life.actors.entries()) {
    const label = `ambientLife.actors[${index}]`;
    if (!actor || !['citizen', 'guard', 'deer', 'bird'].includes(actor.kind)) {
      errors.push(`${file}: ${label} has an unsupported actor kind`);
      continue;
    }
    point(label, actor);
    if (actor.route !== undefined && !Array.isArray(actor.route)) errors.push(`${file}: ${label}.route must be an array`);
    for (const waypoint of Array.isArray(actor.route) ? actor.route : []) point(`${label}.route`, waypoint);
    range(`${label}.speed`, actor.speed, 0, 6);
    range(`${label}.pauseSeconds`, actor.pauseSeconds, 0, 60);
    range(`${label}.scale`, actor.scale, 0.25, 3);
  }
  let particles = 0;
  for (const [index, emitter] of life.emitters.entries()) {
    const label = `ambientLife.emitters[${index}]`;
    if (!emitter || !['smoke', 'embers', 'motes'].includes(emitter.kind)) {
      errors.push(`${file}: ${label} has an unsupported emitter kind`);
      continue;
    }
    point(label, emitter);
    range(`${label}.count`, emitter.count, 1, 48);
    if (emitter.count !== undefined && !Number.isInteger(emitter.count)) errors.push(`${file}: ${label}.count must be an integer`);
    range(`${label}.radius`, emitter.radius, 0.1, 20);
    range(`${label}.y`, emitter.y, -10, 50);
    particles += emitter.count ?? 12;
  }
  if (particles > 384) errors.push(`${file}: ambientLife exceeds the 384 particle budget`);
  for (const item of [...life.actors, ...life.emitters]) {
    if (!item?.id || ids.has(item.id)) errors.push(`${file}: ambientLife ids must be present and unique`);
    if (item?.id) ids.add(item.id);
  }
}

function hashZone(zone) {
  const normalized = { ...zone };
  delete normalized.staticMapHash;
  return createHash('sha256').update(JSON.stringify(normalized)).digest('hex').slice(0, 16);
}
