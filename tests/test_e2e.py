import unittest
import os
import shutil
import tempfile
import time
from corewars8086_lib.engine import CoreWarsEngine

class CoreWarsE2ETest(unittest.TestCase):
    def setUp(self):
        self.engine = CoreWarsEngine()
        self.work_dir = tempfile.mkdtemp()
        self.warriors_dir = os.path.join(self.work_dir, "warriors")
        self.zombies_dir = os.path.join(self.work_dir, "zombies")
        self.results_file = os.path.join(self.work_dir, "scores.csv")
        os.makedirs(self.warriors_dir)
        os.makedirs(self.zombies_dir)

    def tearDown(self):
        self.engine.close()
        try:
            shutil.rmtree(self.work_dir)
        except OSError:
            pass

    def create_warrior(self, name, data, group=""):
        path = os.path.join(self.warriors_dir, name)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def test_survivor_vs_suicide(self):
        # Survivor: JMP -2 (EB FE)
        self.create_warrior("Survivor", b"\xEB\xFE")
        # Suicide: 0x0F (Invalid Opcode) - usually kills the process
        self.create_warrior("Loser", b"\x0F")

        self.engine.load_warriors(self.warriors_dir, self.zombies_dir, results_file=self.results_file)
        
        self.engine.run_competition(battles=10, combination_size=2, parallel=False)
        
        scores = self.engine.get_scores()
        # Survivor should be first
        self.assertEqual(len(scores), 2)
        self.assertEqual(scores[0]['name'], "Survivor")
        # Survivor score should be significantly higher than Loser
        self.assertGreater(scores[0]['score'], scores[1]['score'])
        # Loser should have very low score (likely 0 or near 0 depending on survival time)
        self.assertLess(scores[1]['score'], 10) 

    def test_groups(self):
        # Create Group A warriors
        # Java logic: endsWith("1") starts group, endsWith("2") adds to previous group
        self.create_warrior("TeamA1", b"\xEB\xFE")
        self.create_warrior("TeamA2", b"\xEB\xFE")
        
        # Create single warriors
        self.create_warrior("Loner", b"\xEB\xFE")

        self.engine.load_warriors(self.warriors_dir, self.zombies_dir, results_file=self.results_file)
        count = self.engine.get_warrior_count()
        # TeamA (1 group) + Loner (1 group) = 2 groups
        self.assertEqual(count, 2)
        
        self.engine.run_competition(battles=5, combination_size=2, parallel=False)
        scores = self.engine.get_scores()
        self.assertEqual(len(scores), 2)
        
        # Verify group contents
        group_names = sorted([g['name'] for g in scores])
        self.assertIn("TeamA", group_names)
        self.assertIn("Loner", group_names)

    def test_parallel_execution(self):
        # Create many warriors
        # Avoid names ending in 1 or 2 to prevent grouping
        chars = "ABCDEF"
        for c in chars:
            self.create_warrior(f"Bot_{c}", b"\x90" * 5 + b"\xEB\xFB") 
            
        self.engine.load_warriors(self.warriors_dir, self.zombies_dir, results_file=self.results_file)

        # Run with parallel=True
        self.engine.run_competition(battles=10, combination_size=2, parallel=True, threads=4)                                                                       

        scores = self.engine.get_scores()
        self.assertEqual(len(scores), 6)

    def test_teams_and_zombies(self):
        # 4 teams of 2
        teams = ["TeamA", "TeamB", "TeamC", "TeamD"]
        for team in teams:
            self.create_warrior(f"{team}1", b"\xEB\xFE") # JMP -2
            self.create_warrior(f"{team}2", b"\xEB\xFE") # JMP -2

        # 7 zombies
        for i in range(7):
            path = os.path.join(self.zombies_dir, f"Zombie_{i}")
            with open(path, "wb") as f:
                f.write(b"\x90\xEB\xFD") # NOP, JMP -3

        # 1 H zombie
        path = os.path.join(self.zombies_dir, "Zombie_H")
        with open(path, "wb") as f:
            f.write(b"\x90\xEB\xFD") # NOP, JMP -3
        
        self.engine.load_warriors(self.warriors_dir, self.zombies_dir, results_file=self.results_file)
        
        # Verify we have 4 groups (teams)
        count = self.engine.get_warrior_count()
        self.assertEqual(count, 4)
        
        # Run competition with 10 rounds (battles)
        # We use combination_size=2 (2 teams vs zombies? No, combination_size controls how many GROUPS fight each other)
        # If we want all 4 teams to fight? The prompt just says "series of 10 rounds is ran with 16 warriors".
        # Usually this implies a full melee or a specific setup. 
        # But standard CoreWars 8086 runs combinations.
        # Let's use combination_size=4 (all 4 teams in one battle) if we want all of them. 
        # Or defaults. "ran with 16 warriors" implies all are present?
        # 4 teams * 2 = 8. Zombies = 8. Total 16.
        # If combination_size is 4 (max possible if only 4 groups), then all teams fight each other + zombies.
        # This seems most appropriate to "run with 16 warriors".
        
        self.engine.run_competition(battles=10, combination_size=4, parallel=False)
        
        scores = self.engine.get_scores()
        self.assertEqual(len(scores), 4)
        
        # Verify names
        group_names = sorted([g['name'] for g in scores])
        self.assertEqual(group_names, ["TeamA", "TeamB", "TeamC", "TeamD"])

if __name__ == '__main__':
    unittest.main()

