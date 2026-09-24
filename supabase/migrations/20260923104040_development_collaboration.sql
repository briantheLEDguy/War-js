-- Dedicated development project only. All mutations pass through the trusted
-- gateway; authenticated game clients have no direct table or RPC privileges.
create table public.dev_members (
  user_id uuid primary key references auth.users(id),
  github_id text not null unique,
  status text not null default 'pending' check (status in ('pending','approved','revoked')),
  role text not null default 'developer' check (role in ('owner','developer')),
  generation bigint not null default 0,
  created_at timestamptz not null default now()
);
create unique index dev_single_owner on public.dev_members(role) where role = 'owner';
create table public.dev_drafts (
  id uuid primary key,
  owner_id uuid not null references public.dev_members(user_id),
  revision bigint not null check (revision > 0),
  document jsonb not null check (jsonb_typeof(document) = 'object'),
  updated_at timestamptz not null default now()
);
create table public.dev_versions (
  id uuid primary key,
  author_id uuid not null references public.dev_members(user_id),
  name text not null check (length(name) between 1 and 80),
  source_id uuid not null,
  source_revision bigint not null,
  build_id text not null,
  content_id text not null,
  document jsonb not null,
  created_at timestamptz not null default now()
);
create table public.dev_runs (
  id uuid primary key,
  version_id uuid not null references public.dev_versions(id),
  revision bigint not null default 0,
  document jsonb not null,
  server_id uuid,
  epoch bigint not null default 0,
  lease_until timestamptz,
  build_id text not null,
  content_id text not null,
  closed boolean not null default false
);
create table public.dev_receipts (
  actor_id uuid not null references public.dev_members(user_id),
  request_id uuid not null,
  action text not null,
  body jsonb not null,
  result jsonb not null,
  created_at timestamptz not null default now(),
  primary key(actor_id, request_id)
);
create table public.dev_audit (
  id bigint generated always as identity primary key,
  actor_id uuid not null references public.dev_members(user_id),
  action text not null,
  target_id uuid,
  revision bigint,
  created_at timestamptz not null default now()
);
create table public.dev_join_tickets (
  digest text primary key check (digest ~ '^[0-9a-f]{64}$'),
  user_id uuid not null references public.dev_members(user_id),
  run_id uuid not null references public.dev_runs(id),
  character_id uuid not null references public.dev_drafts(id),
  generation bigint not null,
  expires_at timestamptz not null,
  consumed boolean not null default false
);
alter table public.dev_members enable row level security;
alter table public.dev_drafts enable row level security;
alter table public.dev_versions enable row level security;
alter table public.dev_runs enable row level security;
alter table public.dev_receipts enable row level security;
alter table public.dev_audit enable row level security;
alter table public.dev_join_tickets enable row level security;
revoke all on public.dev_members, public.dev_drafts, public.dev_versions,
  public.dev_runs, public.dev_receipts, public.dev_audit, public.dev_join_tickets from public, anon, authenticated, service_role;
revoke all on sequence public.dev_audit_id_seq from public, anon, authenticated, service_role;
grant select, insert, update on public.dev_members, public.dev_drafts, public.dev_runs,
  public.dev_join_tickets to service_role;
grant select, insert on public.dev_versions, public.dev_receipts, public.dev_audit to service_role;
grant usage on sequence public.dev_audit_id_seq to service_role;

create function public.dev_set_member(p_actor uuid, p_target uuid, p_status text)
returns void language plpgsql security invoker set search_path = '' as $$
begin
  perform 1 from public.dev_members where user_id=p_actor and role='owner' and status='approved' for update;
  if not found then raise exception 'Owner access required'; end if;
  if p_status not in ('approved','revoked') then raise exception 'Invalid status'; end if;
  update public.dev_members set status=p_status, generation=generation+1
    where user_id=p_target and role <> 'owner';
  if not found then raise exception 'Developer not found'; end if;
  insert into public.dev_audit(actor_id,action,target_id) values(p_actor,'access.'||p_status,p_target);
end $$;

-- Identity is verified by Supabase Auth before the gateway supplies p_actor.
-- Locking membership serializes revocation with writes. A replay is checked
-- before CAS, so a lost acknowledgement can be retried without duplication.
create function public.dev_apply(p_actor uuid, p_request uuid, p_action text, p_body jsonb)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
  receipt public.dev_receipts; draft public.dev_drafts; version public.dev_versions;
  run public.dev_runs; target uuid; expected bigint; result jsonb;
