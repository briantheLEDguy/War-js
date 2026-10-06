import { describe, expect, it } from 'vitest';
import { mkdtemp, readFile, rename, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { FileCampaignRepository } from '../server/persistence';
import { createCampaign } from '../shared/orvr/index';

describe('atomic campaign replacement under file contention', () => {
  async function fixture(replace: typeof rename) {
    const directory = await mkdtemp(join(tmpdir(), 'war-campaign-contention-'));
    const filename = join(directory, 'campaign.json');
    const repository = new FileCampaignRepository(filename, replace);
    await repository.load();
    const state = createCampaign();
    await repository.commit(0, state);
    const original = await readFile(filename);
    return { filename, repository, original, state,
      async close() { await repository.close(); await rm(directory, { recursive: true, force: true }); } };
  }

  it('retries sharing violations while preserving the complete old and pending checkpoints', async () => {
    let value: Awaited<ReturnType<typeof fixture>>, failures = 0;
    const codes = ['EPERM', 'EBUSY', 'EACCES'];
    value = await fixture(async (from, to) => {
      if (value && failures < codes.length) {
        expect(await readFile(to)).toEqual(value.original);
        const pending = JSON.parse(await readFile(from, 'utf8'));
        expect(pending.revision).toBe(2);
        expect(pending.state.id).toBe('replacement');
        throw Object.assign(new Error('Reader holds the old checkpoint'), { code: codes[failures++] });
      }
      await rename(from, to);
    });
    try {
      expect(await value.repository.commit(1, { ...value.state, id: 'replacement' })).toBe(2);
      expect(failures).toBe(3);
      expect(JSON.parse(await readFile(value.filename, 'utf8')).revision).toBe(2);
      await expect(value.repository.commit(1, value.state)).rejects.toThrow(/revision mismatch/);
    } finally { await value.close(); }
  });

  it('bounds retries, retains pending bytes and keeps the revision unchanged after failure', async () => {
    let blocked = false, failures = 0;
    const error = Object.assign(new Error('Persistent sharing violation'), { code: 'EPERM' });
    const value = await fixture(async (from, to) => {
      if (blocked) { failures++; throw error; }
      await rename(from, to);
    });
    try {
      blocked = true;
      await expect(value.repository.commit(1, { ...value.state, id: 'replacement' })).rejects.toBe(error);
      expect(failures).toBe(21);
      expect(await readFile(value.filename)).toEqual(value.original);
      expect(JSON.parse(await readFile(`${value.filename}.${process.pid}.tmp`, 'utf8')).revision).toBe(2);
      blocked = false;
      expect(await value.repository.commit(1, value.state)).toBe(2);
    } finally { await value.close(); }
  });

  it('does not retry unrelated storage errors or replace the durable checkpoint', async () => {
    let blocked = false, failures = 0;
    const error = Object.assign(new Error('Storage failure'), { code: 'EIO' });
    const value = await fixture(async (from, to) => {
      if (blocked) { failures++; throw error; }
      await rename(from, to);
    });
    try {
      blocked = true;
      await expect(value.repository.commit(1, value.state)).rejects.toBe(error);
      expect(failures).toBe(1);
      expect(await readFile(value.filename)).toEqual(value.original);
    } finally { await value.close(); }
  });
});
