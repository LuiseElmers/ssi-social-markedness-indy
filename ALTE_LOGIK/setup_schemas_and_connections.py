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


def wait_for_all_agents():
    """Wartet robust per HTTP-Request, bis alle ACA-Py Agenten erreichbar sind."""
    print("\nWaiting for all agents to become responsive...")
    
    agents = {
        "issuer_government": "http://localhost:8032",
        "issuer_employer": "http://localhost:8022",
        "holder_tenant": "http://localhost:8042",
        "verifier_landlord": "http://localhost:8052"
    }
    
    max_retries = 30
    for attempt in range(1, max_retries + 1):
        pending = {}
        for name, url in agents.items():
            try:
                # Wir fragen direkt die Basis-URL ab (ACA-Py antwortet hier zuverlässig)
                res = requests.get(url, timeout=2)
                if res.status_code not in [200, 404, 401, 403]:
                    pending[name] = f"HTTP {res.status_code}"
            except Exception as e:
                pending[name] = str(e)
                
        if not pending:
            print("-> All agents are fully online and responsive!")
            return True
            
        reasons = ", ".join([f"{k} ({v})" for k, v in pending.items()])
        print(f" -> Attempt {attempt}/{max_retries} - Waiting for: {reasons}")
        time.sleep(2.0)
        
    raise ConnectionError(f"Timeout: Agents did not start in time: {pending}")


""" def wait_for_all_agents():
    print("\nWaiting for all agents to become ready...")
    max_retries = 60  
    
    for attempt in range(1, max_retries + 1):
        all_ready = True
        for name, url in AGENTS.items():
            try:
                res = requests.get(f"{url.rstrip('/')}/status", timeout=2)
                if res.status_code != 200:
                    all_ready = False
                    break
            except Exception:
                all_ready = False
                break
                
        if all_ready:
            print("-> All agents are fully online and responsive.")
            return True
            
        time.sleep(1.5)
        
    raise ConnectionError("Not all agents became ready in time.") """


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
            
    
    def get_existing_active_connection_id(self, target_label):
        """Checks if an active connection already exists."""
        try:
            url = f"{self.base_url}/connections"
            res = requests.get(url, headers=self.headers, timeout=5)
            if res.status_code == 200:
                connections = res.json().get("results", [])
                for conn in connections:
                    if conn.get("state") == "active" and conn.get("their_label", "").strip().lower() == target_label.strip().lower():
                        return conn.get("connection_id")
        except Exception:
            pass
        return None
    
            
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
    print(f"\n--- [DEBUG] Connecting {holder_name} with {issuer_name} ---")
    
    # Check existing connection
    existing_holder_conn = holder_client.get_existing_active_connection_id(issuer_name)
    existing_issuer_conn = issuer_client.get_existing_active_connection_id(holder_name)
    
    if existing_holder_conn and existing_issuer_conn:
        print(f"-> Active connection already exists between {holder_name} ({existing_holder_conn}) and {issuer_name} ({existing_issuer_conn}). Skipping.")
        return

    time.sleep(1)
    
    # 2. Establish OOB connection
    print(f"[DEBUG] {issuer_name} creating OOB invitation...")
    inv = issuer_client.create_invitation(alias=f"Invite for {holder_name}")
    print(f"[DEBUG] Invitation payload received: {inv}")
    
    print(f"[DEBUG] {holder_name} receiving invitation...")
    rec = holder_client.receive_invitation(inv["invitation"])
    print(f"[DEBUG] Receive response: {rec}")
    
    time.sleep(1)
    
    oob_id = inv.get("oob_id")
    holder_conn_id = rec.get("connection_id")
    
    issuer_conn_id = None
    for _ in range(10):
        try:
            conns_res = requests.get(f"{issuer_client.base_url}/connections", headers=issuer_client.headers)
            if conns_res.status_code == 200:
                for c in conns_res.json().get("results", []):
                    if c.get("oob_id") == oob_id:
                        issuer_conn_id = c.get("connection_id")
                        break
            if issuer_conn_id:
                break
        except Exception:
            pass
        time.sleep(1)

    print(f"[DEBUG] Extracted IDs -> Issuer Conn ID: {issuer_conn_id}, Holder Conn ID: {holder_conn_id}")
    
    if not issuer_conn_id or not holder_conn_id:
        raise ValueError(f"Could not retrieve active connection IDs for {holder_name} and {issuer_name}.")

    # Accept connection request
    print(f"[DEBUG] Forcing accept-did-exchange on both sides...")
    holder_client.accept_did_exchange(holder_conn_id)
    issuer_client.accept_did_exchange(issuer_conn_id)
    
    time.sleep(2)
    
    print(f"[DEBUG] Entering polling loop for active state...")
    
    max_attempts = 40 
    for attempt in range(1, max_attempts + 1):
        try:
            holder_res = requests.get(f"{holder_client.base_url}/connections/{holder_conn_id}", headers=holder_client.headers, timeout=3)
            issuer_res = requests.get(f"{issuer_client.base_url}/connections/{issuer_conn_id}", headers=issuer_client.headers, timeout=3)
            
            holder_state = "UNKNOWN"
            issuer_state = "UNKNOWN"
            
            if holder_res.status_code == 200:
                holder_state = holder_res.json().get("state")
            if issuer_res.status_code == 200:
                issuer_state = issuer_res.json().get("state")
                
            print(f"[DEBUG] Attempt {attempt}/{max_attempts} -> {holder_name} state: '{holder_state}' | {issuer_name} state: '{issuer_state}'")
            
            if holder_state == "active" and issuer_state == "active":
                print(f"-> Connection successfully established and active!")
                return
                
        except Exception as e:
            print(f"[DEBUG] Exception during polling attempt {attempt}: {e}")
        
     
        if attempt == 8 or attempt == 16:
            print(f"[DEBUG] Re-triggering accept_did_exchange (Self-Healing at attempt {attempt})...")
            try:
                holder_client.accept_did_exchange(holder_conn_id)
                issuer_client.accept_did_exchange(issuer_conn_id)
            except Exception as ex:
                print(f"[DEBUG] Self-healing trigger failed: {ex}")

        time.sleep(2)


    print(f"\n[ERROR] Connection timeout reached between {holder_name} and {issuer_name}.")
    try:
        final_holder = requests.get(f"{holder_client.base_url}/connections/{holder_conn_id}", headers=holder_client.headers).json()
        final_issuer = requests.get(f"{issuer_client.base_url}/connections/{issuer_conn_id}", headers=issuer_client.headers).json()
        print(f"[ERROR] Final Holder Connection Object: {final_holder}")
        print(f"[ERROR] Final Issuer Connection Object: {final_issuer}")
    except Exception as d_err:
        print(f"[ERROR] Could not fetch final debug dump: {d_err}")

    raise TimeoutError(f"Connection between {holder_name} and {issuer_name} did not reach 'active' state in time.")