begin
  perform 1 from public.dev_members where user_id=p_actor and status='approved' for update;
  if not found then raise exception 'Developer access required'; end if;
  select * into receipt from public.dev_receipts where actor_id=p_actor and request_id=p_request;
  if found then
    if receipt.action <> p_action or receipt.body <> p_body then raise exception 'Request identity reused'; end if;
    return receipt.result;
  end if;
  if p_request is null or jsonb_typeof(p_body) <> 'object' or octet_length(p_body::text)>9000000 then
    raise exception 'Invalid request';
  end if;
  target := (p_body->>'id')::uuid;
  if target is null then raise exception 'Missing identity'; end if;
  expected := (p_body->>'revision')::bigint;
  if p_action = 'draft.save' then
    if expected is null or expected < 0 or jsonb_typeof(p_body->'document') is distinct from 'object' then
      raise exception 'Invalid draft';
    end if;
    select * into draft from public.dev_drafts where id=target for update;
    if found then
      if draft.owner_id <> p_actor then raise exception 'Draft ownership required'; end if;
      if draft.revision <> expected then raise exception 'Revision conflict'; end if;
      update public.dev_drafts set revision=revision+1, document=p_body->'document', updated_at=now() where id=target;
    else
      if expected <> 0 then raise exception 'Revision conflict'; end if;
      insert into public.dev_drafts(id,owner_id,revision,document) values(target,p_actor,1,p_body->'document');
    end if;
    result := jsonb_build_object('id',target,'revision',expected+1);
  elsif p_action = 'version.publish' then
    select * into draft from public.dev_drafts where id=(p_body->>'sourceId')::uuid for update;
    if not found or draft.owner_id <> p_actor then raise exception 'Draft ownership required'; end if;
    if expected is null or draft.revision <> expected then raise exception 'Revision conflict'; end if;
    if coalesce(p_body->>'buildId','')='' or coalesce(p_body->>'contentId','')='' then raise exception 'Missing compatibility identity'; end if;
    insert into public.dev_versions(id,author_id,name,source_id,source_revision,build_id,content_id,document)
      values(target,p_actor,p_body->>'name',draft.id,draft.revision,p_body->>'buildId',p_body->>'contentId',draft.document);
    result := jsonb_build_object('id',target,'revision',draft.revision);
  elsif p_action = 'version.fork' then
    select * into version from public.dev_versions where id=(p_body->>'sourceId')::uuid;
    if not found then raise exception 'Version not found'; end if;
    insert into public.dev_drafts(id,owner_id,revision,document) values(target,p_actor,1,version.document);
    result := jsonb_build_object('id',target,'revision',1);
  elsif p_action = 'run.create' then
    select * into version from public.dev_versions where id=(p_body->>'sourceId')::uuid;
    if not found then raise exception 'Version not found'; end if;
    insert into public.dev_runs(id,version_id,document,build_id,content_id)
      values(target,version.id,version.document,version.build_id,version.content_id);
    result := jsonb_build_object('id',target,'revision',0);
  elsif p_action = 'run.checkpoint' then
    select * into run from public.dev_runs where id=target for update;
    if not found or run.closed or run.server_id is distinct from (p_body->>'serverId')::uuid
      or run.epoch is distinct from (p_body->>'epoch')::bigint or run.lease_until is null or run.lease_until <= clock_timestamp() then
      raise exception 'Writer lease required';
    end if;
    if expected is null or run.revision <> expected then raise exception 'Revision conflict'; end if;
    if jsonb_typeof(p_body->'document') is distinct from 'object' then raise exception 'Invalid checkpoint'; end if;
    update public.dev_runs set revision=revision+1, document=p_body->'document' where id=target;
    result := jsonb_build_object('id',target,'revision',expected+1);
  elsif p_action = 'run.publish' then
    select * into run from public.dev_runs where id=(p_body->>'sourceId')::uuid for update;
    if not found then raise exception 'Run not found'; end if;
    if expected is null or run.revision <> expected then raise exception 'Revision conflict'; end if;
    insert into public.dev_versions(id,author_id,name,source_id,source_revision,build_id,content_id,document)
      values(target,p_actor,p_body->>'name',run.id,run.revision,run.build_id,run.content_id,run.document);
    result := jsonb_build_object('id',target,'revision',run.revision);
  else raise exception 'Unknown operation';
  end if;
  insert into public.dev_receipts(actor_id,request_id,action,body,result) values(p_actor,p_request,p_action,p_body,result);
  insert into public.dev_audit(actor_id,action,target_id,revision) values(p_actor,p_action,target,(result->>'revision')::bigint);
  return result;
