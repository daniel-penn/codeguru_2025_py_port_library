# CoreWars8086

Core Wars for standard 8086 assembly.

## Python Library Port (2025)

A Python library (`corewars8086_lib`) that interfaces with the Java engine using Py4J. This allows you to load warriors, run competitions, and get results directly from Python.

### Prerequisites

*   **Java Runtime Environment (JRE) 8+**: Required to run the engine.
*   **Python 3.6+**: Required for the library.
*   **(For Building Only) Gradle**: If you are building the package from source.

### Installation

#### From PyPI (Planned)

```bash
pip install corewars8086-lib
```

#### From Source (Wheel)

To build and install the package locally:

1.  **Build the Package**:
    This will automatically run Gradle to compile the Java engine and bundle the JARs into the Python wheel.
    ```bash
    python setup.py bdist_wheel
    ```

2.  **Install the Wheel**:
    ```bash
    pip install dist/corewars8086_lib-1.0.0-py3-none-any.whl
    ```

#### Development Install

If you want to edit the Python code:

```bash
pip install -e .
```
Note: For editable installs, you must ensure the JARs are built and present in `corewars8086_lib/lib/`. You can do this by running `gradle installDist` manually and copying the files, or running `python setup.py build_py` once.

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