""" def establish_connection(issuer_name, issuer_client, holder_name, holder_client):
    print(f"\n--- Connecting {holder_name} with {issuer_name} ---")
    
    existing_holder_conn = holder_client.get_existing_active_connection_id(issuer_name)
    existing_issuer_conn = issuer_client.get_existing_active_connection_id(holder_name)
    
    if existing_holder_conn and existing_issuer_conn:
        print(f"-> Active connection between {holder_name} and {issuer_name} already exists. Skipping.")
        return

    time.sleep(1)
    
    # Establish OOB connection
    inv = issuer_client.create_invitation(alias=f"Invite for {holder_name}")
    rec = holder_client.receive_invitation(inv["invitation"])
    
    time.sleep(1)
    
    issuer_conn_id = inv.get("oob_id") or inv.get("connection_id")
    holder_conn_id = rec.get("connection_id")
    
    if not issuer_conn_id or not holder_conn_id:
        raise ValueError(f"Could not retrieve connection IDs for {holder_name} and {issuer_name}.")

    # 3. Accept connection request
    print(f"Accepting exchange for {holder_name} and {issuer_name}...")
    holder_client.accept_did_exchange(holder_conn_id)
    issuer_client.accept_did_exchange(issuer_conn_id)
    
    time.sleep(2)
    
    print(f"Waiting for connection handshake to complete...")
    
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            holder_res = requests.get(f"{holder_client.base_url}/connections/{holder_conn_id}", headers=holder_client.headers, timeout=3)
            issuer_res = requests.get(f"{issuer_client.base_url}/connections/{issuer_conn_id}", headers=issuer_client.headers, timeout=3)
            
            if holder_res.status_code == 200 and issuer_res.status_code == 200:
                holder_state = holder_res.json().get("state")
                issuer_state = issuer_res.json().get("state")
                
                if holder_state == "active" and issuer_state == "active":
                    print(f"-> Connection is active.")
                    return
        except Exception:
            pass
        
        if attempt == 5:
            try:
                holder_client.accept_did_exchange(holder_conn_id)
                issuer_client.accept_did_exchange(issuer_conn_id)
            except:
                pass

        time.sleep(1.5)

    raise TimeoutError(f"Connection between {holder_name} and {issuer_name} did not reach 'active' state in time.") """
    

def run():
    """Run schema and connection setup."""
    
    wait_for_all_agents()

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
    
    print("\n--- Registering employer schema & Cred Def ---")
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