end $$;

create function public.dev_claim_run(p_run uuid, p_server uuid, p_epoch bigint)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare run public.dev_runs;
begin
  select * into run from public.dev_runs where id=p_run for update;
  if not found or run.closed or p_server is null then raise exception 'Run unavailable'; end if;
  if run.lease_until > clock_timestamp() then
    if run.server_id is distinct from p_server or run.epoch is distinct from p_epoch then raise exception 'Run already claimed'; end if;
  else
    run.epoch := run.epoch+1;
  end if;
  update public.dev_runs set server_id=p_server, epoch=run.epoch, lease_until=clock_timestamp()+interval '15 seconds' where id=p_run;
  return jsonb_build_object('epoch',run.epoch,'revision',run.revision,'document',run.document,
    'buildId',run.build_id,'contentId',run.content_id);
end $$;

create function public.dev_issue_ticket(p_actor uuid,p_run uuid,p_character uuid,p_digest text,p_build text,p_content text)
returns void language plpgsql security invoker set search_path = '' as $$
declare member public.dev_members; run public.dev_runs;
begin
  select * into member from public.dev_members where user_id=p_actor and status='approved' for update;
  if not found then raise exception 'Developer access required'; end if;
  perform 1 from public.dev_drafts where id=p_character and owner_id=p_actor;
  if not found then raise exception 'Character ownership required'; end if;
  select * into run from public.dev_runs where id=p_run;
  if not found or run.closed or run.lease_until is null or run.lease_until <= clock_timestamp() then raise exception 'Run unavailable'; end if;
  if run.build_id is distinct from p_build or run.content_id is distinct from p_content then raise exception 'Incompatible build or content'; end if;
  insert into public.dev_join_tickets(digest,user_id,run_id,character_id,generation,expires_at)
    values(p_digest,p_actor,p_run,p_character,member.generation,clock_timestamp()+interval '60 seconds');
end $$;

create function public.dev_consume_ticket(p_digest text,p_run uuid,p_server uuid,p_epoch bigint)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare ticket public.dev_join_tickets; member public.dev_members; run public.dev_runs;
begin
  select * into ticket from public.dev_join_tickets where digest=p_digest for update;
  if not found or ticket.consumed or ticket.expires_at <= clock_timestamp() or ticket.run_id <> p_run then raise exception 'Invalid join ticket'; end if;
  select * into member from public.dev_members where user_id=ticket.user_id and status='approved' for share;
  if not found or member.generation <> ticket.generation then raise exception 'Developer access revoked'; end if;
  select * into run from public.dev_runs where id=p_run for share;
  if not found or run.closed or run.server_id is distinct from p_server or run.epoch is distinct from p_epoch
    or run.lease_until is null or run.lease_until <= clock_timestamp() then raise exception 'Writer lease required'; end if;
  update public.dev_join_tickets set consumed=true where digest=p_digest;
  return jsonb_build_object('userId',ticket.user_id,'characterId',ticket.character_id,'generation',member.generation,
    'runId',p_run,'epoch',p_epoch,'role',member.role);
end $$;
revoke all on function public.dev_set_member(uuid,uuid,text), public.dev_apply(uuid,uuid,text,jsonb),
  public.dev_claim_run(uuid,uuid,bigint), public.dev_issue_ticket(uuid,uuid,uuid,text,text,text),
  public.dev_consume_ticket(text,uuid,uuid,bigint) from public, anon, authenticated;
grant execute on function public.dev_set_member(uuid,uuid,text), public.dev_apply(uuid,uuid,text,jsonb),
  public.dev_claim_run(uuid,uuid,bigint), public.dev_issue_ticket(uuid,uuid,uuid,text,text,text),
  public.dev_consume_ticket(text,uuid,uuid,bigint) to service_role;
