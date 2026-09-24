import { createServer as createHttpsServer } from 'node:https';
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { hostname } from 'node:os';
import { createClient } from '@supabase/supabase-js';
import { DevelopmentService, uuid } from './service';
import { developmentHandler } from './http';

const required = (name: string) => { const value = process.env[name]; if (!value) throw new Error(`Configure ${name}.`); return value; };
// Remote launch remains gated until native admission, Linux and network proofs
// exist. Do not infer deployment approval from user-controlled environment flags.
if (process.platform !== 'linux' || hostname() !== 'aegis-dev-server') throw new Error('Run inside the isolated aegis-dev-server Linux guest.');
const url = required('AEGIS_DEV_SUPABASE_URL');
if (new URL(url).origin !== 'https://mfwnnvnvchwureeckdfx.supabase.co') throw new Error('Wrong development project; production credentials are forbidden.');
const database = createClient(url, required('AEGIS_DEV_SUPABASE_SECRET'), { auth: { persistSession: false, autoRefreshToken: false } });
const service = new DevelopmentService(database, false);
const key = required('AEGIS_DEV_SERVER_KEY');
if (key.length < 32) throw new Error('Use at least 32 random bytes for the internal server key.');
const publicServer = createHttpsServer({ cert: readFileSync(required('AEGIS_DEV_TLS_CERT')),
  key: readFileSync(required('AEGIS_DEV_TLS_KEY')), minVersion: 'TLSv1.2' }, developmentHandler(service));
const internalServer = createServer(developmentHandler(service, { key,
  runId: uuid(required('AEGIS_DEV_RUN_ID')), serverId: uuid(required('AEGIS_DEV_SERVER_ID')) }));
publicServer.requestTimeout = internalServer.requestTimeout = 15_000;
publicServer.listen(8443, required('AEGIS_DEV_BIND_ADDRESS'));
internalServer.listen(8789, '127.0.0.1');
for (const signal of ['SIGTERM', 'SIGINT'] as const) process.on(signal, () => {
  publicServer.close(); internalServer.close();
});
console.info('Development account API started. Remote game admission is closed.');
