"""Start the SSI rental-application prototype."""

import sys
from pathlib import Path

from dotenv import load_dotenv
from scripts.aca_client import ACAClientError
from scripts.menu import run_main_menu
from scripts.setup_infrastructure import run_full_initialization

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

def main():
    load_dotenv()
    try:
        run_full_initialization()
    except ACAClientError as error:
        print(f"Initialization failed: {error}")
        return

    run_main_menu()


if __name__ == "__main__":
    main()
