"""Small, direct wrapper for the ACA-Py Admin API."""

import time

import requests

from config import CHECK_INTERVAL, REQUEST_TIMEOUT, WAIT_SECONDS


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
        return self._request(
            "POST",
            path,
            params=params,
            body=body,
        )

    def _request(self, method, path, params=None, body=None):
        url = f"{self.url}/{path.lstrip('/')}"

        try:
            response = requests.request(
                method,
                url,
                params=params,
                json=body,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as error:
            raise ACAClientError(
                f"{self.name} is not reachable: {error}"
            ) from error

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
            response = self.status()
            print(f"{self.name} status: {response}")
            return bool(response.get("version"))
        except ACAClientError as error:
            print(f"{self.name} error: {error}")
            return False
    
    

    def wait_until_ready(self):
        """Wait until the ACA-Py agent is ready."""
        start = time.time()

        while time.time() - start < WAIT_SECONDS:
            if self.is_ready():
                return

            print(f"Waiting for {self.name} ...")
            time.sleep(CHECK_INTERVAL)

        raise ACAClientError(
            f"{self.name} did not become ready within "
            f"{WAIT_SECONDS} seconds."
        )
        
    # OOB/DID exchange


    def create_invitation(self, alias):
        return self.post(
            "/out-of-band/create-invitation",
            body={
                "alias": alias,
                "handshake_protocols": [
                    "https://didcomm.org/didexchange/1.1"
                ],
                "accept": [
                    "didcomm/aip2;env=rfc19"
                ],
                "multi_use": False,
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
            },
        )


    def connections(self):
        """Return all connections known to the agent."""
        return self.get("/connections").get("results", [])

    def connection(self, connection_id):
        """Return one connection."""
        return self.get(f"/connections/{connection_id}")

    def wait_for_connection(self, connection_id):
        """Wait until a DID Exchange connection becomes active."""
        start = time.time()

        while time.time() - start < WAIT_SECONDS:
            connection = self.connection(connection_id)

            if connection.get("state") == "active":
                return connection

            if connection.get("state") == "abandoned":
                raise ACAClientError(
                    f"{self.name}: connection was abandoned."
                )

            time.sleep(CHECK_INTERVAL)

        raise ACAClientError(
            f"{self.name}: connection {connection_id} "
            f"did not become active."
        )
        
    # Schemas

    def create_schema(self, schema):
        """Create an Indy schema on the ledger."""
        return self.post(
            "/schemas",
            body={
                "schema_name": schema["name"],
                "schema_version": schema["version"],
                "attributes": schema["attributes"],
            },
        )
        
    # Credential definitions

    def create_credential_definition(self, schema_id, tag="default"):
        """Create an Indy credential definition."""
        return self.post(
            "/credential-definitions",
            body={
                "schema_id": schema_id,
                "tag": tag,
                "support_revocation": False,
            },
        )

    # Issue credential 

    def send_credential_offer(
        self,
        connection_id,
        cred_def_id,
        attributes,
        comment="Credential offer",
    ):
        """Send an Issue Credential 2.0 offer."""
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
                    "@type": (
                        "https://didcomm.org/"
                        "issue-credential/2.0/"
                        "credential-preview"
                    ),
                    "attributes": preview,
                },
                "filter": {
                    "indy": {
                        "cred_def_id": cred_def_id,
                    }
                },
            },
        )

    def credential_exchange(self, exchange_id):
        """Return one Issue Credential 2.0 exchange."""
        return self.get(
            f"/issue-credential-2.0/records/{exchange_id}"
        )

    def credential_records(self, thread_id=None):
        """Return Issue Credential 2.0 exchanges."""
        params = {}

        if thread_id:
            params["thread_id"] = thread_id

        return self.get(
            "/issue-credential-2.0/records",
            params=params,
        ).get("results", [])

    def send_credential_request(self, exchange_id):
        """Send the holder's credential request."""
        return self.post(
            f"/issue-credential-2.0/records/"
            f"{exchange_id}/send-request"
        )

    def issue_credential(self, exchange_id, comment=None):
        """Issue the credential."""
        body = {}

        if comment:
            body["comment"] = comment

        return self.post(
            f"/issue-credential-2.0/records/"
            f"{exchange_id}/issue",
            body=body,
        )

    def store_credential(self, exchange_id):
        """Store the received credential in the holder wallet."""
        return self.post(
            f"/issue-credential-2.0/records/"
            f"{exchange_id}/store"
        )

    def wallet_credentials(self):
        """Return credentials stored in the wallet."""
        return self.get("/credentials").get("results", [])


    # Present Proof 2.0

    def send_proof_request(
        self,
        connection_id,
        attributes,
        predicates=None,
        comment="Proof for the rental application",
    ):
        """Send a Present Proof 2.0 request."""
        if predicates is None:
            predicates = {}

        return self.post(
            "/present-proof-2.0/send-request",
            body={
                "connection_id": connection_id,
                "comment": comment,
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

    def proof_exchange(self, exchange_id):
        """Return one Present Proof 2.0 exchange."""
        return self.get(
            f"/present-proof-2.0/records/{exchange_id}"
        )

    def proof_records(self, thread_id=None):
        """Return Present Proof 2.0 exchanges."""
        params = {}

        if thread_id:
            params["thread_id"] = thread_id

        return self.get(
            "/present-proof-2.0/records",
            params=params,
        ).get("results", [])

    def proof_credentials(self, exchange_id, referent=None):
        """Return credentials that can satisfy a proof request."""
        params = {}

        if referent:
            params["referent"] = referent

        return self.get(
            f"/present-proof-2.0/records/"
            f"{exchange_id}/credentials",
            params=params,
        ).get("results", [])

    def send_presentation(self, exchange_id, presentation):
        """Send a proof presentation."""
        return self.post(
            f"/present-proof-2.0/records/"
            f"{exchange_id}/send-presentation",
            body={
                "indy": presentation,
            },
        )

    def verify_presentation(self, exchange_id):
        """Verify a received presentation."""
        return self.post(
            f"/present-proof-2.0/records/"
            f"{exchange_id}/verify-presentation"
        )

    # Generic state waiting

    def wait_for_record(
        self,
        get_records,
        thread_id,
        expected_state,
    ):
        """Wait until an ACA-Py exchange reaches a state."""
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
            f"{self.name}: timeout while waiting for "
            f"'{expected_state}'."
        )
