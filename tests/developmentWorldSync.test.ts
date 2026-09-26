import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { PGlite } from '@electric-sql/pglite';
import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { validateWorldSync } from '../server/development/world-sync';

const row = { id: 'house', hidden: false, sourceIdentity: 'mesh:hash', transform: [0,0,0,0,0,0,1,1,1,1] };
const document = { schemaVersion: 2, zoneId: 'aegis_capital', baseline: JSON.stringify({objects:[row]}), objects:[row] };
const map = '/Game/War/Maps/crownward/Capital';
const publication = { action:'publish', map, revision:0, document };

describe('development world transport', () => {
  it('validates native transforms, provenance, object identity and map boundaries', () => {
    expect(validateWorldSync(publication)).toEqual(publication);
    expect(validateWorldSync({action:'read',map,actorId:'forged'})).toEqual({action:'read',map});
    for (const patch of [{map:'/Game/../Other'}, {map:'https://evil.example'}, {revision:0.5}, {revision:-1},
      {document:{...document,objects:[row,row]}}, {document:{...document,baseline:'broken'}},
      {document:{...document,objects:[{...row,sourceIdentity:'untrusted'}]}},
      {document:{...document,objects:[{...row,templateId:'house'}]}},
      {document:{...document,objects:[{...row,transform:[0,0,0,0,0,0,2,1,1,1]}]}},
      {document:{...document,objects:[{...row,transform:[100001,0,0,0,0,0,1,1,1,1]}]}},
      {document:{...document,objects:[{...row,transform:[0,0,0,0,0,0,1,0,1,1]}]}}]) {
      expect(()=>validateWorldSync({...publication,...patch})).toThrow();
    }
    const created = {...row,id:'gm_new',templateId:'house'};
    expect(validateWorldSync({...publication,document:{...document,objects:[row,created]}})).toBeTruthy();
    expect(()=>validateWorldSync({...publication,document:{...document,objects:[created]}})).toThrow('Missing authored');
  });
});

describe('development remote world transactions', () => {
  let db:PGlite;
  const owner=randomUUID(), developer=randomUUID(), pending=randomUUID();
  const sync=(actor:string,body:unknown,request:string|null=randomUUID()) => db.query<{result:any}>(
    'select public.dev_world_sync($1,$2,$3) result',[actor,request,JSON.stringify(body)]);
  beforeAll(async()=>{
    db=await PGlite.create();
    await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
      create schema auth; create table auth.users(id uuid primary key);
      alter default privileges in schema public grant all on tables to service_role, anon, authenticated;
      grant usage on schema public to anon,authenticated,service_role;`);
    for(const id of [owner,developer,pending]) await db.query('insert into auth.users values($1)',[id]);
    await db.exec(await readFile('supabase/migrations/20260923104040_development_collaboration.sql','utf8'));
    await db.exec(await readFile('supabase/migrations/20260925112105_development_world_sync.sql','utf8'));
    await db.exec('set role service_role');
    for(const [id,status,role] of [[owner,'approved','owner'],[developer,'approved','developer'],[pending,'pending','developer']])
      await db.query('insert into public.dev_members(user_id,github_id,status,role) values($1,$2,$3,$4)',[id,id,status,role]);
  },30000);
  afterAll(async()=>{await db?.close();});
  it('allows approved reads but only owner publication; empty remote never means applied',async()=>{
    expect((await sync(developer,{action:'read',map},null)).rows[0].result).toEqual({map,revision:0,document:null,runtimeApplied:false});
    await expect(sync(pending,{action:'read',map})).rejects.toThrow('access required');
    await expect(sync(developer,publication)).rejects.toThrow('Owner access');
    await expect(sync(owner,{...publication,action:'delete'})).rejects.toThrow('Invalid world operation');
  });
  it('publishes once, rejects changed retries and stale writes, and preserves immutable history',async()=>{
    const request=randomUUID();
    const first=(await sync(owner,publication,request)).rows[0].result;
    expect(first).toEqual({map,revision:1,runtimeApplied:false});
    expect((await sync(owner,publication,request)).rows[0].result).toEqual(first);
    await expect(sync(owner,{...publication,revision:1},request)).rejects.toThrow('reused');
    await expect(sync(owner,publication)).rejects.toThrow('Revision conflict');
    expect((await sync(developer,{action:'read',map})).rows[0].result.document).toEqual(document);
    expect((await db.query('select * from public.dev_world_versions')).rows).toHaveLength(1);
    await expect(db.query('delete from public.dev_world_versions')).rejects.toThrow('permission denied');
    await expect(db.query("update public.dev_world_versions set document='{}'" )).rejects.toThrow('permission denied');
    // Separate authored maps cannot overwrite one another even with the same zoneId.
    expect((await sync(owner,{...publication,map:map+'Siege'})).rows[0].result.revision).toBe(1);
  });
  it('rolls back state, version history and receipt together, then safely retries',async()=>{
    const request=randomUUID(),body={...publication,revision:1};
    await db.exec('begin'); await sync(owner,body,request); await db.exec('rollback');
    expect((await sync(owner,{action:'read',map})).rows[0].result.revision).toBe(1);
    expect((await db.query('select * from public.dev_receipts where request_id=$1',[request])).rows).toHaveLength(0);
    await sync(owner,body,request); await sync(owner,body,request);
    expect((await db.query('select * from public.dev_world_versions where map=$1',[map])).rows).toHaveLength(2);
  });
  it('denies direct client access and rechecks revocation before receipt replay',async()=>{
    for(const role of ['anon','authenticated']) {
      await db.exec(`reset role; set role ${role}`);
      await expect(sync(owner,{action:'read',map})).rejects.toThrow('permission denied');
      await expect(db.query('select * from public.dev_world_heads')).rejects.toThrow('permission denied');
    }
    await db.exec('reset role; set role service_role');
    const request=randomUUID(), body={...publication,revision:2};
    await sync(owner,body,request);
    await db.query("update public.dev_members set status='revoked' where user_id=$1",[owner]);
    await expect(sync(owner,body,request)).rejects.toThrow('access required');
  });
});
