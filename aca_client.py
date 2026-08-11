"""Small, direct wrapper for the ACA-Py Admin API."""

import time

import requests

from config import CHECK_INTERVAL, LEDGER_WRITE_TIMEOUT, REQUEST_TIMEOUT, WAIT_SECONDS


class ACAClientError(Exception):
    """Raised when ACA-Py cannot complete a request."""


class ACATimeoutError(ACAClientError):
    """Raised when a request runs past its read timeout."""


class ACAClient:
    """Represents one ACA-Py agent and its Admin API."""

    def __init__(self, name, url):
        self.name = name
        self.url = url.rstrip("/")

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, body=None, params=None, timeout=None):
        return self._request(
            "POST",
            path,
            params=params,
            body=body,
            timeout=timeout,
        )

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
            raise ACATimeoutError(
                f"{self.name}: {method} {path} timed out."
            ) from error
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
            self.status()
            return True
        except ACAClientError:
            return False

    def wait_until_ready(self):
        """Wait until this agent answers on its Admin API."""
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
            f"{self.name} did not become ready within "
            f"{WAIT_SECONDS} seconds."
        )

    # OOB/DID exchange

    def create_invitation(self, alias):
        # auto_accept and multi_use are query parameters here, not body
        # fields. Without auto_accept the issuer never answers the DID
        # Exchange request and the connection never completes.
        return self.post(
            "/out-of-band/create-invitation",
            params={
                "auto_accept": "true",
                "multi_use": "false",
            },
            body={
                "alias": alias,
                "handshake_protocols": [
                    "https://didcomm.org/didexchange/1.1"
                ],
                "accept": [
                    "didcomm/aip2;env=rfc19"
                ],
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
        """Return all connections known to the agent."""
        return self.get("/connections").get("results", [])

    def connection(self, connection_id):
        """Return one connection."""
        return self.get(f"/connections/{connection_id}")

    def find_connection_by_invitation(self, invi_msg_id):
        """Return the connection created from an invitation, or None.

        The inviting agent only gets a connection once the other side
        answers the invitation, so we look it up by the invitation id.
        """
        results = self.get(
            "/connections",
            params={"invitation_msg_id": invi_msg_id},
        ).get("results", [])

        if results:
            return results[0]["connection_id"]

        return None

    def find_usable_connection_by_alias(self, alias):
        """Return a working connection_id for this alias, or None.

        Used to recover a connection that state.json lost track of, or
        that state.json points to but no longer exists in this wallet
        (e.g. after a wallet reset). Old attempts under the same alias
        (abandoned, stuck in request) are skipped -- only a connection
        that actually reached "completed" or "active" counts as usable.
        """
        results = self.get(
            "/connections",
            params={"alias": alias},
        ).get("results", [])

        for connection in results:
            if connection.get("state") in ("completed", "active"):
                return connection["connection_id"]

        return None

    def connection_is_usable(self, connection_id):
        """Return True if connection_id exists here and is usable."""
        if not connection_id:
            return False

        try:
            connection = self.connection(connection_id)
        except ACAClientError:
            return False

        return connection.get("state") in ("completed", "active")

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

    # Public DID

    def get_public_did(self):
        """Return this agent's public DID.

        Schema and credential definition IDs are built from this DID.
        """
        response = self.get("/wallet/did/public")
        result = response.get("result") or {}
        did = result.get("did")

        if not did:
            raise ACAClientError(
                f"{self.name}: no public DID is configured for this agent."
            )

        return did

    # Schemas
    #
    # These use the /anoncreds endpoints (ACA-Py's askar-anoncreds wallet
    # type), not the older /schemas endpoints from plain askar. See:
    # https://aca-py.org/latest/deploying/AnonCredsControllerMigration/

    def created_schemas(self):
        """Return schema IDs this agent's own wallet created.

        This is not the same as what's on the ledger; use fetch_schema()
        to check the ledger directly.
        """
        response = self.get("/anoncreds/schemas")
        return response.get("schema_ids", [])

    def fetch_schema(self, schema_id):
        """Return the schema from the ledger, or None if it isn't there."""
        try:
            response = self.get(f"/anoncreds/schema/{schema_id}")
        except ACAClientError:
            return None

        return response.get("schema") or None

    def create_schema(self, public_did, schema):
        """Create an Indy schema on the ledger."""
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
        """Return credential definition IDs this agent's wallet created.

        Like created_schemas(), this is the wallet's own list, not the
        ledger's. Use fetch_credential_definition() for the ledger.
        """
        response = self.get("/anoncreds/credential-definitions")
        return response.get("credential_definition_ids", [])

    def fetch_credential_definition(self, cred_def_id):
        """Return the credential definition from the ledger, or None.

        Finding it here doesn't mean this wallet can still use it: the
        private signing key lives only in the wallet, so after a wallet
        reset the ledger may still list a definition this agent can no
        longer sign with.
        """
        try:
            response = self.get(f"/anoncreds/credential-definition/{cred_def_id}")
        except ACAClientError:
            return None

        return response.get("credential_definition") or None

    def create_credential_definition(self, public_did, schema_id, tag="default"):
        """Create an Indy credential definition."""
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

    # Issue credential
    #
    # The agents run with --wallet-type askar-anoncreds, so Issue
    # Credential 2.0 and Present Proof 2.0 both expect their filter/
    # request/presentation payloads under an "anoncreds" key, not the
    # older "indy" key -- ACA-Py rejects "indy" outright for an
    # anoncreds-capable issuer (400: "This issuer is anoncreds capable.
    # Please use the anoncreds format.").

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
                    "anoncreds": {
                        "cred_def_id": cred_def_id,
                    }
                },
            },
        )

    def credential_exchange(self, exchange_id):
        """Return one Issue Credential 2.0 exchange."""
        result = self.get(
            f"/issue-credential-2.0/records/{exchange_id}"
        )
        return result.get("cred_ex_record", result)

    def credential_records(self, thread_id=None):
        """Return Issue Credential 2.0 exchanges.

        This endpoint wraps the actual record fields (state, cred_ex_id,
        ...) inside a "cred_ex_record" key alongside per-format details
        (anoncreds/indy/ld_proof/vc_di) -- unlike send-offer's response,
        which is flat. Unwrap it here so callers always see a flat record.
        """
        params = {}

        if thread_id:
            params["thread_id"] = thread_id

        results = self.get(
            "/issue-credential-2.0/records",
            params=params,
        ).get("results", [])

        return [result.get("cred_ex_record", result) for result in results]

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
        """Return one Present Proof 2.0 exchange."""
        result = self.get(
            f"/present-proof-2.0/records/{exchange_id}"
        )
        return result.get("pres_ex_record", result)

    def proof_records(self, thread_id=None):
        """Return Present Proof 2.0 exchanges.

        Same wrapping issue as credential_records() -- the actual record
        fields live under a "pres_ex_record" key here, not at top level.
        """
        params = {}

        if thread_id:
            params["thread_id"] = thread_id

        results = self.get(
            "/present-proof-2.0/records",
            params=params,
        ).get("results", [])

        return [result.get("pres_ex_record", result) for result in results]

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
                "anoncreds": presentation,
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
