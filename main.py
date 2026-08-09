"""Start the SSI rental-application prototype."""

from dotenv import load_dotenv
from aca_client import ACAClientError
from menu import run_main_menu
from scripts.setup_infrastructure import run_full_initialization


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
