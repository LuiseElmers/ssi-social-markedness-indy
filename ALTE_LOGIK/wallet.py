import os
import requests

def check_wallet():
    """Retreives and displays all received credentials from the tenant's wallet."""
    print("\n" + "="*50)
    print("          TENANT WALLET: RECEIVED CREDENTIALS          ")
    print("="*50)
    
    tenant_url = os.getenv("TENANT_AGENT_URL", "http://localhost:8042/")
    
    try:
        # ACA-Py endpoint
        response = requests.get(f"{tenant_url}credentials", timeout=5)
        
        if response.status_code == 200:
            credentials = response.json()
            
            cred_list = credentials.get("results", credentials) if isinstance(credentials, dict) else credentials
            
            if not cred_list:
                print("\nYour wallet is currently empty. No credentials found.")
            else:
                print(f"\nFound {len(cred_list)} credential(s) in your wallet:\n")
                for i, cred in enumerate(cred_list, 1):
                    cred_id = cred.get("referent", "N/A")
                    schema_id = cred.get("schema_id", "Unknown Schema")
                    attributes = cred.get("attrs", {})
                    
                    print(f"[{i}] Credential ID: {cred_id}")
                    print(f"    Schema ID: {schema_id}")
                    print("    Attributes:")
                    for attr_name, attr_value in attributes.items():
                        print(f"      - {attr_name}: {attr_value}")
                    print("-" * 40)
        else:
            print(f"\n[x] Could not fetch credentials. Agent returned status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"\nError: Could not connect to tenant agent at {tenant_url}.")
    except Exception as e:
        print(f"\nError occurred: {e}")
        
    input("\nPress Enter to return to the main menu...")
