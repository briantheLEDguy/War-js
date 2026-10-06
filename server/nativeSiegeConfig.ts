import { randomBytes } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { verifyFullCapitalSiege } from './scenarios/city-content';
import type { NativeSiegeOptions } from './nativeSiege';

/** Bootstrap keys are host-only files; runtime admission still requires current native content proof. */
export function nativeSiegeConfiguration(repository: string): { options: NativeSiegeOptions; publish: (url: string) => void } {
  const directory = path.join(repository, 'unreal/AegisWar/Saved/CampaignSiege');
  mkdirSync(directory, { recursive: true });
  const keyFile = path.join(directory, 'bootstrap-key');
  const key = existsSync(keyFile) ? readFileSync(keyFile, 'utf8').trim() : randomBytes(32).toString('hex');
  if (!/^[a-f0-9]{64}$/.test(key)) throw new Error('Invalid private native siege bootstrap key.');
  if (!existsSync(keyFile)) writeFileSync(keyFile, key, { mode: 0o600, flag: 'wx' });
  return {
    options: { bootstrapKey: key, verifyContent: () => verifyFullCapitalSiege(repository) },
    publish: url => writeFileSync(path.join(directory, 'host.json'), JSON.stringify({ url, key, hostId: 'live-aegis' }), { mode: 0o600, flush: true }),
  };
}
