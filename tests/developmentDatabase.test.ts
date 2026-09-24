import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';
import { randomUUID } from 'node:crypto';

describe('development collaboration database', () => {
  let db: PGlite;
  const owner = randomUUID(), alice = randomUUID(), bob = randomUUID(), pending = randomUUID();
  const draft = randomUUID(), version = randomUUID(), run = randomUUID(), server = randomUUID();
  const apply = (actor: string, action: string, body: unknown, request = randomUUID()) => db.query<{ result: any }>(
    'select public.dev_apply($1,$2,$3,$4) result', [actor, request, action, JSON.stringify(body)]);
  const claim = (serverId = server, epoch = 0) => db.query<{ result: any }>(
    'select public.dev_claim_run($1,$2,$3) result', [run, serverId, epoch]);
  beforeAll(async () => {
    db = await PGlite.create();
    await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
      create schema auth; create table auth.users(id uuid primary key);
      alter default privileges in schema public grant all on tables to service_role, anon, authenticated;
      alter default privileges in schema public grant all on sequences to service_role, anon, authenticated;
      grant usage on schema public to anon, authenticated, service_role;`);
    for (const id of [owner, alice, bob, pending]) await db.query('insert into auth.users values($1)', [id]);
    await db.exec(await readFile('supabase/migrations/20260923104040_development_collaboration.sql', 'utf8'));
    await db.exec('set role service_role');
    for (const [id, status, role] of [[owner,'approved','owner'],[alice,'approved','developer'],
      [bob,'approved','developer'],[pending,'pending','developer']]) {
      await db.query('insert into public.dev_members(user_id,github_id,status,role) values($1,$2,$3,$4)', [id,id,status,role]);
    }
  }, 30_000);
  afterAll(async () => { await db?.close(); });
  it('atomically saves once, rejects altered retries, stale revisions, pending accounts and cross-owner writes', async () => {
    const request = randomUUID(), body = { id: draft, revision: 0, document: { inventory: ['hammer'] } };
    expect((await apply(alice,'draft.save',body,request)).rows[0].result.revision).toBe(1);
    expect((await apply(alice,'draft.save',body,request)).rows[0].result.revision).toBe(1);
    await expect(apply(alice,'draft.save',{...body, revision: 1},request)).rejects.toThrow('Request identity reused');
    await expect(apply(alice,'draft.save',body)).rejects.toThrow('Revision conflict');
    await expect(apply(bob,'draft.save',{...body, revision: 1})).rejects.toThrow('ownership');
    await expect(apply(pending,'draft.save',{...body, id:randomUUID()})).rejects.toThrow('access required');
    expect((await db.query('select * from public.dev_audit')).rows).toHaveLength(1);
  });
  it('publishes immutable snapshots and forks without altering the source', async () => {
    await apply(alice,'version.publish',{id:version,sourceId:draft,revision:1,name:'Arena',buildId:'build',contentId:'content'});
    await expect(db.query("update public.dev_versions set name='tampered'")).rejects.toThrow('permission denied');
    await expect(db.query('delete from public.dev_versions')).rejects.toThrow('permission denied');
    const fork = randomUUID();
    await apply(bob,'version.fork',{id:fork,sourceId:version});
    await apply(bob,'draft.save',{id:fork,revision:1,document:{inventory:[]}});
    expect((await db.query<{document:any}>('select document from public.dev_versions')).rows[0].document.inventory).toEqual(['hammer']);
    await apply(alice,'run.create',{id:run,sourceId:version});
  });
  it('fences competing and expired server writers and atomically checkpoints run state', async () => {
    expect((await claim()).rows[0].result.epoch).toBe(1);
    await expect(claim(randomUUID())).rejects.toThrow('already claimed');
    const checkpoint = {id:run,revision:0,serverId:server,epoch:1,document:{world:'edited'}};
    await apply(alice,'run.checkpoint',checkpoint);
    await db.query("update public.dev_runs set lease_until=now()-interval '1 second' where id=$1",[run]);
    await expect(apply(alice,'run.checkpoint',{...checkpoint, revision:1})).rejects.toThrow('Writer lease');
    expect((await claim()).rows[0].result.epoch).toBe(2);
    await expect(apply(alice,'run.checkpoint',{...checkpoint, revision:1})).rejects.toThrow('Writer lease');
  });
  it('consumes tickets exactly once and binds ownership, build, run and membership generation', async () => {
    const issue = (digest: string, build='build') => db.query('select public.dev_issue_ticket($1,$2,$3,$4,$5,$6)',
      [alice,run,draft,digest,build,'content']);
    const consume = (digest:string, runId=run) => db.query('select public.dev_consume_ticket($1,$2,$3,$4)',[digest,runId,server,2]);
    await expect(consume('f'.repeat(64))).rejects.toThrow('Invalid join');
    await expect(db.query('select public.dev_issue_ticket($1,$2,$3,$4,$5,$6)',
      [bob,run,draft,'e'.repeat(64),'build','content'])).rejects.toThrow('ownership');
    await issue('c'.repeat(64));
    await db.query("update public.dev_join_tickets set expires_at=now()-interval '1 second' where digest=$1",['c'.repeat(64)]);
    await expect(consume('c'.repeat(64))).rejects.toThrow('Invalid join');
    await expect(issue('a'.repeat(64),'wrong')).rejects.toThrow('Incompatible');
    await issue('a'.repeat(64));
    await expect(consume('a'.repeat(64),randomUUID())).rejects.toThrow('Invalid join');
    await consume('a'.repeat(64));
    await expect(consume('a'.repeat(64))).rejects.toThrow('Invalid join');
    await issue('b'.repeat(64));
    await expect(db.query('select public.dev_set_member($1,$2,$3)',[bob,alice,'revoked'])).rejects.toThrow('Owner');
    await db.query('select public.dev_set_member($1,$2,$3)',[owner,alice,'revoked']);
    await expect(consume('b'.repeat(64))).rejects.toThrow('revoked');
    await db.query('select public.dev_set_member($1,$2,$3)',[owner,alice,'approved']);
    await expect(consume('b'.repeat(64))).rejects.toThrow('revoked');
  });
  it('rejects direct client access and service attempts to alter receipts', async () => {
    await expect(db.query("update public.dev_receipts set result='{}'")).rejects.toThrow('permission denied');
    for (const role of ['anon','authenticated']) {
      await db.exec(`reset role; set role ${role}`);
      await expect(db.query('select * from public.dev_drafts')).rejects.toThrow('permission denied');
      await expect(apply(alice,'draft.save',{})).rejects.toThrow('permission denied');
      await expect(db.query("update public.dev_members set role='owner'")).rejects.toThrow('permission denied');
    }
    await db.exec('reset role; set role service_role');
  });
  it('rolls back both the state and receipt when a transaction is interrupted before commit', async () => {
    const id=randomUUID(), request=randomUUID(), body={id,revision:0,document:{inventory:['unique-reward']}};
    await db.exec('begin');
    await apply(bob,'draft.save',body,request);
    await db.exec('rollback');
    expect((await db.query('select id from public.dev_drafts where id=$1',[id])).rows).toHaveLength(0);
    expect((await db.query('select request_id from public.dev_receipts where request_id=$1',[request])).rows).toHaveLength(0);
    await apply(bob,'draft.save',body,request);
    await apply(bob,'draft.save',body,request);
    expect((await db.query('select id from public.dev_drafts where id=$1',[id])).rows).toHaveLength(1);
  });
});
