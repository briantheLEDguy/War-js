# Development world publishing and GM sync

The native City Builder has **Remote world sync** with **Developer sign-in**,
**Sync: pull remote (back up local)** and **Publish remote / retry**. These use
the authenticated development gateway to exchange native world snapshots.
They do not deploy code, native assets, a dedicated server, character saves,
ability changes, or active multiplayer world state. Runtime deployment and
shared GM acceptance gates remain closed.

## Connection status — 2026-09-25

The existing `aegiswar-development` project (`mfwnnvnvchwureeckdfx`) reports
`ACTIVE_HEALTHY`. Its Auth settings enable GitHub and signup. A read-only query
found zero Auth users and zero approved owners. The public client key is now in
the ignored local `.env.development`; no server credentials are in that file.
`npm run dev:check` reaches Auth and reports the missing `AEGIS_DEV_GATEWAY_URL`.
There is no verified running gateway address in this checkout. Host VM inspection
was denied by Windows permissions; no VM or network configuration was changed.

The new migration is **not deployed**. The gateway/native changes have not been
tested against a hosted authenticated session. No live world has been published
and no live game server has been linked. Confirm the intended server before
applying this development-only schema to any hosted project.

## Setup

1. Finish the isolated guest/gateway setup in
   [development-environment.md](development-environment.md) and its
   [checkpoint](development-setup-checkpoint-2026-09-23.md). Keep collaborator
   admission closed until existing isolation and native checks pass.
2. On the **development project only**, review and apply
   `supabase/migrations/20260925112105_development_world_sync.sql` after the
   existing development collaboration schema. Do not blindly apply historical
   migrations; the initial hosted schema was installed without CLI history.
   Deploy the updated gateway in the isolated guest using server-only secrets
   and trusted TLS.
3. Copy `.env.development.example` to `.env.development` on other machines.
   Set the modern publishable key and verified HTTPS gateway origin
   (`https://<your-guest-hostname>:8443`). The gateway URL is **not** the Supabase
   URL. Run `npm run dev:check`.
4. Run `npm run dev:login`, then **Developer sign-in** in the GM sync section
   or the frontend developer-account page. Before launching Unreal, set
   `AEGIS_DEV_GATEWAY_URL` in its parent process environment; the companion reads
   `.env.development`, but Unreal does not. Complete browser GitHub login. Confirm
   the callback allowlist and bootstrap the verified owner with `dev:admin` as
   documented in the development setup guide.
5. Open the local capital GM session and **pull remote first**. An empty remote
   retains the local layout for its first owner publication. An existing remote
   imports after native model/baseline/transform validation. **Publish remote /
   retry** commits an immutable version only if the observed revision matches.

## Recovery and concurrency

Before pulling or starting a publication, the game saves the current layout in
`Saved/WorldEdit/SyncRecovery/<GUID>.json`. These contain world data, not tokens.
Pull is undoable and does not replace the named draft. After a restart, recover
by preserving the existing named draft, copying the desired recovery snapshot
to the map's draft path while the game is closed, then using **Load draft**.
**Publish draft to local game** separately retains a pulled layout next launch.

Edits made during a pull reject its response. Native actor staging retains the
current world on missing models, incompatible baselines or validation errors.
Map package paths isolate publications even when worlds share a zone ID.

A stale publish returns a conflict. Pull, then reapply intended local changes
from undo/recovery before publishing. There is no automatic merge. An uncertain
publish retains the exact document/request UUID in memory for retry; later edits
do not alter it. Pull stays blocked until reconciliation. After restarting, pull
again to observe the committed head; recovery retains the original local layout.

SQL commits publication, revision, immutable history, audit and retry receipt in
one transaction. Current membership is checked before reads and receipt replays.
Approved developers may pull; only the approved owner may publish. Anonymous and
authenticated database roles have no direct table/RPC grants. Every response
reports `runtimeApplied:false`: database commitment is not active-server
deployment. Shared/Shipping GM gates remain unchanged.

## Architecture and verification

- `server/development/world-sync.ts`: bounded native snapshot validation.
- `service.ts` / `http.ts`: verified-identity `POST /world-sync` route.
- `check.ts` / `check-start.ts`: read-only connection diagnostics.
- `WarWorldEditSync.cpp`: authenticated native transfer and recovery.
- `WarWorldSync.cpp`: response/baseline validation before actor changes.
- `dev_world_heads` / `dev_world_versions`: current revision and immutable history.

Run `test:development`, `typecheck:server`, repository tests and native Foundation
tests. Coverage includes rollback, history, conflicts, retries, map isolation,
permissions/revocation, HTTP identity binding, invalid transforms, incompatible
models, edits during requests and undo. Normal OAuth, hosted transfers, rendered
button interaction and dedicated-server application still need acceptance.

Verification on 2026-09-25: all 658 repository tests, 22 focused development
tests, 124 Unreal tooling tests and 56 native Foundation tests passed. The
Windows Editor build, all three TypeScript checks, migration audit, 33-map world
validation and 906-record model validation passed. Native report:
`artifacts/unreal/editor/test-1790335612121-2704/index.json`. The release check
still exits 1 with four blocker categories, as required. `dev:check` intentionally
exits 1 while the gateway URL is missing. This is not hosted sync or graphical
acceptance.
