import { afterEach, describe, expect, it } from 'vitest';
import { mkdtempSync, readFileSync, rmSync, renameSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import type { AddressInfo } from 'node:net';
import { sharedCityFixture } from './fixtures/sharedCityContent';
import { atomicJson, authenticateCampaignHost, provisionDevelopmentPeer, startScenarioHost, verifyScenery } from '../server/scenarios/host';

const cleanups: (() => Promise<void>)[] = [];
afterEach(async () => { for (const cleanup of cleanups.splice(0)) await cleanup(); });
describe('scenario host transport', () => {
  it('rejects edited scenery or navigation after the reviewed content revision', () => {
    const directory = mkdtempSync(path.join(tmpdir(), 'aegis-scenario-content-'));
    try {
      sharedCityFixture(directory);
      expect(verifyScenery(directory)).toBe('current');
      writeFileSync(path.join(directory, 'unreal/AegisWar/Content/Capitals/Siege/AegisCapital_Siege.umap'), 'unreviewed navigation');
      expect(() => verifyScenery(directory)).toThrow('stale');
    } finally { rmSync(directory, { recursive: true, force: true }); }
  });
  it('requires a provisioned realm-bound development identity for LAN campaign hosts', () => {
    const directory = mkdtempSync(path.join(tmpdir(), 'aegis-scenario-peer-'));
    try {
      const file = provisionDevelopmentPeer(directory, 'alice', 'riftbound', 'http://192.0.2.1:8788');
      const config = JSON.parse(readFileSync(file, 'utf8'));
      expect(() => authenticateCampaignHost(directory, 'c'.repeat(64), config.key, '192.0.2.2', false)).toThrow();
      expect(() => authenticateCampaignHost(directory, 'c'.repeat(64), 'c'.repeat(64), '192.0.2.2', true)).toThrow();
      const peer = authenticateCampaignHost(directory, 'c'.repeat(64), config.key, '192.0.2.2', true);
      expect(peer?.id).toBe('alice'); expect(peer?.realm).toBe('riftbound');
      expect(() => provisionDevelopmentPeer(directory, 'alice', 'aegis', 'http://192.0.2.1:8788')).toThrow('already exists');
    } finally { rmSync(directory, { recursive: true, force: true }); }
  });
  it('retries Windows sharing violations without removing the previous recovery journal', () => {
    const directory = mkdtempSync(path.join(tmpdir(), 'aegis-scenario-journal-'));
    try {
      const file = path.join(directory, 'journal.json');
      atomicJson(file, { version: 1 });
      let attempts = 0;
      atomicJson(file, { version: 2 }, (source, destination) => {
        if (++attempts <= 2) {
          expect(JSON.parse(readFileSync(file, 'utf8')).version).toBe(1);
          throw Object.assign(new Error('Sharing violation'), { code: 'EPERM' });
        }
        renameSync(source, destination);
      });
      expect(attempts).toBe(3);
      expect(JSON.parse(readFileSync(file, 'utf8')).version).toBe(2);
      expect(() => atomicJson(file, { version: 3 }, () => { throw Object.assign(new Error('Full'), { code: 'ENOSPC' }); })).toThrow('Full');
      expect(JSON.parse(readFileSync(file, 'utf8')).version).toBe(2);
    } finally { rmSync(directory, { recursive: true, force: true }); }
  });
  it('separates host registration from player queue commands and journals recovery state', async () => {
    const directory = mkdtempSync(path.join(tmpdir(), 'aegis-scenario-test-'));
    const host = await startScenarioHost({ directory, executable: 'unused', project: 'unused', port: 0,
      bind: '127.0.0.1', advertise: '127.0.0.1', allowLan: false });
    cleanups.push(async () => { await host.close(); rmSync(directory, { recursive: true, force: true }); });
    await expect(startScenarioHost({ directory, executable: 'unused', project: 'unused', port: 0,
      bind: '127.0.0.1', advertise: '127.0.0.1', allowLan: false })).rejects.toThrow('already owns');
    const url = `http://127.0.0.1:${(host.server.address() as AddressInfo).port}`;
    const key = readFileSync(path.join(directory, 'control-key'), 'utf8');
    const call = (route: string, token: string, data?: unknown) => fetch(url + route, {
      method: data ? 'POST' : 'GET', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: data ? JSON.stringify(data) : undefined,
    });
    const character = { id: 'native-character', name: 'Native player', realm: 'riftbound', visual: '/Game/Characters/Warbrute',
      returnMap: '/Game/Capitals/Main', returnPosition: [1, 2, 3], document: { inventory: { gold: 42 } } };
    expect((await call('/host/register', 'invalid', character)).status).toBe(403);
    const registration = await (await call('/host/register', key, character)).json();
    const token = registration.data.token;
    expect((await call('/status', 'invalid')).status).toBe(401);
    expect((await call('/host/register', token, character)).status).toBe(403);
    expect((await call('/status', token)).status).toBe(200);
    await call('/command', token, { requestId: 'ready', action: 'ready' });
    const result = await (await call('/command', token, { requestId: 'queue', action: 'queue', target: 'lower_city' })).json();
    expect(result.data.phase).toBe('queued');
    const saved = JSON.parse(readFileSync(path.join(directory, 'journal.json'), 'utf8'));
    expect(saved.players['native-character'].character.document.inventory.gold).toBe(42);
    expect(JSON.stringify(result)).not.toContain(key);
    expect(JSON.stringify(result)).not.toContain(token);
  });
  it('requires explicit LAN configuration', async () => {
    await expect(startScenarioHost({ directory: 'unused', executable: 'unused', project: 'unused', port: 0,
      bind: '0.0.0.0', advertise: '192.0.2.1', allowLan: false })).rejects.toThrow('explicit');
  });
});
