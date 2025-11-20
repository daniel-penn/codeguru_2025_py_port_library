# CoreWars8086 RL Training Framework

This directory contains a reinforcement learning framework for training AI agents to generate counter-strategies against static opponents in CoreWars8086.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Compile Java CoreWars Engine

```bash
cd /workspace
mvn compile
```

### 3. Prepare Opponent Warriors

Place your 7 opponent warrior binaries in a directory (e.g., `opponents/`).

### 4. Train (Mock Mode - No Java Required)

For initial testing without Java integration:

```bash
python train.py --opponents opp1.bin opp2.bin opp3.bin opp4.bin opp5.bin opp6.bin opp7.bin --mock
```

### 5. Train (Full Mode - Requires Java)

Once Java integration is complete:

```bash
python train.py --opponents opponents/opp1 opponents/opp2 ... opponents/opp7 \
    --timesteps 1000000 \
    --output-dir models \
    --log-dir logs
```

### 6. Evaluate Trained Model

```bash
python train.py --eval models/final_model \
    --opponents opponents/opp1 ... opponents/opp7 \
    --eval-episodes 100
```

## Architecture

- `corewars_env.py`: Gym-compatible environment wrapper
- `train.py`: Training and evaluation scripts
- `requirements.txt`: Python dependencies

## Current Status

⚠️ **Note**: The Java integration in `corewars_env.py` is a skeleton. You'll need to:

1. Complete the `_run_battle()` method to properly interface with the Java `War` class
2. Implement proper state extraction from running battles
3. Handle warrior file management and cleanup

## Next Steps

1. **Complete Java Integration**: Implement full battle execution in `_run_battle()`
2. **State Representation**: Improve state features (memory snapshots, CPU states)
3. **Reward Shaping**: Tune rewards based on observed behavior
4. **Network Architecture**: Experiment with different architectures (LSTM, Transformer)
5. **Curriculum Learning**: Start with 1 opponent, gradually add more

## Tips

- Start with `--mock` mode to test the framework
- Use small `--timesteps` initially to verify everything works
- Monitor training with TensorBoard: `tensorboard --logdir logs`
- Analyze generated warriors with a disassembler to understand learned strategies
