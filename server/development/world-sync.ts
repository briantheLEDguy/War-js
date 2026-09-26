/** Transport validation complements native validation against installed model templates.
 * A publication is an authoring snapshot, never proof of runtime deployment. */
export function validateWorldSync(input: unknown): Record<string, unknown> {
  const object = (value: unknown): Record<string, any> => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Expected a world document object.');
    return value as Record<string, any>;
  };
  const body = object(input);
  if (typeof body.map !== 'string' || body.map.length > 256 || !/^\/Game\/[A-Za-z0-9_/]+$/.test(body.map)) throw new Error('Invalid world map.');
  if (body.action === 'read') return { action: 'read', map: body.map };
  if (body.action !== 'publish' || !Number.isInteger(body.revision) || body.revision < 0 || body.revision >= 2_147_483_647) throw new Error('Invalid world operation or revision.');
  const doc = object(body.document);
  if (doc.schemaVersion !== 2 || doc.zoneId !== 'aegis_capital' || typeof doc.baseline !== 'string'
    || Buffer.byteLength(JSON.stringify(doc)) > 8_000_000) throw new Error('Unsupported or oversized native world document.');
  const rows = (value: unknown, baseline: boolean) => {
    if (!Array.isArray(value) || value.length < 1 || value.length > (baseline ? 10000 : 11000)) throw new Error('Invalid world object count.');
    const ids = new Map<string, Record<string, any>>();
    for (const entry of value) {
      const row = object(entry);
      if (typeof row.id !== 'string' || !row.id.length || row.id.length > 128 || row.id.toLowerCase() === 'none'
        || ids.has(row.id.toLowerCase()) || typeof row.hidden !== 'boolean'
        || typeof row.sourceIdentity !== 'string' || row.sourceIdentity.length > 512
        || (row.templateId !== undefined && (baseline || typeof row.templateId !== 'string' || !row.templateId.length))) throw new Error('Invalid world object identity.');
      const t = row.transform;
      if (!Array.isArray(t) || t.length !== 10 || !t.every(v => typeof v === 'number' && Number.isFinite(v))
        || t.slice(0,3).some(v => Math.abs(v) > 100000)
        || Math.abs(t.slice(3,7).reduce((sum, v) => sum + v*v, 0) - 1) > 0.0001
        || t.slice(7).some(v => Math.abs(v) < 0.05 || Math.abs(v) > 20)) throw new Error('Invalid world transform.');
      ids.set(row.id.toLowerCase(), row);
    }
    return ids;
  };
  let baseline: Record<string, any>;
  try { baseline = object(JSON.parse(doc.baseline)); } catch { throw new Error('Invalid authored baseline.'); }
  const original = rows(baseline.objects, true), current = rows(doc.objects, false);
  if (current.size > original.size + 1000) throw new Error('Too many created world objects.');
  for (const id of original.keys()) if (!current.has(id)) throw new Error('Missing authored world object.');
  for (const [id, row] of current) {
    const source = original.get((row.templateId ?? row.id).toLowerCase());
    if (!source || source.sourceIdentity !== row.sourceIdentity || (original.has(id) && row.templateId !== undefined)) throw new Error('Invalid world model template.');
  }
  return { action: 'publish', map: body.map, revision: body.revision, document: doc };
}
