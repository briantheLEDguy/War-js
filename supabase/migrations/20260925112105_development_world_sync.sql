-- Development authoring publications only. These are not active game checkpoints.
create table public.dev_world_heads (
  map text primary key check (length(map) between 7 and 256 and map ~ '^/Game/[A-Za-z0-9_/]+$'),
  revision integer not null check (revision > 0),
  document jsonb not null check (jsonb_typeof(document) = 'object'),
  author_id uuid not null references public.dev_members(user_id),
  updated_at timestamptz not null default now()
);
create table public.dev_world_versions (
  map text not null references public.dev_world_heads(map),
  revision integer not null,
  document jsonb not null,
  author_id uuid not null references public.dev_members(user_id),
  created_at timestamptz not null default now(),
  primary key(map, revision)
);
alter table public.dev_world_heads enable row level security;
alter table public.dev_world_versions enable row level security;
revoke all on public.dev_world_heads, public.dev_world_versions from public, anon, authenticated, service_role;
grant select, insert, update on public.dev_world_heads to service_role;
grant select, insert on public.dev_world_versions to service_role;

create function public.dev_world_sync(p_actor uuid, p_request uuid, p_body jsonb)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
  member public.dev_members; receipt public.dev_receipts; head public.dev_world_heads;
  world_map text; expected integer; result jsonb;
begin
  select * into member from public.dev_members where user_id=p_actor and status='approved' for update;
  if not found then raise exception 'Developer access required'; end if;
  world_map := p_body->>'map';
  if world_map is null or length(world_map) > 256 or world_map !~ '^/Game/[A-Za-z0-9_/]+$' then
    raise exception 'Invalid world map';
  end if;
  -- Serialize the absent-head case as well as updates from different actors.
  perform pg_advisory_xact_lock(hashtextextended('dev_world:' || world_map, 0));
  select * into head from public.dev_world_heads where map=world_map;
  if p_body->>'action' = 'read' then
    return jsonb_build_object('map',world_map,'revision',coalesce(head.revision,0),
      'document',head.document,'runtimeApplied',false);
  end if;
  if p_body->>'action' is distinct from 'publish' then raise exception 'Invalid world operation'; end if;
  if member.role <> 'owner' then raise exception 'Owner access required'; end if;
  if p_request is null then raise exception 'Invalid request'; end if;
  select * into receipt from public.dev_receipts where actor_id=p_actor and request_id=p_request;
  if found then
    if receipt.action <> 'world.publish' or receipt.body <> p_body then raise exception 'Request identity reused'; end if;
    return receipt.result;
  end if;
  expected := (p_body->>'revision')::integer;
  if expected is null or expected < 0 or expected <> coalesce(head.revision,0) then raise exception 'Revision conflict'; end if;
  if jsonb_typeof(p_body->'document') is distinct from 'object' or octet_length(p_body::text)>9000000 then
    raise exception 'Invalid world document';
  end if;
  insert into public.dev_world_heads(map,revision,document,author_id)
    values(world_map,expected+1,p_body->'document',p_actor)
    on conflict(map) do update set revision=excluded.revision,document=excluded.document,author_id=p_actor,updated_at=now();
  insert into public.dev_world_versions(map,revision,document,author_id)
    values(world_map,expected+1,p_body->'document',p_actor);
  result := jsonb_build_object('map',world_map,'revision',expected+1,'runtimeApplied',false);
  insert into public.dev_receipts(actor_id,request_id,action,body,result) values(p_actor,p_request,'world.publish',p_body,result);
  insert into public.dev_audit(actor_id,action,revision) values(p_actor,'world.publish',expected+1);
  return result;
end $$;
revoke all on function public.dev_world_sync(uuid,uuid,jsonb) from public, anon, authenticated;
grant execute on function public.dev_world_sync(uuid,uuid,jsonb) to service_role;
