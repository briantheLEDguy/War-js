# Free development environment — 2026-09-23

**Incomplete; remote admission remains closed.** Branch:
`codex/free-development-multiplayer`. This is the active implementation record,
not certification of multiplayer, shared GM or deployment. The
[long-term strategy](architecture/mmo-hosting-2026-09-23.md) retains paid options.
Unreal Multi-User Editor remains deferred.

Provisioning is paused for game editing. Resume from the
[setup checkpoint](development-setup-checkpoint-2026-09-23.md): Ubuntu VM and
package access work; NetBird CLI is installed, but enrollment and isolation
acceptance remain outstanding.

## Target and present status

Developers keep independent checkouts and approved native content. GitHub through
Supabase creates pending identities; only the owner approves them. An isolated
Linux guest runs Node and Unreal. A separate NetBird project exposes only game
UDP and authenticated HTTPS. Unreal owns combat and the live GM document;
Supabase stores committed development state.

| Deliverable | Current evidence |
|---|---|
| Separate free database | `aegiswar-development`, Frankfurt, ref `mfwnnvnvchwureeckdfx`; created after provider quoted $0/month |
| SQL foundations | Deployed; local PostgreSQL permission, revision, retry, rollback, ticket and lease tests |
| Native sign-in entry | Windows Editor compiles; frontend launches PKCE companion and checks gateway status |
| Actual GitHub sign-in | Not verified; OAuth provider configuration and owner bootstrap outstanding |
| Personal game saves | Draft/version API implemented; native snapshot integration outstanding |
| Linux server | Build failed: missing Linux engine components; installed engine is not a source build |
| VM and project NetBird | Ubuntu guest provisioned manually; NetBird 0.79.0 installed; account/policies/enrollment and isolation acceptance outstanding |
| Asset onboarding | Blocked: no approved distribution roots |
| Normal authenticated joins | Ticket storage implemented; native admission/restoration not implemented |
| Five-second active revocation | Gateway checks current grants; native disconnect watchdog outstanding |
| Shared GM | Local GM preserved; document transport and collision synchronization outstanding |
| Two-machine combat/recovery | Not performed; proof flags are not remote login credentials |
| Production | Steam and release gates remain closed |

Host inspection found approximately 31 GiB RAM and 196 GiB free on C:. These are
observations, not a sizing result. Source-engine builds, native packages and a VM
disk need capacity planning. The signed-in GitHub CLI returned 404 for
`EpicGames/UnrealEngine`; establish source access or supply a matching checkout.

## Implemented boundaries

- `server/development/login.ts`: IPv4 loopback port 43871, PKCE verifier/tokens in
  memory, random one-use callback, Host/Origin checks and per-client bearer key.
- `WarDevelopmentAccount`: non-Shipping frontend entry, pinned Auth URL for system
  browser launch, memory-only token, HTTPS account check and stale-response guard.
- `WarGameMode`: proof connections require numeric loopback addresses; proof flags
  cannot admit VPN or LAN clients.
- `service.ts` / `http.ts`: verified GitHub identity, pending registration, fresh
  grants, isolated drafts, immutable versions, run checkpoints and bound tickets.
- `admin.ts`: owner bootstrap/list/approve/revoke. Repository, game and
  infrastructure permissions stay separate; collaborators get no service secrets.
- `start.ts`: guest-only launcher, TLS public API and loopback private API.
  Admission is hardcoded closed; an environment flag cannot open it.
- `supabase/migrations/20260923104040_development_collaboration.sql`: RLS, no client
  table/RPC grants, limited service grants, transactional receipts/audit, expected
  revisions, membership generations and fenced writer leases.

The schema was installed through the SQL connector, including correction of
inherited service-role grants. Remote CLI migration history is **not** registered.
Compare the deployed schema before reconciling history; never apply all historical
browser migrations to this new development project. Security Advisor's
RLS-without-policy informational notices are intentional: no direct client access.

## Reproducible onboarding

1. Review model, animation and kit distribution rights and collaborator entitlement.
   Record evidence through the existing content policy. Private Git does not
   confer distribution rights. Do not upload purchased packages by assumption.
