"""Snapshot local work without changing its index, branch, or asset approvals.

Private content-addressed backups live below ignored artifacts/. Git history is
retained through recovery tags; this is not a substitute for an off-device backup.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED = {'.git', 'node_modules', 'Binaries', 'Intermediate', 'DerivedDataCache',
            '__pycache__', '.vs', '.deps', 'dist', 'artifacts', 'tmp', '.tmp'}


def git(root, *args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(root), *args])


def digest(file):
    h = hashlib.sha256()
    with file.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def files_below(directory):
    if not directory.exists():
        return
    for parent, dirs, files in os.walk(directory, followlinks=False):
        dirs[:] = [d for d in dirs if d not in EXCLUDED and not (Path(parent) / d).is_symlink()]
        for name in files:
            file = Path(parent) / name
            if not file.is_symlink():
                yield file


def run(output, copy):
    output.mkdir(parents=True, exist_ok=True)
    trees = [line[9:] for line in git(ROOT, 'worktree', 'list', '--porcelain').decode().splitlines()
             if line.startswith('worktree ')]
    branches = []
    for row in git(ROOT, 'for-each-ref', '--format=%(refname:short) %(objectname)', 'refs/heads').decode().splitlines():
        name, commit = row.split()
        counts = git(ROOT, 'rev-list', '--left-right', '--count', 'HEAD...' + name).decode().split()
        branches.append({'name': name, 'commit': commit, 'uniqueBeyondHead': int(counts[1])})
    result = {'schemaVersion': 1, 'branches': branches, 'worktrees': [], 'copied': copy}
    objects = output / 'objects'
    objects.mkdir(exist_ok=True)
    for tree in trees:
        root = Path(tree)
        status = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
        parts = status.decode().split('\0')
        paths, statuses = set(), []
        i = 0
        while i < len(parts):
            entry = parts[i]
            i += 1
            if not entry:
                continue
            code, relative = entry[:2], entry[3:]
            statuses.append({'status': code, 'path': relative})
            paths.add(relative)
            if 'R' in code or 'C' in code:
                i += 1
        # Keep ignored source/art and editable native packages, not rebuildable caches.
        for directory in ['authoring/blender', 'authoring/archives', 'authoring/quarantine',
                          'unreal/AegisWar/Content', 'unreal/AegisWar/AnimationImport',
                          'unreal/AegisWar/Saved/WorldEdit']:
            for file in files_below(root / directory):
                paths.add(file.relative_to(root).as_posix())
        record = {'path': tree, 'head': git(root, 'rev-parse', 'HEAD').decode().strip(),
                  'status': statuses, 'files': []}
        for relative in sorted(paths):
            file = root / relative
            if not file.is_file() or file.is_symlink():
                continue
            sha = digest(file)
            target = objects / sha
            if copy and not target.exists():
                if shutil.disk_usage(output).free - file.stat().st_size < 8 * 1024**3:
                    raise RuntimeError('Preservation stopped: reserve 8 GiB free disk space.')
                shutil.copyfile(file, target)
                if digest(target) != sha:
                    raise RuntimeError('Backup verification failed: ' + relative)
            record['files'].append({'path': relative, 'sha256': sha, 'bytes': file.stat().st_size})
        index = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-path', 'index').decode().strip())
        if copy and index.exists():
            shutil.copyfile(index, output / ('index-' + str(len(result['worktrees']))))
        result['worktrees'].append(record)
        (output / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'worktree': tree, 'changes': len(statuses), 'preservedFiles': len(record['files'])}), flush=True)
    print(json.dumps({'manifest': str(output / 'inventory.json'), 'branches': len(branches), 'worktrees': len(trees)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/retirement-recovery')
    parser.add_argument('--copy', action='store_true')
    options = parser.parse_args()
    run(options.output.resolve(), options.copy)
