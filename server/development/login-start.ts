import { createLoginCompanion } from './login';
const key=process.env.AEGIS_DEV_PUBLISHABLE_KEY;
if (!key) throw new Error('Configure the development project publishable key; never use a service/secret key.');
if (key.startsWith('sb_secret_')) throw new Error('Secret keys are forbidden in the login companion.');
const server=createLoginCompanion('https://mfwnnvnvchwureeckdfx.supabase.co',key);
server.listen(43871,'127.0.0.1',()=>console.info('Development login companion ready on loopback. Sign in from AegisWar.'));
for (const signal of ['SIGTERM','SIGINT'] as const) process.on(signal,()=>server.close());