2. Pin one code commit and approved content manifest SHA-256. Fetch full history
   and `browser-reference-before-retirement-20260922`; run `npm ci`. Use exact
   Unreal 5.8.2. Run `unreal:content-check -- <private-checkout>` and content sync
   only when the existing content gates permit it.
3. Configure a GitHub OAuth application with callback
   `https://mfwnnvnvchwureeckdfx.supabase.co/auth/v1/callback`. Put its ID/secret
   in this Supabase project's GitHub provider, never the game.
4. Allow `http://127.0.0.1:43871/callback/*` in Supabase Auth redirect URLs.
   Do not wildcard the host. Supabase receives GitHub's callback and redirects
   to this PKCE-protected native flow.
5. Give developers only the modern publishable key and verified HTTPS gateway
   URL. Set `AEGIS_DEV_PUBLISHABLE_KEY`; run `npm run dev:login`. Set
   `AEGIS_DEV_GATEWAY_URL` before launching Unreal; select Development sign-in.
   One companion serves one game process; restart when switching the owner.
   Tokens are not chat messages or command-line arguments.
6. The owner signs in normally, supplies `AEGIS_DEV_SUPABASE_SECRET` and their
   `AEGIS_DEV_OWNER_ACCESS_TOKEN` securely in the maintenance environment, then
   runs `npm run dev:admin -- bootstrap-owner`. This works only before an owner
   exists; the unique owner index prevents two owners.
7. Run `npm run dev:admin -- list`; verify pending immutable GitHub identities
   out of band before `approve <UUID>`. Use `revoke <UUID>` to revoke. Editable
   names, email claims, user metadata and client flags grant no permissions.

Steps 3–7 still require an actual end-to-end test. The Supabase browser dashboard
needs interactive owner sign-in. There is no running gateway yet.

## Persistence contract

Documents have `schemaVersion:1`, `kind:world|character`, `buildId` (Git SHA),
`contentId` (manifest SHA-256), and object `payload`. Store asset references;
native packages stay in the approved-content workflow.

`POST /operations` takes `{requestId,action,body}`. Draft save body is
`{id,revision,document}`; creation expects revision zero. Version publication
takes `{id,sourceId,revision,name,buildId,contentId}`; fork and run creation take
`{id,sourceId}`. After a lost response, reuse the **same request UUID and identical
body**. Altered retries/stale revisions fail. HTTP success follows SQL commit.
On failure retain the request for reconciliation; do not report a successful save.

Native adapters still need complete character identity, progression, inventory,
equipment, quests, professions, cultivation, resource cooldown and transaction
receipt validation. Arbitrary JSON storage is not that validation. The adapter
must pause persistent mutations on failure, reconcile uncertain commits, and
never overwrite a personal sandbox from a shared run.

Run leases last 15 seconds and use increasing fencing epochs. Tickets expire in
60 seconds, store only SHA-256 digests, bind identity/character/run/build/content
and membership generation, and consume once. The native bridge must load committed
state before admission and fence every write. A separate fail-closed two-second
grant poll/watchdog must disconnect within five seconds, including outages;
lease duration is not the revocation deadline.

## Deployment and isolation gates

Only the headless `aegis-dev-server` guest may host the shared server. Never read,
modify or reuse host work Tailscale. No collaborator shell, desktop, file share,
subnet route, exit node, host filesystem mount or credential forwarding.

Start provisioning offline. Build the exact Unreal source revision (Epic requires
a source build for dedicated servers), package Linux with approved content, and
measure CPU/RAM/disk/bandwidth/tick time with two players before sizing capacity.
Install NetBird inside the guest under the separate project account. Remove
default all-to-all policy before peers join. Permit approved client groups only
to guest UDP 7777 (or recorded game port) and TCP 8443. Never expose private
loopback API 8789. Use a valid trusted TLS certificate; never disable verification.

Enforce both guest firewall and independent hypervisor/router egress policy:
deny host/LAN destinations, IPv6 escapes, management ports and forwarding;
permit required replies and documented Internet services. A guest firewall alone
does not isolate a compromised guest. Test from a second physical machine and
record exact rules/rollback before admission. No network changes were made here.

