import time

from scripts import wallet, employment_credential

def run_main_menu():
    """Main menu for the SSI Rental Portal."""
    
    while True:
        print("\n" + "="*57)
        print("          SSI RENTAL APPLICATION PORTAL          ")
        print("="*57)
        print(" [1] Check Wallet (View Received Credentials)")
        print(" [2] Start Rental Application Process")
        print(" [X] Exit")
        print("="*57)
        
        choice = input("Select an option: ").strip().upper()
        
        if choice == "1":
            menu_check_wallet()
        elif choice == "2":
            submenu_rental_application_process()
        elif choice == "X":
            print("\nExit")
            break
        else:
            print("\nInvalid input. Choose one of the available options.")
            time.sleep(1)

def menu_check_wallet():
    """Menu option [1] from main menu"""
    wallet.check_wallet()


def submenu_rental_application_process():
    """Submenu for [2]: Rental Application Process"""
    while True:
        print("\n" + "-"*57)
        print("          RENTAL APPLICATION PROCESS          ")
        print("-"*57)
        print(" [1] View Landlord's Proof Request")
        print(" [2] Request Employment Credential from Employer")
        print(" [3] Request Digital ID from Government Agency")
        print(" [4] Select Claims for Proof Request")
        print(" [X] Back to Main Menu")
        print("-"*57)
        
        choice = input("Select an option: ").strip().upper()
        
        if choice == "1":
            print("\n[Feature in Progress] Displaying proof request from landlord...")
            input("\nPress Enter to continue...")
            time.sleep(1.5)
        elif choice == "2":
            time.sleep(1)
            employment_credential.issue_employment_credential()
        elif choice == "3":
            print("\nRequesting digital ID from government...")
            time.sleep(1.5)
            input("\nPress Enter to continue...")
        elif choice == "4":
            time.sleep(1)
            # Jump to the proof generation submenu
            submenu_generate_proof()
        elif choice == "X":
            time.sleep(1)
            break
        else:
            print("\n[!] Invalid input. Please choose 1, 2, 3, 4, or X.")


