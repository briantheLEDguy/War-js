import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import type { AddressInfo } from 'node:net';
import { afterEach, expect, test } from 'vitest';
import { canonical, requireMutation, requireRecovered, requireNativeExit, startRecoveryProxy, waitForNativeEvidence } from '../scripts/unreal/citadel-recovery-proof';

const closers: (() => Promise<void>)[] = [];
afterEach(async () => { for (const close of closers.splice(0).reverse()) await close(); });
async function authority() {
  let commits = 0; const bodies: Buffer[] = [], credentials: string[] = [];
  const server = createServer(async (request, response) => {
    const chunks: Buffer[] = []; for await (const chunk of request) chunks.push(Buffer.from(chunk));
    const body = Buffer.concat(chunks); bodies.push(body); credentials.push(request.headers.authorization ?? '');
    const value = JSON.parse(body.toString()); if (request.url?.endsWith('/replay')) commits++;
    response.writeHead(200, { 'content-type': 'application/json' }); response.end(JSON.stringify({ data: {
      version: 1, characterId: value.characterId, revision: value.baseRevision + 1, walSequence: value.walSequence,
      recoveryPending: true } }));
  });
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  closers.push(() => new Promise<void>(resolve => server.close(() => resolve())));
  return { url: `http://127.0.0.1:${(server.address() as AddressInfo).port}`, bodies, credentials, commits: () => commits };
}
const body = { hostId: 'private-proof', requestId: 'real-request', characterId: 'stable-character', baseRevision: 2, walSequence: 1,
  character: { document: { runtime: { rewards: ['a'.repeat(32)] } } } };
