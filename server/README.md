# Retained campaign and persistence infrastructure

The browser client is retired. This Node authority remains available for backend
development and regression testing; native production gameplay is not wired to it.
Run `npm run server:dev` for loopback-only development authentication or configure
`.env.orvr` from `.env.orvr.example` before `npm run server:start`.

Node 22.19+ is required. Supabase server secrets remain server-only and must never
enter native content, client builds, the public repository or a collaboration VM.
`shared/orvr/` owns numerical simulation and the JSON protocol; map configuration
consumes retained source maps and `shared/` catalogs. Do not remove this authority
until its persistence, authentication and campaign contracts have replacements.

The server persists captures, delivery, purchases, repairs and campaign advances
before acknowledgement. Ordinary combat events batch into the ordered journal;
ordinary combat and movement may roll back up to five seconds after a crash.
Persistence failures restore the last checkpoint and pause the authority.
File checkpoints are atomic and guarded by an exclusive process lease; an actual
dead process lease is recovered. `artifacts/orvr/` is ignored by Git. Startup
compares saved map definitions and ability rules with the current build. An
incompatible checkpoint stops startup with the changed IDs and leaves the save
intact. Restore the matching build or migrate the save explicitly. For an
intentional fresh campaign, select a new `ORVR_CAMPAIGN_ID` and a different
`ORVR_CHECKPOINT` when using file storage. Keep backups of persistent campaigns.

For Supabase, intentionally select a project, apply
`supabase/migrations/20260907141937_shared_orvr_authority.sql`, provision Auth users,
configure URL, publishable key, server secret, origins and TLS, then run
`npm run server:start`. The migration enables RLS on all new tables. Players can
create/read their own named recruits but cannot switch realms or write battle
outcomes. The server RPC uses compare-and-swap revision and commits state with
events in one transaction. No hosted migration/deployment has been performed.
The retired Pages workflow does not deploy this service.

The current shared view uses movement intents and authoritative interpolation.
Its travel menu transfers between active fronts from staging. Generated portals
and optional lair travel remain available through the established local game;
the shared renderer does not yet activate those portal triggers.
Client prediction/reconciliation, complete character progression/inventory,
warband management, persistent pets/deployables and multilevel capital navigation
remain unfinished. Existing city gameplay remains in its established local game.
Replacement art is tracked independently; draft assets cannot claim completion.

Verification: `npm run test:orvr`, `npm run typecheck:server`, `npm run typecheck`,
`npm run build`, `npm run world:validate`. WebSocket tests use actual connections,
including 36-player admission and overflow. SQL tests run the migration under
PGlite/PostgreSQL with explicit Auth-role fixtures, not a hosted Auth deployment.
Reference: [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security),
[PGlite API](https://pglite.dev/docs/api).

Local CPU fixture (36 players concentrated, 1,000 steps): mean simulation step
0.28ms; serialization for all 36 clients 9.87ms; 309,904 bytes per update batch,
approximately 3.10MB/s at 10Hz, before transport overhead. This is not a measured
GPU frame rate, remote latency result, production load test or 60FPS acceptance.
