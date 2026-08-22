"""Checks that are shared by ledger.py and environment.py."""

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR / ".env"
ENV_EXAMPLE_FILE = PROJECT_DIR / ".env.example"


def check_docker():
    if shutil.which("docker") is None:
        sys.exit("Docker is not installed or not on PATH.")
        
    result = subprocess.run(["docker", "compose", "version"], capture_output=True)
    if result.returncode != 0:
        sys.exit("Docker Compose v2 is required.")
        
        
def ensure_env_file():
    if not ENV_FILE.exists():
        if not ENV_EXAMPLE_FILE.exists():
            sys.exit(f"{ENV_EXAMPLE_FILE} is missing.")
        print("No .env could be found, creating one from .env.example...")
        shutil.copy(ENV_EXAMPLE_FILE, ENV_FILE)
