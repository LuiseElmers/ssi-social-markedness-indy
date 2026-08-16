"""Wrapper for the ACA-Py Admin API."""

import time
import requests
from config import CHECK_INTERVAL, LEDGER_WRITE_TIMEOUT, REQUEST_TIMEOUT, WAIT_SECONDS


class ACAClientError(Exception):
    """Raised when ACA-Py cannot complete a request."""


class ACATimeoutError(ACAClientError):
    """Raised when a request runs into a timeout."""


class ACAClient:
    """Represents one ACA-Py agent and its Admin API."""

    def __init__(self, name, url):
        self.name = name
        self.url = url.rstrip("/")

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, body=None, params=None, timeout=None):
        return self._request("POST", path, params=params, body=body, timeout=timeout)

    def _request(self, method, path, params=None, body=None, timeout=None):
        url = f"{self.url}/{path.lstrip('/')}"

        try:
            response = requests.request(
                method,
                url,
                params=params,
                json=body,
                timeout=timeout or REQUEST_TIMEOUT,
            )
        except requests.Timeout as error:
            raise ACATimeoutError(f"{self.name}: {method} {path} timed out.") from error
        except requests.RequestException as error:
            raise ACAClientError(f"{self.name} is not reachable: {error}") from error
        if not response.ok:
            raise ACAClientError(
                f"{self.name}: {method} {path} failed "
                f"({response.status_code}): {response.text}"
            )
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as error:
            raise ACAClientError(
                f"{self.name}: ACA-Py returned invalid JSON."
            ) from error

    # Agent status
    def status(self):
        return self.get("/status")

    def is_ready(self):
        try:
            self.status()
            return True
        except ACAClientError:
            return False

    def wait_until_ready(self):
        start = time.time()
        announced = False

        while time.time() - start < WAIT_SECONDS:
            if self.is_ready():
                return
            if not announced:
                print(f"Waiting for {self.name} ...")
                announced = True

            time.sleep(CHECK_INTERVAL)

        raise ACAClientError(
            f"{self.name} did not become ready within {WAIT_SECONDS} seconds."
        )

    # OOB/DID exchange
    def create_invitation(self, alias):
        return self.post(
            "/out-of-band/create-invitation",
            params={
                "auto_accept": "true",
                "multi_use": "false",
            },
            body={
                "alias": alias,
                "handshake_protocols": ["https://didcomm.org/didexchange/1.1"],
                "accept": ["didcomm/aip2;env=rfc19"],
                "use_public_did": False,
            },
        )

    def receive_invitation(self, invitation, alias):
        return self.post(
            "/out-of-band/receive-invitation",
            body=invitation,
            params={
                "alias": alias,
                "use_existing_connection": "false",
                "auto_accept": "true",
            },
        )

    def connections(self):
        return self.get("/connections").get("results", [])

    def connection(self, connection_id):
        return self.get(f"/connections/{connection_id}")

    def find_connection_by_invitation(self, invi_msg_id):
        results = self.get(
            "/connections", params={"invitation_msg_id": invi_msg_id}
        ).get("results", [])

        if results:
            return results[0]["connection_id"]
        return None

    def find_usable_connection_by_alias(self, alias):
        results = self.get(
            "/connections",
            params={"alias": alias},
        ).get("results", [])

        for connection in results:
            if connection.get("state") in ("completed", "active"):
                return connection["connection_id"]
        return None

    def connection_is_usable(self, connection_id):
        if not connection_id:
            return False
        try:
            connection = self.connection(connection_id)
        except ACAClientError:
            return False
        return connection.get("state") in ("completed", "active")

    def wait_for_connection(self, connection_id):
        start = time.time()

        while time.time() - start < WAIT_SECONDS:
            connection = self.connection(connection_id)

            if connection.get("state") == "active":
                return connection

            if connection.get("state") == "abandoned":
                raise ACAClientError(f"{self.name}: connection was abandoned.")

            time.sleep(CHECK_INTERVAL)

        raise ACAClientError(
            f"{self.name}: connection {connection_id} did not become active."
        )

    # Public DID
    def get_public_did(self):
        response = self.get("/wallet/did/public")
        result = response.get("result") or {}
        did = result.get("did")

        if not did:
            raise ACAClientError(
                f"{self.name}: no public DID is configured for this agent."
            )

        return did

    # Schemas
    def fetch_schema(self, schema_id):
        try:
            response = self.get(f"/anoncreds/schema/{schema_id}")
        except ACAClientError:
            return None

        return response.get("schema") or None

    def create_schema(self, public_did, schema):
        return self.post(
            "/anoncreds/schema",
            body={
                "schema": {
                    "issuerId": public_did,
                    "attrNames": schema["attributes"],
                    "name": schema["name"],
                    "version": schema["version"],
                },
            },
            timeout=LEDGER_WRITE_TIMEOUT,
        )

    # Credential definitions
    def created_credential_definitions(self):
        response = self.get("/anoncreds/credential-definitions")
        return response.get("credential_definition_ids", [])

    def fetch_credential_definition(self, cred_def_id):
        try:
            response = self.get(f"/anoncreds/credential-definition/{cred_def_id}")
        except ACAClientError:
            return None

        return response.get("credential_definition") or None

    def create_credential_definition(self, public_did, schema_id, tag="default"):
        return self.post(
            "/anoncreds/credential-definition",
            body={
                "credential_definition": {
                    "issuerId": public_did,
                    "schemaId": schema_id,
                    "tag": tag,
                },
            },
            timeout=LEDGER_WRITE_TIMEOUT,
        )

    def send_credential_offer(
        self, connection_id, cred_def_id, attributes, comment="Credential offer"
    ):
        preview = [
            {
                "name": name,
                "value": str(value),
            }
            for name, value in attributes.items()
        ]

        return self.post(
            "/issue-credential-2.0/send-offer",
            body={
                "connection_id": connection_id,
                "comment": comment,
                "auto_issue": False,
                "auto_remove": False,
                "credential_preview": {
                    "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
                    "attributes": preview,
                },
                "filter": {
                    "anoncreds": {
                        "cred_def_id": cred_def_id,
                    }
                },
            },
        )

    def credential_exchange(self, exchange_id):
        result = self.get(f"/issue-credential-2.0/records/{exchange_id}")
        return result.get("cred_ex_record", result)

    def credential_records(self, thread_id=None):
        params = {"thread_id": thread_id} if thread_id else {}
        results = self.get("/issue-credential-2.0/records", params=params).get(
            "results", []
        )
        records = []
        for result in results:
            records.append(result.get("cred_ex_record", result))
        return records

    def send_credential_request(self, exchange_id):
        return self.post(f"/issue-credential-2.0/records/{exchange_id}/send-request")

    def issue_credential(self, exchange_id, comment=None):
        body = {"comment": comment} if comment else {}
        return self.post(
            f"/issue-credential-2.0/records/{exchange_id}/issue", body=body
        )

    def store_credential(self, exchange_id):
        return self.post(f"/issue-credential-2.0/records/{exchange_id}/store")

    def wallet_credentials(self):
        return self.get("/credentials").get("results", [])

    # Present Proof 2.0
    def send_proof_request(
        self,
        connection_id,
        attributes,
        predicates=None,
        comment="Proof for the rental application",
    ):
        if predicates is None:
            predicates = {}

        return self.post(
            "/present-proof-2.0/send-request",
            body={
                "connection_id": connection_id,
                "comment": comment,
                "auto_verify": False,
                "presentation_request": {
                    "anoncreds": {
                        "name": "Rental eligibility proof",
                        "version": "1.0",
                        "requested_attributes": attributes,
                        "requested_predicates": predicates,
                    }
                },
            },
        )

    def proof_exchange(self, exchange_id):
        result = self.get(f"/present-proof-2.0/records/{exchange_id}")
        return result.get("pres_ex_record", result)

    def proof_records(self, thread_id=None):
        params = {"thread_id": thread_id} if thread_id else {}
        results = self.get("/present-proof-2.0/records", params=params).get(
            "results", []
        )
        records = []
        for result in results:
            records.append(result.get("pres_ex_record", result))
        return records

    def proof_credentials(self, exchange_id, referent=None):
        params = {"referent": referent} if referent else {}
        return self.get(
            f"/present-proof-2.0/records/{exchange_id}/credentials", params=params
        )

    def send_presentation(self, exchange_id, presentation):
        return self.post(
            f"/present-proof-2.0/records/{exchange_id}/send-presentation",
            body={"anoncreds": presentation},
        )

    def verify_presentation(self, exchange_id):
        return self.post(
            f"/present-proof-2.0/records/{exchange_id}/verify-presentation"
        )

    def send_basic_message(self, connection_id, content):
        return self.post(
            f"/connections/{connection_id}/send-message",
            body={"content": content},
        )

    # General state waiting
    def wait_for_record(self, get_records, thread_id, expected_state):
        start = time.time()

        while time.time() - start < WAIT_SECONDS:
            records = get_records(thread_id)
            if records:
                record = records[0]
                state = record.get("state")
                if state == expected_state:
                    return record
                if state == "abandoned":
                    raise ACAClientError(
                        f"{self.name}: protocol exchange was abandoned."
                    )

            time.sleep(CHECK_INTERVAL)

        raise ACAClientError(
            f"{self.name}: timeout while waiting for {expected_state}."
        )
