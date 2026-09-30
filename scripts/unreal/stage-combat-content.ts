import { readFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { buildContentManifest, validateContentManifest, type ContentManifest } from './export-content';
import { canonicalJson, sha256 } from './content-contract';
import { stageDevelopmentContent } from './stage-content';
import { isMain, repoRoot } from './toolchain';

/** Preserve the installed world's exact source revision; update baseline abilities only. */
export function composeCombatContent(installed: ContentManifest, current: ContentManifest): ContentManifest {
  validateContentManifest(installed); validateContentManifest(current);
  if (canonicalJson(installed.careers) !== canonicalJson(current.careers)) throw new Error('Class/rig roster changed; use reviewed full staging.');
  const result = structuredClone(installed);
  result.abilities = structuredClone(current.abilities);
  const abilityPages = new Map(current.wiki.pages.filter(page => page.id.startsWith('ability-')).map(page => [page.id, page]));
  result.wiki.pages = result.wiki.pages.map(page => structuredClone(abilityPages.get(page.id) ?? page));
  const sources = new Map(result.source.files.map(file => [file.path, file]));
  for (const file of current.source.files) if (file.path.startsWith('shared/game/abilities/')) sources.set(file.path, file);
  result.source.files = [...sources.values()].sort((a, b) => a.path.localeCompare(b.path));
  result.source.sha256 = sha256(canonicalJson(result.source.files));
  const { source: _, ...data } = result;
  result.source.contentSha256 = sha256(canonicalJson(data));
  validateContentManifest(result);
  return result;
}

if (isMain(import.meta.url)) {
  try {
    const filename = path.join(repoRoot, 'unreal/AegisWar/Content/Migration/content.json');
    const previous = await readFile(filename, 'utf8');
    const installed = JSON.parse(previous) as ContentManifest;
    const current = await buildContentManifest();
    const next = composeCombatContent(installed, current);
    const output = path.join(repoRoot, 'artifacts/unreal/combat-stage', `${Date.now()}`);
    await mkdir(output, { recursive: true });
    await writeFile(path.join(output, 'previous-content.json'), previous);
    const world = await readFile(path.join(path.dirname(filename), 'world-visuals.json'), 'utf8');
    await writeFile(path.join(output, 'previous-world-visuals.json'), world);
    // Existing map, package and source-model guards remain mandatory.
    await stageDevelopmentContent(next, repoRoot);
    await writeFile(path.join(output, 'receipt.json'), canonicalJson({ developmentOnly: true, scope: 'baseline-abilities',
      installedSource: installed.source.sha256, abilitySource: current.source.sha256,
      resultSource: next.source.sha256, resultContent: next.source.contentSha256, mapsUnchanged: true }));
    console.log(`Staged baseline combat with installed maps preserved; backup and provenance: ${output}`);
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}
