import { mkdir, readFile, rename, open, unlink } from 'node:fs/promises';
import { dirname } from 'node:path';
import type { SupabaseClient } from '@supabase/supabase-js';
import type { CampaignEvent, CampaignState } from '../src/shared/orvr/protocol';

export interface Checkpoint { revision: number; state: CampaignState }
export interface CampaignRepository {
  load(): Promise<Checkpoint | null>;
  commit(expectedRevision: number, state: CampaignState, events: CampaignEvent[]): Promise<number>;
  close?(): Promise<void>;
}

export class MemoryCampaignRepository implements CampaignRepository {
  checkpoint: Checkpoint | null = null;
  async load(): Promise<Checkpoint | null> { return structuredClone(this.checkpoint); }
  async commit(expectedRevision: number, state: CampaignState): Promise<number> {
    if (expectedRevision !== (this.checkpoint?.revision ?? 0)) throw new Error('Campaign write conflict.');
    this.checkpoint = { revision: expectedRevision + 1, state: structuredClone(state) };
    return this.checkpoint.revision;
  }
}

/** A single local authority uses an exclusive lease and atomic replacement, not browser storage. */
export class FileCampaignRepository implements CampaignRepository {
  private revision = 0;
  private lease: Awaited<ReturnType<typeof open>> | null = null;
  constructor(private readonly filename: string) {}
  async load(): Promise<Checkpoint | null> {
    if (this.lease) throw new Error('Campaign repository is already open.');
    await mkdir(dirname(this.filename), { recursive: true });
    const lockPath = `${this.filename}.lock`;
    try { this.lease = await open(lockPath, 'wx', 0o600); }
    catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error;
      // Serialize stale-owner inspection. An unknown or live PID must never have its lease stolen.
      const recoveryPath = `${this.filename}.recovery`;
      const recovery = await open(recoveryPath, 'wx', 0o600);
      try {
        const owner = JSON.parse(await readFile(lockPath, 'utf8')) as { pid?: number };
        if (!Number.isSafeInteger(owner.pid) || owner.pid! <= 0) throw new Error('Campaign lease owner is invalid; inspect the lock before recovery.');
        try { process.kill(owner.pid!, 0); throw new Error('Campaign already has a live writer.'); }
        catch (probe) { if ((probe as NodeJS.ErrnoException).code !== 'ESRCH') throw probe; }
        await unlink(lockPath);
        this.lease = await open(lockPath, 'wx', 0o600);
      } finally { await recovery.close(); await unlink(recoveryPath); }
    }
    try {
      await this.lease.writeFile(JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() }));
      const checkpoint = JSON.parse(await readFile(this.filename, 'utf8')) as Checkpoint;
      if (checkpoint.state?.version !== 1 || !Number.isSafeInteger(checkpoint.revision)) throw new Error('Invalid campaign checkpoint.');
      this.revision = checkpoint.revision;
      return checkpoint;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') return null;
      await this.close();
      throw error;
    }
  }
  async commit(expectedRevision: number, state: CampaignState): Promise<number> {
    if (!this.lease || this.revision !== expectedRevision) throw new Error('Campaign lease or revision mismatch.');
    const next = expectedRevision + 1;
    const temporary = `${this.filename}.${process.pid}.tmp`;
    const file = await open(temporary, 'w', 0o600);
    try { await file.writeFile(JSON.stringify({ revision: next, state })); await file.sync(); }
    finally { await file.close(); }
    await rename(temporary, this.filename);
    this.revision = next;
    return next;
  }
  async close(): Promise<void> {
    if (!this.lease) return;
    await this.lease.close();
    this.lease = null;
    await unlink(`${this.filename}.lock`);
  }
}

export class SupabaseCampaignRepository implements CampaignRepository {
  constructor(private readonly client: SupabaseClient, private readonly campaignId: string) {}
  async load(): Promise<Checkpoint | null> {
    const { data, error } = await this.client.from('orvr_campaigns').select('revision,state').eq('id', this.campaignId).maybeSingle();
    if (error) throw new Error(`Campaign load failed: ${error.message}`);
    return data ? { revision: data.revision, state: data.state as CampaignState } : null;
  }
  async commit(expectedRevision: number, state: CampaignState, events: CampaignEvent[]): Promise<number> {
    const { data, error } = await this.client.rpc('commit_orvr_campaign', {
      p_id: this.campaignId, p_expected_revision: expectedRevision, p_state: state, p_events: events,
    });
    if (error || !Number.isSafeInteger(data)) throw new Error(`Campaign commit failed: ${error?.message ?? 'invalid revision'}`);
    return data as number;
  }
}