async function send(url: string, value = body) {
  return fetch(`${url}/native/siege/replay`, { method: 'POST', headers: { authorization: 'Bearer private-test-credential',
    'content-type': 'application/json' }, body: JSON.stringify(value) });
}
test('before-commit interruption retains the actual request without forwarding or inventing an ACK', async () => {
  const upstream = await authority(), proxy = await startRecoveryProxy(upstream.url, body.hostId); closers.push(proxy.close);
  const intercepted = proxy.arm('before_commit', body.characterId, 'a'.repeat(32));
  let received = false; const pending = send(proxy.url).then(() => { received = true; }, () => {});
  const captured = await intercepted;
  expect(captured.mode).toBe('before_commit'); expect(captured.body).toEqual(body);
  expect(captured.bytes.toString()).toBe(JSON.stringify(body)); expect(upstream.commits()).toBe(0);
  expect(captured.row.forwarded).toBe(false); expect(captured.row.responseStatus).toBeUndefined(); expect(received).toBe(false);
  await proxy.close(); closers.pop(); await pending;
});
test('committed-before-ACK interruption forwards unchanged bytes and observes the real ACK without sending it to native', async () => {
  const upstream = await authority(), proxy = await startRecoveryProxy(upstream.url, body.hostId); closers.push(proxy.close);
  const intercepted = proxy.arm('after_commit', body.characterId, 'a'.repeat(32));
  let received = false; const pending = send(proxy.url).then(() => { received = true; }, () => {});
  const captured = await intercepted;
  expect(upstream.commits()).toBe(1); expect(upstream.bodies[0].toString()).toBe(JSON.stringify(body));
  expect(upstream.credentials).toEqual(['Bearer private-test-credential']); expect(received).toBe(false);
  expect(captured.row).toMatchObject({ forwarded: true, responseStatus: 200,
    ack: { version: 1, characterId: body.characterId, revision: 3, walSequence: 1, recoveryPending: true } });
  expect(JSON.stringify(proxy.rows)).not.toContain('private-test-credential');
  await proxy.close(); closers.pop(); await pending;
});
test('normal retry responses remain transparent and another identity cannot use the private proxy', async () => {
  const upstream = await authority(), proxy = await startRecoveryProxy(upstream.url, body.hostId); closers.push(proxy.close);
  expect((await send(proxy.url)).status).toBe(200); expect(upstream.commits()).toBe(1);
  expect((await send(proxy.url, { ...body, hostId: 'another-host' })).status).toBe(400);
  expect(upstream.commits()).toBe(1);
  await expect(startRecoveryProxy('https://remote.example', body.hostId)).rejects.toThrow(/loopback/);
});
test('mutation and recovery validation reject missing earned receipts, rollback and unsafe native readiness', () => {
  const payload = '{"id":"actual-test-ability"}', sha256 = createHash('sha256').update(payload).digest('hex');
  const combat = { version: 1, definitions: [{ id: 'actual-test-ability', career: 'stoneguard', version: 'test-catalog', payload, sha256 }],
    statuses: [{ id: 'actual-status', abilityId: 'actual-test-ability', appliedVersion: 'test-catalog', definitionSha256: sha256, expiresAtUnixMs: 9000 }] };
  const abilities = { cooldowns: [{ id: 'actual-test-ability', expiresAtUnixMs: 19000 }] };
  const before = { id: 'target', document: { inventory: { revision: 1, characterProgression: { xp: 0, gold: 0 } },
    runtime: { version: 2, capturedAtUnixMs: 1000, rewards: [], combat, abilities } } };
  const after = { id: 'target', document: { inventory: { revision: 2, characterProgression: { xp: 25, gold: 7 } },
    runtime: { version: 2, capturedAtUnixMs: 1000, rewards: ['a'.repeat(32)], combat, abilities } } };
  const mutation = { schemaVersion: 1, attempt: 0, fixtureId: 'private', receipt: 'a'.repeat(32), mutationSucceeded: true, before, after,
    wal: { filename: 'actual-file.json', sha256: 'b'.repeat(64), requestId: 'actual-request', baseRevision: 1, walSequence: 1 },
    cast: { succeeded: true, abilityId: 'actual-test-ability', career: 'stoneguard', version: 'test-catalog', definitionSha256: sha256,
      startedAtUnixMs: 900, observedAtUnixMs: 1000, statusIds: ['actual-status'], cooldownExpiresAtUnixMs: 19000 },
    witness: { pending: true, movementHeld: true, normalized: false } };
  const expected = { fixtureId: 'private', attempt: 0, target: 'target', receipt: 'a'.repeat(32) };
  expect(() => requireMutation(mutation, expected)).not.toThrow();
  expect(() => requireMutation({ ...mutation, after: before }, expected)).toThrow(/progression/);
  expect(() => requireMutation({ ...mutation, wal: undefined }, expected)).toThrow(/exact flushed/);
  expect(() => requireMutation({ ...mutation, cast: { ...mutation.cast, cooldownExpiresAtUnixMs: 20000 } }, expected)).toThrow(/cooldown/);
  const omitted = structuredClone(mutation); omitted.after.document.runtime.combat.statuses = [];
  expect(() => requireMutation(omitted, expected)).toThrow(/catalog effect/);
  const changed = structuredClone(mutation); changed.after.document.runtime.combat.definitions[0].payload = 'edited';
  expect(() => requireMutation(changed, expected)).toThrow(/catalog effect/);
  const recovered = { heldObserved: true, character: after, witness: { pending: false, normalized: false, modelReady: true,
    sceneReady: true, physicalReady: true, combatLevel: 40 } };
  expect(() => requireRecovered(recovered, mutation)).not.toThrow();
  expect(() => requireRecovered({ ...recovered, witness: { ...recovered.witness, physicalReady: false } }, mutation)).toThrow(/readiness/);
  expect(() => requireRecovered({ ...recovered, character: before }, mutation)).toThrow();
  expect(canonical({ b: 1, a: [3, 2] })).toBe(canonical({ a: [3, 2], b: 1 }));
});

test('process evidence fails promptly for a missing executable and requires a normal final exit', async () => {
  const missing = spawn('codex-citadel-proof-nonexistent-executable', [], { windowsHide: true, stdio: 'ignore' });
  missing.on('error', () => {});
  await expect(waitForNativeEvidence(async () => undefined, missing, 30)).rejects.toThrow(/could not start/);
  const success = spawn(process.execPath, ['-e', 'process.exit(0)'], { windowsHide: true, stdio: 'ignore' });
  await expect(requireNativeExit(success, 3)).resolves.toBeUndefined();
  const failed = spawn(process.execPath, ['-e', 'process.exit(2)'], { windowsHide: true, stdio: 'ignore' });
  await expect(requireNativeExit(failed, 3)).rejects.toThrow(/normal successful exit/);
});
