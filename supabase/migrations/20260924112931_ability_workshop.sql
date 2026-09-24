-- Gateway-only ability authoring. Authenticated game clients never receive SQL grants.
create table public.ability_permissions (
  user_id uuid not null references public.dev_members(user_id),
  environment text not null check (environment ~ '^[a-z0-9_-]{1,64}$'),
  role text not null check (role in ('viewer','editor','publisher')),
  primary key(user_id,environment)
);
create table public.ability_workspaces (
  id uuid primary key,
  environment text not null,
  revision bigint not null check (revision > 0),
  document jsonb not null,
  updated_by uuid not null references public.dev_members(user_id),
  updated_at timestamptz not null default now()
);
create table public.ability_versions (
  id uuid primary key,
  workspace_id uuid not null references public.ability_workspaces(id),
  source_revision bigint not null,
  name text not null,
  catalog_hash text not null check (catalog_hash ~ '^[a-f0-9]{64}$'),
  build_id text not null check (build_id ~ '^[a-f0-9]{40}$'),
  content_id text not null check (content_id ~ '^[a-f0-9]{64}$'),
  document jsonb not null,
  author_id uuid not null references public.dev_members(user_id),
  created_at timestamptz not null default now()
);
create table public.ability_test_results (
  id uuid primary key,
  workspace_id uuid not null references public.ability_workspaces(id),
  revision bigint not null,
  catalog_hash text not null,
  result jsonb not null,
  author_id uuid not null references public.dev_members(user_id),
  created_at timestamptz not null default now()
);
create table public.ability_environments (
  id text primary key,
  active_version uuid references public.ability_versions(id)
);
create table public.ability_servers (
  id uuid primary key,
  run_id uuid not null unique references public.dev_runs(id),
  environment text not null references public.ability_environments(id),
  build_id text not null,
  content_id text not null,
  active_version uuid references public.ability_versions(id),
  last_seen timestamptz not null default now()
);
create table public.ability_deployments (
  id uuid primary key,
  environment text not null references public.ability_environments(id),
  version_id uuid not null references public.ability_versions(id),
  phase text not null check (phase in ('preparing','activating','active','failed')),
  servers jsonb not null,
  author_id uuid not null references public.dev_members(user_id),
  created_at timestamptz not null default now()
);
create unique index ability_one_pending_deployment on public.ability_deployments(environment)
  where phase in ('preparing','activating');
create table public.ability_receipts (
  actor_id uuid not null references public.dev_members(user_id), request_id uuid not null,
  action text not null, body jsonb not null, result jsonb not null,
  primary key(actor_id,request_id)
);
create table public.ability_audit (
  id bigint generated always as identity primary key,
  actor_id uuid not null references public.dev_members(user_id), action text not null,
  target_id uuid not null, result jsonb not null, at timestamptz not null default now()
);
alter table public.ability_permissions enable row level security;
alter table public.ability_workspaces enable row level security;
alter table public.ability_versions enable row level security;
alter table public.ability_test_results enable row level security;
alter table public.ability_environments enable row level security;
alter table public.ability_servers enable row level security;
alter table public.ability_deployments enable row level security;
alter table public.ability_receipts enable row level security;
alter table public.ability_audit enable row level security;
revoke all on public.ability_permissions, public.ability_workspaces, public.ability_versions,
  public.ability_test_results, public.ability_environments, public.ability_servers,
  public.ability_deployments, public.ability_receipts, public.ability_audit from public,anon,authenticated,service_role;
revoke all on sequence public.ability_audit_id_seq from public,anon,authenticated,service_role;
grant select,insert,update on public.ability_permissions, public.ability_workspaces,
  public.ability_environments, public.ability_servers, public.ability_deployments to service_role;
grant select,insert on public.ability_versions, public.ability_test_results, public.ability_receipts, public.ability_audit to service_role;
grant usage on sequence public.ability_audit_id_seq to service_role;

