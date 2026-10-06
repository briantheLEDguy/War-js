import { createHash } from 'node:crypto';
import { existsSync, readFileSync, realpathSync, statSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot } from './toolchain';

export const REVIEWED_CITADEL_ENGINE_SOURCE = '/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst';

/** The one reviewed Engine parent is preserved input; fresh citadel packages always belong to /Game. */
export function requireCitadelPackageOwnership(hashes: unknown, owned: boolean): void {
  if (!hashes || typeof hashes !== 'object' || Array.isArray(hashes) || !Object.keys(hashes).length)
    throw new Error('Citadel package ownership evidence is missing.');
  for (const name of Object.keys(hashes)) if (name.startsWith('/Engine/') && (owned || name !== REVIEWED_CITADEL_ENGINE_SOURCE))
    throw new Error('Engine citadel packages are restricted to the exact preserved cloud parent; Engine ownership is forbidden.');
}

/** Resolve actual package bytes; receipt paths cannot redirect the configured content roots. */
export function requireNativePackageHash(repository: string, name: string, expected: unknown,
  engineRoot = defaultEngineRoot()): void {
  if (!/^\/(?:Game|Engine)\/[A-Za-z0-9_/-]+$/.test(name) || !/^[a-f0-9]{64}$/.test(String(expected))
    || name.slice(name.indexOf('/', 1) + 1).split('/').some(part => !part || part === '.' || part === '..'))
    throw new Error('Invalid native package identity: ' + name);
  if (name.startsWith('/Engine/') && !engineRoot) throw new Error('Actual configured Unreal Engine content root is unavailable.');
  const content = realpathSync(name.startsWith('/Game/') ? path.join(repository, 'unreal/AegisWar/Content')
    : path.join(engineRoot!, 'Engine/Content'));
  const stem = path.resolve(content, name.slice(name.startsWith('/Game/') ? 6 : 8));
  const confined = (file: string) => {
    const relative = path.relative(content, realpathSync(file));
    return relative && relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
  };
  const candidates = ['.umap', '.uasset'].map(extension => stem + extension).filter(existsSync);
  if (candidates.length !== 1 || !statSync(candidates[0]).isFile() || !confined(candidates[0]))
    throw new Error('Native package is missing, ambiguous or escaped its configured Content root: ' + name);
  if (createHash('sha256').update(readFileSync(candidates[0])).digest('hex') !== expected)
    throw new Error('Native candidate dependency changed: ' + name);
}
