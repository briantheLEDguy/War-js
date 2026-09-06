"""Exercise the actual archival statements without importing Blender."""

import ast
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = Path(os.environ.get("PRELATE_ARCHIVE_TEST_SOURCE", ROOT / "tools/build_proof.py"))


def archival_statements():
    tree = ast.parse(IMPLEMENTATION.read_bytes().decode("utf-8"))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    for index, node in enumerate(main.body):
        if isinstance(node, ast.For) and "source_record" in ast.unparse(node):
            scene_write = main.body[index + 1]
            if not isinstance(scene_write, ast.Expr) or "scene.json" not in ast.unparse(scene_write):
                raise AssertionError("Expected source archive loop followed by scene archive write")
            return compile(ast.fix_missing_locations(ast.Module(body=[node, scene_write], type_ignores=[])), str(IMPLEMENTATION), "exec")
    raise AssertionError("No source archival statements found in main")


class SourceSnapshot(dict):
    type = "EMPTY"
    name = "component.left_pauldron"


class SourceArchiveTests(unittest.TestCase):
    def archive(self, source_bytes, scene_bytes):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder)
            snapshot = SourceSnapshot(source_record=source_bytes.decode("utf-8"))
            collection = SimpleNamespace(all_objects=[snapshot, SimpleNamespace(type="MESH")])
            exec(archival_statements(), {
                "archive": archive,
                "collection": collection,
                "scene_data": json.loads(scene_bytes),
                "scene_bytes": scene_bytes,
                "json": json,
            })
            self.assertEqual(sorted(path.name for path in archive.iterdir()), ["left_pauldron.json", "scene.json"])
            return (archive / "left_pauldron.json").read_bytes(), (archive / "scene.json").read_bytes()

    def test_source_crlf_utf8_bytes_and_recorded_hash_are_preserved(self):
        source = '{\r\n  "name": "pauldron", "note": "café — authored"\r\n}\r\n'.encode("utf-8")
        actual, _ = self.archive(source, b'{"cameras": {}}\n')
        self.assertEqual(actual, source)
        self.assertEqual(hashlib.sha256(actual).hexdigest(), hashlib.sha256(source).hexdigest())

    def test_source_lf_utf8_bytes_are_preserved(self):
        source = '{\n  "name": "pauldron", "note": "café"\n}\n'.encode("utf-8")
        actual, _ = self.archive(source, b'{"cameras": {}}\n')
        self.assertEqual(actual, source)

    def test_scene_original_format_and_camera_hash_are_preserved(self):
        scene = '{\r\n "cameras" : {"front": {"scale": 1.0100}},\r\n "note": "caméra"\r\n}\r\n'.encode("utf-8")
        _, actual = self.archive(b'{"name": "pauldron"}\n', scene)
        self.assertEqual(actual, scene)
        self.assertEqual(hashlib.sha256(actual).hexdigest(), hashlib.sha256(scene).hexdigest())


if __name__ == "__main__":
    unittest.main()
