"""Root conftest — adds the project root to sys.path so api/ is importable."""

import sys
from pathlib import Path

# Ensure the project root (where api/ lives) is on the path.
# This must be at the root level so it runs before any test collection.
_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
