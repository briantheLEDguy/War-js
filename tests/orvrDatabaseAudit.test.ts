import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';

describe('ORvR database boundary regression audit', () => {
  let db: PGlite;
  const owner = '30000000-0000-4000-8000-000000000003';
  beforeAll(async () => {
    db = await PGlite.create();
    await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
      create schema auth; create table auth.users(id uuid primary key);
      create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
      grant usage on schema auth, public to anon, authenticated, service_role;
      insert into auth.users values ('${owner}');`);
    await db.exec(await readFile('supabase/migrations/20260907141937_shared_orvr_authority.sql', 'utf8'));
  }, 30_000);
  afterAll(async () => { await db?.close(); });

  it('requires a verified user identity even for a caller with the authenticated database role', async () => {
    await db.exec('set role authenticated');
    await expect(db.query('select public.create_orvr_character($1,$2)', ['Unowned Recruit', 'aegis'])).rejects.toThrow('Authentication required');
    await db.exec('reset role');
    expect((await db.query('select * from public.orvr_accounts')).rows).toHaveLength(0);
  });

  it('caps recruits at eight and keeps the first committed realm locked after rejected creation', async () => {
    await db.exec('set role authenticated');
    await db.query("select set_config('request.jwt.claim.sub', $1, false)", [owner]);
    await expect(db.query('select public.create_orvr_character($1,$2)', [null, 'aegis'])).rejects.toThrow('Invalid character');
    for (let index = 0; index < 8; index += 1) await db.query('select public.create_orvr_character($1,$2)', [`Scout ${index}`, 'aegis']);
    await expect(db.query('select public.create_orvr_character($1,$2)', ['Ninth Scout', 'aegis'])).rejects.toThrow('Character limit reached');
    await expect(db.query('select public.create_orvr_character($1,$2)', ['Enemy Scout', 'riftbound'])).rejects.toThrow('another realm');
    expect((await db.query('select realm,ability_ids from public.orvr_characters')).rows).toEqual(Array.from({ length: 8 }, () => ({ realm: 'aegis', ability_ids: [] })));
  });

  it('rolls back a fresh campaign on an incorrect initial revision and a partially inserted journal on failure', async () => {
    await db.exec('reset role; set role service_role');
    const state = { id: 'audit-campaign', version: 1, supplies: 100 };
    const event = { id: 1, type: 'supplies_delivered', campaignId: state.id, activationId: 'first', data: { amount: 100 } };
    const commit = (revision: number, value: typeof state, events: unknown[]) => db.query('select public.commit_orvr_campaign($1,$2,$3,$4)', [
      state.id, revision, JSON.stringify(value), JSON.stringify(events),
    ]);
    await expect(commit(1, state, [event])).rejects.toThrow('Campaign write conflict');
    expect((await db.query('select * from public.orvr_campaigns')).rows).toHaveLength(0);
    await commit(0, state, [event]);
    await expect(commit(1, { ...state, supplies: 300 }, [{ ...event, id: 2 }, event])).rejects.toThrow('duplicate key');
    expect((await db.query('select event_id from public.orvr_events')).rows).toEqual([{ event_id: 1 }]);
    expect((await db.query('select revision,state from public.orvr_campaigns')).rows).toEqual([{ revision: 1, state }]);
    await expect(commit(1, { ...state, id: 'different' }, [])).rejects.toThrow('Invalid campaign checkpoint');
    await expect(commit(1, state, [{ ...event, id: 3, campaignId: 'another-campaign' }])).rejects.toThrow('Invalid campaign event');
    expect((await db.query('select revision from public.orvr_campaigns')).rows).toEqual([{ revision: 1 }]);
  });
});
