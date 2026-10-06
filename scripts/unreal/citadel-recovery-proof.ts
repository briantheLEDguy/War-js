import { spawn, type ChildProcess } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createServer, request as httpRequest } from 'node:http';
import { mkdir, readFile, readdir, writeFile, copyFile } from 'node:fs/promises';
import path from 'node:path';
import type { AddressInfo } from 'node:net';
import { campaignCandidateContentEvidence, startNativeSiegeProofAuthority } from '../../server/nativeSiegeProof';
import { citadelSiegeProofConfig } from './citadel-siege-proof';
import { requireSameSiegeContent } from './siege-content-evidence';
import { citadelCharacterRecoveryEvidence } from './citadel-recovery-evidence';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, repoRoot } from './toolchain';

const digest = (bytes: string | Buffer) => createHash('sha256').update(bytes).digest('hex');
const json = async (file: string): Promise<any> => JSON.parse((await readFile(file, 'utf8')).replace(/^\uFEFF/, ''));
export function canonical(value: any): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  const result = JSON.stringify(value); if (result === undefined) throw new Error('Non-JSON character value.'); return result;
}
const receipt = (fixture: string, suffix: string) => digest(`${fixture}:reward-${suffix}`).slice(0, 32);
const receiptKey = (value: string) => value.replaceAll('-', '').toLowerCase();
export type RecoveryInterruption = 'before_commit' | 'after_commit';
export interface RecoveryHttpRow {
  index: number; route: string; hostId: string; requestId?: string; characterId?: string;
  bodySha256: string; characterSha256?: string; baseRevision?: number; walSequence?: number;
  action?: string; scope?: string; returned?: boolean; forwarded: boolean; responseStatus?: number;
  ack?: { version?: number; characterId?: string; revision?: number; walSequence?: number; recoveryPending?: boolean };
}
export interface RecoveryIntercept { mode: RecoveryInterruption; row: RecoveryHttpRow; body: any; bytes: Buffer }

