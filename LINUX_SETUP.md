# Setup guide for testing this prototype

This project runs reliably on native Linux. On Windows and macOS, the local
Indy ledger (von-network) has a known, unresolved problem under Docker
Desktop (see the platform notice in the main README). This guide provides
three ways to get a working Linux environment regardless of platform,
plus a fallback.

Provided options:

- **Already on Linux**: no VM needed, see the main
  [README](./README.md#requirements), "Requirements" section, for
  installing the three tools directly, then "Starting the prototype".
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

If VirtualBox warns about VT-x or virtualization when creating a VM,
Hyper-V or WSL2 is probably already active and blocking it. To fix this:

1. Open Windows search, type "Turn Windows features on or off".
2. Uncheck "Hyper-V" and "Windows Subsystem for Linux".
3. Restart the machine.

**4. Set up the project folder**

This folder goes on the host operating system, the normal Windows or
macOS desktop or documents folder, not inside a VM. VirtualBox itself
needs nothing set up yet, Vagrant configures the actual VM automatically
in the next step.

1. Create a new, empty folder, e.g. `ssi-prototype-vm`.
2. Open any text editor (Notepad, Notepad++, VS Code, or similar) and
   paste in the code snippet below.
3. Save the file inside that folder as exactly `Vagrantfile` with a capital V
   and no file extension.
   - Windows Notepad: set "Save as type" to "All Files (\*.\*)" first,
     otherwise Windows silently appends `.txt`.
   - Notepad++: set the same dropdown to "All types (\*.\*)".

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

Navigate to the folder. `<path-to-the-folder>` below is a placeholder,
replace it with the actual location chosen in step 4, for example
`C:\Users\<name>\Desktop\ssi-prototype-vm`:

    cd <path-to-the-folder>

(macOS: `cd <path-to-the-folder>`, for example `/Users/<name>/Desktop/ssi-prototype-vm`.
If the path contains spaces, wrap it in quotes on either platform.)


**6. Build the VM**

Inside the terminal, type:
```
vagrant up
```

This downloads a small Ubuntu base image on first run, then installs Docker,
git and Python inside it automatically. Takes a few minutes depending on
the internet connection.

**7. Log into the VM**
```
vagrant ssh
```

From here on, this is a normal Linux terminal.

**8. Continue with "Running the prototype" below, inside this terminal.**

### Stopping / resuming later

```
vagrant halt      # stops the VM and keeps everything as it is
vagrant up        # starts it again 
vagrant destroy   # deletes the VM 
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

Follow the on-screen Ubuntu installer (choose the standard options), create
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

### Stopping / resuming / deleting later

Stopping and resuming: use UTM's own controls, the stop button pauses or
shuts down the VM and keeps everything as it is. The start (play) button
resumes it later.

Deleting the VM entirely: in UTM's VM list, right-click the VM (or select
it and use the menu) and choose "Delete". This removes the VM and its
virtual disk. It does not touch anything on the Mac host outside UTM.

## Option C: Ready-made VM copy

If neither of the above works properly, a pre-configured Ubuntu
VM (UTM format) with this project already set up is also provided, which
can only be imported and opened with UTM, not VirtualBox or other
virtualization tools. The login details are provided separately.

Stopping, resuming and deleting this VM works the same way as in Option B, 
see "Stopping / resuming / deleting later" above.

## Running the prototype

Once inside a Linux environment (native Linux, the terminal opened with
`vagrant ssh`, or the UTM VM's own terminal), continue with "Starting the
prototype" in the main [README](./README.md). The commands and the
startup sequence are the same for each option above.
