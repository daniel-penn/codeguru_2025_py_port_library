"""
Java Bridge for CoreWars8086

This module provides a cleaner interface to the Java CoreWars engine
for RL training purposes.
"""

import os
import jpype
import jpype.imports
from typing import List, Dict, Optional
import tempfile
import numpy as np


class CoreWarsJavaBridge:
    """
    Bridge class to interact with Java CoreWars engine.
    Handles JVM initialization and provides battle execution interface.
    """
    
    def __init__(self, classpath: Optional[str] = None, warriors_dir: str = "survivors", zombies_dir: str = "zombies"):
        """
        Initialize Java bridge.
        
        Args:
            classpath: Path to compiled Java classes (default: target/classes)
            warriors_dir: Directory for warrior files
            zombies_dir: Directory for zombie files
        """
        self.warriors_dir = warriors_dir
        self.zombies_dir = zombies_dir
        self._init_jvm(classpath)
        self._load_classes()
    
    def _init_jvm(self, classpath: Optional[str]):
        """Initialize JVM if not already started."""
        if jpype.isJVMStarted():
            return
        
        if classpath is None:
            # Try common locations
            possible_paths = [
                "target/classes",
                "../target/classes",
                os.path.join(os.path.dirname(__file__), "../target/classes")
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    classpath = path
                    break
            
            if classpath is None:
                raise FileNotFoundError(
                    "Could not find compiled Java classes. "
                    "Please compile with: mvn compile"
                )
        
        # Add all JAR dependencies
        jar_paths = []
        if os.path.exists("target/dependency"):
            for jar in os.listdir("target/dependency"):
                if jar.endswith(".jar"):
                    jar_paths.append(os.path.join("target/dependency", jar))
        
        full_classpath = classpath
        if jar_paths:
            full_classpath += ":" + ":".join(jar_paths)
        
        jpype.startJVM(
            jpype.getDefaultJVMPath(),
            f"-Djava.class.path={full_classpath}",
            convertStrings=False
        )
    
    def _load_classes(self):
        """Load required Java classes."""
        # Import classes
        from java.util import ArrayList
        from java.io import File, FileInputStream, IOException
        
        self.Options = jpype.JClass("il.co.codeguru.corewars8086.cli.Options")
        self.WarriorRepository = jpype.JClass("il.co.codeguru.corewars8086.war.WarriorRepository")
        self.WarriorData = jpype.JClass("il.co.codeguru.corewars8086.war.WarriorData")
        self.WarriorType = jpype.JClass("il.co.codeguru.corewars8086.war.WarriorType")
        self.WarriorGroup = jpype.JClass("il.co.codeguru.corewars8086.war.WarriorGroup")
        self.War = jpype.JClass("il.co.codeguru.corewars8086.war.War")
        self.CompetitionEventListener = jpype.JClass("il.co.codeguru.corewars8086.war.CompetitionEventListener")
        self.MemoryEventListener = jpype.JClass("il.co.codeguru.corewars8086.memory.MemoryEventListener")
        self.RealModeAddress = jpype.JClass("il.co.codeguru.corewars8086.memory.RealModeAddress")
        
        self.ArrayList = ArrayList
        self.File = File
        self.FileInputStream = FileInputStream
    
    def run_single_battle(
        self,
        agent_code: bytes,
        agent_name: str,
        opponent_paths: List[str],
        seed: int = 0
    ) -> Dict:
        """
        Run a single battle with the agent against opponents.
        
        Args:
            agent_code: Bytecode for the RL agent warrior
            agent_name: Name for the agent warrior
            opponent_paths: List of paths to opponent warrior files
            seed: Random seed for battle
            
        Returns:
            Dictionary with battle results:
            {
                'won': bool,
                'rounds': int,
                'alive_count': int,
                'opponents_killed': int,
                'agent_alive': bool,
                'opponent_names': List[str]
            }
        """
        # Create temporary directory for agent warrior
        temp_dir = tempfile.mkdtemp()
        agent_path = os.path.join(temp_dir, agent_name)
        
        try:
            # Write agent code to file
            with open(agent_path, 'wb') as f:
                f.write(agent_code)
            
            # Create options
            options = self.Options()
            options.warriorsDir = self.warriors_dir
            options.zombiesDir = self.zombies_dir
            options.headless = True
            
            # Create battle listener to track results
            listener = BattleListener()
            
            # Create warrior repository
            repo = self.WarriorRepository(False, options)  # Don't read warriors file
            
            # Create agent warrior group
            agent_data = self.WarriorData(agent_name, agent_code, self.WarriorType.SURVIVOR)
            agent_group = self.WarriorGroup(agent_name + "_group")
            agent_group.addWarrior(agent_data)
            
            # Create opponent warrior groups
            opponent_groups = []
            for opp_path in opponent_paths:
                opp_name = os.path.basename(opp_path)
                with open(opp_path, 'rb') as f:
                    opp_code = f.read()
                
                opp_data = self.WarriorData(opp_name, opp_code, self.WarriorType.SURVIVOR)
                opp_group = self.WarriorGroup(opp_name + "_group")
                opp_group.addWarrior(opp_data)
                opponent_groups.append(opp_group)
            
            # Create war
            war_listener = WarListener(agent_name)
            memory_listener = self.MemoryEventListener.__new__(self.MemoryEventListener)
            
            war = self.War(memory_listener, war_listener, False, options)
            war.setSeed(seed)
            
            # Load all warrior groups
            all_groups = [agent_group] + opponent_groups
            war.loadWarriorGroups(all_groups)
            
            # Run battle
            round_num = 0
            max_rounds = 200000
            
            while round_num < max_rounds and not war.isOver():
                war.nextRound(round_num)
                round_num += 1
            
            # Get results
            alive_count = war.getNumRemainingWarriors()
            alive_names = war.getRemainingWarriorNames().split(", ")
            
            agent_alive = agent_name in alive_names
            won = agent_alive and alive_count == 1
            
            opponents_killed = len(opponent_paths) - sum(
                1 for name in alive_names if name != agent_name
            )
            
            return {
                'won': won,
                'rounds': round_num,
                'alive_count': alive_count,
                'opponents_killed': opponents_killed,
                'agent_alive': agent_alive,
                'opponent_names': [os.path.basename(p) for p in opponent_paths],
                'alive_names': alive_names
            }
            
        finally:
            # Cleanup
            if os.path.exists(agent_path):
                try:
                    os.remove(agent_path)
                except:
                    pass
            try:
                os.rmdir(temp_dir)
            except:
                pass
    
    def shutdown(self):
        """Shutdown JVM (use carefully - affects all JPype instances)."""
        if jpype.isJVMStarted():
            jpype.shutdownJVM()


class WarListener:
    """Listener to track war events."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.events = []
    
    def onWarStart(self, seed: int):
        self.events.append(('war_start', seed))
    
    def onWarEnd(self, reason: int, names: str):
        self.events.append(('war_end', reason, names))
    
    def onWarriorBirth(self, name: str):
        self.events.append(('warrior_birth', name))
    
    def onWarriorDeath(self, name: str, reason: str):
        self.events.append(('warrior_death', name, reason))
    
    def onRound(self, round_num: int):
        pass
    
    def onEndRound(self):
        pass


class BattleListener:
    """Placeholder for battle event tracking."""
    pass


# Example usage
if __name__ == "__main__":
    # Test the bridge
    bridge = CoreWarsJavaBridge()
    
    # Create a simple test warrior (NOP instructions)
    test_code = bytes([0x90] * 16)  # 16 NOPs
    
    # Test battle (requires opponent files)
    # result = bridge.run_single_battle(
    #     test_code,
    #     "test_agent",
    #     ["opponent1", "opponent2", ...],
    #     seed=42
    # )
    # print(result)
