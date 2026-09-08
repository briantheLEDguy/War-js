#!/usr/bin/env node
/** Read-only inventory: count source separately from generated data and binary assets. */
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const files = [...new Set(execFileSync('git', ['ls-files', '--cached', '--others', '--exclude-standard', '-z'],
  { cwd: root, maxBuffer: 32 * 1024 * 1024 }).toString().split('\0').filter(Boolean))];
const textExtensions = /\.(json|ts|tsx|js|mjs|py|sql|md|css|txt|html|yaml|yml|csv|xml)$/;
const rows = [], duplicates = new Map();
for (const file of files) {
  const absolute = path.join(root, file), stat = statSync(absolute, { throwIfNoEntry: false });
  if (!stat?.isFile() || !textExtensions.test(file)) continue;
  const bytes = readFileSync(absolute);
  const row = { file, bytes: bytes.length, lines: bytes.reduce((sum, byte) => sum + (byte === 10), 0) };
  rows.push(row);
  if (bytes.length < 4096) continue;
  const digest = createHash('sha256').update(bytes).digest('hex');
  const matches = duplicates.get(digest) ?? [];
  matches.push(row);
  duplicates.set(digest, matches);
}
const total = entries => entries.reduce((sum, entry) => ({
  files: sum.files + 1, bytes: sum.bytes + entry.bytes, lines: sum.lines + entry.lines,
}), { files: 0, bytes: 0, lines: 0 });
const groups = new Map();
for (const row of rows) {
  const group = row.file.startsWith('public/assets/') ? row.file.split('/').slice(0, 3).join('/')
    : row.file.includes('/') ? row.file.split('/').slice(0, 2).join('/') : '(root files)';
  const entries = groups.get(group) ?? [];
  entries.push(row);
  groups.set(group, entries);
}
const report = {
  text: total(rows),
  applicationSource: total(rows.filter(row => /^(src|server)\/.*\.tsx?$/.test(row.file))),
  groups: [...groups].map(([group, entries]) => ({ group, ...total(entries) })).sort((a, b) => b.lines - a.lines),
  largest: rows.sort((a, b) => b.lines - a.lines).slice(0, 20),
  duplicateCandidates: [...duplicates.values()].filter(entries => entries.length > 1)
    .map(entries => ({ redundantBytes: entries[0].bytes * (entries.length - 1), files: entries.map(row => row.file) }))
    .sort((a, b) => b.redundantBytes - a.redundantBytes).slice(0, 20),
};
if (process.argv.includes('--json')) console.log(JSON.stringify(report, null, 2));
else {
  console.log('Tracked and unignored text:', report.text);
  console.log('Application TypeScript (includes generated catalogs):', report.applicationSource);
  console.table(report.groups.slice(0, 15));
  console.table(report.largest);
  console.log('Duplicate bytes are audit candidates, not evidence that files are unused. Use --json for paths.');
}
