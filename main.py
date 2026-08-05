import os
import subprocess
import requests
import sys
import time

from dotenv import load_dotenv
from scripts import register_seeds
from scripts import setup_schemas_and_connections

def ask_retry(action_name):
    """Ask the user to retry after an error."""
    while True:
        choice = input(f"Retry {action_name}? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            print("[*] Retrying...")
            return True
        elif choice in ['n', 'no', 'q', 'quit']:
            print("Exit.")
            sys.exit(1)
        print("Enter 'y' or 'n'.")

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
            print("Exit.")
            sys.exit(0)
            
        check = subprocess.run(["docker", "network", "inspect", user_input], capture_output=True)
        if check.returncode == 0:
            von_network = user_input
        else:
            print(f"[x] Network '{user_input}' not found. Try again.")

    print(f"Using network: {von_network}")
    time.sleep(2)

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
            print(".env file successfully written.")
            break
        except Exception as e:
            print(f"\n[x] Failed to write .env: {e}")
            ask_retry("writing .env")
    time.sleep(2)

    # 3. Register ledger seeds
    print("\n[3/5] Registering agent seeds...")
    while True:
        try:
            register_seeds.run_setup()
            print("Seeds successfully registered.")
            break
        except Exception as e:
            print(f"\n[x] Error: {e}")
            ask_retry("seed registration")
    time.sleep(2)

    # 4. Start Docker containers
    print("\n[4/5] Starting Docker containers...")
    while True:
        try:
            subprocess.run(["docker", "compose", "up", "-d"], check=True)
            break
        except subprocess.CalledProcessError as e:
            print(f"\n[x] Docker start failed (Exit code {e.returncode})")
            ask_retry("Docker startup")

    print("\nWaiting for agents to set up...")
    agent_urls = [
        os.getenv("GOV_AGENT_URL", "http://localhost:8032/"),
        os.getenv("EMP_AGENT_URL", "http://localhost:8022/"),
        os.getenv("TENANT_AGENT_URL", "http://localhost:8042/"),
        os.getenv("LANDLORD_AGENT_URL", "http://localhost:8052/")
    ]

    max_retries = 50
    for url in agent_urls:
        agent_name = url.strip("/").split(":")[-1]
        ready = False
        for attempt in range(max_retries):
            try:
                res = requests.get(f"{url}status/ready", timeout=2)
                if res.status_code == 200:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(2)
        
        if not ready:
            print(f"[!] Warning: Agent at {url} took too long to respond.")
        else:
            print(f"-> Agent {url} is online and ready.")

    print("All agents are set up.")
    

    # 5. Setup schemas and connections
    print("\n[5/5] Setting up schemas and connections...")
    
    while True:
        try:
            setup_schemas_and_connections.run()
            break
        except Exception as e:
            print(f"\n[x] Error: {e}")
            ask_retry("setup")
    
    print("\n>>> Setup finished, all agents are ready.\n")


if __name__ == "__main__":
    initialize_system_infrastructure()
