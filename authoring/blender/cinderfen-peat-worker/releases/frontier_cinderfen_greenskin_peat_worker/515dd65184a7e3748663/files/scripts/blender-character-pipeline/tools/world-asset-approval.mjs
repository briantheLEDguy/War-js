import fs from 'node:fs';
import { createHash } from 'node:crypto';

/** Record the user's standing art approval without claiming a new visual inspection. */
export function standingWorldAssetApproval(evidence) {
  const bytes = fs.readFileSync(new URL('../data/world-asset-approval.json', import.meta.url));
  const instruction = JSON.parse(bytes);
  return {
    status: 'approved', reviewedBy: instruction.approvedBy, reviewedAt: instruction.approvedAt,
    basis: 'explicit_user_standing_approval',
    instructionSha256: createHash('sha256').update(bytes).digest('hex'),
    notes: instruction.instruction,
    evidence,
  };
}
