import { createServer } from 'node:http';
import { randomBytes } from 'node:crypto';
import { createClient } from '@supabase/supabase-js';
import { privateKeyMatches } from './http';

/** Native development companion: OAuth verifier/session live in this process,
 * never in URLs, command-line arguments, logs or repository files. */
export function createLoginCompanion(url: string, publishableKey: string) {
  if (new URL(url).origin !== 'https://mfwnnvnvchwureeckdfx.supabase.co') throw new Error('Only the isolated development project is supported.');
  if (!publishableKey.startsWith('sb_publishable_')) throw new Error('A modern publishable key is required; secret and legacy JWT keys are forbidden.');
  const storage = new Map<string, string>();
  const client = createClient(url, publishableKey, { auth: { flowType: 'pkce', autoRefreshToken: true,
    detectSessionInUrl: false, persistSession: true, storage: {
      getItem: key => storage.get(key) ?? null, setItem: (key,value) => { storage.set(key,value); },
      removeItem: key => { storage.delete(key); },
    } } });
  let localKey = '', callback = '', deadline = 0, failure = '', pending = false, exchanging = false;
  let generation = 0;
  const server = createServer(async (request, response) => {
    response.setHeader('Cache-Control', 'no-store');
    response.setHeader('X-Content-Type-Options', 'nosniff');
    const finish = (code: number, data: unknown) => { response.statusCode = code; response.setHeader('Content-Type','application/json'); response.end(JSON.stringify(data)); };
    try {
      if (!['127.0.0.1','::ffff:127.0.0.1'].includes(request.socket.remoteAddress ?? '')
        || request.headers.host !== '127.0.0.1:43871' || request.headers.origin) { finish(403,{error:'Loopback native requests only.'}); return; }
      const path = new URL(request.url ?? '/', 'http://127.0.0.1:43871');
      if (request.method === 'GET' && callback && path.pathname === callback) {
        if (Date.now() > deadline || !pending || exchanging) { finish(400,{error:'Login expired or already used. Start again from the game.'}); return; }
        exchanging = true;
        const attempt = generation;
        callback = '';
        const code = path.searchParams.get('code');
        if (!code || path.searchParams.has('error')) failure = 'GitHub sign-in did not complete.';
        else {
          const result = await client.auth.exchangeCodeForSession(code);
          if (attempt !== generation) {
            await client.auth.signOut({scope:'local'}); storage.clear();
            exchanging = false;
            finish(409,{error:'Login was cancelled.'}); return;
          }
          if (result.error) failure = 'Could not exchange login code. Start again from the game.';
        }
        pending = false; exchanging = false;
        finish(failure ? 400 : 200, {message: failure || 'Sign-in complete. Return to AegisWar.'}); return;
      }
      const supplied = request.headers.authorization?.replace(/^Bearer /,'') ?? '';
      if (!/^[A-Za-z0-9_-]{32,128}$/.test(supplied)) { finish(401,{error:'Native session key required.'}); return; }
      if (!localKey && request.method === 'POST' && path.pathname === '/login') localKey = supplied;
      if (!privateKeyMatches(supplied,localKey)) { finish(403,{error:'Another native client owns this companion. Restart it for another client.'}); return; }
      if (request.method === 'POST' && path.pathname === '/login') {
        if (exchanging || (pending && Date.now() < deadline)) { finish(409,{error:'Complete the existing browser sign-in.'}); return; }
        const attempt = ++generation;
        callback = `/callback/${randomBytes(24).toString('hex')}`; deadline = Date.now()+300_000; failure=''; pending=true;
        await client.auth.signOut({scope:'local'}); storage.clear();
        const {data,error} = await client.auth.signInWithOAuth({provider:'github',options:{
          redirectTo:`http://127.0.0.1:43871${callback}`,skipBrowserRedirect:true,
        }});
        if (attempt !== generation) { pending=false; callback=''; finish(409,{error:'Login was cancelled.'}); return; }
        if (error || !data.url) { pending=false; finish(503,{error:'GitHub authentication is not configured or is unavailable.'}); return; }
        finish(200,{url:data.url}); return;
      }
      if (request.method === 'GET' && path.pathname === '/session') {
        const {data} = await client.auth.getSession();
        if (failure) { finish(400,{error:failure}); return; }
        finish(200,{pending,accessToken:pending ? '' : data.session?.access_token ?? '',expiresAt:pending ? 0 : data.session?.expires_at ?? 0}); return;
      }
      if (request.method === 'POST' && path.pathname === '/logout') {
        ++generation;
        await client.auth.signOut({scope:'local'}); storage.clear(); callback=''; pending=false; failure='';
        finish(200,{signedOut:true}); return;
      }
      finish(404,{error:'Unknown route.'});
    } catch { failure='Development sign-in unavailable.'; pending=false; exchanging=false; finish(503,{error:failure}); }
  });
  server.requestTimeout=10_000;
  server.on('close', () => { client.auth.stopAutoRefresh(); storage.clear(); });
  return server;
}