Gateway environment: `AEGIS_DEV_SUPABASE_URL`, `AEGIS_DEV_SUPABASE_SECRET`,
`AEGIS_DEV_SERVER_KEY` (32+ random bytes), `AEGIS_DEV_RUN_ID`,
`AEGIS_DEV_SERVER_ID`, `AEGIS_DEV_TLS_CERT`, `AEGIS_DEV_TLS_KEY`,
`AEGIS_DEV_BIND_ADDRESS`. Store secrets owner-only in the guest, not Git. Launch
`npm run dev:gateway`. Hostname checking prevents accidental launch; it is not an
isolation security boundary.

## Remaining implementation and acceptance

1. Implement native ticket admission, owned-character selection/restoration,
   server-bound identity, compatibility and active revocation. Proof flags must
   never authenticate remote players; preserve Shipping denial.
2. Connect native personal saves and version UI; validate complete snapshots and
   approved asset references before restoration.
3. Make runtime GM an Unreal-owned document: serialize requests, check current
   grants/expected revisions, commit checkpoints before success. Initial snapshot
   plus ordered updates must detect gaps and resynchronize. Load world/collision
   before player entry. Authorize traversal separately; undo creates a validated
   new revision and cannot silently remove intervening work.
4. On two real developer machines prove install, login, combat, death, respawn,
   reconnect, concurrent edits, placement/removal/transforms/visibility/collision,
   late join, publishing, restart and checkpoint recovery.
5. Test pending/revoked users, forged/replayed/expired tickets, incompatible builds,
   cross-sandbox access, duplicate rewards, interrupted commits, lost replies,
   edit conflicts, expired leases and unavailable persistence.
6. Make encrypted off-device backups; restore into an isolated target, invalidate
   outstanding tickets/leases, verify receipts, references and native state before
   admitting anyone. Same-disk VM snapshots are insufficient. No backup restoration
   has been demonstrated.

Run `test:development`, all repository tests/typechecks, native foundation tests,
world/model validation and migration audit. `unreal:release-check` must keep
failing until production acceptance. Record tester/date/machines/code/content
hashes and evidence. Development data never automatically enters production.

References: [GitHub provider](https://supabase.com/docs/guides/auth/social-login/auth-github),
[PKCE](https://supabase.com/docs/guides/auth/sessions/pkce-flow),
[dedicated servers](https://dev.epicgames.com/documentation/unreal-engine/setting-up-dedicated-servers-in-unreal-engine),
[NetBird plans](https://docs.netbird.io/manage/settings/plans-and-billing).

## Verification recorded on 2026-09-23

- `npm test`: 84 files, 598 tests passed. Focused development rerun: 12 passed,
  including forged/expired/replayed tickets and interrupted-transaction rollback.
- `typecheck`, `typecheck:server`, `typecheck:unreal-tools`: passed.
- `test:unreal`: 17 files, 112 tests passed. Windows Editor build passed.
- `unreal:test-native`: 44 passed; latest report
  `artifacts/unreal/editor/test-1790161297268-2016`.
- `unreal:network-proof`: passed after correcting the authored arena fixture's
  logical zone. Both test characters now share the same authoritative zone;
  combat restrictions were not weakened. Report:
  `artifacts/unreal/network/1790161446616-22644/report.json`.
  This uses loopback Windows Editor processes and unauthorized-GM rejection,
  **not** two-machine login, packaged Linux deployment or shared-GM acceptance.
- `world:validate`: 33 maps; `models:validate`: 906 records; both passed.
- `unreal:audit`: completed, packaging/release readiness false.
  `unreal:release-check`: failed as required; four release blockers remain.
- Hosted SQL privilege checks confirm no anonymous/authenticated draft read or
  mutation RPC, and no service update/delete/truncate of immutable records tested.
  A hosted save/retry transaction completed and rolled back; no test user remained.
- Diff whitespace review and scoped credential-pattern scan found no issues.

No normal GitHub login, Linux packaging, VPN/isolation, five-second disconnect,
native persisted-character round trip, shared editing or backup restore has been
verified. Those gates remain open work, not inferred successes.
