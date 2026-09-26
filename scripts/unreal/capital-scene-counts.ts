import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

interface ActorState { tags: string[]; components: { class: string; mesh?: string | null }[] }
interface ActorRecord { package: string; actor: string; state: ActorState; zone?: string }

export function countEditableCapital(states: ActorState[]) {
  const ids = new Set<string>(), models = new Set<string>();
  for (const state of states) {
    if (!state.tags.includes('WarCapitalBuilding')) continue;
    const identities = state.tags.filter(tag => tag.startsWith('WarWorldObject_'));
    const hashes = state.tags.filter(tag => tag.startsWith('WarModelSha256_'));
    const mesh = state.components.find(component => component.class === 'StaticMeshComponent')?.mesh;
    if (identities.length !== 1 || hashes.length !== 1 || ids.has(identities[0])
      || !/^[a-f0-9]{64}$/.test(hashes[0].slice(15)) || !mesh?.startsWith('/Game/')) {
      throw new Error('Invalid reviewed capital identity or static template.');
    }
    ids.add(identities[0]); models.add(`${mesh}:${hashes[0].slice(15)}`);
  }
  return { objects: ids.size, models: models.size };
}

/** Expanded scenes supersede the retired whole-capital builder's object totals. */
export function capitalExpansionCounts(root: string, officialMap: string) {
  const directory = path.join(root, 'artifacts/unreal/capital-expansion');
  if (!existsSync(path.join(directory, 'applied.json'))) return undefined;
  const read = (file: string) => JSON.parse(readFileSync(file, 'utf8'));
  const world = read(path.join(root, 'artifacts/unreal/world-portals/build.json'));
  if (world.map !== officialMap) throw new Error('Expansion receipts belong to another official map.');
  const applied = read(path.join(directory, 'applied.json')) as {
    packageHashes: Record<string, string>; added: ActorRecord[];
  };
  for (const [packageName, expected] of Object.entries(applied.packageHashes)) {
    if (!packageName.startsWith('/Game/') || packageName.includes('..')) throw new Error('Invalid capital package.');
    const bytes = readFileSync(path.join(root, 'unreal/AegisWar/Content', `${packageName.slice(6)}.umap`));
    if (createHash('sha256').update(bytes).digest('hex') !== expected) throw new Error('Capital changed after authoring verification.');
  }
  const baseline = read(path.join(directory, 'baseline.json')).aegis_capital.actors as {
    package: string; name: string; state: ActorState;
  }[];
  const replacementFile = path.join(directory, 'replacements.json');
  const replacements = existsSync(replacementFile) ? read(replacementFile).edits as {
    package: string; actor: string; after: ActorState;
  }[] : [];
  const edited = new Map(replacements.map(row => [`${row.package}|${row.actor}`, row.after]));
  return countEditableCapital([
    ...baseline.map(row => edited.get(`${row.package}|${row.name}`) ?? row.state),
    ...applied.added.filter(row => row.zone === 'aegis_capital').map(row => row.state),
  ]);
}
