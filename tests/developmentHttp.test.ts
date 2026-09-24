import { afterEach, describe, expect, it, vi } from 'vitest';
import { createServer, type Server } from 'node:http';
import { randomUUID } from 'node:crypto';
import { developmentHandler } from '../server/development/http';
import { DevelopmentError, DevelopmentService, document } from '../server/development/service';

const servers: Server[] = [];
async function listen(handler: ReturnType<typeof developmentHandler>) {
  const server = createServer(handler); servers.push(server);
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('Missing address');
  return `http://127.0.0.1:${address.port}`;
}
afterEach(async () => { await Promise.all(servers.splice(0).map(server => new Promise<void>(resolve => {
  server.close(resolve); server.closeAllConnections();
}))); });

describe('development HTTP boundaries', () => {
  it('verifies the token and uses the verified member, never a supplied identity', async () => {
    const member = { user_id:randomUUID(), status:'pending', role:'developer', generation:0 };
    const service = { admissionOpen:false, identity:vi.fn(async (token:string) => {
      if (token !== 'verified') throw new DevelopmentError(401,'Invalid token');
      return member;
    }), userOperation:vi.fn(async () => { throw new DevelopmentError(403,'Developer approval required.'); }) };
    const url = await listen(developmentHandler(service as unknown as DevelopmentService));
    expect((await fetch(`${url}/session`)).status).toBe(401);
    expect((await fetch(`${url}/session`,{headers:{Authorization:'Bearer forged'}})).status).toBe(401);
    const response = await fetch(`${url}/session`,{headers:{Authorization:'Bearer verified'}});
    expect((await response.json()).data).toMatchObject({status:'pending',admissionOpen:false});
    expect(response.headers.get('cache-control')).toBe('no-store');
    const body={requestId:randomUUID(),action:'draft.save',body:{id:randomUUID(),actorId:randomUUID()}};
    expect((await fetch(`${url}/operations`,{method:'POST',headers:{Authorization:'Bearer verified'},body:JSON.stringify(body)})).status).toBe(403);
    expect(service.userOperation).toHaveBeenCalledWith(member,body.requestId,body.action,body.body);
  });
  it('binds internal calls to the configured server/run and denies missing or incorrect credentials', async () => {
    const key='s'.repeat(64), runId=randomUUID(), serverId=randomUUID();
    const service={claim:vi.fn(async () => ({epoch:1}))};
    const url=await listen(developmentHandler(service as unknown as DevelopmentService,{key,runId,serverId}));
    for (const credential of ['', 'short', 'x'.repeat(64)]) {
      expect((await fetch(`${url}/claim`,{method:'POST',headers:{Authorization:`Bearer ${credential}`},body:'{}'})).status).toBe(credential ? 403 : 401);
    }
    expect((await fetch(`${url}/claim`,{method:'POST',headers:{Authorization:`Bearer ${key}`},body:JSON.stringify({epoch:0,runId:randomUUID(),serverId:randomUUID()})})).status).toBe(200);
    expect(service.claim).toHaveBeenCalledExactlyOnceWith(runId,serverId,0);
  });
  it('keeps admission closed even with a valid account and sanitizes unexpected exceptions', async () => {
    const service=new DevelopmentService({} as never);
    vi.spyOn(service,'identity').mockResolvedValue({user_id:randomUUID(),github_id:'123',status:'approved',role:'developer',generation:1});
    const url=await listen(developmentHandler(service));
    expect((await fetch(`${url}/join`,{method:'POST',headers:{Authorization:'Bearer token'},body:'{}'})).status).toBe(503);
    vi.spyOn(service,'read').mockRejectedValue(new Error('database-password-must-not-leak'));
    const response=await fetch(`${url}/drafts`,{headers:{Authorization:'Bearer token'}});
    expect(response.status).toBe(500); expect(await response.text()).not.toContain('password');
  });
  it('validates document compatibility and shape before saving', () => {
    const value={schemaVersion:1,kind:'world',buildId:'a'.repeat(40),contentId:'b'.repeat(64),payload:{}};
    expect(document(value)).toEqual(value);
    for (const invalid of [{...value,payload:[]},{...value,buildId:'latest'},{...value,kind:'production'},null]) {
      expect(()=>document(invalid)).toThrow();
    }
  });
  it('keeps ability publication and deployment closed even for an approved owner', async () => {
    const service=new DevelopmentService({} as never);
    const member={user_id:randomUUID(),github_id:'123',status:'approved',role:'owner',generation:1};
    vi.spyOn(service,'member').mockResolvedValue(member);
    for (const action of ['ability.publish','ability.deploy']) await expect(service.userOperation(member,randomUUID(),action,{id:randomUUID()})).rejects.toThrow('native admission');
  });
});