/** Transparent private loopback transport. It never fabricates an ACK or modifies a character body. */
export async function startRecoveryProxy(upstream: string, hostId: string) {
  if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(upstream)) throw new Error('Recovery proxy only forwards a private loopback authority.');
  const rows: RecoveryHttpRow[] = [], sockets = new Set<import('node:net').Socket>();
  let armed: { mode: RecoveryInterruption; target: string; receipt: string;
    resolve: (value: RecoveryIntercept) => void; reject: (reason: Error) => void } | undefined;
  const server = createServer(async (incoming, response) => {
    try {
      if (incoming.method !== 'POST' || !/^\/native\/siege\/[a-z]+$/.test(incoming.url ?? '')) {
        response.writeHead(404); response.end(); return;
      }
      const chunks: Buffer[] = []; let size = 0;
      for await (const chunk of incoming) {
        const bytes = Buffer.from(chunk); size += bytes.length;
        if (size > 16 * 1024 * 1024) throw new Error('Bounded native request exceeded the proxy limit.');
        chunks.push(bytes);
      }
      const bytes = Buffer.concat(chunks), body = JSON.parse(bytes.toString('utf8'));
      if (body.hostId !== hostId) throw new Error('Proxy request belongs to another native host.');
      const route = incoming.url!.slice('/native/siege/'.length);
      const row: RecoveryHttpRow = { index: rows.length, route, hostId, requestId: body.requestId,
        characterId: body.characterId ?? body.character?.id, bodySha256: digest(bytes), forwarded: false,
        ...(body.character ? { characterSha256: digest(canonical(body.character)) } : {}),
        ...Object.fromEntries(['baseRevision', 'walSequence', 'action', 'scope', 'returned']
          .filter(key => body[key] !== undefined).map(key => [key, body[key]])) };
      rows.push(row);
      const rewards = body.character?.document?.runtime?.rewards;
      const selected = route === 'replay' && armed && body.characterId === armed.target
        && Array.isArray(rewards) && rewards.some((value: unknown) => typeof value === 'string' && receiptKey(value) === armed!.receipt);
      const interruption = selected ? armed : undefined;
      if (interruption) armed = undefined;
      if (interruption?.mode === 'before_commit') {
        interruption.resolve({ mode: interruption.mode, row, body, bytes }); return;
      }
      row.forwarded = true;
      const forwarded = httpRequest(new URL(incoming.url!, upstream), { method: 'POST', headers: incoming.headers }, upstreamResponse => {
        const responseChunks: Buffer[] = [];
        upstreamResponse.on('data', chunk => responseChunks.push(Buffer.from(chunk)));
        upstreamResponse.on('end', () => {
          const responseBytes = Buffer.concat(responseChunks); row.responseStatus = upstreamResponse.statusCode ?? 0;
          let data: any;
          try { data = JSON.parse(responseBytes.toString('utf8')).data; } catch { /* Forward the actual malformed response unchanged. */ }
          if (data) row.ack = Object.fromEntries(['version', 'characterId', 'revision', 'walSequence', 'recoveryPending']
            .filter(key => data[key] !== undefined).map(key => [key, data[key]]));
          if (interruption) {
            if (row.responseStatus !== 200 || !data) interruption.reject(new Error('Selected real replay did not commit with an actual authority ACK.'));
            else interruption.resolve({ mode: interruption.mode, row, body, bytes });
            return;
          }
          response.writeHead(upstreamResponse.statusCode ?? 502, upstreamResponse.headers); response.end(responseBytes);
        });
      });
      forwarded.on('error', error => { interruption?.reject(error); if (!response.destroyed) { response.writeHead(502); response.end(); } });
      forwarded.end(bytes);
    } catch (error) {
      armed?.reject(error instanceof Error ? error : new Error(String(error)));
      if (!response.destroyed) { response.writeHead(400); response.end(); }
    }
  });
  server.on('connection', socket => { sockets.add(socket); socket.on('close', () => sockets.delete(socket)); });
  await new Promise<void>((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  return { url: `http://127.0.0.1:${(server.address() as AddressInfo).port}`, rows,
    arm(mode: RecoveryInterruption, target: string, transaction: string): Promise<RecoveryIntercept> {
      if (armed) throw new Error('Only one actual replay interruption may be armed.');
      return new Promise((resolve, reject) => { armed = { mode, target, receipt: receiptKey(transaction), resolve, reject }; });
    },
    async close() { armed?.reject(new Error('Recovery proxy closed.')); armed = undefined;
      for (const socket of sockets) socket.destroy(); await new Promise<void>(resolve => server.close(() => resolve())); }
  };
}

async function nativeSources(directory: string): Promise<string[]> {
  const rows = await readdir(directory, { withFileTypes: true });
  const found = await Promise.all(rows.map(row => row.isDirectory() ? nativeSources(path.join(directory, row.name))
    : /\.(cpp|h|cs)$/.test(row.name) ? [path.join(directory, row.name)] : []));
  return found.flat().sort();
}
export async function waitForNativeEvidence<T>(read: () => Promise<T | undefined>, child: ChildProcess, seconds: number): Promise<T> {
  const until = Date.now() + seconds * 1000;
  while (Date.now() < until) {
    const result = await read(); if (result !== undefined) return result;
    if (!child.pid || child.exitCode !== null || child.signalCode !== null)
      throw new Error('Native recovery process could not start or exited before its real checkpoint.');
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error('Actual native recovery checkpoint timed out; preserve its protected files.');
}
const maybeJson = async (file: string) => { try { return await json(file); } catch (error: any) { if (error.code === 'ENOENT' || error instanceof SyntaxError) return undefined; throw error; } };
async function stopped(child: ChildProcess): Promise<boolean> {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null) return false;
  await new Promise<void>((resolve, reject) => {
    child.once('exit', () => resolve());
    if (!child.kill('SIGKILL')) reject(new Error('The owned native recovery process could not be terminated.'));
  });
  return true;
}
export async function requireNativeExit(child: ChildProcess, seconds = 30): Promise<void> {
  if (!child.pid) throw new Error('Native recovery process did not start.');
  if (child.exitCode === null && child.signalCode === null) {
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => { child.removeListener('exit', exited); reject(new Error('Native recovery did not exit after its final report.')); }, seconds * 1000);
      const exited = () => { clearTimeout(timer); resolve(); }; child.once('exit', exited);
    });
  }
  if (child.exitCode !== 0 || child.signalCode !== null) throw new Error('Native recovery did not complete with a normal successful exit.');
}
export function requireMutation(record: any, expected: { fixtureId: string; attempt: number; target: string; receipt: string }) {
  if (record?.schemaVersion !== 1 || record.attempt !== expected.attempt || record.fixtureId !== expected.fixtureId
    || record.mutationSucceeded !== true || receiptKey(record.receipt ?? '') !== expected.receipt
    || record.before?.id !== expected.target || record.after?.id !== expected.target
    || record.witness?.pending !== true || record.witness.movementHeld !== true || record.witness.normalized !== false)
    throw new Error('Missing real native successful mutation and durability hold witness.');
  const before = record.before.document.inventory, after = record.after.document.inventory;
  if (after.revision !== before.revision + 1 || after.characterProgression.xp !== before.characterProgression.xp + 25
    || after.characterProgression.gold !== before.characterProgression.gold + 7
    || !record.after.document.runtime.rewards.some((value: string) => receiptKey(value) === expected.receipt))
    throw new Error('The actual native mutation does not contain its earned progression and receipt.');
  const runtime = record.after.document.runtime, cast = record.cast, wal = record.wal;
  const definition = runtime.combat?.definitions?.find((row: any) => row.sha256 === cast?.definitionSha256);
  const statuses = runtime.combat?.statuses?.filter((row: any) => row.abilityId === cast?.abilityId && row.appliedVersion === cast?.version
    && row.definitionSha256 === cast?.definitionSha256) ?? [];
  const cooldown = runtime.abilities?.cooldowns?.find((row: any) => row.id === cast?.abilityId);
  if (record.before.document.runtime.version !== 2 || runtime.version !== 2 || runtime.combat?.version !== 1
    || cast?.succeeded !== true || !definition || definition.id !== cast.abilityId || definition.career !== cast.career
    || definition.version !== cast.version || digest(definition.payload) !== definition.sha256
    || !Number.isSafeInteger(cast.startedAtUnixMs) || cast.startedAtUnixMs <= 0 || cast.startedAtUnixMs > runtime.capturedAtUnixMs
    || cast.observedAtUnixMs !== runtime.capturedAtUnixMs || !statuses.length || statuses.some((row: any) => row.expiresAtUnixMs <= runtime.capturedAtUnixMs)
    || canonical(statuses.map((row: any) => row.id).sort()) !== canonical([...(cast.statusIds ?? [])].sort())
    || !cooldown || cooldown.expiresAtUnixMs !== cast.cooldownExpiresAtUnixMs || cooldown.expiresAtUnixMs <= runtime.capturedAtUnixMs
    || !/^[a-f0-9]{64}$/.test(wal?.sha256 ?? '') || !/^[^/\\]+\.json$/.test(wal?.filename ?? '')
    || typeof wal?.requestId !== 'string' || !wal.requestId || !Number.isSafeInteger(wal.baseRevision) || wal.baseRevision < 1
    || !Number.isSafeInteger(wal.walSequence) || wal.walSequence < 1)
    throw new Error('Recovery requires a real catalog effect and cooldown in the exact flushed version-two WAL character.');
}
export function requireRecovered(record: any, mutation: any) {
  if (record?.heldObserved !== true || record.character?.id !== mutation.after.id
    || canonical(record.character.document.inventory) !== canonical(mutation.after.document.inventory)
    || canonical([...record.character.document.runtime.rewards].sort()) !== canonical([...mutation.after.document.runtime.rewards].sort())
    || record.witness?.pending !== false || record.witness.normalized !== false || record.witness.modelReady !== true
    || record.witness.sceneReady !== true || record.witness.physicalReady !== true || record.witness.combatLevel !== 40)
    throw new Error('Actual restored native character, movement protection or physical readiness differs from its original mutation.');
}

