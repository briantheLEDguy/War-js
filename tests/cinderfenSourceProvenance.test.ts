import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, test } from 'vitest';

const junction = path.resolve('authoring/blender/cinderfen-architecture/junction');
const digest = (filename: string) => createHash('sha256').update(readFileSync(filename)).digest('hex');
const provenance = JSON.parse(readFileSync(path.join(junction, 'source/source-provenance.json'), 'utf8'));

describe('Cinderfen companion source provenance', () => {
  test('retains every reference and binds the shared source to its reviewed bytes', () => {
    for (const reference of provenance.pipeline_references) {
      expect(existsSync(path.resolve(junction, reference.retained_copy)), reference.utility).toBe(true);
    }
    const library = provenance.pipeline_references.find(
      (reference: { utility: string }) => reference.utility === 'reviewed Cinderfen cage library',
    );
    expect(library).toBeDefined();
    expect(library.retained_copy).toBe('../source/architecture.json');
    const source = JSON.parse(readFileSync(path.join(junction, 'source/architecture.json'), 'utf8'));
    expect(digest(path.resolve(junction, library.retained_copy))).toBe(library.sha256);
    expect(library.sha256).toBe(source.reused_authored_construction.sha256);
    expect(digest(path.join(junction, 'source/architecture.json'))).toBe(provenance.source_sha256);
  });

  test('records the updated writer without retaining redundant cage-library snapshots', () => {
    const writer = 'tools/write_provenance.py';
    expect(digest(path.join(junction, writer))).toBe(provenance.tools[writer]);
    expect(readdirSync(path.join(junction, 'source/pipeline-references')).filter(
      (filename) => filename.endsWith('_reviewed_kit.json'),
    )).toEqual([]);
  });
});
