import os
import subprocess
import time

# 1. Search for networks that contain the word "von"
try:
    result = subprocess.run(
        ["docker", "network", "ls", "--format", "{{.Name}}"],
        capture_output=True, text=True, check=True
    )
    networks = result.stdout.splitlines()
    von_network = next((net for net in networks if "von" in net), None)
except Exception:
    von_network = None

# 2. If network name not found, ask user
if not von_network:
    print("No network name found.")
    print("Please execute 'docker network ls | grep von' in another terminal and extract the von-network name.")
    von_network = input("Please enter the exact name (e.g. von_von): ").strip()

print(f"Use Von-Network name: {von_network}")

# 3. Write the name into .env-file for Docker Compose
with open(".env", "w") as f:
    f.write(f"VON_NETWORK_NAME={von_network}\n")

# 4. Start Docker Compose
subprocess.run(["docker", "compose", "up", "-d"], check=True)

# Give containers a few seconds to fully initialize their services & admin APIs
print("Waiting for agents to initialize (10s)...")
time.sleep(10)

# 5. Run Step 1: Ledger Registration via setup_schemas_and_connections.py
subprocess.run(["python3", "scripts/setup_schemas_and_connections.py"], check=True)

