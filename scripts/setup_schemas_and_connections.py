import os
import requests
import time

from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

AGENTS = {
    "government": os.getenv("GOV_AGENT_URL", "http://localhost:8032/"),
    "employer": os.getenv("EMP_AGENT_URL", "http://localhost:8022/"),
    "tenant": os.getenv("TENANT_AGENT_URL", "http://localhost:8042/"),
    "landlord": os.getenv("LANDLORD_AGENT_URL", "http://localhost:8052/")
}

class AgentController:
    """Functions as a controller to interact with the ACA-Py admin API."""
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}

    def create_invitation(self, alias=""):
        # Create an out-of-band invitation
        url = f"{self.base_url}/out-of-band/create-invitation"
        body = {
            "alias": alias,
            "handshake_protocols": ["didexchange/1.1"]
        }
        res = requests.post(url, json=body, headers=self.headers)
        res.raise_for_status()
        return res.json()

    def receive_invitation(self, invitation):
        # Receive the invitation on the holder side
        url = f"{self.base_url}/out-of-band/receive-invitation"
        res = requests.post(url, json=invitation, headers=self.headers)
        res.raise_for_status()
        return res.json()

    def accept_did_exchange(self, conn_id):
        for action in ["accept-invitation", "accept-request"]:
            try:
                url = f"{self.base_url}/didexchange/{conn_id}/{action}"
                requests.post(url, headers=self.headers)
            except:
                pass

def establish_connection(issuer_name, issuer_client, holder_name, holder_client):
    print(f"\n--- Connecting {holder_name} with {issuer_name} ---")
    
    # 1. Issuer creates invite, holder receives it
    inv = issuer_client.create_invitation(alias=f"Invite for {holder_name}")
    rec = holder_client.receive_invitation(inv["invitation"])
    
    time.sleep(2)
    
    # 2. Read out IDs
    issuer_conn_id = inv.get("oob_id") or inv.get("connection_id")
    holder_conn_id = rec.get("connection_id")
    
    if not issuer_conn_id or not holder_conn_id:
        raise ValueError(f"Could not retrieve connection/oob IDs for {holder_name} and {issuer_name}.")

    # 3. Accept connection on both sides
    holder_client.accept_did_exchange(holder_conn_id)
    issuer_client.accept_did_exchange(issuer_conn_id)
    
    time.sleep(2)
    print(f"Connected: {holder_name} and {issuer_name}")


def run():
    """Run schema and connection setup."""
    gov = AgentController(AGENTS["government"])
    tenant = AgentController(AGENTS["tenant"])
    employer = AgentController(AGENTS["employer"])
    landlord = AgentController(AGENTS["landlord"])

    # Establish necessary connections
    establish_connection("Government", gov, "Tenant", tenant)
    establish_connection("Employer", employer, "Tenant", tenant)
    establish_connection("Landlord", landlord, "Tenant", tenant)

if __name__ == "__main__":
    run()
