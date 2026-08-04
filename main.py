import os
import subprocess
import sys
import time

# Import scripts as Python modules
from scripts import register_seeds
from scripts import setup_schemas_and_connections

def initialize_system_infrastructure():
    """Initialize the SSI rental portal infrastructure.
    
    This function performs the following setup steps automatically before the user accesses the main menu:
    1. Detects the active Docker network for the von-network.
    2. Writes the network configuration to a local '.env' file.
    3. Registers the agent seeds on the von-network ledger (via module call).
    4. Starts the Docker Compose containers (ACA-Py agents).
    5. Sets up schemas and P2P connections (via module call).
    """
    print("======================================================")
    print("           SSI RENTAL PORTAL: INITIALIZATION          ")
    print("======================================================")
    
    # Step 1: Determine docker network name for the von-network
    print("\n[1/5] Detecting Von-Network...")
    von_network = None

    try:
        result = subprocess.run(
            ["docker", "network", "ls", "--format", "{{.Name}}"],
            capture_output=True, text=True, check=True
        )
        von_network = next((net for net in result.stdout.splitlines() if "von" in net), None)
    except Exception:
        pass

    # If network detection fails
    while not von_network:
        print("\n[!] No von-network found automatically.")
        user_input = input("Enter exact von-network name (or 'q' to quit): ").strip()
        
        if user_input.lower() in ["", "exit", "quit", "q"]:
            print("Initialization aborted by user. Exiting...")
            sys.exit(0)
            
        # Check if network exists
        res = subprocess.run(["docker", "network", "inspect", user_input], capture_output=True)
        if res.returncode == 0:
            von_network = user_input
        else:
            print(f"[x] Network '{user_input}' not found in Docker. Please try again.")

    print(f"[*] Using Von-Network name: {von_network}")

    # Step 2: Write network name into .env-file (for Docker Compose)
    print("\n[2/5] Writing configuration to .env file...")
    
    while True:
        try:
            with open(".env", "w") as f:
                f.write(f"VON_NETWORK_NAME={von_network}\n")
            break  # Exit loop if successful
        except Exception as e:
            print(f"\n[x] Error: Failed to write to '.env' file: {e}")
            
            choice = input("\nDo you want to (r)etry, or (q)uit/abort initialization? [r/q]: ").strip().lower()
            if choice == 'q':
                print("Initialization aborted by user. Exiting...")
                sys.exit(1)
            elif choice == 'r':
                print("[*] Retrying to write '.env' file...")
            else:
                print("Invalid input. Aborting...")
                sys.exit(1)
        
# Step 3: Register seeds on the ledger 
    print("\n[3/5] Registering agent seeds on the ledger...")
    
    while True:
        try:
            register_seeds.run_setup()  # Runs the main function in register_seeds.py
            break  # Exit loop if successful
        except Exception as e:
            print(f"\n[x] Error during ledger seed registration: {e}")
            
            choice = input("\nDo you want to (r)etry, or (q)uit/abort initialization? [r/q]: ").strip().lower()
            if choice == 'q':
                print("Initialization aborted by user. Exiting...")
                sys.exit(1)
            elif choice == 'r':
                print("[*] Retrying seed registration on ledger...")
            else:
                print("Invalid input. Aborting...")
                sys.exit(1)

    # Step 4: Start Docker infrastructure and ACA-Py agents
    print("\n[4/5] Starting Docker containers (ACA-Py agents)...")
    subprocess.run(["docker", "compose", "up", "-d"], check=True)

    while True:
        try:
            subprocess.run(["docker", "compose", "up", "-d"], check=True)
            break  # Exit loop if successful
        except subprocess.CalledProcessError as e:
            print(f"\n[x] Error: Failed to start Docker containers (Exit Code: {e.returncode})")
            print("Please check if Docker is running and ports are available.")
            
            choice = input("\nDo you want to (r)etry, or (q)uit initialization? [r/q]: ").strip().lower()
            if choice == 'q':
                print("Initialization aborted by user. Exiting...")
                sys.exit(1)
            elif choice == 'r':
                print("[*] Retrying to start Docker containers...")
            else:
                print("Invalid input. Aborting...")
                sys.exit(1)

    print("Waiting for agents to initialize their admin APIs (10s)...")
    time.sleep(10)

    # Step 5: Setup schemas, cred defs and connections
    while True:
        try:
            setup_schemas_and_connections.run()  # Muss der Main function des Moduls entsprechen!
            break  # Exit loop if successful
        except Exception as e:
            print(f"\n[x] Error during schema setup or connection establishment: {e}")
            
            choice = input("\nDo you want to (r)etry, or (q)uit/abort initialization? [r/q]: ").strip().lower()
            if choice == 'q':
                print("Initialization aborted by user. Exiting...")
                sys.exit(1)
            elif choice == 'r':
                print("[*] Retrying setup...")
            else:
                print("Invalid input. Aborting...")
                sys.exit(1)
    
    print("\n>>> System initialization complete! All agents are ready.\n")


