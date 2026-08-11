# SSI rental-application prototype

This repository contains a small ACA-Py / Hyperledger Indy demonstrator for a
privacy-preserving rental application. It includes a real 4-node Indy ledger
(von-network) as part of the repository, so no separate infrastructure setup
is needed.

## Two-step start: ledger once, prototype every time

Starting a 4-node Indy ledger from cold is the slow part of this project --
on an emulated host (e.g. Apple Silicon running the project's `linux/amd64`
images) it can take several minutes for the nodes to find consensus. That
cost only needs to be paid **once per work session**, not on every test run
or demo -- so ledger startup and prototype startup are two separate scripts:

```bash
git clone --recurse-submodules <repository-url>
cd <repository>
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

python3 ledger_up.py   # once per session (after a reboot, or the first time)
python3 start.py       # every time you want the prototype -- fast
```

If you already cloned without `--recurse-submodules`, `ledger_up.py`
fetches von-network for you on its first run -- no manual clone of a
separate von-network repository is needed either way, and cloning it
separately would not be any faster: it's the same Docker images and the
same emulation either way. The speed comes purely from **not** tearing the
ledger down and rebuilding it between runs.

**`ledger_up.py`** (slow, run once per session):

1. Creates `.env` from `.env.example` if it doesn't exist yet.
2. Fetches von-network (git submodule) if it isn't there yet.
3. Starts von-network's `webserver`, `node1`-`node4` containers via its own
   `./manage start` script -- the same containers and startup logic the
   von-network project itself uses and tests, not a reimplementation. If
   they're already running unchanged, this is an instant no-op.
4. Waits for the ledger to answer (this is the step that can take several
   minutes on a cold start), then fetches the current `genesis.txn` from it.
5. Discovers the Docker network von-network created and writes it into
   `.env` as `VON_NETWORK_NAME`.

Leave the containers running after this finishes -- don't run it again just
to start the prototype.

**`start.py`** (fast, run every time):

1. Checks that von-network is already up and ready (a couple of seconds).
   If it isn't, this fails immediately with a pointer back to `ledger_up.py`
   instead of waiting or trying to start it itself.
2. Resolves free host ports for the four agents if the defaults are busy.
3. Runs `main.py`, which performs the existing SSI startup sequence.

`main.py` itself is unchanged and always performs the same sequence:

1. Check that the von-network Docker network exists.
2. Start the Government, Employer, Tenant and Landlord containers.
3. Poll each ACA-Py `/status` endpoint (all four in parallel) until they answer.
4. Register the two issuer DIDs on the ledger.
5. Create missing schemas, credential definitions and connections.
6. Show the CLI menu.

The IDs created during setup are stored in `runtime/state.json`. Therefore a
second start does not create new schemas or connections.

Tenant and Landlord do not need a ledger write role. They use DIDComm peer DIDs;
only Government and Employer write schemas and credential definitions.

## Resetting

`python3 start.py` is safe to run repeatedly: the four agent wallets are kept.

To wipe the agent wallets and `runtime/state.json` and start the prototype
fresh, run:

```bash
python3 reset.py
```

This asks for explicit confirmation before deleting anything, so a normal
`python3 start.py` can never accidentally trigger a reset. It then separately
asks whether to also wipe the Indy ledger itself (von-network) -- default is
no, since that forces the slow rebuild `ledger_up.py`/`start.py` are split up
to avoid paying repeatedly, and is rarely actually necessary: schemas and
credential definitions live in the ledger, but which ones an agent can still
use is governed by its wallet, which this always resets. Only choose to also
wipe the ledger if you specifically need a truly empty one (e.g. starting a
new demo environment from scratch). If you do, run `ledger_up.py` again
before `start.py`.

## Ports and resources

Only the ports actually needed on the host are published: the four ACA-Py
Admin/inbound port pairs (8021-8052, or whatever `start.py` moved them to if
the defaults were busy), von-network's webserver on `9000` (used both for
the demo ledger browser and for the `/register` and `/genesis` endpoints
this project's own code calls), and the eight Indy node ports (`9701`-`9708`)
von-network's own compose file publishes by default. `--admin-insecure-mode`
on the ACA-Py agents is a deliberate, documented choice for this local
prototype, not something to carry over into any non-local deployment.

A full 4-node Indy pool is the minimum for a real Byzantine-fault-tolerant
ledger (3f+1 nodes tolerate f faults, so 4 nodes for f=1) -- there isn't a
smaller "lightweight" node count without changing that property, so this
project doesn't offer one. What you can safely reduce on a constrained
machine is Docker's own CPU/RAM allocation (see your Docker/VM settings);
the prototype doesn't need to reserve resources beyond what Docker itself
is configured to use.

## Troubleshooting on Apple Silicon (Docker Desktop / UTM)

The images in this project are `linux/amd64` and therefore run emulated on
Apple Silicon, which is the dominant source of slow or flaky starts. If
`ledger_up.py` repeatedly can't get the ledger ready:

- In Docker Desktop, check **Settings > General > "Use Rosetta for
  x86_64/amd64 emulation on Apple Silicon"** -- without it, Docker falls
  back to full QEMU emulation, which is markedly slower.
- Check **Settings > Resources** (CPU/RAM) -- four emulated Indy nodes plus
  the webserver competing for too little CPU is a common cause of a pool
  that never finishes finding consensus.
- If containers are left in a broken state after a failed attempt:
  ```bash
  docker compose down
  cd von-network && ./manage down && cd ..
  python3 ledger_up.py
  ```

## Advanced / manual start

If you want to run von-network with different options (see
`von-network/manage`), start it yourself first (`./manage start` from the
`von-network/` directory), then set `VON_NETWORK_NAME` in `.env` to
whatever Docker network it created, and run `python3 main.py` directly
instead of `python3 start.py`.

