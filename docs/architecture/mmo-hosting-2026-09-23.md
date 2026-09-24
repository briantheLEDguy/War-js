# MMO hosting strategy — 2026-09-23

The approved current phase is the [free development environment](../development-environment.md).
Paid infrastructure is a future decision; no purchases are authorized.

Unreal dedicated servers own combat, movement validation, NPC simulation and live
world edits. Account/admission services own identity, permissions, tickets and
durable transactions. PostgreSQL stores persistent records. Supabase Realtime
does not replace Unreal replication/prediction/simulation. Moving to PC does not
remove authority, consistency or recovery requirements.

| Option | Architecture | Planning cost and tradeoff |
|---|---|---|
| Free development, selected | Existing PC, isolated Linux guest, Unreal + Node, Supabase Free, separate NetBird Free | $0 new subscriptions within quotas; hardware, electricity and effort remain costs. Five NetBird users including owner. Available while host/guest run, without an MMO availability guarantee. |
| Low-cost closed alpha | EU dedicated-vCPU game host, separate gateway, Supabase Pro/PostgreSQL, backups/monitoring | Prior budget €100–250/month plus tax/traffic/currency differences. Illustrative Hetzner calculation: CCX23 €85.99 + CX23 €5.49 + IPv4 €1 + approximately €18.30 backups; Supabase Pro separately $25/month. Requote before spending. Owner operated. |
| Managed production | Regional Unreal GameLift fleets, redundant admission services, RDS PostgreSQL Multi-AZ/PITR, monitoring and incident response | Prior planning envelope $1,000–5,000+/month, not a capacity quote. Utilization, egress, I/O, regions and staffing determine cost. Managed services do not replace application correctness or on-call work. |

PlayFab remains an alternative for account/live operations and managed servers;
Nakama can provide account/social/matchmaking with Unreal hosting separate; EOS
provides online services without implementing a persistent MMO world. None
automatically supplies correct economy transactions or a scalable seamless world.

Earlier planning assumed Europe, scheduled closed-alpha sessions, planned wipes,
no paid goods and owner operations. Desired 100–1,000 concurrency is not measured
capacity. The repository targets 18 players per realm per contested zone;
concurrent zones, AI, replication and tick budget determine process count. Test
the actual packaged game before promising capacity or buying servers.

Production Steam login remains later: verify tickets on trusted services and map
immutable identities. Keep development and production projects, secrets and
economies separate. Budget for off-device backups/restore drills, telemetry,
patch/rollback, abuse handling, incident coverage and network protection before
public alpha. Scale when measurements justify it.

All prices/quotas require rechecking before procurement. Primary references:
[Unreal networking](https://dev.epicgames.com/documentation/en-us/unreal-engine/networking-overview-for-unreal-engine),
[Supabase pricing](https://supabase.com/pricing), [NetBird pricing](https://netbird.io/pricing),
[Hetzner Cloud](https://www.hetzner.com/cloud/),
[GameLift pricing](https://aws.amazon.com/gamelift/servers/pricing/),
[RDS PostgreSQL](https://aws.amazon.com/rds/postgresql/),
[PlayFab](https://learn.microsoft.com/en-us/gaming/playfab/multiplayer/servers/),
[Nakama](https://heroiclabs.com/docs/nakama/), [EOS](https://onlineservices.epicgames.com/).
