import os
import subprocess
import sys
import time

from dotenv import load_dotenv
from scripts import register_seeds
from scripts import setup_schemas_and_connections

def ask_retry(action_name):
    """Helper to ask the user to retry after an error."""
    while True:
        choice = input(f"Retry {action_name}? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            print("[*] Retrying...")
            return True
        elif choice in ['n', 'no', 'q', 'quit']:
            print("Aborted.")
            sys.exit(1)
        print("Please enter 'y' or 'n'.")

def initialize_system_infrastructure():
    print("======================================================")
    print("           SSI RENTAL PORTAL: INITIALIZATION          ")
    print("======================================================")
    
    # 1. Detect von-network
    print("\n[1/5] Detecting Von-Network...")
    von_network = None

    try:
        res = subprocess.run(["docker", "network", "ls", "--format", "{{.Name}}"], capture_output=True, text=True, check=True)
        von_network = next((net for net in res.stdout.splitlines() if "von" in net), None)
    except Exception:
        pass

    while not von_network:
        print("\n[!] No von-network found.")
        user_input = input("Enter exact von-network name (or 'q' to quit): ").strip()
        
        if user_input.lower() in ["", "exit", "quit", "q"]:
            print("Aborted.")
            sys.exit(0)
            
        check = subprocess.run(["docker", "network", "inspect", user_input], capture_output=True)
        if check.returncode == 0:
            von_network = user_input
        else:
            print(f"[x] Network '{user_input}' not found. Try again.")

    print(f"Using network: {von_network}")

   # 2. Write .env file
    print("\n[2/5] Writing .env file...")
    while True:
        try:
            with open(".env", "w") as f:
                f.write(f"VON_NETWORK_NAME={von_network}\n")
                f.write("GOV_AGENT_URL=http://localhost:8032/\n")
                f.write("EMP_AGENT_URL=http://localhost:8022/\n")
                f.write("TENANT_AGENT_URL=http://localhost:8042/\n")
                f.write("LANDLORD_AGENT_URL=http://localhost:8052/\n")
            break
        except Exception as e:
            print(f"\n[x] Failed to write .env: {e}")
            ask_retry("writing .env")

    # 3. Register ledger seeds
    print("\n[3/5] Registering agent seeds...")
    while True:
        try:
            register_seeds.run_setup()
            break
        except Exception as e:
            print(f"\n[x] Error: {e}")
            ask_retry("seed registration")

    # 4. Start Docker containers
    print("\n[4/5] Starting Docker containers...")
    while True:
        try:
            subprocess.run(["docker", "compose", "up", "-d"], check=True)
            break
        except subprocess.CalledProcessError as e:
            print(f"\n[x] Docker start failed (Exit code {e.returncode})")
            ask_retry("Docker startup")

    print("Waiting for agents to start (40s)...")
    time.sleep(40)

    # 5. Setup schemas and connections
    print("\n[5/5] Setting up schemas and connections...")
    while True:
        try:
            setup_schemas_and_connections.run()
            break
        except Exception as e:
            print(f"\n[x] Error: {e}")
            ask_retry("setup")
    
    print("\n>>> Initialization complete! All agents are ready.\n")


if __name__ == "__main__":
    initialize_system_infrastructure()
