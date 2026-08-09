"""Console menus for the SSI rental-application prototype."""

from aca_client import ACAClientError
from scripts.workflows import check_wallet, generate_proof, issue_employment_credential, issue_government_id, show_landlord_proof_request


def run_action(action):
    try:
        action()
    except ACAClientError as error:
        print(f"\nError: {error}")


def wait_for_return():
    """Wait until the user confirms they're done and want to go back."""
    while True:
        choice = input("\nPress X to return to the main menu: ").strip().upper()
        if choice == "X":
            return


def submenu_generate_proof():
    while True:
        print("\n" + "-" * 57)
        print("          SELECT CLAIMS FOR PROOF REQUEST")
        print("-" * 57)
        print(" [1] Show selected claims")
        print(" [2] Send minimal rental proof")
        print(" [X] Back to rental application")
        print("-" * 57)
        choice = input("Select an option: ").strip().upper()
        if choice == "1":
            run_action(show_landlord_proof_request)
        elif choice == "2":
            run_action(generate_proof)
        elif choice == "X":
            return
        else:
            print("Invalid input. Choose 1, 2, or X.")


def submenu_rental_application_process():
    while True:
        print("\n" + "-" * 57)
        print("          RENTAL APPLICATION PROCESS")
        print("-" * 57)
        print(" [1] View Landlord's Proof Request")
        print(" [2] Request Employment Credential from Employer")
        print(" [3] Request Digital ID from Government Agency")
        print(" [4] Select Claims for Proof Request")
        print(" [X] Back to Main Menu")
        print("-" * 57)
        choice = input("Select an option: ").strip().upper()
        if choice == "1":
            run_action(show_landlord_proof_request)
        elif choice == "2":
            run_action(issue_employment_credential)
        elif choice == "3":
            run_action(issue_government_id)
        elif choice == "4":
            submenu_generate_proof()
        elif choice == "X":
            return
        else:
            print("Invalid input. Choose 1, 2, 3, 4, or X.")


def run_main_menu():
    while True:
        print("\n" + "=" * 57)
        print("          SSI RENTAL APPLICATION PORTAL")
        print("=" * 57)
        print(" [1] Check Wallet (View Received Credentials)")
        print(" [2] Start Rental Application Process")
        print(" [X] Exit")
        print("=" * 57)
        choice = input("Select an option: ").strip().upper()
        if choice == "1":
            run_action(check_wallet)
            wait_for_return()
        elif choice == "2":
            submenu_rental_application_process()
        elif choice == "X":
            print("\nExit")
            return
        else:
            print("\nInvalid input. Choose one of the available options.")
