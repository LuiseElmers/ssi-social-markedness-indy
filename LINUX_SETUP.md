# Setup guide for testing the SSI prototype

This prototype runs reliably on native Linux. On Windows and macOS, the used
local Indy ledger (von-network) has a known, unresolved problem under Desktop
(see the platform notice in the [README](./README.md)). This guide provides three ways to
get a working Linux environment plus a fallback.

Provided options:

- **Already on Linux**: no VM is needed in this case, see the main [README](./README.md#requirements),
"Requirements" section for installing the three tools directly, then "Starting the prototype".
- **Windows or Intel/AMD macOS**: use Vagrant [(Option A)](#option-a-vagrant-windows-and-macos-with-intelamd-cpus).
- **Apple Silicon Mac**: this is the environment the prototype was developed and tested in. 
Use UTM [(Option B)](#option-b-utm-apple-silicon-mac)
- **Neither of these works or is practical**: use the provided VM copy [(Option C)](#option-c-ready-made-vm-copy).

## Option A: Vagrant (Windows and macOS with Intel/AMD CPUs)

Vagrant automatically builds a small Ubuntu VM with everything needed already installed.

**1. Install VirtualBox**

- Windows: [virtualbox.org/wiki/Downloads](https://www.virtualbox.org/wiki/Downloads), download the Windows installer, run it and keep the defaults on.
- macOS (Intel): [virtualbox.org/wiki/Downloads](https://www.virtualbox.org/wiki/Downloads), download
the macOS installer and run it.
- macOS (Apple Silicon: M1/M2/M3/M4): VirtualBox support here is unreliable. Use Option B (UTM) instead of this option.

**2. Install Vagrant**

[developer.hashicorp.com/vagrant/downloads](https://developer.hashicorp.com/vagrant/downloads):

1. Download the installer for the OS in use
2. Run it
3. Restart the machine afterwards (needed so the `vagrant` command is recognized).

**3. Windows only: check for a Hyper-V/WSL2 conflict**

If VirtualBox warns about VT-x or virtualization, Hyper-V or WSL2 is probably already active and
blocking it.

To fix this:

1. Open a Windows search, type "Turn Windows features on or off".
2. Uncheck "Hyper-V" and "Windows Subsystem for Linux".
3. Restart the machine.

**4. Set up the project folder**

This folder is created on the host OS and not inside the VM. 

1. Create a new folder, for example `ssi-prototype-vm`.
2. Open a text editor (Notepad, Notepad++, VS Code or similar) and paste in the code snippet below.
3. Save the file inside that folder as exactly `Vagrantfile` with a capital V and no file extension.
   - Windows Notepad and Notepad++: set "Save as type" to "All Files" first, otherwise Windows automatically adds
    `.txt` as a file extension.

```ruby
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"

  config.vm.network "forwarded_port", guest: 9000, host: 9000
  config.vm.network "forwarded_port", guest: 8021, host: 8021
  config.vm.network "forwarded_port", guest: 8022, host: 8022
  config.vm.network "forwarded_port", guest: 8031, host: 8031
  config.vm.network "forwarded_port", guest: 8032, host: 8032
  config.vm.network "forwarded_port", guest: 8041, host: 8041
  config.vm.network "forwarded_port", guest: 8042, host: 8042
  config.vm.network "forwarded_port", guest: 8051, host: 8051
  config.vm.network "forwarded_port", guest: 8052, host: 8052

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
- macOS: Terminal app or something similar.

Navigate to the folder created in Step 4.
- Windows: `C:\Users\<name>\Desktop\ssi-prototype-vm\`
- macOS: `cd /Users/<name>/Desktop/ssi-prototype-vm`. If the path contains spaces, they have to be wrapped up in quotes.

These are only placeholders and must be replaced with the actual path to the folder.

**6. Build the VM**

Inside the terminal, type:
```bash
vagrant up
```

This downloads a small Ubuntu base image, then installs Docker, git and Python automatically.

**7. Log into the VM**

```bash
vagrant ssh
```

From here on, this is a normal Linux terminal.

**8. Continue with "Running the prototype" below, inside the terminal.**

### Stopping/resuming later

If still logged into the VM (from `vagrant ssh`), type `exit` first to get back to the host's own terminal.

```bash
vagrant halt # Stopps the VM and keeps everything as it is
vagrant up # Starts the VM again
vagrant destroy # Deletes the VM
```

These commands run on the host, from the folder with the Vagrantfile, not inside the VM. To make sure that `vagrant halt` worked, check with `vagrant status`, which should show "poweroff".

### Troubleshooting: wrong forwarded port

If the browser or host machine shows a connection error for one or more of the agent ports while
the ledger at `http://localhost:9000`is reachable, the running prototype has chosen a different port
than the default one (see `scripts/environment.py`), this only happens if the default port was already
busy at that moment.

To find out and fix it:

1. Inside the VM, check the ports:
```bash
grep ADMIN_PORT .env
```
2. On the host machine, edit the Vagrantfile:
   - change the `host:`value on the matching `forwarded_port`line above to the port found in step 1.
3. From the folder with the Vagrantfile, on the host, type in a terminal:
```bash
vagrant reload
```
This restarts the VM with the updated networking without rebuilding it or losing anything
installed inside it.

## Option B: UTM (Apple Silicon Mac)

This is the setup this prototype was developed and tested in (an x86_64 Ubuntu VM, emulated, under UTM on
Apple Silicon).

**1. Install UTM**

[mac.getutm.app](https://mac.getutm.app/) or via the macOS App Store.

**2. Download Ubuntu**

[releases.ubuntu.com/jammy](https://releases.ubuntu.com/jammy), Ubuntu 22.04. LTS
This matches the Ubuntu version that is used in the Vagrant setup. Download the "64-bit PC (AMD64) server install image" (not the ARM64 one, even though the Mac itself is Apple Silicon). The is equal to the tested setup and the linux/amd64 Docker images that were used.

**3. Create the VM in UTM**

1. Open UTM, click "Create a New Virtual Machine".
2. Choose **Virtualize** only if the guest and host architecture (own machine) match. Since the guest here is x86_64 and the Mac is Apple Silicon (arm64), choose **Emulate** instead.
3. Choose "Linux" as OS.
4. Assign at least 9 GB RAM (9216 MiB) and 5 CPU cores.
5. Assign at least 60GB of disk space, as the Docker images and ledger data take up a lot of it.
6. Browse the downloaded Ubuntu ISO.
7. Finish the VM setup with the default settings and start the VM.

**4. Install Ubuntu**

Follow the on-screen Ubuntu installer (choose the standard options), create a user account and restart when prompted. The server install image has no graphical interface, so after the restart, the VM is used through the text-based terminal inside UTM.

**Optional: connect via SSH from the Mac terminal**

This makes it easier to copy and execute commands for the VM from inside a Mac Terminal.
1. Install SSH:
```bash
sudo apt-get update
sudo apt-get install -y openssh-server
```
2. Find the VM's IP address from inside the UTM's terminal:
```bash
ip a
```
3. On the macOS, open a terminal session and connect:
```bash
ssh <username>@<vm-ip>
```
- Replace `<username>`with the account created during the VM installation. If unsure, type `whoami`into the UTM terminal to find out the account name.
- `<vm-ip>` is the IP address from step 2.
- From here on, all following commands (like Docker installation, "Running the prototype") can be run from this Mac terminal window instead of UTM's terminal.

**5. Install Docker, git and Python inside the VM**

Open a terminal inside the running Ubuntu VM and run the following commands:

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

Log out and back in (or restart the VM) afterwards, so the user is recognized as part of the `docker` group.

**6. Continue with "Running the prototype" below, inside the VM's terminal.**

### Stopping/resuming/deleting later

**Stopping and resuming:**

Use UTM's own control buttons, the stop button pauses or shuts down the VM and keeps everything as it is.
The start(play) button resumes it later.

**Deleting the VM:**

In UTM's VM list, right-click the VM or select it and use the menu, and choose "Delete". This removes the VM
and its virtual disk. It does not touch anything on the Mac host outside UTM.

## Option C: Ready-made VM copy

If neither of the options described above work properly, a pre-configured Ubuntu VM (a copy of the original VM
used for development and testing) is also provided, which can only be imported and opened with UTM, not VirtualBox
or other virtualization tools. The login details are provided separately.

Stopping, resuming and deleting the VM works the same way as in Option B, see "Stopping/resuming/deleting later" above.

## Running the prototype

Once inside a Linux environment, continue with "Starting the prototype" in the main [README](./README.md). The commands and the startup sequence are the same for each option described here.
