"""Read-only model storage checks, excluding Git history and linked directories."""
import os
from pathlib import Path
import re


MODEL_SUFFIXES = {'.blend', '.glb', '.gltf', '.fbx', '.uasset', '.umap', '.npz', '.npy'}


def is_model_payload(path):
    return Path(path).suffix.lower() in MODEL_SUFFIXES or is_blender_backup(path)


def is_blender_backup(path):
    return re.search(r'\.blend\d+$', str(path), re.IGNORECASE) is not None


def regular_files(root):
    """Do not follow Windows junctions: their targets can be active Content."""
    root = Path(root)
    if not root.exists():
        return
    for entry in os.scandir(root):
        info = entry.stat(follow_symlinks=False)
        if entry.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            continue
        if entry.is_dir(follow_symlinks=False):
            if entry.name not in {'.git', 'node_modules', '__pycache__'}:
                yield from regular_files(entry.path)
        elif entry.is_file(follow_symlinks=False):
            yield Path(entry.path)


def recovery_model_objects(root):
    """Recovery objects are extensionless; use both provenance and file magic."""
    import json
    root = Path(root)
    inventory = root / 'artifacts/retirement-recovery/inventory.json'
    model_hashes = set()
    if inventory.exists():
        for worktree in json.loads(inventory.read_text())['worktrees']:
            model_hashes.update(row['sha256'] for row in worktree['files']
                                if is_model_payload(row['path']))
    for path in regular_files(root / 'artifacts/retirement-recovery/objects'):
        with path.open('rb') as stream:
            magic = stream.read(24)
        if path.name in model_hashes or magic.startswith((b'glTF', b'BLENDER', b'Kaydara FBX Binary')):
            yield path


def retired_storage_failures(root, manifest):
    root = Path(root).resolve()
    failures = []
    for row in manifest['files'] + manifest['directories']:
        path = (root / row['path']).resolve()
        if not path.is_relative_to(root) or path == root:
            raise ValueError('Retired path escapes workspace: ' + row['path'])
        if path.exists():
            failures.append('Retired storage remains: ' + row['path'])
    for folder in ('authoring', 'artifacts', 'tmp', 'blends'):
        for path in regular_files(root / folder):
            if is_blender_backup(path):
                failures.append('Blender version backup remains: ' + path.relative_to(root).as_posix())
    failures.extend('Recovery model payload remains: ' + path.relative_to(root).as_posix()
                    for path in recovery_model_objects(root))
    return failures
