-- Static Aegis/Riftbound campaign map and shared campaign state.
-- Apply this migration, then run supabase/seed_campaign_static.sql.

create table if not exists campaign_static_zones (
  zone_id text primary key,
  name text not null,
  realm text not null check (realm in ('aegis', 'riftbound')),
  tier text not null check (tier in ('T1', 'T2', 'T3', 'T4', 'Fortress', 'City', 'Boss')),
  lane text not null,
  node_role text not null check (node_role in ('capital', 'fortress', 'battlefield', 'boss_lair')),
  static_map_version text not null,
  map_hash text not null,
  updated_at timestamptz not null default now()
);

create table if not exists campaign_edges (
  from_zone_id text not null references campaign_static_zones(zone_id) on delete cascade,
  to_zone_id text not null references campaign_static_zones(zone_id) on delete cascade,
  primary key (from_zone_id, to_zone_id)
);

create table if not exists campaign_objectives (
  zone_id text not null references campaign_static_zones(zone_id) on delete cascade,
  objective_id text not null,
  objective_type text not null check (objective_type in ('battle_objective', 'keep', 'fortress', 'city_gate', 'boss')),
  label text not null,
  x real not null,
  z real not null,
  capture_radius real not null check (capture_radius > 0),
  default_realm text not null check (default_realm in ('aegis', 'riftbound')),
  primary key (zone_id, objective_id)
);

create table if not exists campaign_zone_state (
  zone_id text primary key references campaign_static_zones(zone_id) on delete cascade,
  controlled_by text not null check (controlled_by in ('aegis', 'riftbound', 'contested')),
  locked boolean not null default false,
  updated_at timestamptz not null default now()
);

create table if not exists campaign_objective_state (
  zone_id text not null references campaign_static_zones(zone_id) on delete cascade,
  objective_id text not null,
  controlled_by text not null check (controlled_by in ('aegis', 'riftbound', 'contested')),
  claimed_by_user_id uuid,
  updated_at timestamptz not null default now(),
  primary key (zone_id, objective_id),
  foreign key (zone_id, objective_id) references campaign_objectives(zone_id, objective_id) on delete cascade
);

create table if not exists world_edit_versions (
  version_id text primary key,
  zone_id text not null,
  status text not null check (status in ('draft', 'published')),
  parent_version_id text,
  notes text,
  author_user_id uuid,
  author_email text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  published_at timestamptz
);

create table if not exists world_edit_objects (
  version_id text not null references world_edit_versions(version_id) on delete cascade,
  object_id text not null,
  object jsonb not null,
  primary key (version_id, object_id)
);

create table if not exists world_edit_chunks (
  version_id text not null references world_edit_versions(version_id) on delete cascade,
  chunk_key text not null,
  chunk jsonb not null,
  primary key (version_id, chunk_key)
);

create table if not exists gm_user_roles (
  user_id uuid,
  email text,
  role text not null check (role in ('gm', 'admin')),
  created_at timestamptz not null default now()
);

alter table campaign_static_zones enable row level security;
alter table campaign_edges enable row level security;
alter table campaign_objectives enable row level security;
alter table campaign_zone_state enable row level security;
alter table campaign_objective_state enable row level security;
alter table world_edit_versions enable row level security;
alter table world_edit_objects enable row level security;
alter table world_edit_chunks enable row level security;
alter table gm_user_roles enable row level security;

create policy "campaign static read" on campaign_static_zones
  for select using (true);
create policy "campaign edges read" on campaign_edges
  for select using (true);
create policy "campaign objectives read" on campaign_objectives
  for select using (true);
create policy "campaign zone state read" on campaign_zone_state
  for select using (true);
create policy "campaign objective state read" on campaign_objective_state
  for select using (true);

create policy "published world edits read" on world_edit_versions
  for select using (status = 'published');
create policy "published world objects read" on world_edit_objects
  for select using (
    exists (
      select 1 from world_edit_versions v
      where v.version_id = world_edit_objects.version_id
        and v.status = 'published'
    )
  );
create policy "published world chunks read" on world_edit_chunks
  for select using (
    exists (
      select 1 from world_edit_versions v
      where v.version_id = world_edit_chunks.version_id
        and v.status = 'published'
    )
  );
