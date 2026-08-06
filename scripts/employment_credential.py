import os
import requests
import time

from dotenv import load_dotenv

def issue_employment_credential():
    """Requests and issues the employment credential from the employer to the tenant."""
    
    load_dotenv(override=True)
    
    employer_url = os.getenv("EMPLOYER_AGENT_URL", "http://localhost:8022/")
    
    try:
        time.sleep(5)
        # Get connection ID for the tenant
        print("\n[*] Fetching and waiting for active connection...")
        connection_id = None
        
        # Get connection ID for the tenant
        print("\n[*] Waiting for connection to become active...")
        connection_id = None
        
        for attempt in range(15):
            conn_res = requests.get(f"{employer_url}connections", timeout=10)
            if conn_res.status_code == 200:
                connections = conn_res.json().get("results", [])
                for conn in connections:
                    if conn.get("state") in ["active", "completed"]:
                        connection_id = conn.get("connection_id")
                        break
            if connection_id:
                break
            time.sleep(1)
            
        if not connection_id:
            print("Error: Connection did not become active in time.")
            return
        
        cred_def_id = os.getenv("EMPLOYMENT_CRED_DEF_ID")
        if not cred_def_id:
            print("Error: EMPLOYMENT_CRED_DEF_ID is not set.")
            return
        
        # Employer sends credential offer
        offer_payload = {
            "connection_id": connection_id,
            "filter": {
                "indy": {
                    "cred_def_id": cred_def_id,
                    "attributes": {
                        "employee_name": "Anna Bauer",
                        "employer_name": "IT Solutions GmbH",
                        "employment_status": "Active",
                        "monthly_income": "3500"
                    }
                }
            }
        }
        
        print("\nSending credential offer from employer...")
        response = requests.post(f"{employer_url}issue-credential-2.0/send-offer", json=offer_payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        cred_ex_id = data.get("credential_exchange_id")
        print(f"    Exchange ID: {cred_ex_id}")
        print(f"    State: {data.get('state', 'Unknown')}")
        
        # 2. Wait until offer is received
        tenant_url = os.getenv("TENANT_AGENT_URL", "http://localhost:8042/")
        
        tenant_cred_ex_id = None
        for _ in range(15):
            time.sleep(2)
            records_res = requests.get(f"{tenant_url}issue-credential-2.0/records", params={"connection_id": connection_id}, timeout=5)
            if records_res.status_code == 200:
                records = records_res.json().get("results", [])
                for rec in records:
                    if rec.get("state") == "offer-received":
                        tenant_cred_ex_id = rec.get("credential_exchange_id")
                        break
            if tenant_cred_ex_id:
                break
                
        if not tenant_cred_ex_id:
            print("Error: Credential offer could not be received.")
            return

        # 3. Tenant sends back credentials request
        print(f"[*] Tenant accepting offer and sending request (Record ID: {tenant_cred_ex_id})...")
        req_res = requests.post(f"{tenant_url}issue-credential-2.0/records/{tenant_cred_ex_id}/send-request", timeout=10)
        req_res.raise_for_status()
        
        # 4. Wait until employer issues credential and tenant receives it
        time.sleep(3)
        print("[*] Tenant storing credential in wallet...")
        store_res = requests.post(f"{tenant_url}issue-credential-2.0/records/{tenant_cred_ex_id}/store", timeout=10)
        store_res.raise_for_status()
        
        print(f"\n[✓] Credential successfully stored.")
            
    except requests.exceptions.ConnectionError:
        print(f"\nError: Could not connect to employer agent at {employer_url}.")
    except Exception as e:
        print(f"\nError occurred: {e}")
        
    input("\nPress Enter to return to the menu.")
