import { readdir, rm } from 'node:fs/promises';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const testsDir = join(root, 'tests');
const outDir = join(root, 'tmp', 'unit-tests');

async function findTests(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const tests = [];
  for (const entry of entries) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      tests.push(...await findTests(path));
    } else if (entry.name.endsWith('.test.ts')) {
      tests.push(path);
    }
  }
  return tests;
}

const tests = await findTests(testsDir);
if (tests.length === 0) {
  throw new Error('No unit tests found under tests/**/*.test.ts');
}

await rm(outDir, { recursive: true, force: true });

let passed = 0;
for (const test of tests) {
  const rel = relative(testsDir, test).replace(/\.ts$/, '.mjs');
  const outfile = join(outDir, rel);
  await build({
    entryPoints: [test],
    outfile,
    bundle: true,
    platform: 'node',
    format: 'esm',
    target: 'es2022',
    sourcemap: 'inline',
    logLevel: 'silent',
  });

  await import(pathToFileURL(outfile).href);
  console.log(`ok ${relative(root, test)}`);
  passed += 1;
}

console.log(`Unit tests passed: ${passed}`);
