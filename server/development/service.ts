import { createHash, randomBytes, randomUUID } from 'node:crypto';
import type { SupabaseClient } from '@supabase/supabase-js';
import { AbilityWorkshopError, prepareAbilityOperation } from './ability-workshop';

export class DevelopmentError extends Error {
  constructor(readonly status: number, message: string) { super(message); }
}
export interface Member { user_id: string; github_id: string; status: string; role: string; generation: number }
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export function uuid(value: unknown): string {
  if (typeof value !== 'string' || !uuidPattern.test(value)) throw new DevelopmentError(400, 'Invalid identity.');
  return value;
}
export function record(value: unknown): Record<string, any> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new DevelopmentError(400, 'Expected an object.');
  return value as Record<string, any>;
}
export function document(value: unknown): Record<string, any> {
  const data = record(value);
  if (data.schemaVersion !== 1 || !['world', 'character'].includes(data.kind)
    || typeof data.buildId !== 'string' || !/^[0-9a-f]{40}$/.test(data.buildId)
    || typeof data.contentId !== 'string' || !/^[0-9a-f]{64}$/.test(data.contentId)) {
    throw new DevelopmentError(400, 'Invalid development document or compatibility identity.');
  }
  record(data.payload);
  if (Buffer.byteLength(JSON.stringify(data)) > 8_000_000) throw new DevelopmentError(413, 'Document too large.');
  return data;
}
export const ticketDigest = (value: string) => createHash('sha256').update(value).digest('hex');

/** Only the isolated gateway owns this service-role client. No client-supplied
 * account ID, metadata role or development flag is an authorization source. */