create function public.ability_require(p_actor uuid,p_environment text,p_capability text) returns void
language plpgsql security invoker set search_path=public,pg_temp as $$
declare member public.dev_members; access_role text;
begin
  select * into member from public.dev_members where user_id=p_actor for share;
  if not found or member.status<>'approved' then raise exception 'Approved ability access required'; end if;
  if member.role='owner' then return; end if;
  select role into access_role from public.ability_permissions where user_id=p_actor and environment=p_environment for share;
  if access_role is null or (p_capability='edit' and access_role not in ('editor','publisher'))
    or (p_capability='publish' and access_role<>'publisher') then raise exception 'Ability permission required'; end if;
end $$;

create function public.ability_apply(p_actor uuid,p_request uuid,p_action text,p_body jsonb) returns jsonb
language plpgsql security invoker set search_path=public,pg_temp as $$
declare
  target uuid := (p_body->>'id')::uuid; env text; expected bigint := (p_body->>'revision')::bigint;
  workspace public.ability_workspaces; version public.ability_versions; receipt public.ability_receipts;
  result jsonb; snapshot jsonb; server_states jsonb;
begin
  -- Serialize retries before reading the receipt; altered retries never become a second operation.
  perform pg_advisory_xact_lock(hashtext(p_actor::text||p_request::text));
  if p_action='ability.save' then
    -- Serialize the first save as well: a missing row cannot be locked FOR UPDATE.
    perform pg_advisory_xact_lock(hashtext('ability-workspace:'||target::text));
    env := p_body->>'environment';
    if env is null or env !~ '^[a-z0-9_-]{1,64}$' then raise exception 'Invalid environment'; end if;
    perform public.ability_require(p_actor,env,'edit');
  elsif p_action in ('ability.publish','ability.test') then
    select * into workspace from public.ability_workspaces where id=(p_body->>'workspaceId')::uuid for update;
    if not found then raise exception 'Workspace not found'; end if;
    env := workspace.environment;
    perform public.ability_require(p_actor,env,case when p_action='ability.publish' then 'publish' else 'edit' end);
  elsif p_action='ability.deploy' then
    select * into version from public.ability_versions where id=(p_body->>'versionId')::uuid;
    if not found then raise exception 'Version not found'; end if;
    select * into workspace from public.ability_workspaces where id=version.workspace_id;
    env := p_body->>'environment';
    if env is distinct from workspace.environment then raise exception 'Environment mismatch'; end if;
    perform public.ability_require(p_actor,env,'publish');
  else raise exception 'Unsupported ability operation'; end if;
  select * into receipt from public.ability_receipts where actor_id=p_actor and request_id=p_request;
  if found then
    if receipt.action<>p_action or receipt.body<>p_body then raise exception 'Request identity reused'; end if;
    return receipt.result;
  end if;
  if p_action='ability.save' then
    if jsonb_typeof(p_body->'document')<>'object' or octet_length((p_body->'document')::text)>8000000
      or (p_body->'document'->>'id')::uuid<>target or (p_body->'document'->>'revision')::bigint is distinct from expected then raise exception 'Invalid workspace document'; end if;
    select * into workspace from public.ability_workspaces where id=target for update;
    if found then
      if workspace.environment<>env then raise exception 'Environment mismatch'; end if;
      if workspace.revision is distinct from expected then raise exception 'Revision conflict'; end if;
    elsif expected is distinct from 0 then raise exception 'Revision conflict'; end if;
    snapshot := jsonb_set(p_body->'document','{revision}',to_jsonb(expected+1));
    insert into public.ability_workspaces(id,environment,revision,document,updated_by) values(target,env,expected+1,snapshot,p_actor)
      on conflict(id) do update set revision=excluded.revision,document=excluded.document,updated_by=p_actor,updated_at=now();
    insert into public.ability_environments(id) values(env) on conflict do nothing;
    result := jsonb_build_object('id',target,'revision',expected+1);
  elsif p_action='ability.publish' then
    if workspace.revision is distinct from expected then raise exception 'Revision conflict'; end if;
    if coalesce(length(trim(p_body->>'name')),0) not between 1 and 80 then raise exception 'Invalid version name'; end if;
    insert into public.ability_versions(id,workspace_id,source_revision,name,catalog_hash,build_id,content_id,document,author_id)
      values(target,workspace.id,expected,p_body->>'name',p_body->>'catalogHash',workspace.document->>'buildId',workspace.document->>'contentId',workspace.document,p_actor);
    result := jsonb_build_object('id',target,'revision',expected,'catalogHash',p_body->>'catalogHash');
  elsif p_action='ability.test' then
    if workspace.revision is distinct from expected then raise exception 'Revision conflict'; end if;
    insert into public.ability_test_results(id,workspace_id,revision,catalog_hash,result,author_id)
      values(target,workspace.id,expected,p_body->>'catalogHash',p_body->'result',p_actor);
    result := jsonb_build_object('id',target,'revision',expected);
  elsif p_action='ability.deploy' then
    perform 1 from public.ability_environments where id=env for update;
    if exists(select 1 from public.ability_deployments where environment=env and phase in ('preparing','activating')) then raise exception 'Deployment already pending'; end if;
    if not exists(select 1 from public.ability_servers where environment=env) then raise exception 'No admitted servers available'; end if;
    if exists(select 1 from public.ability_servers s left join public.dev_runs r on r.id=s.run_id where s.environment=env and
      (s.build_id<>version.build_id or s.content_id<>version.content_id or s.last_seen<now()-interval '15 seconds' or r.lease_until is null or r.lease_until<now() or r.closed is distinct from false)) then raise exception 'Incompatible or unavailable server'; end if;
    select jsonb_object_agg(id::text,jsonb_build_object('state','pending')) into server_states from public.ability_servers where environment=env;
    insert into public.ability_deployments(id,environment,version_id,phase,servers,author_id) values(target,env,version.id,'preparing',server_states,p_actor);
    result := jsonb_build_object('id',target,'phase','preparing','servers',server_states);
  end if;
  insert into public.ability_receipts values(p_actor,p_request,p_action,p_body,result);
  insert into public.ability_audit(actor_id,action,target_id,result) values(p_actor,p_action,target,result);
  return result;
