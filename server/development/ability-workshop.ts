import { createHash } from 'node:crypto';
import type { SupabaseClient } from '@supabase/supabase-js';
import { validateWorkspace } from '../../shared/game/abilities/workshop/validation';

export class AbilityWorkshopError extends Error {
  constructor(readonly status: number, message: string) { super(message); }
}
export function canonicalCatalog(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalCatalog).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.entries(value).filter(([, item]) => item !== undefined).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)
    .map(([key, item]) => `${JSON.stringify(key)}:${canonicalCatalog(item)}`).join(',')}}`;
  return JSON.stringify(value);
}
export const catalogHash = (document: unknown) => createHash('sha256').update(canonicalCatalog(document)).digest('hex');

export async function prepareAbilityOperation(database: SupabaseClient, actor: string, action: string, input: Record<string, any>, requestId?: string): Promise<Record<string, any>> {
  const body = structuredClone(input);
  if (!['ability.save', 'ability.publish', 'ability.test', 'ability.deploy'].includes(action)) throw new AbilityWorkshopError(403, 'Operation is not available to clients.');
  if (requestId) {
    const { data: receipt, error } = await database.from('ability_receipts').select('action,body').eq('actor_id', actor).eq('request_id', requestId).maybeSingle();
    if (error) throw new AbilityWorkshopError(503, 'Could not reconcile the previous request.');
    if (receipt) {
      const previous = structuredClone(receipt.body);
      if (action === 'ability.publish' || action === 'ability.test') { delete previous.catalogHash; delete body.catalogHash; }
      if (receipt.action !== action || canonicalCatalog(previous) !== canonicalCatalog(body)) throw new AbilityWorkshopError(409, 'Request identity reused.');
      // ability_apply still checks current access before replaying this receipt.
      return receipt.body;
    }
  }
  if (action === 'ability.save') {
    if (body.document?.id !== body.id || body.document?.revision !== body.revision) throw new AbilityWorkshopError(400, 'Workspace identity/revision mismatch.');
    const issues = validateWorkspace(body.document);
    if (issues.length) throw new AbilityWorkshopError(400, JSON.stringify({ issues }));
    if (Buffer.byteLength(JSON.stringify(body.document)) > 8_000_000) throw new AbilityWorkshopError(413, 'Workspace exceeds 8 MB.');
  }
  if (action === 'ability.publish' || action === 'ability.test') {
    const { data: workspace, error } = await database.from('ability_workspaces').select('environment,revision,document').eq('id', body.workspaceId).single();
    if (error || !workspace) throw new AbilityWorkshopError(404, 'Workspace not found.');
    const permission = await database.rpc('ability_require', { p_actor: actor, p_environment: workspace.environment, p_capability: action === 'ability.publish' ? 'publish' : 'edit' });
    if (permission.error) throw new AbilityWorkshopError(403, 'Ability permission required.');
    // The database checks revision under lock as well, closing the validation/commit race.
    if (workspace.revision !== body.revision) throw new AbilityWorkshopError(409, 'Revision conflict.');
    const issues = validateWorkspace(workspace.document);
    if (issues.length) throw new AbilityWorkshopError(400, JSON.stringify({ issues }));
    body.catalogHash = catalogHash(workspace.document);
    if (action === 'ability.test') {
      if (!body.result || body.result.kind !== 'calculated' || body.result.catalogHash !== body.catalogHash || body.result.revision !== body.revision) {
        throw new AbilityWorkshopError(400, 'Client test reports must be calculated and identify the exact saved revision. Native evidence is server-owned.');
      }
    }
  }
  return body;
}