# =====================================================================
# CLI menu
# =====================================================================

'''
def show_main_menu():
    while True:
        print("======================================================")
        print("           SSI RENTAL APPLICATION PORTAL              ")
        print("======================================================")
        print(" [1] Check Wallet (View Received Credentials)")
        print(" [2] Start Rental Application Process")
        print(" [X] Exit")
        print("======================================================")
        
        choice = input("Please select an option: ").strip().upper()
        
        if choice == "1":
            print("\n--> Running: Check Wallet...")
            # subprocess.run(["python3", "scripts/1_check_wallet.py"])
            input("\nPress Enter to return to main menu...")
            
        elif choice == "2":
            run_application_menu()
            
        elif choice == "X":
            print("Exiting portal. Goodbye!")
            break
        else:
            print("Invalid option. Please try again.\n")

def run_application_menu():
    while True:
        print("\n---------------------------------------------------------")
        print("              RENTAL APPLICATION PROCESS                 ")
        print("---------------------------------------------------------")
        print(" [1] View Landlord's Proof Request")
        print(" [2] Request Employment Credential (from Employer)")
        print(" [3] Request Digital ID (from Government Agency)")
        print(" [4] Select Claims for Proof Request")
        print(" [X] Back to Main Menu")
        print("---------------------------------------------------------")
        
        choice = input("Please select an option: ").strip().upper()
        
        if choice == "1":
            print("\n--> Running: Check Credential Requirements...")
            # subprocess.run(["python3", "scripts/3a_check_requirements.py"])
            input("\nPress Enter to continue...")
            
        elif choice == "2":
            print("\n--> Requesting Employment Credential...")
            # subprocess.run(["python3", "scripts/2a_issue_employment.py"])
            input("\nPress Enter to continue...")
            
        elif choice == "3":
            print("\n--> Requesting Digital ID...")
            # subprocess.run(["python3", "scripts/2b_issue_government.py"])
            input("\nPress Enter to continue...")
            
        elif choice == "4":
            run_proof_menu()
            
        elif choice == "X":
            break
        else:
            print("Invalid option.\n")

def run_proof_menu():
    while True:
        print("\n------------------------------------------------------")
        print("             GENERATE & SUBMIT PROOF                  ")
        print("------------------------------------------------------")
        print(" [1] Choose Specific Claims (Selective Disclosure)")
        print(" [2] Send Proof to Landlord")
        print(" [X] Back to Application Menu")
        print("------------------------------------------------------")
        
        choice = input("Please select an option: ").strip().upper()
        
        if choice == "1":
            print("\n--> Configuring Selective Disclosure...")
            # subprocess.run(["python3", "scripts/4a_selective_disclosure.py"])
            input("\nPress Enter to continue...")
            
        elif choice == "2":
            print("\n--> Sending Zero-Knowledge Proof to Landlord...")
            # subprocess.run(["python3", "scripts/4b_verify_proof.py"])
            input("\nPress Enter to continue...")
            
        elif choice == "X":
            break
        else:
            print("Invalid option.\n")
'''


if __name__ == "__main__":
    initialize_system_infrastructure()
    
    # show_main_menu()