end $$;

create function public.ability_read(p_actor uuid,p_environment text,p_kind text,p_id uuid default null) returns jsonb
language plpgsql security invoker set search_path=public,pg_temp as $$
declare result jsonb;
begin
  perform public.ability_require(p_actor,p_environment,'view');
  if p_kind='workspaces' then
    select coalesce(jsonb_agg(case when p_id is null then to_jsonb(t)-'document' else to_jsonb(t) end),'[]') into result from (select * from public.ability_workspaces where environment=p_environment and (p_id is null or id=p_id) order by updated_at desc limit 100) t;
  elsif p_kind='versions' then
    select coalesce(jsonb_agg(case when p_id is null then to_jsonb(t)-'document' else to_jsonb(t) end),'[]') into result from (select v.* from public.ability_versions v join public.ability_workspaces w on w.id=v.workspace_id where w.environment=p_environment and (p_id is null or v.id=p_id) order by v.created_at desc limit 100) t;
  elsif p_kind='deployments' then
    select coalesce(jsonb_agg(to_jsonb(t)),'[]') into result from (select * from public.ability_deployments where environment=p_environment and (p_id is null or id=p_id) order by created_at desc limit 100) t;
  elsif p_kind='tests' then
    select coalesce(jsonb_agg(case when p_id is null then to_jsonb(t)-'result' else to_jsonb(t) end),'[]') into result from (select r.* from public.ability_test_results r join public.ability_workspaces w on w.id=r.workspace_id where w.environment=p_environment and (p_id is null or r.id=p_id) order by r.created_at desc limit 100) t;
  else raise exception 'Unknown ability collection'; end if;
  return result;
