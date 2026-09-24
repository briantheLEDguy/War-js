import { afterEach, describe, expect, it, vi } from 'vitest';
import { request, type Server } from 'node:http';
const mocks=vi.hoisted(()=>({auth:{signOut:vi.fn(),signInWithOAuth:vi.fn(),getSession:vi.fn(),exchangeCodeForSession:vi.fn(),stopAutoRefresh:vi.fn()}}));
vi.mock('@supabase/supabase-js',()=>({createClient:()=>({auth:mocks.auth})}));
import { createLoginCompanion } from '../server/development/login';

let server:Server|undefined, port=0;
async function start() {
  mocks.auth.signOut.mockResolvedValue({error:null});
  mocks.auth.signInWithOAuth.mockResolvedValue({data:{url:'https://mfwnnvnvchwureeckdfx.supabase.co/auth/v1/authorize?provider=github'},error:null});
  mocks.auth.getSession.mockResolvedValue({data:{session:{access_token:'memory-token',expires_at:100}}});
  mocks.auth.exchangeCodeForSession.mockResolvedValue({error:null});
  server=createLoginCompanion('https://mfwnnvnvchwureeckdfx.supabase.co','sb_publishable_test');
  await new Promise<void>(resolve=>server!.listen(0,'127.0.0.1',resolve));
  const address=server.address(); if (!address || typeof address==='string') throw new Error('No address'); port=address.port;
}
function call(path:string,method='GET',headers:Record<string,string>={}) {
  return new Promise<{status:number,body:any}>((resolve,reject)=>{
    const req=request({hostname:'127.0.0.1',port,path,method,headers:{Host:'127.0.0.1:43871',...headers}},response=>{
      const chunks:Buffer[]=[]; response.on('data',chunk=>chunks.push(chunk));
      response.on('end',()=>resolve({status:response.statusCode!,body:JSON.parse(Buffer.concat(chunks).toString())}));
    }); req.on('error',reject); req.end();
  });
}
afterEach(async()=>{
  if(server) await new Promise<void>(resolve=>{server!.close(()=>resolve()); server!.closeAllConnections();});
  server=undefined; vi.clearAllMocks();
});
describe('development login companion',()=>{
  it('rejects database secrets, DNS rebinding, cross-origin browser requests and different native clients',async()=>{
    expect(()=>createLoginCompanion('https://mfwnnvnvchwureeckdfx.supabase.co','sb_secret_no')).toThrow('publishable');
    expect(()=>createLoginCompanion('https://wrong.supabase.co','sb_publishable_test')).toThrow('isolated');
    await start(); const headers={Authorization:`Bearer ${'a'.repeat(64)}`};
    expect((await call('/login','POST',{...headers,Host:'attacker.example'})).status).toBe(403);
    expect((await call('/login','POST',{...headers,Origin:'https://attacker.example'})).status).toBe(403);
    expect((await call('/session')).status).toBe(401);
    expect((await call('/login','POST',headers)).status).toBe(200);
    expect((await call('/session','GET',{Authorization:`Bearer ${'b'.repeat(64)}`})).status).toBe(403);
    expect((await call('/session','GET',headers)).body).toMatchObject({pending:true,accessToken:''});
  });
  it('accepts the exact one-use callback and exposes the session only to the initiating native client',async()=>{
    await start(); const headers={Authorization:`Bearer ${'a'.repeat(64)}`};
    await call('/login','POST',headers);
    const callback=new URL(mocks.auth.signInWithOAuth.mock.calls[0][0].options.redirectTo).pathname;
    expect((await call('/callback/forged?code=test')).status).toBe(401);
    expect((await call(callback+'?code=code')).status).toBe(200);
    expect(mocks.auth.exchangeCodeForSession).toHaveBeenCalledExactlyOnceWith('code');
    expect((await call(callback+'?code=code')).status).toBe(401);
    expect((await call('/session','GET',headers)).body.accessToken).toBe('memory-token');
    expect((await call('/logout','POST',headers)).status).toBe(200);
    expect(mocks.auth.signOut).toHaveBeenCalledWith({scope:'local'});
  });
});
