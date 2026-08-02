import time
import requests

# Endpoint configuration
LEDGER_REGISTER_URL = "http://192.168.64.6:9000/register"

# Seeds defined in docker-compose.yml
GOV_SEED = "gov_agent_seed_32_characters_01"
EMP_SEED = "emp_agent_seed_32_characters_02"


def register_did(seed, role="ENDORSER", agent_name="agent"):
  """Register an agent seed on the ledger."""
  payload = {"seed": seed, "role": role}
  print(
      f"Registering seed for {agent_name} agent on ledger..."
  )
  response = requests.post(LEDGER_REGISTER_URL, json=payload)
  if response.status_code == 200:
    print("-> Successfully registered on ledger!")
  else:
    print(f"-> Notice/Response from ledger: {response.text}")


def run_setup():
  register_did(GOV_SEED, "ENDORSER", agent_name="government agency")
  register_did(EMP_SEED, "ENDORSER", agent_name="employer")
  time.sleep(2)  # Wait for ledger processing
  print(
      "--- Ledger registration completed, a DID for each issuer agent was"
      " derived ---"
  )


if __name__ == "__main__":
  run_setup()
