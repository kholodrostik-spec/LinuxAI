"""
scripts/seed_base_data.py
Seeds reference data: distros, drivers, devices, packages, commands.
Safe to run multiple times — uses ON CONFLICT DO NOTHING everywhere.
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.db import get_connection


def get_distro_id(cur, name: str) -> int:
    cur.execute("SELECT id FROM distros WHERE name = %s", (name,))
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"Distro not found: {name}")
    return row[0]


def main() -> None:
    distros = [
        ("Ubuntu",      "Debian",   "apt",    "sudo apt install {package}"),
        ("Debian",      "Debian",   "apt",    "sudo apt install {package}"),
        ("Pop!_OS",     "Debian",   "apt",    "sudo apt install {package}"),
        ("Linux Mint",  "Debian",   "apt",    "sudo apt install {package}"),
        ("Fedora",      "Red Hat",  "dnf",    "sudo dnf install {package}"),
        ("Arch",        "Arch",     "pacman", "sudo pacman -S {package}"),
        ("Manjaro",     "Arch",     "pacman", "sudo pacman -S {package}"),
        ("EndeavourOS", "Arch",     "pacman", "sudo pacman -S {package}"),
        ("openSUSE",    "SUSE",     "zypper", "sudo zypper install {package}"),
    ]

    drivers = [
        ("nvidia",                "nvidia",                 "proprietary", "NVIDIA proprietary driver"),
        ("nouveau",               "nouveau",                "kernel",      "Open-source NVIDIA driver"),
        ("i915",                  "i915",                   "kernel",      "Intel integrated graphics driver"),
        ("xe",                    "xe",                     "kernel",      "New Intel Xe graphics driver"),
        ("amdgpu",                "amdgpu",                 "kernel",      "AMD GPU kernel driver"),
        ("radeon",                "radeon",                 "kernel",      "Older AMD Radeon driver"),
        ("iwlwifi",               "iwlwifi",                "kernel",      "Intel Wi-Fi kernel driver"),
        ("rtw88",                 "rtw88",                  "kernel",      "Realtek Wi-Fi kernel driver family"),
        ("rtw89",                 "rtw89",                  "kernel",      "Realtek newer Wi-Fi kernel driver family"),
        ("rtl8821ce",             "8821ce",                 "dkms",        "Realtek RTL8821CE DKMS driver"),
        ("ath10k",                "ath10k_pci",             "kernel",      "Qualcomm Atheros Wi-Fi driver"),
        ("ath11k",                "ath11k_pci",             "kernel",      "Qualcomm Wi-Fi 6 driver"),
        ("mt7921e",               "mt7921e",                "kernel",      "MediaTek MT7921 PCIe Wi-Fi driver"),
        ("mt7925e",               "mt7925e",                "kernel",      "MediaTek newer PCIe Wi-Fi driver"),
        ("btusb",                 "btusb",                  "kernel",      "Generic USB Bluetooth driver"),
        ("bluetooth",             "bluetooth",              "kernel",      "Linux Bluetooth kernel subsystem"),
        ("r8169",                 "r8169",                  "kernel",      "Realtek Ethernet kernel driver"),
        ("e1000e",                "e1000e",                 "kernel",      "Intel Ethernet kernel driver"),
        ("igc",                   "igc",                    "kernel",      "Intel 2.5G Ethernet driver"),
        ("snd_hda_intel",         "snd_hda_intel",          "kernel",      "Intel HD Audio driver"),
        ("snd_sof_pci_intel_tgl", "snd_sof_pci_intel_tgl", "kernel",      "Intel SOF audio driver for newer laptops"),
        ("snd_sof_pci_intel_cnl", "snd_sof_pci_intel_cnl", "kernel",      "Intel SOF audio driver"),
        ("snd_usb_audio",         "snd_usb_audio",          "kernel",      "USB audio driver"),
        ("libinput",              "libinput",               "userspace",   "Common Linux input driver stack"),
        ("i2c_hid",               "i2c_hid",                "kernel",      "I2C HID touchpad/touchscreen driver"),
        ("hid_multitouch",        "hid_multitouch",         "kernel",      "Multitouch HID input driver"),
        ("nvme",                  "nvme",                   "kernel",      "NVMe storage driver"),
        ("ahci",                  "ahci",                   "kernel",      "SATA AHCI driver"),
    ]

    devices = [
        ("NVIDIA GTX 1650 Laptop GPU",         "NVIDIA",            "gpu",         None, None, "Discrete laptop GPU"),
        ("NVIDIA RTX 3050 Laptop GPU",         "NVIDIA",            "gpu",         None, None, "Discrete laptop GPU"),
        ("NVIDIA RTX 3060 Laptop GPU",         "NVIDIA",            "gpu",         None, None, "Discrete laptop GPU"),
        ("NVIDIA RTX 4050 Laptop GPU",         "NVIDIA",            "gpu",         None, None, "Discrete laptop GPU"),
        ("NVIDIA RTX 4060 Laptop GPU",         "NVIDIA",            "gpu",         None, None, "Discrete laptop GPU"),
        ("NVIDIA RTX 4070 Laptop GPU",         "NVIDIA",            "gpu",         None, None, "Discrete laptop GPU"),
        ("Intel UHD Graphics",                 "Intel",             "gpu",         None, None, "Intel integrated graphics"),
        ("Intel Iris Xe Graphics",             "Intel",             "gpu",         None, None, "Intel integrated graphics"),
        ("Intel Arc Graphics",                 "Intel",             "gpu",         None, None, "Intel Arc graphics"),
        ("AMD Radeon Vega Graphics",           "AMD",               "gpu",         None, None, "AMD integrated graphics"),
        ("AMD Radeon RX 5500M",                "AMD",               "gpu",         None, None, "AMD laptop GPU"),
        ("AMD Radeon RX 6600M",                "AMD",               "gpu",         None, None, "AMD laptop GPU"),
        ("AMD Radeon RX 7600S",                "AMD",               "gpu",         None, None, "AMD laptop GPU"),
        ("Intel AC 9560 Wi-Fi",                "Intel",             "wifi",        None, None, "Intel Wi-Fi adapter"),
        ("Intel AX200 Wi-Fi",                  "Intel",             "wifi",        None, None, "Intel Wi-Fi 6 adapter"),
        ("Intel AX201 Wi-Fi",                  "Intel",             "wifi",        None, None, "Intel Wi-Fi 6 adapter"),
        ("Intel AX210 Wi-Fi",                  "Intel",             "wifi",        None, None, "Intel Wi-Fi 6E adapter"),
        ("Intel AX211 Wi-Fi",                  "Intel",             "wifi",        None, None, "Intel Wi-Fi 6E adapter"),
        ("Intel BE200 Wi-Fi",                  "Intel",             "wifi",        None, None, "Intel Wi-Fi 7 adapter"),
        ("Realtek RTL8821CE Wi-Fi",            "Realtek",           "wifi",        None, None, "Common Realtek Wi-Fi adapter"),
        ("Realtek RTL8822CE Wi-Fi",            "Realtek",           "wifi",        None, None, "Common Realtek Wi-Fi adapter"),
        ("Realtek RTL8852AE Wi-Fi",            "Realtek",           "wifi",        None, None, "Realtek Wi-Fi 6 adapter"),
        ("Realtek RTL8852BE Wi-Fi",            "Realtek",           "wifi",        None, None, "Realtek Wi-Fi 6 adapter"),
        ("Realtek RTL8852CE Wi-Fi",            "Realtek",           "wifi",        None, None, "Realtek Wi-Fi 6 adapter"),
        ("MediaTek MT7921 Wi-Fi",              "MediaTek",          "wifi",        None, None, "MediaTek Wi-Fi 6 adapter"),
        ("MediaTek MT7922 Wi-Fi",              "MediaTek",          "wifi",        None, None, "MediaTek Wi-Fi 6E adapter"),
        ("MediaTek MT7925 Wi-Fi",              "MediaTek",          "wifi",        None, None, "MediaTek newer Wi-Fi adapter"),
        ("Qualcomm Atheros QCA9377 Wi-Fi",     "Qualcomm Atheros",  "wifi",        None, None, "Qualcomm/Atheros Wi-Fi adapter"),
        ("Qualcomm Atheros QCA6174 Wi-Fi",     "Qualcomm Atheros",  "wifi",        None, None, "Qualcomm/Atheros Wi-Fi adapter"),
        ("Intel Bluetooth",                    "Intel",             "bluetooth",   None, None, "Bluetooth paired with Intel Wi-Fi adapters"),
        ("Realtek Bluetooth",                  "Realtek",           "bluetooth",   None, None, "Bluetooth paired with Realtek Wi-Fi adapters"),
        ("MediaTek Bluetooth",                 "MediaTek",          "bluetooth",   None, None, "Bluetooth paired with MediaTek Wi-Fi adapters"),
        ("Qualcomm Bluetooth",                 "Qualcomm",          "bluetooth",   None, None, "Bluetooth paired with Qualcomm Wi-Fi adapters"),
        ("Intel HD Audio",                     "Intel",             "audio",       None, None, "Common Intel laptop audio device"),
        ("Realtek ALC Audio",                  "Realtek",           "audio",       None, None, "Common Realtek audio codec"),
        ("AMD HD Audio",                       "AMD",               "audio",       None, None, "AMD HDMI/DisplayPort audio"),
        ("NVIDIA HD Audio",                    "NVIDIA",            "audio",       None, None, "NVIDIA HDMI/DisplayPort audio"),
        ("Synaptics Touchpad",                 "Synaptics",         "touchpad",    None, None, "Common laptop touchpad"),
        ("ELAN Touchpad",                      "ELAN",              "touchpad",    None, None, "Common laptop touchpad"),
        ("Precision Touchpad",                 "Microsoft/Generic", "touchpad",    None, None, "Modern laptop precision touchpad"),
        ("Goodix Fingerprint Reader",          "Goodix",            "fingerprint", None, None, "Fingerprint reader, support varies"),
        ("Validity Fingerprint Reader",        "Validity/Synaptics","fingerprint", None, None, "Fingerprint reader, support varies"),
        ("Realtek RTL8111/8168/8411 Ethernet", "Realtek",           "ethernet",    None, None, "Common Realtek Ethernet adapter"),
        ("Intel I219 Ethernet",                "Intel",             "ethernet",    None, None, "Common Intel Ethernet adapter"),
        ("Intel I225 Ethernet",                "Intel",             "ethernet",    None, None, "Intel 2.5G Ethernet adapter"),
        ("Intel I226 Ethernet",                "Intel",             "ethernet",    None, None, "Intel 2.5G Ethernet adapter"),
        ("NVMe SSD",                           "Generic",           "storage",     None, None, "NVMe storage device"),
        ("SATA SSD",                           "Generic",           "storage",     None, None, "SATA storage device"),
        ("Intel RST Controller",               "Intel",             "storage",     None, None, "May require switching BIOS from RAID/RST to AHCI"),
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.executemany(
                """
                INSERT INTO distros (name, family, package_manager, install_command_template)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
                """,
                distros,
            )

            cur.executemany(
                """
                INSERT INTO drivers (name, kernel_module, driver_type, notes)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
                """,
                drivers,
            )

            cur.executemany(
                """
                INSERT INTO devices (name, vendor, device_type, pci_id, usb_id, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (name, vendor) DO NOTHING
                """,
                devices,
            )

            ubuntu_id    = get_distro_id(cur, "Ubuntu")
            debian_id    = get_distro_id(cur, "Debian")
            popos_id     = get_distro_id(cur, "Pop!_OS")
            mint_id      = get_distro_id(cur, "Linux Mint")
            fedora_id    = get_distro_id(cur, "Fedora")
            arch_id      = get_distro_id(cur, "Arch")
            manjaro_id   = get_distro_id(cur, "Manjaro")
            endeavour_id = get_distro_id(cur, "EndeavourOS")
            opensuse_id  = get_distro_id(cur, "openSUSE")
            arch_like_ids = [arch_id, manjaro_id, endeavour_id]

            packages: list[tuple] = []

            for distro_id in [ubuntu_id, popos_id, mint_id]:
                packages.extend([
                    ("linux-firmware",  distro_id, "Firmware for Wi-Fi, Bluetooth, GPU",           "sudo apt install linux-firmware"),
                    ("nvidia-driver",   distro_id, "NVIDIA proprietary driver family",             "sudo ubuntu-drivers autoinstall"),
                    ("nvidia-prime",    distro_id, "NVIDIA Optimus hybrid graphics switching",     "sudo apt install nvidia-prime"),
                    ("mesa-utils",      distro_id, "OpenGL diagnostic tools (glxinfo)",            "sudo apt install mesa-utils"),
                    ("vulkan-tools",    distro_id, "Vulkan diagnostic tools (vulkaninfo)",         "sudo apt install vulkan-tools"),
                    ("dkms",            distro_id, "Dynamic Kernel Module Support",                "sudo apt install dkms"),
                    ("build-essential", distro_id, "Build tools for compiling kernel modules",     "sudo apt install build-essential"),
                    ("mokutil",         distro_id, "Tool for checking Secure Boot state",          "sudo apt install mokutil"),
                    ("inxi",            distro_id, "System information tool",                      "sudo apt install inxi"),
                    ("hardinfo",        distro_id, "GUI system information tool",                  "sudo apt install hardinfo"),
                    ("lm-sensors",      distro_id, "Hardware sensors and temperatures",            "sudo apt install lm-sensors"),
                    ("powertop",        distro_id, "Power usage diagnostic tool",                  "sudo apt install powertop"),
                    ("tlp",             distro_id, "Laptop battery optimization",                  "sudo apt install tlp"),
                    ("fwupd",           distro_id, "Firmware update daemon",                       "sudo apt install fwupd"),
                    ("bluez",           distro_id, "Bluetooth stack",                              "sudo apt install bluez"),
                    ("blueman",         distro_id, "Bluetooth manager GUI",                        "sudo apt install blueman"),
                    ("pavucontrol",     distro_id, "PulseAudio/PipeWire volume control",           "sudo apt install pavucontrol"),
                    ("pipewire",        distro_id, "Modern Linux audio server",                    "sudo apt install pipewire"),
                    ("wireplumber",     distro_id, "PipeWire session manager",                     "sudo apt install wireplumber"),
                ])

            packages.extend([
                ("firmware-iwlwifi",      debian_id, "Intel Wi-Fi firmware on Debian",         "sudo apt install firmware-iwlwifi"),
                ("firmware-realtek",      debian_id, "Realtek firmware on Debian",             "sudo apt install firmware-realtek"),
                ("firmware-misc-nonfree", debian_id, "Various non-free firmware on Debian",    "sudo apt install firmware-misc-nonfree"),
                ("nvidia-driver",         debian_id, "NVIDIA proprietary driver on Debian",    "sudo apt install nvidia-driver"),
                ("linux-headers-amd64",   debian_id, "Kernel headers for DKMS modules",        "sudo apt install linux-headers-amd64"),
                ("dkms",                  debian_id, "Dynamic Kernel Module Support",           "sudo apt install dkms"),
                ("build-essential",       debian_id, "Build tools",                            "sudo apt install build-essential"),
                ("mesa-utils",            debian_id, "OpenGL diagnostic tools",                "sudo apt install mesa-utils"),
                ("vulkan-tools",          debian_id, "Vulkan diagnostic tools",                "sudo apt install vulkan-tools"),
                ("mokutil",               debian_id, "Secure Boot status tool",                "sudo apt install mokutil"),
                ("inxi",                  debian_id, "System information tool",                "sudo apt install inxi"),
                ("bluez",                 debian_id, "Bluetooth stack",                        "sudo apt install bluez"),
                ("blueman",               debian_id, "Bluetooth manager GUI",                  "sudo apt install blueman"),
                ("pipewire",              debian_id, "Modern Linux audio server",              "sudo apt install pipewire"),
                ("wireplumber",           debian_id, "PipeWire session manager",               "sudo apt install wireplumber"),
            ])

            packages.extend([
                ("linux-firmware",           fedora_id, "Firmware for hardware support",           "sudo dnf install linux-firmware"),
                ("akmod-nvidia",             fedora_id, "NVIDIA driver via RPM Fusion",            "sudo dnf install akmod-nvidia"),
                ("xorg-x11-drv-nvidia-cuda", fedora_id, "NVIDIA CUDA support via RPM Fusion",     "sudo dnf install xorg-x11-drv-nvidia-cuda"),
                ("mesa-demos",               fedora_id, "OpenGL diagnostic tools",                 "sudo dnf install mesa-demos"),
                ("vulkan-tools",             fedora_id, "Vulkan diagnostic tools",                 "sudo dnf install vulkan-tools"),
                ("dkms",                     fedora_id, "Dynamic Kernel Module Support",           "sudo dnf install dkms"),
                ("kernel-devel",             fedora_id, "Kernel headers/devel package",            "sudo dnf install kernel-devel"),
                ("gcc",                      fedora_id, "GNU compiler",                            "sudo dnf install gcc"),
                ("make",                     fedora_id, "Build tool",                              "sudo dnf install make"),
                ("mokutil",                  fedora_id, "Secure Boot status tool",                 "sudo dnf install mokutil"),
                ("inxi",                     fedora_id, "System information tool",                 "sudo dnf install inxi"),
                ("lm_sensors",               fedora_id, "Hardware sensors",                        "sudo dnf install lm_sensors"),
                ("bluez",                    fedora_id, "Bluetooth stack",                         "sudo dnf install bluez"),
                ("blueman",                  fedora_id, "Bluetooth manager GUI",                   "sudo dnf install blueman"),
                ("pipewire",                 fedora_id, "Modern Linux audio server",               "sudo dnf install pipewire"),
                ("wireplumber",              fedora_id, "PipeWire session manager",                "sudo dnf install wireplumber"),
            ])

            for distro_id in arch_like_ids:
                packages.extend([
                    ("linux-firmware", distro_id, "Firmware for hardware support",                 "sudo pacman -S linux-firmware"),
                    ("nvidia",         distro_id, "NVIDIA proprietary driver for standard kernel", "sudo pacman -S nvidia"),
                    ("nvidia-utils",   distro_id, "NVIDIA utilities including nvidia-smi",         "sudo pacman -S nvidia-utils"),
                    ("nvidia-dkms",    distro_id, "NVIDIA DKMS driver",                            "sudo pacman -S nvidia-dkms"),
                    ("mesa-utils",     distro_id, "OpenGL diagnostic tools",                       "sudo pacman -S mesa-utils"),
                    ("vulkan-tools",   distro_id, "Vulkan diagnostic tools",                       "sudo pacman -S vulkan-tools"),
                    ("dkms",           distro_id, "Dynamic Kernel Module Support",                 "sudo pacman -S dkms"),
                    ("base-devel",     distro_id, "Build tools group",                             "sudo pacman -S base-devel"),
                    ("sof-firmware",   distro_id, "Sound Open Firmware for newer laptops",         "sudo pacman -S sof-firmware"),
                    ("alsa-utils",     distro_id, "ALSA audio utilities",                          "sudo pacman -S alsa-utils"),
                    ("pipewire",       distro_id, "Modern Linux audio server",                     "sudo pacman -S pipewire"),
                    ("wireplumber",    distro_id, "PipeWire session manager",                      "sudo pacman -S wireplumber"),
                    ("bluez",          distro_id, "Bluetooth stack",                               "sudo pacman -S bluez"),
                    ("bluez-utils",    distro_id, "Bluetooth utilities",                           "sudo pacman -S bluez-utils"),
                    ("fwupd",          distro_id, "Firmware update daemon",                        "sudo pacman -S fwupd"),
                    ("inxi",           distro_id, "System information tool",                       "sudo pacman -S inxi"),
                    ("lm_sensors",     distro_id, "Hardware sensors",                              "sudo pacman -S lm_sensors"),
                ])

            packages.extend([
                ("kernel-firmware-all", opensuse_id, "Firmware for hardware support",         "sudo zypper install kernel-firmware-all"),
                ("nvidia-driver",       opensuse_id, "NVIDIA proprietary driver",             "sudo zypper install-new-recommends"),
                ("Mesa-demo-x",         opensuse_id, "OpenGL diagnostic tools",               "sudo zypper install Mesa-demo-x"),
                ("vulkan-tools",        opensuse_id, "Vulkan diagnostic tools",               "sudo zypper install vulkan-tools"),
                ("dkms",                opensuse_id, "Dynamic Kernel Module Support",         "sudo zypper install dkms"),
                ("gcc",                 opensuse_id, "GNU compiler",                          "sudo zypper install gcc"),
                ("make",                opensuse_id, "Build tool",                            "sudo zypper install make"),
                ("mokutil",             opensuse_id, "Secure Boot status tool",               "sudo zypper install mokutil"),
                ("inxi",                opensuse_id, "System information tool",               "sudo zypper install inxi"),
                ("bluez",               opensuse_id, "Bluetooth stack",                       "sudo zypper install bluez"),
            ])

            cur.executemany(
                """
                INSERT INTO packages (name, distro_id, purpose, install_command)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name, distro_id) DO NOTHING
                """,
                packages,
            )

            commands: list[tuple] = [
                (None, "Show OS release",                "cat /etc/os-release",                                    "low",    "Shows Linux distribution information",             None),
                (None, "List PCI devices and drivers",   "lspci -nnk",                                             "low",    "Shows PCI hardware and active kernel drivers",     None),
                (None, "List USB devices",               "lsusb",                                                  "low",    "Shows connected USB devices",                      None),
                (None, "Show kernel version",            "uname -a",                                               "low",    "Shows Linux kernel version",                       None),
                (None, "List loaded kernel modules",     "lsmod",                                                  "low",    "Shows loaded kernel modules",                      None),
                (None, "Check Secure Boot status",       "mokutil --sb-state",                                     "low",    "Shows whether Secure Boot is enabled",             None),
                (None, "Check blocked wireless devices", "rfkill list",                                            "low",    "Shows Wi-Fi/Bluetooth block status",               None),
                (None, "Show network interfaces",        "ip a",                                                   "low",    "Shows network interfaces",                         None),
                (None, "Show Wi-Fi devices",             "iw dev",                                                 "low",    "Shows wireless interfaces",                        None),
                (None, "Show recent firmware errors",    "dmesg | grep -i firmware",                               "low",    "Searches kernel log for firmware errors",          None),
                (None, "Show recent NVIDIA errors",      "dmesg | grep -i nvidia",                                 "low",    "Searches kernel log for NVIDIA messages",          None),
                (None, "Show recent Wi-Fi errors",       "dmesg | grep -i wifi",                                   "low",    "Searches kernel log for Wi-Fi messages",           None),
                (None, "Show NVIDIA driver status",      "nvidia-smi",                                             "low",    "Shows NVIDIA GPU status if driver is working",     None),
                (None, "Show GPU devices",               "lspci -nnk | grep -A3 -E 'VGA|3D|Display'",             "low",    "Shows GPU devices and drivers",                    None),
                (None, "Show network devices",           "lspci -nnk | grep -A3 -E 'Network|Ethernet|Wireless'",  "low",    "Shows network devices and drivers",                None),
                (None, "Show audio devices",             "lspci -nnk | grep -A3 -i audio",                        "low",    "Shows audio devices and drivers",                  None),
                (None, "Show system summary",            "inxi -Fxxx",                                             "low",    "Shows full hardware summary",                      None),
                (None, "Check audio sinks",              "pactl list short sinks",                                 "low",    "Lists audio output devices",                       None),
                (None, "Check PipeWire service",         "systemctl --user status pipewire",                       "low",    "Shows PipeWire user service status",               None),
                (None, "Check Bluetooth service",        "systemctl status bluetooth",                             "low",    "Shows Bluetooth service status",                   None),
                (None, "Start Bluetooth service",        "sudo systemctl start bluetooth",                         "medium", "Starts Bluetooth service",                         "sudo systemctl stop bluetooth"),
                (None, "Enable Bluetooth service",       "sudo systemctl enable bluetooth",                        "medium", "Enables Bluetooth service at boot",                "sudo systemctl disable bluetooth"),
            ]

            for distro_id in [ubuntu_id, popos_id, mint_id]:
                commands.extend([
                    (distro_id, "Update package lists",               "sudo apt update",                                   "low",    "Refreshes package metadata",                        None),
                    (distro_id, "Upgrade packages",                   "sudo apt upgrade",                                  "medium", "Upgrades installed packages",                       None),
                    (distro_id, "List available Ubuntu drivers",      "ubuntu-drivers devices",                            "low",    "Shows recommended proprietary drivers",             None),
                    (distro_id, "Install recommended Ubuntu drivers",  "sudo ubuntu-drivers autoinstall",                  "medium", "Installs recommended proprietary drivers",          None),
                    (distro_id, "Install Linux firmware",             "sudo apt install linux-firmware",                   "medium", "Installs firmware package",                         "sudo apt remove linux-firmware"),
                    (distro_id, "Install NVIDIA Prime",               "sudo apt install nvidia-prime",                     "medium", "Installs NVIDIA Prime tools",                       "sudo apt remove nvidia-prime"),
                    (distro_id, "Switch to NVIDIA performance mode",  "sudo prime-select nvidia",                          "medium", "Switches hybrid graphics to NVIDIA mode",           "sudo prime-select intel"),
                    (distro_id, "Switch to Intel graphics mode",      "sudo prime-select intel",                           "medium", "Switches hybrid graphics to Intel mode",            "sudo prime-select nvidia"),
                    (distro_id, "Install Mesa utils",                 "sudo apt install mesa-utils",                       "medium", "Installs OpenGL diagnostic tools",                  "sudo apt remove mesa-utils"),
                    (distro_id, "Install Vulkan tools",               "sudo apt install vulkan-tools",                     "medium", "Installs Vulkan diagnostic tools",                  "sudo apt remove vulkan-tools"),
                    (distro_id, "Install DKMS",                       "sudo apt install dkms",                             "medium", "Installs DKMS",                                     "sudo apt remove dkms"),
                    (distro_id, "Install build tools",                "sudo apt install build-essential",                  "medium", "Installs build tools",                              "sudo apt remove build-essential"),
                    (distro_id, "Install sensors",                    "sudo apt install lm-sensors",                       "medium", "Installs hardware sensors tool",                    "sudo apt remove lm-sensors"),
                    (distro_id, "Detect sensors",                     "sudo sensors-detect",                               "medium", "Detects available hardware sensors",                None),
                    (distro_id, "Install Bluetooth stack",            "sudo apt install bluez blueman",                    "medium", "Installs Bluetooth stack and manager",              "sudo apt remove bluez blueman"),
                    (distro_id, "Install PipeWire audio tools",       "sudo apt install pipewire wireplumber pavucontrol", "medium", "Installs PipeWire audio components",                "sudo apt remove pipewire wireplumber pavucontrol"),
                ])

            commands.extend([
                (debian_id, "Update package lists",           "sudo apt update",                         "low",    "Refreshes package metadata",                          None),
                (debian_id, "Upgrade packages",               "sudo apt upgrade",                        "medium", "Upgrades installed packages",                         None),
                (debian_id, "Install Intel Wi-Fi firmware",   "sudo apt install firmware-iwlwifi",       "medium", "Installs Intel Wi-Fi firmware on Debian",             "sudo apt remove firmware-iwlwifi"),
                (debian_id, "Install Realtek firmware",       "sudo apt install firmware-realtek",       "medium", "Installs Realtek firmware on Debian",                 "sudo apt remove firmware-realtek"),
                (debian_id, "Install miscellaneous firmware", "sudo apt install firmware-misc-nonfree",  "medium", "Installs various non-free firmware packages",         "sudo apt remove firmware-misc-nonfree"),
                (debian_id, "Install NVIDIA driver",          "sudo apt install nvidia-driver",          "medium", "Installs NVIDIA proprietary driver on Debian",        "sudo apt remove nvidia-driver"),
                (debian_id, "Install kernel headers",         "sudo apt install linux-headers-amd64",    "medium", "Installs kernel headers for DKMS modules",            "sudo apt remove linux-headers-amd64"),
            ])

            commands.extend([
                (fedora_id, "Check Fedora updates",         "sudo dnf check-update",                    "low",    "Checks available package updates",                    None),
                (fedora_id, "Upgrade Fedora packages",      "sudo dnf upgrade",                         "medium", "Upgrades installed packages",                         None),
                (fedora_id, "Install Linux firmware",       "sudo dnf install linux-firmware",          "medium", "Installs firmware package",                           "sudo dnf remove linux-firmware"),
                (fedora_id, "Install NVIDIA akmod",         "sudo dnf install akmod-nvidia",            "medium", "Installs NVIDIA driver via RPM Fusion",               "sudo dnf remove akmod-nvidia"),
                (fedora_id, "Install NVIDIA CUDA support",  "sudo dnf install xorg-x11-drv-nvidia-cuda","medium", "Installs NVIDIA CUDA support via RPM Fusion",         "sudo dnf remove xorg-x11-drv-nvidia-cuda"),
                (fedora_id, "Install kernel devel package", "sudo dnf install kernel-devel",            "medium", "Installs kernel-devel for building modules",          "sudo dnf remove kernel-devel"),
                (fedora_id, "Install build tools",          "sudo dnf install gcc make",                "medium", "Installs compiler and make",                          "sudo dnf remove gcc make"),
            ])

            for distro_id in arch_like_ids:
                commands.extend([
                    (distro_id, "Update package database",    "sudo pacman -Sy",                         "medium", "Refreshes package database",                          None),
                    (distro_id, "Full system upgrade",        "sudo pacman -Syu",                        "medium", "Upgrades the system",                                 None),
                    (distro_id, "Install Linux firmware",     "sudo pacman -S linux-firmware",           "medium", "Installs firmware package",                           "sudo pacman -R linux-firmware"),
                    (distro_id, "Install NVIDIA driver",      "sudo pacman -S nvidia nvidia-utils",      "medium", "Installs NVIDIA driver and utilities",                "sudo pacman -R nvidia nvidia-utils"),
                    (distro_id, "Install NVIDIA DKMS driver", "sudo pacman -S nvidia-dkms nvidia-utils", "medium", "Installs NVIDIA DKMS driver and utilities",           "sudo pacman -R nvidia-dkms nvidia-utils"),
                    (distro_id, "Install Mesa utils",         "sudo pacman -S mesa-utils",               "medium", "Installs OpenGL diagnostic tools",                    "sudo pacman -R mesa-utils"),
                    (distro_id, "Install Vulkan tools",       "sudo pacman -S vulkan-tools",             "medium", "Installs Vulkan diagnostic tools",                    "sudo pacman -R vulkan-tools"),
                    (distro_id, "Install SOF firmware",       "sudo pacman -S sof-firmware",             "medium", "Installs Sound Open Firmware",                        "sudo pacman -R sof-firmware"),
                    (distro_id, "Install Bluetooth tools",    "sudo pacman -S bluez bluez-utils",        "medium", "Installs Bluetooth tools",                            "sudo pacman -R bluez bluez-utils"),
                    (distro_id, "Enable Bluetooth service",   "sudo systemctl enable --now bluetooth",   "medium", "Enables and starts Bluetooth service",                "sudo systemctl disable --now bluetooth"),
                ])

            commands.extend([
                (opensuse_id, "Refresh repositories",         "sudo zypper refresh",                     "low",    "Refreshes repository metadata",                       None),
                (opensuse_id, "Update packages",              "sudo zypper update",                      "medium", "Updates installed packages",                          None),
                (opensuse_id, "Install firmware",             "sudo zypper install kernel-firmware-all", "medium", "Installs firmware packages",                          "sudo zypper remove kernel-firmware-all"),
                (opensuse_id, "Install recommended packages", "sudo zypper install-new-recommends",      "medium", "Installs recommended packages including drivers",     None),
                (opensuse_id, "Install Vulkan tools",         "sudo zypper install vulkan-tools",        "medium", "Installs Vulkan tools",                               "sudo zypper remove vulkan-tools"),
            ])

            inserted_commands = 0
            for cmd in commands:
                distro_id_val, title = cmd[0], cmd[1]
                cur.execute(
                    """
                    SELECT id FROM commands
                    WHERE title = %s
                      AND (distro_id = %s OR (distro_id IS NULL AND %s IS NULL))
                    """,
                    (title, distro_id_val, distro_id_val),
                )
                if cur.fetchone() is None:
                    cur.execute(
                        """
                        INSERT INTO commands
                            (distro_id, title, command, risk_level, purpose, rollback_command)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        cmd,
                    )
                    inserted_commands += 1

        conn.commit()

    print("Base SQL data inserted successfully.")
    print(f"  Distros:  {len(distros)}")
    print(f"  Drivers:  {len(drivers)}")
    print(f"  Devices:  {len(devices)}")
    print(f"  Packages: {len(packages)}")
    print(f"  Commands inserted (new): {inserted_commands} of {len(commands)}")


if __name__ == "__main__":
    main()