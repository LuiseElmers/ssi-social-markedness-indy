import os
import subprocess
import requests
import sys
import time

from dotenv import load_dotenv
from scripts import register_seeds
from scripts import setup_schemas_and_connections


class SystemInitializer:
    """Initializes the whole infrastructure setup."""
    def __init__(self):
        self.von_network = None

    def _ask_retry(self, action_name):
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

    def detect_von_network(self):
        print("\n[1/4] Detecting Von-Network...")
        try:
            res = subprocess.run(["docker", "network", "ls", "--format", "{{.Name}}"], capture_output=True, text=True, check=True)
            self.von_network = next((net for net in res.stdout.splitlines() if "von" in net), None)
        except Exception:
            pass

        while not self.von_network:
            print("\nNo von-network found.")
            user_input = input("Enter exact von-network name (or 'q' to quit): ").strip()
            
            if user_input.lower() in ["", "exit", "quit", "q"]:
                print("Exit.")
                sys.exit(0)
                
            check = subprocess.run(["docker", "network", "inspect", user_input], capture_output=True)
            if check.returncode == 0:
                self.von_network = user_input
            else:
                print(f"Network '{user_input}' not found. Try again.")

        print(f"Using network: {self.von_network}")
        time.sleep(2)

    def write_env_file(self):
        while True:
            try:
                with open(".env", "w") as f:
                    f.write(f"VON_NETWORK_NAME={self.von_network}\n")
                    f.write("GOV_AGENT_URL=http://localhost:8032/\n")
                    f.write("EMP_AGENT_URL=http://localhost:8022/\n")
                    f.write("TENANT_AGENT_URL=http://localhost:8042/\n")
                    f.write("LANDLORD_AGENT_URL=http://localhost:8052/\n")
                break
            except Exception as e:
                print(f"\nCould not write .env: {e}")
                self._ask_retry("writing .env")
        time.sleep(2)
    
        

    def register_ledger_seeds(self):
        print("\n[2/4] Registering agent seeds...")
        while True:
            try:
                register_seeds.run_setup()
                break
            except Exception as e:
                print(f"\nError: {e}")
                self._ask_retry("seed registration")
        time.sleep(2)
        
        
    import os
import subprocess
import requests
import sys
import time

from dotenv import load_dotenv
from scripts import register_seeds
from scripts import setup_schemas_and_connections


class SystemInitializer:
    """Initializes the whole infrastructure setup."""
    def __init__(self):
        self.von_network = None

    def _ask_retry(self, action_name):
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

    def detect_von_network(self):
        print("\n[1/4] Detecting Von-Network...")
        try:
            res = subprocess.run(["docker", "network", "ls", "--format", "{{.Name}}"], capture_output=True, text=True, check=True)
            self.von_network = next((net for net in res.stdout.splitlines() if "von" in net), None)
        except Exception:
            pass

        while not self.von_network:
            print("\nNo von-network found.")
            user_input = input("Enter exact von-network name (or 'q' to quit): ").strip()
            
            if user_input.lower() in ["", "exit", "quit", "q"]:
                print("Exit.")
                sys.exit(0)
                
            check = subprocess.run(["docker", "network", "inspect", user_input], capture_output=True)
            if check.returncode == 0:
                self.von_network = user_input
            else:
                print(f"Network '{user_input}' not found. Try again.")

        print(f"Using network: {self.von_network}")
        time.sleep(2)

    def write_env_file(self):
        while True:
            try:
                with open(".env", "w") as f:
                    f.write(f"VON_NETWORK_NAME={self.von_network}\n")
                    f.write("GOV_AGENT_URL=http://localhost:8032/\n")
                    f.write("EMP_AGENT_URL=http://localhost:8022/\n")
                    f.write("TENANT_AGENT_URL=http://localhost:8042/\n")
                    f.write("LANDLORD_AGENT_URL=http://localhost:8052/\n")
                break
            except Exception as e:
                print(f"\nCould not write .env: {e}")
                self._ask_retry("writing .env")
        time.sleep(2)
    
        

    def register_ledger_seeds(self):
        print("\n[2/4] Registering agent seeds...")
        while True:
            try:
                register_seeds.run_setup()
                break
            except Exception as e:
                print(f"\nError: {e}")
                self._ask_retry("seed registration")
        time.sleep(2)
        
        
    def start_docker_containers(self):
        print("\n[3/4] Starting Docker containers (preserving persistent wallets)...")
        while True:
            try:
                # 1. Alle Agenten-Container starten
                subprocess.run([
                    "docker", "compose", "up", "-d", 
                    "issuer_government", "issuer_employer", "holder_tenant", "verifier_landlord"
                ], check=True)
                
                print("Containers launched. Waiting for agents to become responsive...")
                
                # 2. Auf den HTTP-basierten Health-Check warten
                setup_schemas_and_connections.wait_for_all_agents()
                break
                
            except subprocess.CalledProcessError as e:
                print(f"\n[x] Docker startup failed (Exit code {e.returncode})")
                self._ask_retry("Docker startup")
                
                
        
    def setup_schemas_and_connections(self):
        print("\n[4/4] Setting up schemas and connections...")
        try:
            time.sleep(2)  
            setup_schemas_and_connections.run()
            print("\n>>> Setup finished, all agents are ready.\n")
        except Exception as e:
            print(f"\nError: Could not complete setup automatically ({e}).")
            if not self._ask_retry("setup"):
                sys.exit(1)
        

    def run_full_initialization(self):
        """Executes the initialization sequentially."""
        print("======================================================")
        print("           SSI RENTAL PORTAL: INITIALIZATION          ")
        print("======================================================")
        
        self.detect_von_network()
        self.write_env_file()
        self.register_ledger_seeds()
        self.start_docker_containers()
        self.setup_schemas_and_connections()
                
                
        
    def setup_schemas_and_connections(self):
        print("\n[4/4] Setting up schemas and connections...")
        try:
            time.sleep(2)  
            setup_schemas_and_connections.run()
            print("\n>>> Setup finished, all agents are ready.\n")
        except Exception as e:
            print(f"\nError: Could not complete setup automatically ({e}).")
            if not self._ask_retry("setup"):
                sys.exit(1)
        

    def run_full_initialization(self):
        """Executes the initialization sequentially."""
        print("======================================================")
        print("           SSI RENTAL PORTAL: INITIALIZATION          ")
        print("======================================================")
        
        self.detect_von_network()
        self.write_env_file()
        self.register_ledger_seeds()
        self.start_docker_containers()
        self.setup_schemas_and_connections()