export class DevelopmentService {
  constructor(private readonly database: SupabaseClient, readonly admissionOpen = false) {}
  private async rpc(name: string, args: Record<string, unknown>): Promise<any> {
    const { data, error } = await this.database.rpc(name, args);
    if (error) {
      if (/conflict|claimed|reused/i.test(error.message)) throw new DevelopmentError(409, error.message);
      if (/required|revoked|ownership|ticket|Incompatible/i.test(error.message)) throw new DevelopmentError(403, error.message);
      if (/not found|unavailable/i.test(error.message)) throw new DevelopmentError(404, error.message);
      throw new DevelopmentError(503, 'Persistence unavailable; success has not been acknowledged.');
    }
    return data;
  }
  async identity(token: string): Promise<Member> {
    const { data, error } = await this.database.auth.getUser(token);
    const identity = data.user?.identities?.find(value => value.provider === 'github');
    if (error || !data.user || !identity || !identity.id) throw new DevelopmentError(401, 'Verified GitHub sign-in required.');
    const userId = uuid(data.user.id);
    // Provider identity is returned by the Auth server, not user_metadata.
    const { error: registrationError } = await this.database.from('dev_members').upsert(
      { user_id: userId, github_id: identity.id }, { onConflict: 'user_id', ignoreDuplicates: true });
    if (registrationError) throw new DevelopmentError(503, 'Could not register development identity.');
    const member = await this.member(userId, false);
    if (member.github_id !== identity.id) throw new DevelopmentError(403, 'Identity linkage changed; owner review required.');
    return member;
  }
  async member(userId: string, requireApproved = true): Promise<Member> {
    const { data, error } = await this.database.from('dev_members').select('*').eq('user_id', uuid(userId)).single();
    if (error || !data) throw new DevelopmentError(403, 'Developer access unavailable.');
    if (requireApproved && data.status !== 'approved') throw new DevelopmentError(403, 'Developer approval required.');
    return data as Member;
  }
  async userOperation(member: Member, requestId: string, action: string, input: unknown): Promise<any> {
    await this.member(member.user_id);
    const body = record(input);
    uuid(body.id);
    if (action.startsWith('ability.')) {
      if (['ability.publish', 'ability.deploy'].includes(action) && !this.admissionOpen) throw new DevelopmentError(503, 'Shared ability publication and deployment remain closed pending native admission and GM authorization acceptance.');
      try {
        const prepared = await prepareAbilityOperation(this.database, member.user_id, action, body, uuid(requestId));
        return await this.rpc('ability_apply', { p_actor: member.user_id, p_request: uuid(requestId), p_action: action, p_body: prepared });
      } catch (error) {
        if (error instanceof AbilityWorkshopError) throw new DevelopmentError(error.status, error.message);
        throw error;
      }
    }
    // Writer lease credentials never enter the public API.
    if (!['draft.save', 'version.publish', 'version.fork', 'run.create', 'run.publish'].includes(action)) {
      throw new DevelopmentError(403, 'Operation is not available to clients.');
    }
    if (action === 'draft.save') document(body.document);
    if (action.endsWith('publish')) {
      if (typeof body.name !== 'string' || !body.name.trim() || body.name.length > 80) throw new DevelopmentError(400, 'Invalid version name.');
    }
    return this.rpc('dev_apply', { p_actor: member.user_id, p_request: uuid(requestId), p_action: action, p_body: body });
  }
  async read(member: Member, kind: string, id?: string): Promise<unknown> {
    await this.member(member.user_id);
    if (!['drafts', 'versions', 'runs'].includes(kind)) throw new DevelopmentError(404, 'Unknown collection.');
    // Shared-run state is delivered by Unreal to its admitted participants.
    const fields = kind === 'runs' ? 'id,version_id,revision,build_id,content_id,closed' : '*';
    let query = this.database.from(`dev_${kind}`).select(fields);
    if (kind === 'drafts') query = query.eq('owner_id', member.user_id);
    if (id) query = query.eq('id', uuid(id));
    const { data, error } = await query.limit(100);
    if (error) throw new DevelopmentError(503, 'Could not load development data.');
    return data;
  }
  async issue(member: Member, input: unknown): Promise<unknown> {
    if (!this.admissionOpen) throw new DevelopmentError(503, 'Remote development admission remains closed pending acceptance.');
    const body = record(input), ticket = randomBytes(32).toString('base64url');
    await this.rpc('dev_issue_ticket', { p_actor: member.user_id, p_run: uuid(body.runId),
      p_character: uuid(body.characterId), p_digest: ticketDigest(ticket), p_build: body.buildId, p_content: body.contentId });
    return { ticket, expiresInSeconds: 60 };
  }
  async readAbilities(member: Member, environment: string, kind: string, id?: string): Promise<unknown> {
    if (!/^[a-z0-9_-]{1,64}$/.test(environment) || !['workspaces', 'versions', 'deployments', 'tests'].includes(kind)) throw new DevelopmentError(400, 'Invalid ability collection.');
    return this.rpc('ability_read', { p_actor: member.user_id, p_environment: environment, p_kind: kind, p_id: id ? uuid(id) : null });
  }
  async abilityServer(runId: string, serverId: string, input: unknown): Promise<unknown> {
    const body = record(input);
    if (!Number.isSafeInteger(body.epoch) || body.epoch < 1 || typeof body.environment !== 'string' || !/^[a-z0-9_-]{1,64}$/.test(body.environment)) throw new DevelopmentError(400, 'Invalid ability server lease.');
    return this.rpc('ability_server', { p_run: uuid(runId), p_server: uuid(serverId), p_epoch: body.epoch,
      p_environment: body.environment, p_deployment: body.deploymentId ? uuid(body.deploymentId) : null,
      p_state: body.state ?? null, p_message: typeof body.message === 'string' ? body.message.slice(0, 500) : '' });
  }
  async claim(runId: string, serverId: string, epoch: number): Promise<any> {
    return this.rpc('dev_claim_run', { p_run: uuid(runId), p_server: uuid(serverId), p_epoch: epoch });
  }
  async consume(ticket: string, runId: string, serverId: string, epoch: number): Promise<any> {
    if (!this.admissionOpen) throw new DevelopmentError(503, 'Remote admission is closed.');
    if (typeof ticket !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(ticket)) throw new DevelopmentError(403, 'Invalid join ticket.');
    return this.rpc('dev_consume_ticket', { p_digest: ticketDigest(ticket), p_run: uuid(runId), p_server: uuid(serverId), p_epoch: epoch });
  }
  async checkpoint(actorId: string, runId: string, serverId: string, epoch: number,
    revision: number, snapshot: unknown, requestId = randomUUID()): Promise<any> {
    return this.rpc('dev_apply', { p_actor: uuid(actorId), p_request: uuid(requestId), p_action: 'run.checkpoint',
      p_body: { id: uuid(runId), serverId: uuid(serverId), epoch, revision, document: record(snapshot) } });
  }
}