/** Three actual native processes reuse one authority identity and its original flushed WAL files. */
export async function runCitadelRecoveryProof(repository: string, map: string, executable: string) {
  const config = citadelSiegeProofConfig(repository, map);
  if (!map.endsWith('/CampaignCandidate') || config.players?.length !== 36) throw new Error('Recovery requires a prepared real live candidate.');
  const fixtureId = `recovery-${Date.now()}-${process.pid}`, hostId = `citadel-proof-${fixtureId}`, target = config.players[0];
  const directory = path.join(repository, 'unreal/AegisWar/Saved/CitadelSiegeProof', fixtureId);
  const output = path.join(repository, 'artifacts/unreal/citadel-reference/recovery-proofs', fixtureId);
  const binaryPath = path.join(repository, 'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll');
  const sourceHashes = Object.fromEntries(await Promise.all((await nativeSources(path.join(repository, 'unreal/AegisWar/Source')))
    .map(async file => [file, digest(await readFile(file))])));
  const binarySha256 = digest(await readFile(binaryPath)), mutations: any[] = [], cases: any[] = [], http: RecoveryHttpRow[][] = [], processes: any[] = [];
  const walDirectory = path.join(repository, 'unreal/AegisWar/Saved/CampaignSiege/Wal', createHash('sha1').update(hostId).digest('hex'));
  await mkdir(output, { recursive: true });
  let authority: Awaited<ReturnType<typeof startNativeSiegeProofAuthority>> | undefined;
  let proxy: Awaited<ReturnType<typeof startRecoveryProxy>> | undefined, child: ChildProcess | undefined;
  try {
    for (let attempt = 0; attempt < 3; attempt++) {
      requireSameSiegeContent(config, campaignCandidateContentEvidence(repository, map));
      if (digest(await readFile(binaryPath)) !== binarySha256) throw new Error('The compiled native binary changed between recovery attempts.');
      authority = await startNativeSiegeProofAuthority({ repositoryRoot: repository, map, fixtureId, resume: attempt !== 0 });
      proxy = await startRecoveryProxy(authority.server.httpUrl, hostId);
      const hostConfig = await json(authority.hostConfigPath);
      await writeFile(authority.hostConfigPath, JSON.stringify({ ...hostConfig, url: proxy.url }), { mode: 0o600, flush: true });
      const folder = path.join(directory, `attempt-${attempt}`); await mkdir(folder);
      const expected = await Promise.all(mutations.map(async (_record, index) => {
        const file = path.join(directory, `attempt-${index}/mutation.json`); return { path: file, sha256: digest(await readFile(file)) };
      }));
      const recovery = { version: 1, attempt, fixtureId, receiptA: receipt(fixtureId, 'a'), receiptB: receipt(fixtureId, 'b'),
        binaryPath, binarySha256, sourceHashes, expected };
      const configFile = path.join(folder, 'config.json');
      await writeFile(configFile, JSON.stringify({ ...config, recoveryOnly: true, recovery }, null, 2) + '\n');
      await copyFile(configFile, path.join(output, `config-${attempt}.json`));
      const interruption = attempt < 2 ? proxy.arm(attempt === 0 ? 'before_commit' : 'after_commit', target,
        attempt === 0 ? recovery.receiptA : recovery.receiptB) : undefined;
      interruption?.catch(() => {}); // Keep cleanup rejection handled before its later awaited checkpoint.
      const startedAt = Date.now();
      child = spawn(executable, [path.join(repository, 'unreal/AegisWar/AegisWar.uproject'), `${map}?game=/Script/AegisWar.WarGameMode`,
        '-game', '-nullrhi', '-unattended', '-nop4', '-nosound', '-nosplash', '-WarDevelopmentNetworking',
        '-WarCitadelSiegeProof', '-WarCitadelSiegeRecoveryProof', `-WarCitadelSiegeProofConfig=${configFile}`,
        `-WarCampaignSiegeHostConfig=${authority.hostConfigPath}`, `-abslog=${path.join(output, `native-${attempt}.log`)}`],
      { cwd: repository, stdio: 'ignore', windowsHide: true });
      let spawnError: Error | undefined; child.on('error', error => { spawnError = error; });
      if (attempt > 0) {
        const recovered = await waitForNativeEvidence(() => maybeJson(path.join(folder, 'recovered.json')), child, 400);
        if (spawnError) throw spawnError; requireRecovered(recovered, mutations[attempt - 1]);
        await copyFile(path.join(folder, 'recovered.json'), path.join(output, `recovered-${attempt}.json`));
        const routeRows = proxy.rows;
        const replay = routeRows.find(row => row.route === 'replay' && row.requestId === cases[attempt - 1].requestId && row.responseStatus === 200);
        const restore = routeRows.find(row => row.route === 'restore' && row.characterId === target);
        const restored = routeRows.find(row => row.route === 'restored' && row.characterId === target && row.responseStatus === 200);
        if (!replay || !restore || !restored || !(replay.index < restore.index && restore.index < restored.index)
          || replay.ack?.version !== 1 || replay.ack.characterId !== target
          || replay.ack.revision !== cases[attempt - 1].baseRevision + 1 || replay.ack.walSequence !== cases[attempt - 1].walSequence)
          throw new Error('Actual native replay, restore and readiness acknowledgment were not observed in order.');
        const files = await readdir(walDirectory);
        if (files.includes(cases[attempt - 1].walFilename)) throw new Error('Native replay ACK did not remove the original retained WAL.');
      }
      if (attempt < 2) {
        const record = await waitForNativeEvidence(() => maybeJson(path.join(folder, 'mutation.json')), child, 400);
        requireMutation(record, { fixtureId, attempt, target, receipt: attempt === 0 ? recovery.receiptA : recovery.receiptB });
        const captured = await Promise.race([interruption!, new Promise<never>((_, reject) => setTimeout(() => reject(new Error('Real native replay was not intercepted.')), 10_000))]);
        const files = await readdir(walDirectory); let wal: any, walBytes: Buffer | undefined, walFilename = '';
        for (const filename of files.filter(file => file.endsWith('.json'))) {
          const bytes = await readFile(path.join(walDirectory, filename)); const parsed = JSON.parse(bytes.toString('utf8'));
          if (parsed.hostId === hostId && parsed.body?.requestId === captured.body.requestId) { wal = parsed; walBytes = bytes; walFilename = filename; break; }
        }
        if (!walBytes || wal.schemaVersion !== 1 || canonical(wal.body) !== canonical(captured.body)
          || canonical(wal.body.character) !== canonical(record.after) || record.wal.filename !== walFilename
          || record.wal.sha256 !== digest(walBytes) || record.wal.requestId !== captured.body.requestId
          || record.wal.baseRevision !== captured.body.baseRevision || record.wal.walSequence !== captured.body.walSequence)
          throw new Error('Intercepted replay does not match the original actually flushed native WAL.');
        const checkpointBytes = await readFile(authority.checkpointPath), checkpoint = JSON.parse(checkpointBytes.toString('utf8'));
        const canonicalRecord = checkpoint.state.nativeSiegeJournal.characters[`${hostId}:${target}`];
        const committed = attempt === 1;
        if (canonicalRecord.revision !== captured.body.baseRevision + Number(committed)
          || (committed && (canonicalRecord.walSequence !== captured.body.walSequence || canonical(canonicalRecord.character) !== canonical(record.after)))
          || (!committed && canonicalRecord.walSequence >= captured.body.walSequence))
          throw new Error('The durable owning-host journal does not prove the selected real interruption boundary.');
        if (committed && (captured.row.ack?.version !== 1 || captured.row.ack.characterId !== target
          || captured.row.ack.revision !== captured.body.baseRevision + 1 || captured.row.ack.walSequence !== captured.body.walSequence))
          throw new Error('The actual withheld Node ACK does not match its durable mutation revision.');
        await writeFile(path.join(output, `wal-${attempt}.json`), walBytes, { flag: 'wx', mode: 0o600, flush: true });
        await copyFile(path.join(folder, 'mutation.json'), path.join(output, `mutation-${attempt}.json`));
        await writeFile(path.join(output, `checkpoint-${attempt}.json`), checkpointBytes, { flag: 'wx', mode: 0o600, flush: true });
        const killRequested = await stopped(child);
        if (!killRequested) throw new Error('The intended interruption was not an observed kill of the owned native process.');
        processes.push({ attempt, pid: child.pid, startedAt, endedAt: Date.now(), termination: 'SIGKILL', killRequested,
          exitCode: child.exitCode, signalCode: child.signalCode, requestId: captured.body.requestId, configSha256: digest(await readFile(configFile)) });
        cases.push({ mode: captured.mode, requestId: captured.body.requestId, baseRevision: captured.body.baseRevision,
          walSequence: captured.body.walSequence, walFilename, walSha256: digest(walBytes), nodeRevision: canonicalRecord.revision,
          nodeCommittedBeforeKill: committed, replayBodySha256: digest(captured.bytes), nativeAckWithheld: true, processKilled: true,
          nativeMutationFileSha256: digest(await readFile(path.join(folder, 'mutation.json'))) });
        mutations.push(record); child = undefined;
      } else {
        const report = await waitForNativeEvidence(() => maybeJson(path.join(folder, 'recovery-report.json')), child, 500);
        if (!report.passed || report.attempt !== 2 || report.signature !== config.signature || report.mapSha256 !== config.mapSha256
          || report.configSha256 !== digest(await readFile(configFile)) || report.returnWitnesses?.length !== 36 || report.characters?.length !== 36
          || report.returnWitnesses.some((row: any) => !row.safeReturn || row.pending || row.member || row.normalized || !row.physicalReady || !row.sceneReady))
          throw new Error('Real native recovery or validated ordinary return remained failed or incomplete.');
        const checkpointBytes = await readFile(authority.checkpointPath), checkpoint = JSON.parse(checkpointBytes.toString('utf8'));
        for (const character of report.characters) {
          const saved = checkpoint.state.nativeSiegeJournal.characters[`${hostId}:${character.id}`];
          const allowed = checkpoint.state.zones.aegis_capital.nativeSiege.safeEvacuationZones[character.realm];
          if (!saved?.returned || saved.recoveryPending || saved.character.document.zone !== character.document.zone
            || !allowed.includes(character.document.zone) || saved.scope !== 'evacuation'
            || canonical(saved.character.document.inventory) !== canonical(character.document.inventory))
            throw new Error('Native normal return is not backed by the actual durable owning-host document.');
          const leave = proxy.rows.find(row => row.route === 'membership' && row.characterId === character.id && row.action === 'leave' && row.responseStatus === 200);
          const participantReturn = proxy.rows.find(row => row.route === 'checkpoint' && row.ack?.characterId === character.id
            && row.scope === 'participant' && row.returned === true && row.responseStatus === 200);
          const evacuation = proxy.rows.find(row => row.route === 'checkpoint' && row.ack?.characterId === character.id
            && row.scope === 'evacuation' && row.returned !== true && row.responseStatus === 200);
          const safeReturn = proxy.rows.find(row => row.route === 'checkpoint' && row.ack?.characterId === character.id
            && row.scope === 'evacuation' && row.returned === true && row.responseStatus === 200);
          if (!leave || !participantReturn || !evacuation || !safeReturn
            || !(leave.index < participantReturn.index && participantReturn.index < evacuation.index && evacuation.index < safeReturn.index))
            throw new Error('Actual participant return and its later validated evacuation were not acknowledged in order.');
        }
        await copyFile(path.join(folder, 'recovery-report.json'), path.join(output, 'native-recovery-report.json'));
        await writeFile(path.join(output, `checkpoint-${attempt}.json`), checkpointBytes, { flag: 'wx', mode: 0o600, flush: true });
        await requireNativeExit(child);
        processes.push({ attempt, pid: child.pid, startedAt, endedAt: Date.now(), termination: 'normal_exit', killRequested: false,
          exitCode: child.exitCode, signalCode: child.signalCode, configSha256: digest(await readFile(configFile)) }); child = undefined;
      }
      http.push(proxy.rows); await proxy.close(); proxy = undefined; await authority.close(); authority = undefined;
    }
    await writeFile(path.join(output, 'http.json'), JSON.stringify({ schemaVersion: 1, fixtureId, hostId, attempts: http }, null, 2) + '\n');
    await writeFile(path.join(output, 'processes.json'), JSON.stringify({ schemaVersion: 1, fixtureId, hostId, attempts: processes }, null, 2) + '\n');
    const reference = async (name: string) => ({ path: path.relative(repository, path.join(output, name)).split(path.sep).join('/'),
      sha256: digest(await readFile(path.join(output, name))) });
    const evidence = { version: 1, nativeReport: await reference('native-recovery-report.json'),
      mutations: await Promise.all([0, 1].map(i => reference(`mutation-${i}.json`))),
      recovered: await Promise.all([1, 2].map(i => reference(`recovered-${i}.json`))),
      wals: await Promise.all([0, 1].map(i => reference(`wal-${i}.json`))),
      configs: await Promise.all([0, 1, 2].map(i => reference(`config-${i}.json`))),
      checkpoints: await Promise.all([0, 1, 2].map(i => reference(`checkpoint-${i}.json`))),
      http: await reference('http.json'), processes: await reference('processes.json') };
    const report = { schemaVersion: 1, passed: true, recoveryOnly: true, fixtureId, hostId, ...config,
      binaryPath, binarySha256, sourceHashes, cases, http, evidence,
      normalCharacterRecoveryVerified: true, outcomeRecoveryVerified: false, equipmentMutationVerified: false, deadIntentVerified: false,
      productionAdmission: false, steamAdmission: false, humanPlaytest: false, visualApproval: false, fullSiegeAdmission: false,
      releaseAcceptance: false, victoryAcceptance: false, conquestAcceptance: false };
    await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
    citadelCharacterRecoveryEvidence(repository, await reference('report.json'), campaignCandidateContentEvidence(repository, map));
    return { output, report };
  } catch (error) {
    await writeFile(path.join(output, 'failed.json'), JSON.stringify({ schemaVersion: 1, passed: false, recoveryOnly: true,
      proofOnly: true, fixtureId, hostId, map, cases, http: [...http, ...(proxy ? [proxy.rows] : [])],
      detail: error instanceof Error ? error.message : String(error), productionAdmission: false, fullSiegeAdmission: false }, null, 2));
    throw error;
  } finally { if (child) await stopped(child); await proxy?.close(); await authority?.close(); }
}

if (isMain(import.meta.url)) {
  const args = parseArguments(process.argv.slice(2), [], ['--map']);
  const engine = inspectToolchain(defaultEngineRoot());
  if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
  runCitadelRecoveryProof(repoRoot, args.get('--map') ?? '', engine.editorCommand)
    .then(({ output }) => console.log(JSON.stringify({ passed: true, recoveryOnly: true, output, fullSiegeAdmission: false })))
    .catch(error => { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; });
}
