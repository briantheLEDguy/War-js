"""Regression checks for hidden model copies and safe directory traversal."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from storage_inventory import regular_files, recovery_model_objects, retired_storage_failures


class StorageInventoryTests(unittest.TestCase):
    def test_extensionless_models_are_found_from_provenance_and_magic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recovery = root / 'artifacts/retirement-recovery'
            objects = recovery / 'objects'
            objects.mkdir(parents=True)
            (objects / 'compressed-blend').write_bytes(b'compressed authoring payload')
            (objects / 'unknown-glb').write_bytes(b'glTF' + bytes(20))
            (objects / 'unique-code').write_text('print("preserve")')
            (recovery / 'inventory.json').write_text(json.dumps({'worktrees': [{'files': [
                {'path': 'authoring/old.blend1', 'sha256': 'compressed-blend'}]}]}))
            self.assertEqual({p.name for p in recovery_model_objects(root)},
                             {'compressed-blend', 'unknown-glb'})

    def test_retired_paths_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                retired_storage_failures(directory, {'files': [{'path': '../outside'}], 'directories': []})

    def test_backups_fail_but_current_models_and_git_history_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'authoring').mkdir()
            (root / 'authoring/current.blend').write_bytes(b'current')
            (root / 'authoring/current.blend2').write_bytes(b'old')
            (root / '.git').mkdir()
            (root / '.git/history.blend1').write_bytes(b'history')
            failures = retired_storage_failures(root, {'files': [], 'directories': []})
            self.assertEqual(failures, ['Blender version backup remains: authoring/current.blend2'])
            self.assertNotIn('history.blend1', {p.name for p in regular_files(root)})

    def test_windows_junction_does_not_traverse_active_content(self):
        with tempfile.TemporaryDirectory() as directory:
            junction = Mock()
            junction.stat.return_value = SimpleNamespace(st_file_attributes=0x400)
            junction.is_symlink.return_value = False
            with patch('storage_inventory.os.scandir', return_value=[junction]):
                self.assertEqual(list(regular_files(directory)), [])
            junction.is_dir.assert_not_called()


if __name__ == '__main__':
    unittest.main()
