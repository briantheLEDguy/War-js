import { createCampaign, type CampaignConfig, type CampaignState } from '../src/shared/orvr';

/** Match persisted JSON semantics while ignoring object/property insertion order. Array order remains meaningful. */
function canonicalJson(value: unknown): string {
  return JSON.stringify(value, (_key, item: unknown) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return item;
    return Object.fromEntries(Object.entries(item).sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0));
  }) ?? 'undefined';
}

function differences(saved: Record<string, unknown>, expected: Record<string, unknown>): string[] {
  return [...new Set([...Object.keys(saved), ...Object.keys(expected)])].sort()
    .filter(key => canonicalJson(saved[key]) !== canonicalJson(expected[key]));
}

function summarize(entries: string[]): string {
  const first = entries.slice(0, 8).join(', ');
  return entries.length > 8 ? `${first} (+${entries.length - 8} more)` : first;
}

/** Static definitions come from the current server build, never silently from an older checkpoint. */
export function assertCampaignConfigCompatible(saved: CampaignState, config: CampaignConfig): void {
  const expected = createCampaign(config);
  const problems: string[] = [];
  if (config.id !== undefined && config.id !== saved.id) problems.push(`campaign ID ${saved.id} differs from ${config.id}`);
  const zones: string[] = [];
  for (const id of [...new Set([...Object.keys(saved.zones), ...Object.keys(expected.zones)])].sort()) {
    const before = saved.zones[id]?.config;
    const after = expected.zones[id]?.config;
    if (!before || !after) { zones.push(`${id} (${before ? 'removed' : 'added'})`); continue; }
    const fields = differences(before as unknown as Record<string, unknown>, after as unknown as Record<string, unknown>);
    if (fields.length) zones.push(`${id} [${fields.join(', ')}]`);
  }
  if (zones.length) problems.push(`zone definitions: ${summarize(zones)}`);
  const abilities = differences(saved.abilities, expected.abilities);
  if (abilities.length) problems.push(`ability rules: ${summarize(abilities)}`);
  if (!problems.length) return;
  throw new Error(`Saved campaign configuration is incompatible with the current server (${problems.join('; ')}). `
    + 'The checkpoint has been preserved. Restore the matching map and ability build, or migrate the checkpoint explicitly before restarting. '
    + 'For a separate new campaign, use a new ORVR_CAMPAIGN_ID and a separate ORVR_CHECKPOINT path when using file storage.');
}
