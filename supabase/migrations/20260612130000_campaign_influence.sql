-- Add per-zone realm influence for keep siege unlocks.
-- Existing campaign migrations stay intact; this only extends dynamic state.

create table if not exists campaign_zone_influence (
  zone_id text primary key references campaign_static_zones(zone_id) on delete cascade,
  aegis_influence integer not null default 0 check (aegis_influence >= 0),
  riftbound_influence integer not null default 0 check (riftbound_influence >= 0),
  updated_at timestamptz not null default now()
);

alter table campaign_zone_influence enable row level security;

create policy "campaign zone influence read" on campaign_zone_influence
  for select using (true);
