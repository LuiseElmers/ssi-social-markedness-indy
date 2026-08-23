# SSI rental-application prototype

This repository contains a small SSI prototype for a rental application based on Hyperledger Indy. It included a real 4-node Indy ledger (von-network) as part of the
repository, so no separate infrastructure setup is needed.

## Platform notice: use Linux

The local Indy ledger (von-network) has a known startup problem under Docker Desktop
on MacOS and Windows: the ledger webserver tries to connect to the four consensus nodes
before they have finished syncing, and that connection attempt can fail permanently, even after retries. This is documented as an open, unresolved issue in von-network's
own repository ([bcgov/von-network#192](https://github.com/bcgov/von-network/issues/192)), not something that is only specific to this prototype.

Native Linux does not have this problem, since Docker runs directly on the system there
instead of inside the VM that Docker Desktop needs on macOS and Windows.
Running this prototype on Linux, or in a Linux VM, is the recommended and tested way to run it.

For step-by-step instructions on setting up a Linux environment (Vagrant, UTM, or a ready-made VM), see [LINUX_SETUP.md](./LINUX_SETUP.md).

## Requirements

Three system tools are needed: Docker, Python 3.10+, and git. This is about these three tools only, not about the project's own Python packages as these come from `requirements.txt` later in the section "Starting the prototype".

There are two situations, pick the one that matches:

### Running Linux natively

1. Open a terminal anywhere on the host machine.
2. Install Python and git:
```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-venv git
```
3. Install Docker Engine and the Compose plugin, see [docs.docker.com/engine/install](https://docs.docker.com/engine/install/).
4. Continue with "Starting the prototype" below, from the same terminal.

### Running Windows or macOS

1. Follow [LINUX_SETUP.md](./LINUX_SETUP.md) to build a working Linux environment (Vagrant, UTM, or a ready-made VM). That setup installs Docker, Python and git automatically, so nothing needs to be installed manually.
2. Open a terminal inside that environment: `vagrant ssh`for Vagrant, or the terminal inside the UTM VM. This lands in the VM's own home directory, not the folder on the Windoes or macOS host that contains the Vagrantfile (that folder is only needed to build the VM itself).
3. Continue with "Starting the prototype" below,  from the same terminal. It creates its own project folder there with `git clone`.

## Starting the prototype

Run these commands inside the Linux environment:
-  on native Linux, that is the regular terminal.
-  Inside a Vagrant VM, the terminal opened with `vagrant ssh`.
-  Inside a UTM, the terminal inside the running Ubuntu VM.

```bash
git clone --recurse-submodules https://github.com/LuiseElmers/ssi-social-markedness-indy.git
cd ssi-social-markedness-indy
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

python3 main.py
```

The whole start procedure is done via one command. main.py checks whether von-network is already running and starts it itself if it is not, so there is no separate ledger step to run first.

The first run includes a cold start of the ledger, which took about 10 minutes during development inside the emulated VM. The console prints the progress the whole time. Every run after that is much faster (only about a few seconds) as long as the ledger and agent containers are still running from the previous run. If the containers were stopped, for example after shutting down the VM overnight, see "Resuming after a break" below.

If the repository was cloned without `--recurse-submodules`, main.py fetches von-network on its own on the first run.

main.py always runs the following sequence:

1. Check whether von-network is up, start it if it is not.
2. Prepare `.env`and resolve free host ports for the four agents.
3. Start the Government, Employer, Tenant and Landlord containers.
4. Wait for all four ACA-Py agents to answer on /status.
5. Register the two issuer DIDs (Government, Employer) on the ledger.
6. Create missing schemas, credential definitions and connections.
7. Show the CLI menu.

The IDs created during setup are stored in `runtime/state.json`, so a second start does not recreate schemas or connections.

The Tenant and Landlord agents do not need a ledger write role, they use DIDComm peer DIDs. Only the Government and Employer agents write schemas and credential definitions.

## What the prototype does
The CLI menu covers the full Issuer to Holder to Verifier flow for the rental application use case. The Government and Employer act as issuers, the Tenant is the holder, and the Landlord is the verifier. From the menu, the Tenant requests a Digital ID credential from the Government and an Employment credential from the Employer, then sends a proof to the Landlord. No attribute is revealed to the Landlord in plain text. The attributes current employment, income, age and ID validity are all proven through ZKP predicates instead of disclosing the actual values (for example, it is proven that the income is at least 2500 without revealing the exact number). The Landlord's proof request itself can also be inspected from the menu before sending anything, to see exactly what would be disclosed.

## Viewing the ledger

Once the von-network is up:

```bash
http://localhost:9000
```

This is the von-network's own ledger browser. It shows the schemas and credential definitions written during the setup as well as transaction details, and pool status. It is separate from the prototype's CLI menu and stays reachable as long as the containers run. main.py also prints this URL once the ledger is ready.

How to reach this URL from a browser depends on the environment set up in [LINUX_SETUP.md](./LINUX_SETUP.md). 

Inside a UTM VM on Apple Silicon, no graphical desktop is installed, so there is no browser inside the VM itself. Once the ledger is running (after "Running the prototype"), main.py prints the VM's own network address. Open that address directly in a browser on the macOS host to access the ledger browser.

Inside a Vagrant VM, the URL is already reachable directly from the host machine's own browser, due to the port forwarding set up in the Vagrantfile. On native Linux, it opens locally without any extra steps.

## Resuming after a break

To continue after having already set the prototype up once:

### On native Linux

1. Open a terminal and navigate to the folder the GitHub repo was cloned into.
2. Activate the virtual environment:
```bash
. .venv/bin/activate
```
3. Run the start command for the SSI prototype:
```bash
   python3 main.py
```

### Inside a VM (Vagrant or UTM)

1. Resume the VM itself first (`vagrant up` for Vagrant or starting the VM in UTM's own interface for UTM).
2. Log into the VM: for Vagrant,
```bash
vagrant ssh
```
   For UTM, no separate login is needed, just open a terminal directly inside the VM's own window once it is running.
3. Navigate to the project folder:
```bash
   cd ssi-social-markedness-indy
```
4. Activate the virtual environment:
```bash
   . .venv/bin/activate
``` 
5. Run the start command for the SSI prototype:
```bash 
   python3 main.py
```

## Resetting

`python3 main.py`is safe to run several times and the four agent wallets stay intact.

To wipe the agent wallets and `runtime/state.json`and start fresh:

```bash
python3 reset.py
```

This asks for confirmation before deleting anything, so a normal `python3 main.py` cannot accidentally trigger a reset. Whether to also wipe the ledger is asked separately. The default here is no, since wiping it means having to run the slow rebuild from the beginning. Schemas and credential definitions stay on the ledger, only the agent wallets get deleted here. Wipe the ledger too only if an empty one is really needed, the next `python3 main.py` then runs full cold start again.

## Ports and resources

Only the ports that are actually needed on the host get published: the four ACA-Py Admin/inbound port pairs (8021-8052, or wherever main.py moved them if the defaults were occupied), von-network's webserver on `9000` (used for the ledger browser above and for the `/register` and `/genesis`endpoints that are called), and the eight Indy node ports (`9701`-`9708`) von-network's own compose file publishes. `--admin-insecure-mode`on the ACA-Py agents is a deliberate choice for this local prototype.

A full 4-node Indy pool is the minimum for a real Byzantine-fault-tolerant ledger (3f+1 nodes tolerate f faults, so 4 nodes for f=1), there is no smaller option without changing that property. What can be reduced on a machine is the CPU/RAM assigned to Docker itself. On native Linux that is set directly on the host machine, inside a VM by the VM's own resource settings. The prototype itself does not need more than that.

## Troubleshooting

### First run ends with a timeout while waiting for the agents

In that case, nothing is broken. On a slow (emulated) host the four agents can need longer than the wait window on the very first cold start, while the Indy nodes are still settling. The containers stay up and keep starting in the background, so just run `python3 main.py`again. The ledger and agents are already up by then, so this second start is a warm start and finishes in a few seconds.

If the setup process gets stuck, the best option is to run `python3 reset.py`, choose not to delete the ledger when asked, then `python3 main.py`again.

This keeps the ledger running (unless the option to delete the ledger was chosen during the reset), so usually another cold start is unnecessary.

To check whether the four agents are actually reachable, run the following from the project directory:

```bash
docker compose ps
```

This shows whether the containers are running at all. If they are but something still seems wrong, access the Admin API directly:

```bash
curl -s http://localhost:8022/status # Employer
curl -s http://localhost:8032/status # Government
curl -s http://localhost:8042/status # Tenant
curl -s http://localhost:8052/status # Landlord
```

The same URLs also work in a browser, but where depends on the environment:
- following the Vagrant setup, they also work directly in a browser on the Windows or Intel/AMD macOS host, since those ports are forwarded there by default, alongside port 9000. 
- Inside a UTM VM on Apple Silicon, there is no browser inside the VM itself. Use the VM's own network address from a browser on the macOS host instead (see "Viewing the ledger" above for the same distinction with the ledger browser).

The ports may be different if the default ports were already occupied, so check `.env` for the actual values. A working agent answers with JSON containing a `version`field. No response or a connection error means that agent is not up yet or has crashed.

### Ledger is stuck or not ready for a long time

This can be the Docker Desktop issue described in the platform notice at the top of this document:
```bash
curl -s http://localhost:9000/status
```

If this repeatedly shows `"init_error": "Error initializing pool ledger"`, that is the issue. Switching to Linux (see [LINUX_SETUP.md](./LINUX_SETUP.md)) is the only reliable fix found so far. von-network's own suggested fix (`./manage stop` followed by `./manage start` from the `von-network` directory) sometimes helps but did not reliably fix this issue during testing.

On Apple Silicon, running inside a Linux VM, the images here are linux/amd64 and run emulated, which is the main source of slow starts, separate from the Docker Desktop issue above. If steps during the process are slow but do eventually finish, check the VM's assigned CPU/RAM in its own settings.

### Containers are stuck in a broken state

```bash
docker compose down
cd von-network && ./manage down && cd ..
python3 main.py
```

## Advanced/manual start

To run von-network with different options (see `von-network/manage`), start it first (`./manage start` from the `von-network/` directory), then set `VON_NETWORK_NAME` in `.env` to whatever Docker network it created, and run `python3 main.py` as usual. It detects the already-running ledger and skips straight to the agent setup.

