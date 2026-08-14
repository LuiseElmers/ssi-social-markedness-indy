#!/usr/bin/env python3
"""Single entry point for the SSI prototype."""

from dotenv import load_dotenv


def main():
    from scripts.ledger import ensure_ledger_up, ledger_is_ready

    if ledger_is_ready():
        print("von-network is already up, skipping the ledger startup ...")
    else:
        print(
            "von-network is not ready yet. Starting the installation... "
            "(This can take a while on a cold start)"
        )
        ensure_ledger_up()

    from scripts.environment import prepare_environment

    prepare_environment()

    load_dotenv(override=True)

    from aca_client import ACAClientError
    from menu import run_main_menu
    from scripts.setup_infrastructure import run_full_initialization

    try:
        run_full_initialization()
    except ACAClientError as error:
        print(f"Initialization failed: {error}")
        return

    run_main_menu()


if __name__ == "__main__":
    main()
