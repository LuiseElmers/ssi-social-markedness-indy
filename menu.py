"""Console menus for the SSI rental-application prototype."""

import time

from aca_client import ACAClientError
from scripts.workflows import (
    check_wallet,
    generate_proof,
    issue_employment_credential,
    issue_government_id,
    show_landlord_proof_request,
)

# Small pause after menu actions so output does not scroll by too fast
MENU_PAUSE_SECONDS = 0.3


def run_action(action):
    time.sleep(MENU_PAUSE_SECONDS)
    try:
        action()
    except ACAClientError as error:
        print(f"\nError: {error}")


def wait_for_return():
    while True:
        choice = input("\nPress X to go back: ").strip().upper()
        if choice == "X":
            time.sleep(MENU_PAUSE_SECONDS)
            return
        print("Press X to go back.")


def submenu_rental_application_process():
    while True:
        print("\n" + "-" * 57)
        print("          RENTAL APPLICATION PROCESS")
        print("-" * 57)
        print(" [1] View landlord's proof request")
        print(" [2] Request employment credential from employer")
        print(" [3] Request digital ID from government agency")
        print(" [4] Send minimal rental proof")
        print(" [X] Back to main menu")
        print("-" * 57)
        choice = input("Select an option: ").strip().upper()
        if choice == "1":
            run_action(show_landlord_proof_request)
            wait_for_return()
        elif choice == "2":
            run_action(issue_employment_credential)
            wait_for_return()
        elif choice == "3":
            run_action(issue_government_id)
            wait_for_return()
        elif choice == "4":
            run_action(generate_proof)
            wait_for_return()
        elif choice == "X":
            time.sleep(MENU_PAUSE_SECONDS)
            return
        else:
            print("\nInvalid input. Choose one of the available options.")


def run_main_menu():
    while True:
        print("\n" + "=" * 57)
        print("          SSI RENTAL APPLICATION PORTAL")
        print("=" * 57)
        print(" [1] Check wallet (view received credentials)")
        print(" [2] Start rental application process")
        print(" [X] Exit")
        print("=" * 57)
        choice = input("Select an option: ").strip().upper()
        if choice == "1":
            run_action(check_wallet)
            wait_for_return()
        elif choice == "2":
            time.sleep(MENU_PAUSE_SECONDS)
            submenu_rental_application_process()
        elif choice == "X":
            print("\nExit")
            time.sleep(MENU_PAUSE_SECONDS)
            return
        else:
            print("\nInvalid input. Choose one of the available options.")
