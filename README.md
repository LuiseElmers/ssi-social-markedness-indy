# SSI rental-application prototype

This repository contains a small ACA-Py / Hyperledger Indy demonstrator for a
privacy-preserving rental application. It includes a real 4-node Indy ledger
(von-network) as part of the repository, so no separate infrastructure setup
is needed.

## Platform notice: use Linux

The local Indy ledger (von-network) has a known startup problem under Docker
Desktop on macOS and Windows: the ledger webserver tries to connect to the
four consensus nodes before they have finished syncing, and that connection
attempt can fail permanently, even after retries. This is documented as an
open, unresolved issue in von-network's own repository
([bcgov/von-network#192](https://github.com/bcgov/von-network/issues/192)),
not something specific to this project.

Native Linux does not have this problem, since Docker runs directly on the
system there instead of inside the hidden VM that Docker Desktop needs on
macOS and Windows. **Running this prototype on Linux, or in a Linux VM, is
the recommended and tested way to run it.**

For step-by-step instructions on setting up a Linux environment (Vagrant,
UTM, or a ready-made VM), see [LINUX_SETUP.md](./LINUX_SETUP.md).

## Requirements

Docker, Python 3.10+ and git are needed. This project is tested and
recommended on Linux:

- [Docker Engine + the Compose plugin](https://docs.docker.com/engine/install/)
- [Python 3.10 or newer](https://www.python.org/downloads/)
- [git](https://git-scm.com/downloads)

If you are already on Linux, install the three items above directly, then continue
with "Starting the prototype" below.

If you are not on Linux, see [LINUX_SETUP.md](./LINUX_SETUP.md) for how to set up a
working Linux environment on Windows or macOS first (Vagrant, UTM, or a
ready-made VM), then follow the same steps inside it.

## Starting the prototype

```bash
git clone --recurse-submodules https://github.com/LuiseElmers/ssi-social-markedness-indy.git
cd ssi-social-markedness-indy
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

python3 main.py
```

The whole start procedure is done via one command: main.py checks whether
von-network is already running and starts it itself if it is not, so
there is no separate ledger step to remember or run first.

The first run includes a cold start of the 4-node Indy ledger, which took
about 10 minutes during development. The console prints the progress the whole time.
Every run after that is much faster (only a few seconds) since the ledger and agent
containers stay up between runs.

If the repository was cloned without `--recurse-submodules`, main.py
fetches von-network on its own on the first run.

main.py always runs the same sequence:

1. Check whether von-network is up, start it if not.
2. Prepare `.env` and resolve free host ports for the four agents.
3. Start the Government, Employer, Tenant and Landlord containers.
4. Wait for all four ACA-Py agents to answer on /status.
5. Register the two issuer DIDs (Government, Employer) on the ledger.
6. Create missing schemas, credential definitions and connections.
7. Show the CLI menu.

The IDs created during setup are stored in `runtime/state.json`, so a
second start does not recreate schemas or connections.

Tenant and Landlord do not need a ledger write role, they use DIDComm peer
DIDs. Only Government and Employer write schemas and credential
definitions.

## What the prototype does

The CLI menu covers the full Issuer to Holder to Verifier flow for the
rental use case. The Government and Employer act as issuers, the Tenant
is the holder, and the Landlord is the verifier. From the menu, the
Tenant requests a Digital ID credential from the Government and an
Employment credential from the Employer, then sends a proof to the
Landlord. That proof reveals only the employment status in plain text:
income, age and ID validity are proven through zero-knowledge predicates
instead of disclosing the actual values (for example, proving the income
is at least 2500 without revealing the exact number). The Landlord's
proof request itself can also be inspected from the menu before sending
anything, to see exactly what would be disclosed.

## Viewing the ledger

Once von-network is up:

```
http://localhost:9000
```

This is von-network's own ledger browser. It shows the schemas and
credential definitions written during setup, transaction details, and pool
status. It is separate from the prototype's CLI menu and stays reachable as
long as the containers run, so it can be opened anytime during or after a
demo. main.py also prints this URL once the ledger is ready.

## Resetting

`python3 main.py` is safe to run several times and the four agent wallets
stay intact.

To wipe the agent wallets and `runtime/state.json` and start fresh:

```bash
python3 reset.py
```

This asks for confirmation before deleting anything, so a normal
`python3 main.py` cannot accidentally trigger a reset. Whether to also
wipe the ledger is asked separately, default is no, since wiping it
means having to run the slow rebuild from the beginning. Schemas and credential
definitions stay on the ledger, only the agent wallets get deleted here.
Wipe the ledger too only if an empty one is really needed, the next
`python3 main.py` then runs the full cold start again.

## Ports and resources

Only the ports actually needed on the host get published: the four ACA-Py
Admin/inbound port pairs (8021-8052, or wherever main.py moved them if the
defaults were busy), von-network's webserver on `9000` (used for the ledger
browser above and for the `/register` and `/genesis` endpoints that are called), 
and the eight Indy node ports (`9701`-`9708`) von-network's own
compose file publishes. `--admin-insecure-mode` on the ACA-Py agents is a
deliberate choice for this local prototype.

A full 4-node Indy pool is the minimum for a real Byzantine-fault-tolerant
ledger (3f+1 nodes tolerate f faults, so 4 nodes for f=1), there is no
smaller option without changing that property. What can be reduced on a machine
is the CPU/RAM assigned to Docker itself. On native Linux that is set directly 
on the host machine, inside a VM by the VM's own resource settings. The prototype itself does
not need more than that.

## Troubleshooting

If the setup process gets stuck, the best option is to run
`python3 reset.py`, choose not to delete the ledger when asked, then
`python3 main.py` again.

This keeps the ledger running (unless told otherwise during the reset), so usually 
another cold start is not necessary.

To check whether the four agents are actually reachable, run the following from the project
directory:

```bash
docker compose ps
```

This shows whether the containers are running at all. If they are but something
still seems wrong, access the Admin API directly:

```bash
curl -s http://localhost:8032/status   # Government
curl -s http://localhost:8022/status   # Employer
curl -s http://localhost:8042/status   # Tenant
curl -s http://localhost:8052/status   # Landlord
```

(ports may be different if the default ports were already occupied, check `.env` for the
actual values). A working agent answers with JSON containing a `version`
field. No response or a connection error means that agent is not up yet or
crashed.

**If the ledger stays stuck on "not ready" for a long time**, this is
most likely the Docker Desktop issue described in the platform notice
at the top of this document:

```bash
curl -s http://localhost:9000/status
```

If this repeatedly shows `"init_error": "Error initializing pool ledger"`,
that is the issue. Switching to Linux (see [LINUX_SETUP.md](./LINUX_SETUP.md))
is the only reliable fix found so far; von-network's own suggested
workaround (`./manage stop` followed by `./manage start` from the
`von-network/` directory) sometimes helps but did not reliably fix this
during testing.

**On Apple Silicon**, running inside a Linux VM (see
[LINUX_SETUP.md](./LINUX_SETUP.md)), the images here are linux/amd64 and
run emulated, which is the main source of slow starts, separate from the
Docker Desktop issue above. If things are slow but do eventually finish,
check the VM's assigned CPU/RAM in its own settings, four emulated Indy
nodes plus the webserver fighting over too little CPU is a common reason
the pool never finds consensus.

If containers are stuck in a broken state after a failed attempt:

```bash
docker compose down
cd von-network && ./manage down && cd ..
python3 main.py
```

## Advanced / manual start

To run von-network with different options (see `von-network/manage`),
start it yourself first (`./manage start` from the `von-network/`
directory), then set `VON_NETWORK_NAME` in `.env` to whatever Docker
network it created, and run `python3 main.py` as usual. It detects the
already-running ledger and skips straight to the agent setup.