end $$;

-- Called only by the loopback gateway bound to this exact run/server, never by client operations.
create function public.ability_server(p_run uuid,p_server uuid,p_epoch bigint,p_environment text,p_deployment uuid default null,p_state text default null,p_message text default '') returns jsonb
language plpgsql security invoker set search_path=public,pg_temp as $$
declare run public.dev_runs; deployment public.ability_deployments; version public.ability_versions; current_state text;
begin
  select * into run from public.dev_runs where id=p_run for update;
  if not found or run.server_id is distinct from p_server or run.epoch is distinct from p_epoch or run.lease_until is null or run.lease_until<now() or run.closed is distinct from false then raise exception 'Writer lease required'; end if;
  if not exists(select 1 from public.ability_environments where id=p_environment) then raise exception 'Environment not found'; end if;
  insert into public.ability_servers(id,run_id,environment,build_id,content_id) values(p_server,p_run,p_environment,run.build_id,run.content_id)
    on conflict(id) do update set last_seen=now() where ability_servers.run_id=p_run and ability_servers.environment=p_environment;
  if not found then raise exception 'Server binding mismatch'; end if;
  if p_deployment is not null then
    select * into deployment from public.ability_deployments where id=p_deployment and environment=p_environment for update;
    if not found or not deployment.servers ? p_server::text then raise exception 'Deployment/server not found'; end if;
    current_state := deployment.servers->p_server::text->>'state';
    if p_state='prepared' and current_state='pending' and deployment.phase='preparing' then
      deployment.servers := jsonb_set(deployment.servers,array[p_server::text],jsonb_build_object('state','prepared'));
      if not exists(select 1 from jsonb_each(deployment.servers) s where s.value->>'state'<>'prepared') then deployment.phase := 'activating'; end if;
    elsif p_state='active' and current_state='prepared' and deployment.phase='activating' then
      deployment.servers := jsonb_set(deployment.servers,array[p_server::text],jsonb_build_object('state','active'));
      update public.ability_servers set active_version=deployment.version_id where id=p_server;
      if not exists(select 1 from jsonb_each(deployment.servers) s where s.value->>'state'<>'active') then
        deployment.phase := 'active'; update public.ability_environments set active_version=deployment.version_id where id=p_environment;
      end if;
    elsif p_state='failed' and deployment.phase in ('preparing','activating') then
      deployment.phase := 'failed'; deployment.servers := jsonb_set(deployment.servers,array[p_server::text],jsonb_build_object('state','failed','message',left(p_message,500)));
    elsif p_state is distinct from current_state then raise exception 'Invalid deployment transition'; end if;
    update public.ability_deployments set servers=deployment.servers,phase=deployment.phase where id=deployment.id;
  end if;
  select * into deployment from public.ability_deployments where environment=p_environment and phase in ('preparing','activating') order by created_at desc limit 1;
  if not found then return jsonb_build_object('phase','idle'); end if;
  select * into version from public.ability_versions where id=deployment.version_id;
  return jsonb_build_object('id',deployment.id,'phase',deployment.phase,'state',deployment.servers->p_server::text->>'state','versionId',version.id,'catalogHash',version.catalog_hash,'document',version.document);
end $$;

revoke all on function public.ability_require(uuid,text,text),public.ability_apply(uuid,uuid,text,jsonb),
  public.ability_read(uuid,text,text,uuid),public.ability_server(uuid,uuid,bigint,text,uuid,text,text) from public,anon,authenticated;
grant execute on function public.ability_require(uuid,text,text),public.ability_apply(uuid,uuid,text,jsonb),
  public.ability_read(uuid,text,text,uuid),public.ability_server(uuid,uuid,bigint,text,uuid,text,text) to service_role;
