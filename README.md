# CoreWars8086

Core Wars for standard 8086 assembly.

## Python Library Port (2025)

A Python library (`corewars8086_lib`) that interfaces with the Java engine using Py4J. This allows you to load warriors, run competitions, and get results directly from Python.

### Prerequisites

*   **Java Development Kit (JDK) 8+**: Required to run the engine.
*   **Python 3.6+**: Required for the library.
*   **Gradle**: For building the Java project (included wrapper or system install).

### Installation

1.  **Build the Java Distribution**:
    The Python library relies on the compiled JARs. Build them using Gradle:
    ```bash
    gradle installDist
    ```

2.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Usage

```python
from corewars8086_lib import CoreWarsEngine

# Initialize the engine (starts the Java process automatically)
engine = CoreWarsEngine()

try:
    # Load warriors from a directory
    # You can also supply a separate directory for zombies if needed
    engine.load_warriors("path/to/your/warriors")
    
    # Or add warriors programmatically from bytes
    engine.add_warrior_from_bytes("MyBot", b"...")

    # Run a competition
    # battles: number of battles per combination
    # combination_size: how many warriors fight in the arena at once
    engine.run_competition(battles=100, combination_size=4, parallel=True)

    # Retrieve scores
    scores = engine.get_scores()
    for group in scores:
        print(f"{group['name']}: {group['score']}")
        for w in group['warriors']:
            print(f"  - {w['name']}: {w['score']}")

finally:
    # Always close the engine to terminate the Java process
    engine.close()
```

### Testing

Run the included tests to verify the installation:

```bash
pytest tests/
```

