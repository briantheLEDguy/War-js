import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

const root = process.cwd();
const mapsDir = path.join(root, 'public', 'assets', 'maps');
const errors = [];

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
  if (!Number.isFinite(zone.size) || zone.size <= 0) errors.push(`${file}: invalid zone size`);
  if (!Number.isInteger(zone.segments) || zone.segments <= 0) errors.push(`${file}: invalid terrain segments`);

  validateArray(file, zone.props, 'props');
  validateArray(file, zone.enemies, 'enemies');
  validateArray(file, zone.npcs ?? [], 'npcs');
  validateArray(file, zone.paths ?? [], 'paths');
  validateArray(file, zone.biomeKits ?? [], 'biomeKits');

  for (const [index, prop] of (zone.props ?? []).entries()) {
    validateFinite(file, `props[${index}].x`, prop.x);
    validateFinite(file, `props[${index}].z`, prop.z);
    if (prop.model && !/^[a-z0-9_\-./]+\.glb$/i.test(prop.model)) {
      errors.push(`${file}: props[${index}].model is not a fallback-safe GLB filename`);
    }
    for (const [colliderIndex, collider] of (prop.colliders ?? []).entries()) {
      validatePositive(file, `props[${index}].colliders[${colliderIndex}].width`, collider.width);
      validatePositive(file, `props[${index}].colliders[${colliderIndex}].depth`, collider.depth);
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
}

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
