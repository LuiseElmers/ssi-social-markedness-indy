# Setup guide for testing this prototype

This project runs reliably on native Linux. On Windows and macOS, the local
Indy ledger (von-network) has a known, unresolved problem under Docker
Desktop (see the platform notice in the main README). This guide provides
three ways to get a working Linux environment regardless of platform,
plus a fallback.

Provided options:

- **Already on Linux**: skip to "Running the prototype" below.
- **Windows or Intel/AMD macOS**: use Vagrant (Option A).
- **Apple Silicon Mac** (this is the exact environment this project was
  developed and tested in): use UTM (Option B).
- **Neither of these works or is practical**: use the provided VM copy
  (Option C).

## Option A: Vagrant (Windows and macOS with Intel/AMD CPUs)

Vagrant automatically builds a small Ubuntu VM with everything needed
already installed.

**1. Install VirtualBox**

- Windows: [virtualbox.org/wiki/Downloads](https://www.virtualbox.org/wiki/Downloads), download the Windows installer, run it, keep the defaults.
- macOS (Intel): [virtualbox.org/wiki/Downloads](https://www.virtualbox.org/wiki/Downloads), download the macOS installer and run it.
- macOS (Apple Silicon: M1/M2/M3/M4): VirtualBox support here is still experimental and not reliable. Use Option B (UTM) instead of this option.

**2. Install Vagrant**

[developer.hashicorp.com/vagrant/downloads](https://developer.hashicorp.com/vagrant/downloads):

1. Download the installer for the OS in use
2. Run it
3. Restart the machine afterwards (needed so the `vagrant` command is recognized).

**3. Windows only: check for a Hyper-V/WSL2 conflict**

If VirtualBox complains about VT-x or virtualization when creating a VM,
Hyper-V or WSL2 is likely already active and blocking it. To fix:

1. Open Windows search, type "Windows-Features aktivieren oder deaktivieren" ("Turn Windows features on or off").
2. Uncheck "Hyper-V" and "Windows-Subsystem für Linux" (Windows Subsystem for Linux).
3. Restart the machine.

**4. Set up the project folder**

Create a new, empty folder, e.g. `ssi-prototype-vm`, and place the
`Vagrantfile` below inside it:

```ruby
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"

  # Makes the ledger browser (http://localhost:9000) reachable from the
  # host machine's own browser, not just from inside the VM.
  config.vm.network "forwarded_port", guest: 9000, host: 9000

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "9216"
    vb.cpus = 5
  end

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update
    apt-get install -y ca-certificates curl gnupg python3 python3-venv git

    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
      | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    usermod -aG docker vagrant
  SHELL
end
```

**5. Open a terminal**

- Windows: PowerShell or Command Prompt.
- macOS: Terminal.app or any other terminal.

Navigate to the folder:

    cd Path\to\ssi-prototype-vm

(macOS: `cd /path/to/ssi-prototype-vm`. If the path contains spaces, wrap it in quotes on either platform.)


**6. Build the VM**
```
vagrant up
```

Downloads a small Ubuntu base image on first run, then installs Docker,
git and Python inside it automatically. Takes a few minutes depending on
the internet connection.

**7. Log into the VM**
```
vagrant ssh
```

From here on, this is a normal Linux terminal.

**8. Continue with "Running the prototype" below, inside this terminal.**

### Viewing the ledger browser

Once the ledger is up, `http://localhost:9000` can be opened directly in
the host machine's normal browser (Windows/macOS), no extra step needed,
thanks to the port forwarding set up in the Vagrantfile.

### Stopping / resuming later

```
vagrant halt      # stop the VM, keeps everything as is
vagrant up        # start it again later
vagrant destroy   # delete the VM completely
```

## Option B: UTM (Apple Silicon Mac)

This matches the exact setup this project was developed and tested in
(an x86_64 Ubuntu VM, emulated, under UTM on Apple Silicon).

**1. Install UTM**

[mac.getutm.app](https://mac.getutm.app/) or via the Mac App Store.

**2. Download Ubuntu**

[ubuntu.com/download/desktop](https://ubuntu.com/download/desktop), the
regular **x86_64** ISO (not the ARM64 one, even though the Mac itself is Apple Silicon. 
This matches the tested setup and the linux/amd64 Docker images this project uses).

**3. Create the VM in UTM**

1. Open UTM, click "Create a New Virtual Machine".
2. Choose "Virtualize" only if guest and host architecture match. Since
   the guest here is x86_64 and the Mac is Apple Silicon (arm64), choose
   **"Emulate"** instead.
3. Choose "Linux", browse to the downloaded Ubuntu ISO.
4. Assign at least 9 GB RAM and 5 CPU cores.
5. Assign at least 60 GB of disk space (Docker images and the ledger data
   need room).
6. Finish and start the VM.

**4. Install Ubuntu**

Follow the on-screen Ubuntu installer (standard options are fine), create
a user account, restart when prompted.

**5. Install Docker, git and Python inside the VM**

Open a terminal inside the running Ubuntu VM:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg python3 python3-venv git

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc > /dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Log out and back in (or restart the VM) afterwards, so the user is
recognized as part of the `docker` group.

**6. Continue with "Running the prototype" below, inside the VM's terminal.**

**7. Viewing the ledger browser**

Since the browser inside the Ubuntu VM works normally, `http://localhost:9000`
can be opened directly there and no extra networking setup is needed.

## Option C: Ready-made VM copy

If neither of the above works properly, a pre-configured Ubuntu
VM (UTM format) with this project already set up is also provided, which
can only be imported and opened with UTM, not VirtualBox or other
virtualization tools. The login details are provided separately.

## Running the prototype

Once inside a Linux environment:

```bash
git clone --recurse-submodules https://github.com/LuiseElmers/ssi-social-markedness-indy.git
cd ssi-social-markedness-indy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 main.py
```

The first run cold-starts the 4-node Indy ledger, which took about 10
minutes during development. The console prints the progress the whole time.
Every run after that is much faster (only a few seconds) since the ledger and agent
containers stay up between runs.

See the main [README](./README.md) for what the startup does step by
step, how to reset, and further troubleshooting.
