"""
Training script for CoreWars8086 RL agent.

Usage:
    python train.py --opponents opp1.bin opp2.bin ... opp7.bin
"""

import argparse
import os
import sys
from pathlib import Path
import numpy as np

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
    from stable_baselines3.common.vec_env import DummyVecEnv
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    print("Warning: stable-baselines3 not available. Install with: pip install stable-baselines3")

from corewars_env import CoreWarsEnv, SimpleCoreWarsEnv


def create_env(opponent_paths, use_mock=False, **kwargs):
    """Create and return environment."""
    if use_mock or not SB3_AVAILABLE:
        return SimpleCoreWarsEnv(opponent_paths, **kwargs)
    else:
        return CoreWarsEnv(opponent_paths, **kwargs)


def train(
    opponent_paths,
    total_timesteps=1_000_000,
    learning_rate=3e-4,
    use_mock=False,
    output_dir="models",
    log_dir="logs"
):
    """Train RL agent."""
    
    print(f"Training against {len(opponent_paths)} opponents:")
    for i, opp in enumerate(opponent_paths, 1):
        print(f"  {i}. {opp}")
    
    # Create environment
    env = create_env(opponent_paths, use_mock=use_mock)
    
    # Wrap for vectorized environments (if using SB3)
    if SB3_AVAILABLE:
        env = DummyVecEnv([lambda: env])
    
    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    
    if SB3_AVAILABLE:
        # Create PPO agent
        model = PPO(
            'MlpPolicy',
            env,
            learning_rate=learning_rate,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            verbose=1,
            tensorboard_log=log_dir
        )
        
        # Callbacks
        eval_callback = EvalCallback(
            env,
            best_model_save_path=output_dir,
            log_path=log_dir,
            eval_freq=10000,
            deterministic=True,
            render=False
        )
        
        checkpoint_callback = CheckpointCallback(
            save_freq=50000,
            save_path=output_dir,
            name_prefix='checkpoint'
        )
        
        # Train
        print(f"\nStarting training for {total_timesteps} timesteps...")
        model.learn(
            total_timesteps=total_timesteps,
            callback=[eval_callback, checkpoint_callback],
            progress_bar=True
        )
        
        # Save final model
        final_model_path = os.path.join(output_dir, "final_model")
        model.save(final_model_path)
        print(f"\nTraining complete! Model saved to {final_model_path}")
        
        return model
    else:
        # Simple training loop without SB3
        print("\nRunning simple training loop (install stable-baselines3 for full RL)...")
        
        # Random policy baseline
        best_reward = float('-inf')
        best_code = None
        
        for episode in range(1000):
            state = env.reset()
            total_reward = 0
            done = False
            
            # Generate random warrior code
            action = np.random.randint(0, 256, size=512, dtype=np.uint8)
            
            while not done:
                state, reward, done, info = env.step(action)
                total_reward += reward
            
            if total_reward > best_reward:
                best_reward = total_reward
                best_code = action.copy()
                print(f"Episode {episode}: New best reward = {best_reward:.2f}")
        
        # Save best code
        if best_code is not None:
            output_path = os.path.join(output_dir, "best_warrior.bin")
            with open(output_path, 'wb') as f:
                f.write(best_code.tobytes())
            print(f"\nBest warrior saved to {output_path}")
        
        return None


def evaluate(model_path, opponent_paths, num_episodes=100, use_mock=False):
    """Evaluate trained model."""
    
    print(f"Evaluating model: {model_path}")
    
    env = create_env(opponent_paths, use_mock=use_mock)
    
    if SB3_AVAILABLE and os.path.exists(model_path + ".zip"):
        model = PPO.load(model_path, env=env)
    else:
        print("Model not found or SB3 not available. Using random policy.")
        model = None
    
    wins = 0
    total_rewards = []
    
    for episode in range(num_episodes):
        obs = env.reset()
        done = False
        total_reward = 0
        
        if model:
            action, _ = model.predict(obs, deterministic=True)
        else:
            action = env.action_space.sample()
        
        while not done:
            obs, reward, done, info = env.step(action)
            total_reward += reward
        
        if info.get('won', False):
            wins += 1
        total_rewards.append(total_reward)
        
        if (episode + 1) % 10 == 0:
            win_rate = wins / (episode + 1) * 100
            avg_reward = np.mean(total_rewards)
            print(f"Episode {episode + 1}/{num_episodes}: "
                  f"Win rate: {win_rate:.1f}%, Avg reward: {avg_reward:.2f}")
    
    final_win_rate = wins / num_episodes * 100
    avg_reward = np.mean(total_rewards)
    
    print(f"\nFinal Results:")
    print(f"  Win rate: {final_win_rate:.1f}%")
    print(f"  Average reward: {avg_reward:.2f}")
    print(f"  Best reward: {max(total_rewards):.2f}")
    print(f"  Worst reward: {min(total_rewards):.2f}")


def main():
    parser = argparse.ArgumentParser(description="Train RL agent for CoreWars8086")
    parser.add_argument(
        '--opponents',
        nargs=7,
        required=True,
        help='Paths to 7 opponent warrior binaries'
    )
    parser.add_argument(
        '--timesteps',
        type=int,
        default=1_000_000,
        help='Total training timesteps'
    )
    parser.add_argument(
        '--learning-rate',
        type=float,
        default=3e-4,
        help='Learning rate'
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock environment (no Java required)'
    )
    parser.add_argument(
        '--eval',
        type=str,
        help='Evaluate saved model (provide model path)'
    )
    parser.add_argument(
        '--eval-episodes',
        type=int,
        default=100,
        help='Number of evaluation episodes'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='models',
        help='Output directory for models'
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='Log directory for tensorboard'
    )
    
    args = parser.parse_args()
    
    # Validate opponent files exist
    for opp_path in args.opponents:
        if not os.path.exists(opp_path) and not args.mock:
            print(f"Warning: Opponent file not found: {opp_path}")
    
    if args.eval:
        evaluate(args.eval, args.opponents, args.eval_episodes, args.mock)
    else:
        train(
            args.opponents,
            total_timesteps=args.timesteps,
            learning_rate=args.learning_rate,
            use_mock=args.mock,
            output_dir=args.output_dir,
            log_dir=args.log_dir
        )


if __name__ == "__main__":
    main()
