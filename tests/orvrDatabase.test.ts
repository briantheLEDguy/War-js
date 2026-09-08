import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';

describe('ORvR PostgreSQL permissions and atomic journal', () => {
  let db: PGlite;
  const alice = '10000000-0000-4000-8000-000000000001';
  const bob = '10000000-0000-4000-8000-000000000002';
  beforeAll(async () => {
    db = await PGlite.create();
    // Supabase's Auth identity boundary is represented explicitly; no mock database queries.
    await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
      create schema auth; create table auth.users(id uuid primary key);
      create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
      grant usage on schema auth, public to anon, authenticated, service_role;
      insert into auth.users values ('${alice}'), ('${bob}');`);
    await db.exec(await readFile('supabase/migrations/20260907141937_shared_orvr_authority.sql', 'utf8'));
  }, 30_000);
  afterAll(async () => { await db?.close(); });
  const user = async (id: string) => {
    await db.exec('reset role; set role authenticated;');
    await db.query("select set_config('request.jwt.claim.sub', $1, false)", [id]);
  };
  it('allows recruit creation, isolates account rows, and rejects realm switching and direct writes', async () => {
    await user(alice);
    await db.query('select public.create_orvr_character($1,$2)', ['Lysa Vale', 'aegis']);
    await expect(db.query('select public.create_orvr_character($1,$2)', ['Lysa Vale', 'riftbound'])).rejects.toThrow('another realm');
    await expect(db.query("update public.orvr_characters set ability_ids = '{admin}'")).rejects.toThrow('permission denied');
    await user(bob);
    expect((await db.query('select * from public.orvr_characters')).rows).toHaveLength(0);
    await db.query('select public.create_orvr_character($1,$2)', ['Varr Ash', 'riftbound']);
    expect((await db.query('select realm from public.orvr_characters')).rows).toEqual([{ realm: 'riftbound' }]);
    await expect(db.query('select * from public.orvr_campaigns')).rejects.toThrow('permission denied');
    await expect(db.query("select public.commit_orvr_campaign('world',0,'{}','[]')")).rejects.toThrow('permission denied');
  });
  it('commits state plus delivery once, and rolls back both on conflict or journal failure', async () => {
    await db.exec('reset role; set role service_role;');
    const state = { id: 'test-world', version: 1, supplies: 100 };
    const event = { id: 1, campaignId: state.id, type: 'caravan_delivered', activationId: 'first', data: { supplies: 100 } };
    const commit = (revision: number, value = state, events = [event]) => db.query(
      'select public.commit_orvr_campaign($1,$2,$3,$4) as revision', [state.id, revision, JSON.stringify(value), JSON.stringify(events)],
    );
    expect((await commit(0)).rows).toEqual([{ revision: 1 }]);
    await expect(commit(0)).rejects.toThrow('Campaign write conflict');
    await expect(commit(1, { ...state, supplies: 200 })).rejects.toThrow('duplicate key');
    expect((await db.query('select revision,state from public.orvr_campaigns')).rows).toEqual([{ revision: 1, state }]);
    expect((await db.query('select * from public.orvr_events')).rows).toHaveLength(1);
    expect((await commit(1, { ...state, supplies: 200 }, [{ ...event, id: 2 }])).rows).toEqual([{ revision: 2 }]);
  });
  it('denies anonymous creation and campaign mutation', async () => {
    await db.exec('reset role; set role anon;');
    await expect(db.query("select public.create_orvr_character('Intruder','aegis')")).rejects.toThrow('permission denied');
    await expect(db.query("insert into public.orvr_events values ('test-world',3,'capture',null,'{}',now())")).rejects.toThrow('permission denied');
  });
});
