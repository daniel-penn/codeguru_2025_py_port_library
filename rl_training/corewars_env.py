"""
CoreWars8086 Reinforcement Learning Environment

This module provides a Gym-compatible environment for training RL agents
to generate warrior code that can defeat static opponents.
"""

import os
import sys
import numpy as np
from typing import Tuple, Dict, List, Optional
import tempfile

try:
    import jpype
    JPYPE_AVAILABLE = True
except ImportError:
    JPYPE_AVAILABLE = False
    print("Warning: JPype not available. Install with: pip install jpype1")

# Gym compatibility
try:
    from gym import Env
    from gym.spaces import Box, Discrete
except ImportError:
    # Fallback for gymnasium
    try:
        from gymnasium import Env
        from gymnasium.spaces import Box, Discrete
    except ImportError:
        print("Warning: Gym not available. Install with: pip install gym")


class CoreWarsEnv(Env):
    """
    CoreWars8086 RL Environment
    
    The agent generates warrior bytecode (up to 512 bytes) to compete
    against 7 static opponents.
    """
    
    MAX_CODE_SIZE = 512
    MAX_ROUNDS = 200000
    
    def __init__(
        self,
        opponent_paths: List[str],
        java_classpath: Optional[str] = None,
        warriors_dir: str = "survivors",
        zombies_dir: str = "zombies"
    ):
        """
        Initialize the CoreWars environment.
        
        Args:
            opponent_paths: List of 7 file paths to opponent warrior binaries
            java_classpath: Path to compiled CoreWars Java classes
            warriors_dir: Directory for warrior files
            zombies_dir: Directory for zombie files
        """
        super().__init__()
        
        self.opponent_paths = opponent_paths
        if len(opponent_paths) != 7:
            raise ValueError(f"Expected 7 opponents, got {len(opponent_paths)}")
        
        self.warriors_dir = warriors_dir
        self.zombies_dir = zombies_dir
        
        # Initialize Java bridge
        self._init_java(java_classpath)
        
        # Action space: Generate bytecode (each byte is 0-255)
        # We'll use a simplified action space: generate code length + byte values
        self.action_space = Box(
            low=0, high=255, 
            shape=(self.MAX_CODE_SIZE,), 
            dtype=np.uint8
        )
        
        # State space: Opponent embeddings + battle stats
        # Simplified: opponent code features + round number + alive count
        state_dim = 7 * 64 + 2  # 7 opponents * 64 features + round + alive
        self.observation_space = Box(
            low=0, high=1,
            shape=(state_dim,),
            dtype=np.float32
        )
        
        self.current_warrior_path = None
        self.last_battle_result = None
        
    def _init_java(self, classpath: Optional[str]):
        """Initialize JPype and load CoreWars classes."""
        if not JPYPE_AVAILABLE:
            raise ImportError("JPype is required. Install with: pip install jpype1")
        
        if not jpype.isJVMStarted():
            if classpath is None:
                # Try to find compiled classes
                classpath = "target/classes"
                if not os.path.exists(classpath):
                    raise FileNotFoundError(
                        f"Java classes not found at {classpath}. "
                        "Compile with: mvn compile"
                    )
            
            jpype.startJVM(
                jpype.getDefaultJVMPath(),
                f"-Djava.class.path={classpath}",
                convertStrings=False
            )
        
        # Import CoreWars classes
        self.Competition = jpype.JClass("il.co.codeguru.corewars8086.war.Competition")
        self.WarriorRepository = jpype.JClass("il.co.codeguru.corewars8086.war.WarriorRepository")
        self.WarriorData = jpype.JClass("il.co.codeguru.corewars8086.war.WarriorData")
        self.WarriorType = jpype.JClass("il.co.codeguru.corewars8086.war.WarriorType")
        self.Options = jpype.JClass("il.co.codeguru.corewars8086.cli.Options")
        self.War = jpype.JClass("il.co.codeguru.corewars8086.war.War")
        
    def _extract_opponent_features(self, opponent_path: str) -> np.ndarray:
        """
        Extract features from opponent bytecode.
        Simple feature extraction: byte histogram + code size.
        """
        with open(opponent_path, 'rb') as f:
            code = f.read()
        
        # Feature vector: byte histogram (64 bins) + size + common patterns
        features = np.zeros(64, dtype=np.float32)
        
        if len(code) > 0:
            # Byte histogram (4 bins per byte value, 64 total)
            hist, _ = np.histogram(code, bins=64, range=(0, 256))
            features[:64] = hist / max(len(code), 1)
        
        return features
    
    def _get_state(self, round_num: int = 0, alive_count: int = 8) -> np.ndarray:
        """
        Construct state representation.
        
        Args:
            round_num: Current round number
            alive_count: Number of warriors still alive
        """
        # Extract features from all 7 opponents
        opponent_features = []
        for opp_path in self.opponent_paths:
            features = self._extract_opponent_features(opp_path)
            opponent_features.append(features)
        
        # Normalize round number
        round_normalized = min(round_num / self.MAX_ROUNDS, 1.0)
        
        # Normalize alive count (max 8: 7 opponents + 1 agent)
        alive_normalized = alive_count / 8.0
        
        # Concatenate all features
        state = np.concatenate([
            np.concatenate(opponent_features),
            np.array([round_normalized, alive_normalized])
        ])
        
        return state.astype(np.float32)
    
    def reset(self) -> np.ndarray:
        """Reset environment and return initial state."""
        # Clean up previous warrior file
        if self.current_warrior_path and os.path.exists(self.current_warrior_path):
            try:
                os.remove(self.current_warrior_path)
            except:
                pass
        
        self.last_battle_result = None
        return self._get_state()
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute one step: generate warrior and run battle.
        
        Args:
            action: Bytecode array (up to MAX_CODE_SIZE bytes)
            
        Returns:
            observation: New state
            reward: Reward value
            done: Whether episode is finished
            info: Additional information
        """
        # Convert action to valid bytecode
        warrior_code = action[:self.MAX_CODE_SIZE].astype(np.uint8)
        
        # Remove trailing zeros to get actual code size
        non_zero_indices = np.where(warrior_code != 0)[0]
        if len(non_zero_indices) > 0:
            actual_size = non_zero_indices[-1] + 1
            warrior_code = warrior_code[:actual_size]
        else:
            warrior_code = warrior_code[:16]  # Minimum size
        
        # Ensure minimum viable size
        if len(warrior_code) < 16:
            warrior_code = np.pad(warrior_code, (0, 16 - len(warrior_code)), 'constant')
        
        # Run battle
        result = self._run_battle(warrior_code)
        self.last_battle_result = result
        
        # Calculate reward
        reward = self._calculate_reward(result)
        
        # Check if done
        done = result['finished']
        
        # Get new state
        observation = self._get_state(
            round_num=result['rounds'],
            alive_count=result['alive_count']
        )
        
        info = {
            'won': result['won'],
            'rounds': result['rounds'],
            'opponents_killed': result['opponents_killed']
        }
        
        return observation, reward, done, info
    
    def _run_battle(self, warrior_code: np.ndarray) -> Dict:
        """
        Run a single battle with the generated warrior against 7 opponents.
        
        Returns dictionary with battle results.
        """
        # Create temporary warrior file
        temp_dir = tempfile.mkdtemp()
        warrior_name = "rl_agent"
        warrior_path = os.path.join(temp_dir, warrior_name)
        
        try:
            # Write warrior code to file
            with open(warrior_path, 'wb') as f:
                f.write(warrior_code.tobytes())
            
            # Create Options object
            options = self.Options()
            options.warriorsDir = self.warriors_dir
            options.zombiesDir = self.zombies_dir
            options.headless = True
            
            # Create competition
            competition = self.Competition(options)
            
            # Create warrior groups
            # Group 1: Our RL agent + 7 opponents
            agent_group = self.WarriorRepository.__new__(self.WarriorRepository)
            agent_data = self.WarriorData(
                warrior_name,
                warrior_code.tobytes(),
                self.WarriorType.SURVIVOR
            )
            
            # For simplicity, we'll run a single war
            # In practice, you'd want to integrate with the Competition class properly
            
            # Simplified battle simulation
            # This is a placeholder - you'll need to properly integrate with War class
            result = {
                'won': False,
                'finished': True,
                'rounds': 1000,  # Placeholder
                'alive_count': 1,
                'opponents_killed': 0,
                'died': True
            }
            
            # TODO: Properly integrate with War class to run actual battles
            # This requires more Java integration work
            
            return result
            
        finally:
            # Cleanup
            if os.path.exists(warrior_path):
                try:
                    os.remove(warrior_path)
                except:
                    pass
            try:
                os.rmdir(temp_dir)
            except:
                pass
    
    def _calculate_reward(self, result: Dict) -> float:
        """
        Calculate reward based on battle result.
        
        Reward structure:
        - Win: +1000
        - Survival per round: +0.1
        - Opponent killed: +50
        - Death: -100
        """
        reward = 0.0
        
        if result['won']:
            reward += 1000.0
        
        # Survival bonus
        reward += result['rounds'] * 0.1
        
        # Opponent elimination bonus
        reward += result['opponents_killed'] * 50.0
        
        # Death penalty
        if result['died'] and not result['won']:
            reward -= 100.0
        
        return reward
    
    def close(self):
        """Clean up resources."""
        if self.current_warrior_path and os.path.exists(self.current_warrior_path):
            try:
                os.remove(self.current_warrior_path)
            except:
                pass
        
        # Note: Don't shutdown JVM if it might be reused
        # jpype.shutdownJVM()


class SimpleCoreWarsEnv(CoreWarsEnv):
    """
    Simplified environment for testing without full Java integration.
    Uses mock battle results for development.
    """
    
    def __init__(self, opponent_paths: List[str], **kwargs):
        super().__init__(opponent_paths, **kwargs)
        self.mock_mode = True
    
    def _run_battle(self, warrior_code: np.ndarray) -> Dict:
        """Mock battle for testing without Java."""
        # Simple heuristic: longer, more diverse code tends to survive longer
        code_size = len(warrior_code)
        code_diversity = len(np.unique(warrior_code)) / 256.0
        
        # Mock survival probability
        survival_prob = min(code_size / 100.0, 1.0) * code_diversity
        
        import random
        won = random.random() < survival_prob * 0.1  # Low win rate
        rounds = int(random.random() * 10000 * survival_prob)
        
        return {
            'won': won,
            'finished': True,
            'rounds': rounds,
            'alive_count': 1 if won else 0,
            'opponents_killed': 7 if won else random.randint(0, 3),
            'died': not won
        }


if __name__ == "__main__":
    # Example usage
    opponent_paths = [f"opponent_{i}.bin" for i in range(7)]
    
    # For testing without Java
    env = SimpleCoreWarsEnv(opponent_paths)
    
    # Test reset
    state = env.reset()
    print(f"Initial state shape: {state.shape}")
    
    # Test step
    action = np.random.randint(0, 256, size=512, dtype=np.uint8)
    obs, reward, done, info = env.step(action)
    print(f"Reward: {reward}, Done: {done}, Info: {info}")
