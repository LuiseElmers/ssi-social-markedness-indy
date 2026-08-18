"""Shared pytest setup. Puts the project root on sys.path so tests can do "import config",
"import aca_client" etc. the same way.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
