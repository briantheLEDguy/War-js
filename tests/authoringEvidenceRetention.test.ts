import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, test } from 'vitest';

const readJson = (file: string) => JSON.parse(readFileSync(file, 'utf8'));
const approvedDirectory = 'scripts/blender-character-pipeline/data/approved-assets';
const provenanceRecords = readdirSync(approvedDirectory).filter(file => file.endsWith('.json'))
  .map(file => readJson(path.join(approvedDirectory, file)).provenance)
  .filter(record => record?.evidenceArchive);
const fileHashes = new Map<string, string>();
function digest(file: string): string {
  if (!fileHashes.has(file)) fileHashes.set(file, createHash('sha256').update(readFileSync(file)).digest('hex'));
  return fileHashes.get(file)!;
}

function imageDigest(file: string): string {
  const bytes = readFileSync(file);
  // Unhydrated Git LFS checkouts retain the image's SHA256 in the pointer.
  const pointer = bytes.length < 256
    ? /^version https:\/\/git-lfs.github.com\/spec\/v1\r?\noid sha256:([a-f0-9]{64})\r?\nsize \d+\r?\n?$/.exec(bytes.toString('utf8'))
    : null;
  return pointer?.[1] ?? createHash('sha256').update(bytes).digest('hex');
}

describe('evidence retained through repository cleanup', () => {
  test('preserves the exact archived reports and source records required by current approvals', () => {
    expect(provenanceRecords.length).toBeGreaterThan(0);
    for (const record of provenanceRecords) {
      for (const [filename, key] of [
        ['validation_report.json', 'validationReportSha256'],
        ['runtime_report.json', 'runtimeReportSha256'],
        ['visual_review.json', 'visualReviewSha256'],
      ]) {
        const file = path.join(record.evidenceArchive, filename);
        expect(digest(file), file).toBe(record[key]);
      }
      for (const source of record.sourceRecords ?? []) {
        const file = path.join(record.evidenceArchive, source.file.replaceAll('\\', '/'));
        expect(digest(file), file).toBe(source.sha256);
      }
    }
  });

  test('retains every byte-bound input in approved source ledgers', () => {
    const ledgers = new Map<string, string>();
    for (const record of provenanceRecords) if (record.sourceLedger) {
      expect(digest(record.sourceLedger), record.sourceLedger).toBe(record.sourceLedgerSha256);
      ledgers.set(record.sourceLedger, path.dirname(record.sourceLedger));
    }
    expect(ledgers.size).toBeGreaterThan(0);
    for (const [ledger, directory] of ledgers) {
      const files = readJson(ledger).files as Record<string, { sha256: string }>;
      for (const [relative, evidence] of Object.entries(files)) {
        const file = path.join(directory, relative);
        expect(digest(file), file).toBe(evidence.sha256);
      }
    }
  });

  test('preserves images and supplemental diagnostics explicitly included in accepted reviews', () => {
    const archives = new Set<string>(provenanceRecords.map(record => record.evidenceArchive));
    for (const archive of archives) {
      const review = readJson(path.join(archive, 'visual_review.json'));
      const packageName = path.basename(path.dirname(archive));
      const directory = path.join('authoring/blender', packageName);
      for (const evidence of review.evidence ?? []) {
        const file = path.join(directory, evidence.path);
        expect(imageDigest(file), file).toBe(evidence.sha256);
      }
      for (const [filename, expected] of Object.entries(review.additional_reports ?? {})) {
        const file = path.join(directory, 'review', filename);
        expect(digest(file), file).toBe(expected);
      }
    }
  });
});
