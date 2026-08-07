"""Small, direct wrapper for the ACA-Py Admin API."""

import time

import requests

from scripts.config import CHECK_INTERVAL, REQUEST_TIMEOUT, WAIT_SECONDS


class ACAClientError(Exception):
    """Raised when ACA-Py cannot complete a request."""


class ACAClient:
    """Represents one ACA-Py agent and its Admin API."""

    def __init__(self, name, url):
        self.name = name
        self.url = url.rstrip("/")

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, body=None, params=None):
        return self._request("POST", path, params=params, body=body)

    def _request(self, method, path, params=None, body=None):
        try:
            response = requests.request(
                method,
                self.url + "/" + path.lstrip("/"),
                params=params,
                json=body,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as error:
            raise ACAClientError(f"{self.name} is not reachable: {error}")

        if not response.ok:
            raise ACAClientError(
                f"{self.name}: {method} {path} failed ({response.status_code}): {response.text}"
            )
        return response.json() if response.content else {}

    def status(self):
        return self.get("/status")

    def create_invitation(self, alias):
        return self.post(
            "/out-of-band/create-invitation",
            {
                "alias": alias,
                "handshake_protocols": ["https://didcomm.org/connections/1.0"],
                "multi_use": False,
                "use_public_did": False,
            },
        )

    def receive_invitation(self, invitation, alias):
        return self.post(
            "/out-of-band/receive-invitation",
            invitation,
            {"alias": alias, "use_existing_connection": "false"},
        )

    def connection(self, connection_id):
        return self.get(f"/connections/{connection_id}")

    def create_schema(self, schema):
        return self.post(
            "/schemas",
            {
                "schema_name": schema["name"],
                "schema_version": schema["version"],
                "attributes": schema["attributes"],
            },
        )

    def create_credential_definition(self, schema_id):
        return self.post(
            "/credential-definitions",
            {"schema_id": schema_id, "tag": "default", "support_revocation": False},
        )

    def send_credential_offer(self, connection_id, cred_def_id, attributes, comment):
        preview = [{"name": name, "value": value} for name, value in attributes.items()]
        return self.post(
            "/issue-credential-2.0/send-offer",
            {
                "connection_id": connection_id,
                "comment": comment,
                "auto_issue": False,
                "auto_remove": False,
                "credential_preview": {
                    "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
                    "attributes": preview,
                },
                "filter": {"indy": {"cred_def_id": cred_def_id}},
            },
        )

    def credential_records(self, thread_id):
        return self.get("/issue-credential-2.0/records", {"thread_id": thread_id}).get("results", [])

    def send_credential_request(self, record_id):
        return self.post(f"/issue-credential-2.0/records/{record_id}/send-request")

    def issue_credential(self, record_id):
        return self.post(f"/issue-credential-2.0/records/{record_id}/issue")

    def store_credential(self, record_id):
        return self.post(f"/issue-credential-2.0/records/{record_id}/store")

    def wallet_credentials(self):
        return self.get("/credentials").get("results", [])

    def send_proof_request(self, connection_id, attributes, predicates):
        return self.post(
            "/present-proof-2.0/send-request",
            {
                "connection_id": connection_id,
                "comment": "Proof for the rental application",
                "auto_verify": False,
                "presentation_request": {
                    "indy": {
                        "name": "Rental eligibility proof",
                        "version": "1.0",
                        "requested_attributes": attributes,
                        "requested_predicates": predicates,
                    }
                },
            },
        )

    def proof_records(self, thread_id):
        return self.get("/present-proof-2.0/records", {"thread_id": thread_id}).get("results", [])

    def proof_credentials(self, record_id, referent):
        return self.get(
            f"/present-proof-2.0/records/{record_id}/credentials", {"referent": referent}
        ).get("results", [])

    def send_presentation(self, record_id, selected_credentials):
        return self.post(
            f"/present-proof-2.0/records/{record_id}/send-presentation",
            {"indy": selected_credentials},
        )

    def verify_presentation(self, record_id):
        return self.post(f"/present-proof-2.0/records/{record_id}/verify-presentation")

    def wait_for_record(self, get_records, thread_id, expected_state):
        """Wait until an ACA-Py exchange reaches the requested state."""
        start = time.time()
        while time.time() - start < WAIT_SECONDS:
            records = get_records(thread_id)
            if records:
                record = records[0]
                if record.get("state") == expected_state:
                    return record
                if record.get("state") == "abandoned":
                    raise ACAClientError("ACA-Py abandoned the protocol exchange.")
            time.sleep(CHECK_INTERVAL)
        raise ACAClientError(f"Timeout while waiting for '{expected_state}'.")
