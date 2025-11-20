import unittest
import os
import time
import tempfile
import shutil
from corewars8086_lib.engine import CoreWarsEngine

class TestCoreWarsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = CoreWarsEngine()
        self.test_dir = tempfile.mkdtemp()
        self.warriors_dir = os.path.join(self.test_dir, "warriors")
        self.zombies_dir = os.path.join(self.test_dir, "zombies")
        os.makedirs(self.warriors_dir)
        os.makedirs(self.zombies_dir)

    def tearDown(self):
        self.engine.close()
        try:
            shutil.rmtree(self.test_dir)
        except OSError:
            pass

    def test_init(self):
        self.assertIsNotNone(self.engine)

    def test_load_warriors(self):
        warrior_path = os.path.join(self.warriors_dir, "TestWarrior")
        with open(warrior_path, "wb") as f:
            f.write(b"\x90" * 10) 
        self.engine.load_warriors(self.warriors_dir, self.zombies_dir)
        count = self.engine.get_warrior_count()
        self.assertEqual(count, 1)

    def test_run_competition(self):
        names = ["Alpha", "Beta"]
        for name in names:
            path = os.path.join(self.warriors_dir, name)
            with open(path, "wb") as f:
                f.write(b"\xEB\xFE")

        self.engine.load_warriors(self.warriors_dir, self.zombies_dir)
        self.assertEqual(self.engine.get_warrior_count(), 2)
        
        self.engine.run_competition(battles=1, combination_size=2, parallel=False)
        
        scores = self.engine.get_scores()
        self.assertEqual(len(scores), 2)
        
        names_in_scores = [s["name"] for s in scores]
        self.assertIn("Alpha", names_in_scores)
        self.assertIn("Beta", names_in_scores)

    def test_add_warrior_from_bytes(self):
        # Add two warriors via bytes
        self.engine.add_warrior_from_bytes("ByteBotA", b"\x90\xEB\xFE")
        self.engine.add_warrior_from_bytes("ByteBotB", b"\x90\xEB\xFE")
        
        # Explicitly load loaded warriors to verify file creation
        self.engine.load_warriors(self.engine._managed_dir)
        self.assertEqual(self.engine.get_warrior_count(), 2)

        # Should run without explicit load_warriors call if we use the managed dir logic                                                                            
        self.engine.run_competition(battles=1, combination_size=2, parallel=False)

        scores = self.engine.get_scores()
        self.assertEqual(len(scores), 2)
        names = sorted([s["name"] for s in scores])
        self.assertEqual(names, ["ByteBotA", "ByteBotB"])

if __name__ == '__main__':
    unittest.main()
