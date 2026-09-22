import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("twohand", Path(__file__).resolve().parents[1] / "scripts/unreal/prelate_two_handed.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AnimationBindingTests(unittest.TestCase):
    def setUp(self):
        self.imported = {key: "/Game/Test/" + key for key in module.CLIPS}
        self.grips = {key: {"maximumUnreachableCm": 0.} for key in module.CLIPS}

    def test_preserves_unprovided_roles_and_installs_live_roles(self):
        old = {key: "/Game/Original/" + key for key in ("idle", "run", "death", "cast", "jump")}
        merged = module.merge_bindings(old, self.imported, self.grips)
        self.assertEqual(merged["attack_melee"], self.imported["slash_alternate"])
        self.assertEqual(merged["idle"], self.imported["idle"])
        for role in ("run", "death", "cast", "jump"):
            self.assertEqual(merged[role], old[role])
        self.assertEqual(old["idle"], "/Game/Original/idle")
        self.assertEqual(merged["two_handed_spin_attack"], self.imported["spin_attack"])

    def test_rejects_missing_or_aliased_source_clips(self):
        self.imported.pop("jump_attack")
        with self.assertRaises(ValueError):
            module.merge_bindings({}, self.imported, self.grips)
        self.imported["jump_attack"] = self.imported["idle"]
        with self.assertRaises(ValueError):
            module.merge_bindings({}, self.imported, self.grips)

    def test_unreachable_or_missing_live_grip_blocks_activation(self):
        for error in (1.2, float("nan"), float("inf"), -.1):
            self.grips["slash_alternate"]["maximumUnreachableCm"] = error
            with self.assertRaises(ValueError):
                module.merge_bindings({}, self.imported, self.grips)
        del self.grips["slash_alternate"]
        with self.assertRaises(ValueError):
            module.merge_bindings({}, self.imported, self.grips)


if __name__ == "__main__":
    unittest.main()
