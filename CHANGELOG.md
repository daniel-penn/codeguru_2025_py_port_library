# Changelog

## [Unreleased]

### Fixed
- Fixed Java classpath separator issue where `;` was hardcoded, causing failures on non-Windows platforms. Now using `os.pathsep` for cross-platform compatibility.
- Fixed test pollution issue where `scores.csv` was being written to the project root during e2e tests. Tests now use a temporary file.
- Updated `setup.py` repository URL to point to the correct fork.

### Added
- Added `results_file` parameter to `CoreWarsEngine.load_warriors()` to allow specifying the output file path for competition scores.
- Added e2e test case `test_teams_and_zombies` covering 4 teams of 2 warriors, 7 zombies, and 1 H zombie.
