-- Campaign state and its economic journal commit together before network acknowledgement.
create table public.orvr_accounts (
  user_id uuid primary key references auth.users(id) on delete cascade,
  realm text not null check (realm in ('aegis', 'riftbound')),
  created_at timestamptz not null default now()
);
create table public.orvr_characters (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.orvr_accounts(user_id) on delete cascade,
  name text not null check (length(trim(name)) between 2 and 32),
  realm text not null check (realm in ('aegis', 'riftbound')),
  ability_ids text[] not null default '{}',
  created_at timestamptz not null default now()
);
create index orvr_characters_user_id_idx on public.orvr_characters(user_id);
create table public.orvr_campaigns (
  id text primary key,
  revision bigint not null default 0 check (revision >= 0),
  state jsonb not null,
  updated_at timestamptz not null default now()
);
create table public.orvr_events (
  campaign_id text not null references public.orvr_campaigns(id) on delete cascade,
  event_id bigint not null,
  event_type text not null,
  activation_id text,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  primary key (campaign_id, event_id)
);
alter table public.orvr_accounts enable row level security;
alter table public.orvr_characters enable row level security;
alter table public.orvr_campaigns enable row level security;
alter table public.orvr_events enable row level security;
revoke all on public.orvr_accounts, public.orvr_characters, public.orvr_campaigns, public.orvr_events from anon, authenticated;
grant select on public.orvr_accounts, public.orvr_characters to authenticated;
grant all on public.orvr_accounts, public.orvr_characters, public.orvr_campaigns, public.orvr_events to service_role;
create policy orvr_own_account on public.orvr_accounts for select to authenticated using (user_id = (select auth.uid()));
create policy orvr_own_characters on public.orvr_characters for select to authenticated using (user_id = (select auth.uid()));

-- A client may create a named recruit, but cannot switch realms, grant abilities or mutate progress.
create function public.create_orvr_character(p_name text, p_realm text) returns uuid
language plpgsql security definer set search_path = '' as $$
declare v_user uuid := auth.uid(); v_realm text; v_id uuid;
begin
  if v_user is null then raise exception 'Authentication required' using errcode = '42501'; end if;
  if p_realm not in ('aegis', 'riftbound') or p_realm is null or p_name is null or length(trim(p_name)) not between 2 and 32 then
    raise exception 'Invalid character';
  end if;
  insert into public.orvr_accounts(user_id, realm) values(v_user, p_realm) on conflict (user_id) do nothing;
  select realm into v_realm from public.orvr_accounts where user_id = v_user for update;
  if v_realm <> p_realm then raise exception 'This account belongs to another realm'; end if;
  if (select count(*) from public.orvr_characters where user_id = v_user) >= 8 then raise exception 'Character limit reached'; end if;
  insert into public.orvr_characters(user_id, name, realm) values(v_user, trim(p_name), v_realm) returning id into v_id;
  return v_id;
end $$;
revoke all on function public.create_orvr_character(text, text) from public, anon;
grant execute on function public.create_orvr_character(text, text) to authenticated;

-- Service-role-only CAS rejects competing authorities and stale writes atomically.
create function public.commit_orvr_campaign(p_id text, p_expected_revision bigint, p_state jsonb, p_events jsonb) returns bigint
language plpgsql security invoker set search_path = '' as $$
declare v_revision bigint; v_event jsonb;
begin
  if p_expected_revision < 0 or p_expected_revision is null or p_state->>'id' is distinct from p_id or p_state->>'version' is distinct from '1'
    or jsonb_typeof(p_events) is distinct from 'array' then raise exception 'Invalid campaign checkpoint'; end if;
  insert into public.orvr_campaigns(id, state) values(p_id, p_state) on conflict (id) do nothing;
  select revision into v_revision from public.orvr_campaigns where id = p_id for update;
  if v_revision <> p_expected_revision then raise exception 'Campaign write conflict' using errcode = '40001'; end if;
  for v_event in select value from jsonb_array_elements(p_events) loop
    if v_event->>'campaignId' is distinct from p_id or v_event->>'type' is null then raise exception 'Invalid campaign event'; end if;
    insert into public.orvr_events(campaign_id, event_id, event_type, activation_id, payload)
    values(p_id, (v_event->>'id')::bigint, v_event->>'type', v_event->>'activationId', v_event);
  end loop;
  update public.orvr_campaigns set revision = v_revision + 1, state = p_state, updated_at = now() where id = p_id;
  return v_revision + 1;
end $$;
revoke all on function public.commit_orvr_campaign(text, bigint, jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.commit_orvr_campaign(text, bigint, jsonb, jsonb) to service_role;
