"""Render final camera positions against backed-up pre-expansion maps, then restore.

Run with ordinary Python, with every Unreal process closed. The restore journal
and verified current-map copies remain available if the host itself is stopped.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/unreal/capital-expansion'
CONTENT = ROOT / 'unreal/AegisWar/Content'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')


def fingerprint(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def main():
    active = subprocess.run(['powershell', '-NoProfile', '-Command',
        "@(Get-Process UnrealEditor,UnrealEditor-Cmd,AegisWar -ErrorAction SilentlyContinue).Count"],
        capture_output=True, text=True, check=True).stdout.strip()
    if active != '0':
        raise RuntimeError('Close all Unreal editor and game processes first.')
    receipt = json.loads((OUT / 'applied.json').read_text())
    baseline = json.loads((OUT / 'baseline.json').read_text())
    restore = OUT / ('capture-restore-' + uuid.uuid4().hex)
    rows = []
    for package, expected in receipt['packageHashes'].items():
        if not package.startswith('/Game/') or '..' in package:
            raise RuntimeError('Invalid capital package')
        target = (CONTENT / (package.removeprefix('/Game/') + '.umap')).resolve()
        if not target.is_relative_to(CONTENT.resolve()):
            raise RuntimeError('Capital package is outside project content')
        source = Path(receipt['backup']) / target.name
        old_hashes = [zone['hashes'][package] for zone in baseline.values()
                      if isinstance(zone, dict) and package in zone.get('hashes', {})]
        if len(old_hashes) != 1 or fingerprint(source) != old_hashes[0]:
            raise RuntimeError('Pre-expansion backup fingerprint mismatch')
        if fingerprint(target) != expected:
            raise RuntimeError('Current capital changed after verification')
        rows.append({'target': str(target), 'source': str(source),
                     'restore': str(restore / target.name), 'expected': expected})
    if len(rows) != 2 or len({row['restore'] for row in rows}) != 2:
        raise RuntimeError('Expected exactly two distinct authored capital maps')
    restore.mkdir()
    for row in rows:
        shutil.copy2(row['target'], row['restore'])
        if fingerprint(Path(row['restore'])) != row['expected']:
            raise RuntimeError('Current-map backup failed verification')
    journal = restore / 'journal.json'
    journal.write_text(json.dumps({'state': 'prepared', 'maps': rows}, indent=2) + '\n')
    started = time.time_ns()
    try:
        for row in rows:
            shutil.copy2(row['source'], row['target'])
        with (OUT / 'before-final-console.log').open('w') as log:
            subprocess.run([str(ENGINE), str(ROOT / 'unreal/AegisWar/AegisWar.uproject'),
                '-game', '-WarDevelopmentGM', '-WarExpansionProof', '-WarExpansionBefore',
                '-WarExpansionRun=capital-expansion-final', '-RenderOffscreen', '-windowed',
                '-ForceRes', '-ResX=1280', '-ResY=800', '-unattended', '-nosplash', '-nosound',
                '-ExecCmds=t.MaxFPS 60', '-abslog=' + str(OUT / 'before-final.log')],
                stdout=log, stderr=subprocess.STDOUT, timeout=600, check=True,
                creationflags=subprocess.CREATE_NO_WINDOW)
    finally:
        for row in rows:
            if fingerprint(Path(row['restore'])) != row['expected']:
                raise RuntimeError('Restore copy changed; inspect the capture journal')
            shutil.copy2(row['restore'], row['target'])
            if fingerprint(Path(row['target'])) != row['expected']:
                raise RuntimeError('Restore failed; inspect the capture journal')
        journal.write_text(json.dumps({'state': 'restored', 'maps': rows}, indent=2) + '\n')
    report_file = (ROOT / 'unreal/AegisWar/Saved/CapitalExpansion/'
                   'capital-expansion-final/before/report.json')
    if not report_file.exists() or report_file.stat().st_mtime_ns < started:
        raise RuntimeError('Fresh baseline report missing; final maps were restored')
    report = json.loads(report_file.read_text(encoding='utf-8-sig'))
    if not report['passed'] or report['views'] != 28 or not report['before']:
        raise RuntimeError('Full baseline view capture did not pass; final maps were restored')
    print('Captured 28 matching baseline views; both final maps restored byte-for-byte.')


if __name__ == '__main__':
    main()
