import time
import requests

# Endpoint configuration
LEDGER_REGISTER_URL = "http://192.168.64.6:9000/register"

# Seeds matching docker-compose.yml  (32 characters for each agent)
GOV_SEED = "gov_agent_seed_32_characters_01!"
EMP_SEED = "emp_agent_seed_32_characters_02!"
TENANT_SEED = "tenant_agent_seed_32_characters0"
LANDLORD_SEED = "landlord_agent_seed_32_chars0040"

def register_did(seed, role="ENDORSER", agent_name="agent"):
    """Register an agent seed on the ledger. Returns True on success."""
    payload = {"seed": seed, "role": role}
    print(f"Registering seed for {agent_name} agent on ledger...")
    
    try:
        response = requests.post(LEDGER_REGISTER_URL, json=payload)
        if response.status_code == 200:
            print(f"-> Successfully registered {agent_name} on ledger!")
            return True
        else:
            print(f"-> Error registering {agent_name}: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"-> Connection error for {agent_name}: {e}")
        return False


def run_setup():
    agents = [
        (GOV_SEED, "ENDORSER", "government agency"),
        (EMP_SEED, "ENDORSER", "employer"),
        (TENANT_SEED, "ENDORSER", "tenant"),
        (LANDLORD_SEED, "ENDORSER", "landlord")
    ]

    success = True
    for seed, role, name in agents:
        if not register_did(seed, role, agent_name=name):
            success = False
        time.sleep(1)  

    if success:
        time.sleep(2)  # Wait for ledger processing
        print("\n--- Ledger registration completed, a DID for all four agents was derived ---")
    else:
        print("\n--- ERROR: Not all agents could be registered successfully! ---")


if __name__ == "__main__":
    run_setup()
