#!/usr/bin/env python3
"""Single entry point for the SSI rental-application prototype.

    ./main.py

Checks whether von-network is already up and ready. If it is, the slow
ledger cold start (several minutes under emulation, e.g. on Apple
Silicon) is skipped entirely and only the fast agent setup below runs.
If it isn't, the ledger is started first -- exactly what ledger_up.py
always did, just triggered automatically instead of by hand. Either
way, this is the only command needed to reach the CLI main menu.

Import order matters here and is NOT arbitrary: aca_client, menu, and
scripts.setup_infrastructure all pull in config.py, which reads .env at
import time. Importing any of them before the ledger/environment steps
below have finished writing to .env would freeze them to stale
defaults (e.g. the wrong agent ports) for the rest of this process --
this is not a bug that shows up as a crash, it silently talks to the
wrong port. So those imports are deliberately local to main(), after
prepare_environment() has run, not at module level.

ledger_up.py and start.py still exist for the advanced/manual case
described in the README (e.g. starting von-network yourself with
custom options) -- they now just call the same functions this script
calls, so there's only one place the logic actually lives.
"""

from dotenv import load_dotenv


def main():
    from scripts.ledger import ensure_ledger_up, ledger_is_ready

    if ledger_is_ready():
        print("von-network is already up and ready, skipping the ledger startup ...")
    else:
        print(
            "von-network is not ready yet -- starting it now "
            "(this can take a while on a cold start, please be patient) ..."
        )
        ensure_ledger_up()

    from scripts.environment import prepare_environment

    prepare_environment()

    # ensure_ledger_up()/prepare_environment() may just have written new
    # values to .env (VON_NETWORK_NAME, agent ports). Reload with
    # override=True so config.py picks them up in a moment instead of
    # whatever was already in os.environ from an earlier load_dotenv()
    # call -- plain load_dotenv() does not overwrite variables that are
    # already set.
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
