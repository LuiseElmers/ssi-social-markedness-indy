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
    """Controller that interacts with the ACA-Py admin API."""
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        
        for _ in range(30):
            try:
                res = requests.get(f"{self.base_url}/status", timeout=2)
                if res.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1.5)
        else:
            raise ConnectionError(f"Agent at {self.base_url} did not become ready in time.")
    

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
            
    def create_schema(self, schema_name, schema_version, attributes):
        """Register a schema on the ledger."""
        
        try:
            res = requests.get(f"{self.base_url}/schemas/created", headers=self.headers)
            res.raise_for_status()
            created_schemas = res.json().get("schema_ids", [])
            
            for s_id in created_schemas:
                if f":2:{schema_name}:{schema_version}" in s_id:
                    print(f"Schema already exists on ledger. ID: {s_id}")
                    return s_id
        except Exception:
            pass
        
        schema_body = {
            "schema_name": schema_name,
            "schema_version": schema_version,
            "attributes": attributes
        }
        
        res = requests.post(
            f"{self.base_url}/schemas", 
            json=schema_body, 
            headers=self.headers
        )
        res.raise_for_status()
        schema_id = res.json().get("schema_id")
        print(f"Schema created. ID: {schema_id}")
        return schema_id
    
    
    def create_credential_definition(self, schema_id, tag="default"):
        """Create a credential definition based on a given schema ID."""
        
        try:
            res = requests.get(f"{self.base_url}/credential-definitions/created", headers=self.headers)
            res.raise_for_status()
            created_cred_defs = res.json().get("credential_definition_ids", [])
            
            for cd_id in created_cred_defs:
                if cd_id.endswith(f":{tag}"):
                    print(f"Credential definition already exists in wallet. ID: {cd_id}")
                    return cd_id
        except Exception:
            pass
        
        cred_def_body = {
            "schema_id": schema_id,
            "support_revocation": False,
            "tag": tag
        }
            
        try:
            res = requests.post(
                f"{self.base_url}/credential-definitions", 
                json=cred_def_body, 
                headers=self.headers
            )
            res.raise_for_status()
            cred_def_id = res.json().get("credential_definition_id")
            print(f"Credential definition was created. ID: {cred_def_id}")
            return cred_def_id
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400 and "is on ledger" in e.response.text:
                print(f"Credential definition for tag '{tag}' already exists on ledger. Recovering ID...")
           
                error_text = e.response.text
                parts = error_text.split()
                for part in parts:
                    if f":{tag}" in part:
                        recovered_id = part.strip("'\".,")
                        print(f"-> Recovered existing Cred Def ID: {recovered_id}")
                        return recovered_id
                        
                raise e 
            else:
                raise e
            
def _write_to_env(key, value):
        env_path = ".env"
        lines = []
        
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
                
        key_found = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                key_found = True
            else:
                new_lines.append(line)
                
        if not key_found:
            new_lines.append(f"{key}={value}\n")
            
        with open(env_path, "w") as f:
            f.writelines(new_lines)   


def establish_connection(issuer_name, issuer_client, holder_name, holder_client):
    print(f"\n--- Connecting {holder_name} with {issuer_name} ---")
    
    # Issuer creates invite, holder receives it
    inv = issuer_client.create_invitation(alias=f"Invite for {holder_name}")
    rec = holder_client.receive_invitation(inv["invitation"])
    
    time.sleep(2)
    
    # Read out IDs
    issuer_conn_id = inv.get("oob_id") or inv.get("connection_id")
    holder_conn_id = rec.get("connection_id")
    
    if not issuer_conn_id or not holder_conn_id:
        raise ValueError(f"Could not retrieve connection/oob IDs for {holder_name} and {issuer_name}.")

    # Accept connection on both sides
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
    
    # Define attributes for government digital ID
    gov_attributes = [
        "first_name",
        "last_name",
        "date_of_birth",
        "place_of_residence",
        "current_address",
        "nationality",
        "gender"
    ]

    # Define attributes for employer credential
    employer_attributes = [
        "employer_name",
        "employment_status",
        "start_date",
        "monthly_income",
        "is_probationary"
    ]
    
    # Register schemas and credential definitions on the ledger
    gov_schema_id = gov.create_schema("digital_id_schema", "1.0", gov_attributes)
    gov_cred_def_id = gov.create_credential_definition(gov_schema_id, tag="gov-default")
    time.sleep(2)
    
    print("\n--- Registering Employer Schema & Cred Def ---")
    emp_schema_id = employer.create_schema("employment_schema", "1.0", employer_attributes)
    emp_cred_def_id = employer.create_credential_definition(emp_schema_id, tag="emp-default")
    time.sleep(2)
    
    _write_to_env("GOV_CRED_DEF_ID", gov_cred_def_id)
    _write_to_env("EMPLOYMENT_CRED_DEF_ID", emp_cred_def_id)

    # Establish necessary connections
    establish_connection("Government", gov, "Tenant", tenant)
    establish_connection("Employer", employer, "Tenant", tenant)
    establish_connection("Landlord", landlord, "Tenant", tenant)

if __name__ == "__main__":
    run()
