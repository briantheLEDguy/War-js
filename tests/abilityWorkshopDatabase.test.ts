import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { PGlite } from '@electric-sql/pglite';
import { baselineWorkspace } from '../shared/game/abilities/workshop/workspace';
import { catalogHash } from '../server/development/ability-workshop';

describe('ability workshop shared persistence', () => {
  let db: PGlite;
  const owner=randomUUID(), editor=randomUUID(), viewer=randomUUID(), outsider=randomUUID(), workspace=randomUUID(), version=randomUUID();
  const apply=(actor:string,action:string,body:unknown,request=randomUUID()) => db.query<{result:any}>('select public.ability_apply($1,$2,$3,$4) result',[actor,request,action,JSON.stringify(body)]);
  const doc=baselineWorkspace('a'.repeat(40),'b'.repeat(64),workspace);
  beforeAll(async () => {
    db=await PGlite.create();
    await db.exec('create role anon; create role authenticated; create role service_role bypassrls; create schema auth; create table auth.users(id uuid primary key); grant usage on schema public to anon,authenticated,service_role;');
    for (const id of [owner,editor,viewer,outsider]) await db.query('insert into auth.users values($1)',[id]);
    await db.exec(await readFile('supabase/migrations/20260923104040_development_collaboration.sql','utf8'));
    await db.exec(await readFile('supabase/migrations/20260924112931_ability_workshop.sql','utf8'));
    await db.exec('set role service_role');
    for (const id of [owner,editor,viewer,outsider]) await db.query('insert into public.dev_members(user_id,github_id,status,role) values($1,$2,$3,$4)',[id,id,'approved',id===owner?'owner':'developer']);
    await db.query("insert into public.ability_permissions values($1,'development','editor'),($2,'development','viewer')",[editor,viewer]);
  },30000);
  afterAll(async () => { await db?.close(); });
  it('saves once, rejects stale/altered retries, and shares only with granted users', async () => {
    const body={id:workspace,environment:'development',revision:0,document:doc}, request=randomUUID();
    expect((await apply(editor,'ability.save',body,request)).rows[0].result.revision).toBe(1);
    expect((await apply(editor,'ability.save',body,request)).rows[0].result.revision).toBe(1);
    await expect(apply(editor,'ability.save',{...body,revision:1},request)).rejects.toThrow('reused');
    await expect(apply(editor,'ability.save',body)).rejects.toThrow('Revision conflict');
    await expect(apply(viewer,'ability.save',body)).rejects.toThrow('permission');
    await expect(db.query("select public.ability_read($1,'development','workspaces',null)",[outsider])).rejects.toThrow('permission');
    const rows=await db.query<{data:any}>("select public.ability_read($1,'development','workspaces',null) data",[viewer]);
    expect(rows.rows[0].data[0].revision).toBe(1);
    expect(rows.rows[0].data[0].document).toBeUndefined();
  });
  it('requires publish permission and preserves immutable versions', async () => {
    const body={id:version,workspaceId:workspace,revision:1,name:'Balance 1',catalogHash:catalogHash({...doc,revision:1})};
    await expect(apply(editor,'ability.publish',body)).rejects.toThrow('permission');
    await apply(owner,'ability.publish',body);
    await expect(db.query("update public.ability_versions set name='changed'")).rejects.toThrow('permission denied');
    await expect(db.query('delete from public.ability_versions')).rejects.toThrow('permission denied');
    await expect(apply(owner,'ability.deploy',{id:randomUUID(),versionId:version,environment:'development'})).rejects.toThrow('No admitted servers');
  });
  it('blocks revoked access even when retrying an acknowledged request', async () => {
    const body={id:workspace,environment:'development',revision:1,document:{...doc,revision:1}}, request=randomUUID();
    await apply(editor,'ability.save',body,request);
    await db.query("select public.dev_set_member($1,$2,'revoked')",[owner,editor]);
    await expect(apply(editor,'ability.save',body,request)).rejects.toThrow('Approved ability access');
  });
  it('denies direct browser SQL and changes to immutable receipts', async () => {
    await expect(db.query("update public.ability_receipts set result='{}'")).rejects.toThrow('permission denied');
    for (const role of ['anon','authenticated']) {
      await db.exec(`reset role; set role ${role}`);
      await expect(db.query('select * from public.ability_workspaces')).rejects.toThrow('permission denied');
      await expect(apply(owner,'ability.save',{})).rejects.toThrow('permission denied');
    }
    await db.exec('reset role; set role service_role');
  });
  it('stages all servers before activation, fences acknowledgements and records partial failure', async () => {
    const source=randomUUID(), runs=[randomUUID(),randomUUID()], servers=[randomUUID(),randomUUID()];
    await db.query('insert into public.dev_versions(id,author_id,name,source_id,source_revision,build_id,content_id,document) values($1,$2,$3,$4,1,$5,$6,$7)',
      [source,owner,'Workshop arena',workspace,doc.buildId,doc.contentId,'{}']);
    const poll=async (i:number,deployment:string|null=null,state:string|null=null,epoch=1) => (await db.query<{result:any}>(
      "select public.ability_server($1,$2,$3,'development',$4,$5,'fixture failure') result",[runs[i],servers[i],epoch,deployment,state])).rows[0].result;
    for (let i=0;i<2;i++) {
      await db.query("insert into public.dev_runs(id,version_id,document,server_id,epoch,lease_until,build_id,content_id) values($1,$2,'{}',$3,1,now()+interval '1 hour',$4,$5)",[runs[i],source,servers[i],doc.buildId,doc.contentId]);
      await poll(i);
    }
    const deployment=randomUUID();
    await apply(owner,'ability.deploy',{id:deployment,versionId:version,environment:'development'});
    await expect(poll(0,deployment,'active')).rejects.toThrow('Invalid deployment transition');
    await expect(poll(0,deployment,'prepared',2)).rejects.toThrow('Writer lease');
    expect((await poll(0,deployment,'prepared')).phase).toBe('preparing');
    expect((await poll(0,deployment,'prepared')).phase).toBe('preparing'); // An acknowledged retry is harmless.
    expect((await poll(1,deployment,'prepared')).phase).toBe('activating');
    expect((await poll(0,deployment,'active')).phase).toBe('activating');
    expect((await db.query<{active_version:string|null}>("select active_version from public.ability_environments where id='development'")).rows[0].active_version).toBeNull();
    expect((await poll(1,deployment,'active')).phase).toBe('idle');
    expect((await db.query<{active_version:string}>("select active_version from public.ability_environments where id='development'")).rows[0].active_version).toBe(version);
    const failure=randomUUID();
    await apply(owner,'ability.deploy',{id:failure,versionId:version,environment:'development'});
    await poll(0,failure,'prepared'); await poll(1,failure,'prepared'); await poll(0,failure,'active'); await poll(1,failure,'failed');
    const failed=(await db.query<{phase:string;servers:any}>('select phase,servers from public.ability_deployments where id=$1',[failure])).rows[0];
    expect(failed.phase).toBe('failed'); expect(failed.servers[servers[0]].state).toBe('active'); expect(failed.servers[servers[1]].state).toBe('failed');
    await db.query("update public.dev_runs set lease_until=null where id=$1",[runs[1]]);
    await expect(poll(1)).rejects.toThrow('Writer lease');
    await expect(apply(owner,'ability.deploy',{id:randomUUID(),versionId:version,environment:'development'})).rejects.toThrow('unavailable');
  });
});
