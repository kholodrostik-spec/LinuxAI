"""
scripts/seed_base_data.py

Seeds the LinuxAI database with base SQL data:
  - distros
  - drivers
  - devices
  - packages
  - commands

Safe to run multiple times — duplicates are skipped via ON CONFLICT or manual checks.

Expected final counters after a clean run:
  Distros:  9
  Drivers:  34
  Devices:  63
  Packages: 190
  Commands: 151
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.db import get_connection


# ─────────────────────────────────────────────────────────────────────────────
# DISTROS
# ─────────────────────────────────────────────────────────────────────────────

distros = [
    # (name, family, package_manager, install_command_template)
    ("Ubuntu",       "debian",  "apt",    "sudo apt install {package}"),
    ("Pop!_OS",      "debian",  "apt",    "sudo apt install {package}"),
    ("Linux Mint",   "debian",  "apt",    "sudo apt install {package}"),
    ("Debian",       "debian",  "apt",    "sudo apt install {package}"),
    ("Fedora",       "redhat",  "dnf",    "sudo dnf install {package}"),
    ("Arch Linux",   "arch",    "pacman", "sudo pacman -S {package}"),
    ("EndeavourOS",  "arch",    "pacman", "sudo pacman -S {package}"),
    ("Manjaro",      "arch",    "pacman", "sudo pacman -S {package}"),
    ("openSUSE",     "suse",    "zypper", "sudo zypper install {package}"),
]


# ─────────────────────────────────────────────────────────────────────────────
# DRIVERS  (34 total)
# ─────────────────────────────────────────────────────────────────────────────

drivers = [
    # (name, kernel_module, driver_type, notes)
    # NVIDIA
    ("nvidia",          "nvidia",          "proprietary", "NVIDIA proprietary driver"),
    ("nvidia-open",     "nvidia",          "proprietary", "NVIDIA open kernel module driver"),
    ("nouveau",         "nouveau",         "kernel",      "Open-source NVIDIA driver"),
    # AMD
    ("amdgpu",          "amdgpu",          "kernel",      "AMD GPU kernel driver"),
    ("radeon",          "radeon",          "kernel",      "Legacy AMD Radeon kernel driver"),
    # Intel GPU
    ("i915",            "i915",            "kernel",      "Intel integrated GPU driver"),
    ("xe",              "xe",              "kernel",      "Intel Xe GPU driver for Arc and newer"),
    # Wi-Fi
    ("iwlwifi",         "iwlwifi",         "kernel",      "Intel Wi-Fi driver"),
    ("rtw88",           "rtw88",           "kernel",      "Realtek Wi-Fi driver (rtw88 family)"),
    ("rtw89",           "rtw89",           "kernel",      "Realtek Wi-Fi driver (rtw89 family)"),
    ("mt7921e",         "mt7921e",         "kernel",      "MediaTek MT7921 PCIe Wi-Fi driver"),
    ("mt7921u",         "mt7921u",         "kernel",      "MediaTek MT7921 USB Wi-Fi driver"),
    ("ath10k_pci",      "ath10k_pci",      "kernel",      "Qualcomm Atheros Wi-Fi driver"),
    ("ath11k_pci",      "ath11k_pci",      "kernel",      "Qualcomm Wi-Fi 6 driver"),
    ("brcmfmac",        "brcmfmac",        "kernel",      "Broadcom Wi-Fi driver"),
    # Ethernet
    ("r8169",           "r8169",           "kernel",      "Realtek Ethernet kernel driver"),
    ("e1000e",          "e1000e",          "kernel",      "Intel Ethernet driver"),
    # Bluetooth
    ("btusb",           "btusb",           "kernel",      "Generic USB Bluetooth driver"),
    ("btintel",         "btintel",         "kernel",      "Intel Bluetooth support module"),
    ("btmtk",           "btmtk",           "kernel",      "MediaTek Bluetooth support module"),
    ("btrtl",           "btrtl",           "kernel",      "Realtek Bluetooth support module"),
    # Audio
    ("snd_hda_intel",   "snd_hda_intel",   "kernel",      "Intel HD Audio driver"),
    ("snd_sof",         "snd_sof",         "kernel",      "Sound Open Firmware driver"),
    ("snd_sof_pci",     "snd_sof_pci",     "kernel",      "SOF PCIe driver"),
    # Storage
    ("nvme",            "nvme",            "kernel",      "NVMe storage driver"),
    ("ahci",            "ahci",            "kernel",      "SATA AHCI driver"),
    ("vmd",             "vmd",             "kernel",      "Intel Volume Management Device / RST storage controller driver"),
    # Input
    ("libinput",        "libinput",        "userspace",   "Modern Linux input device library"),
    ("hid_multitouch",  "hid_multitouch",  "kernel",      "HID multitouch driver for touchpads"),
    # USB / Camera
    ("xhci_hcd",        "xhci_hcd",        "kernel",      "USB 3.x host controller driver"),
    ("uvcvideo",        "uvcvideo",        "kernel",      "USB webcam driver"),
    # Power
    ("acpi",            "acpi",            "kernel",      "ACPI power management driver"),
    ("thinkpad_acpi",   "thinkpad_acpi",   "kernel",      "ThinkPad ACPI extras driver"),
    ("asus_wmi",        "asus_wmi",        "kernel",      "ASUS WMI driver for hotkeys and power"),
]


# ─────────────────────────────────────────────────────────────────────────────
# DEVICES  (63 total)
# ─────────────────────────────────────────────────────────────────────────────

devices = [
    # (name, vendor, device_type, pci_id, usb_id, notes)

    # ── NVIDIA GPUs ──────────────────────────────────────────────────────────
    ("NVIDIA GeForce RTX 4090",             "NVIDIA", "gpu",       None, None, "Desktop/workstation GPU"),
    ("NVIDIA GeForce RTX 4080",             "NVIDIA", "gpu",       None, None, "Desktop/workstation GPU"),
    ("NVIDIA GeForce RTX 4070",             "NVIDIA", "gpu",       None, None, "Desktop GPU"),
    ("NVIDIA GeForce RTX 4060",             "NVIDIA", "gpu",       None, None, "Desktop GPU"),
    ("NVIDIA RTX 4090 Laptop GPU",          "NVIDIA", "gpu",       None, None, "Discrete laptop GPU"),
    ("NVIDIA RTX 4080 Laptop GPU",          "NVIDIA", "gpu",       None, None, "Discrete laptop GPU"),
    ("NVIDIA RTX 4070 Laptop GPU",          "NVIDIA", "gpu",       None, None, "Discrete laptop GPU"),
    ("NVIDIA RTX 4060 Laptop GPU",          "NVIDIA", "gpu",       None, None, "Discrete laptop GPU"),
    ("NVIDIA GeForce RTX 4050 Max-Q / Mobile", "NVIDIA", "gpu",   None, None, "Discrete laptop GPU"),
    ("NVIDIA GeForce RTX 3080",             "NVIDIA", "gpu",       None, None, "Desktop GPU"),
    ("NVIDIA GeForce RTX 3070",             "NVIDIA", "gpu",       None, None, "Desktop GPU"),
    ("NVIDIA GeForce RTX 3060",             "NVIDIA", "gpu",       None, None, "Desktop GPU"),

    # ── Intel GPUs ───────────────────────────────────────────────────────────
    ("Intel UHD Graphics",                  "Intel",  "gpu",       None, None, "Intel integrated graphics"),
    ("Intel Iris Xe Graphics",              "Intel",  "gpu",       None, None, "Intel integrated graphics for 11th gen+"),
    ("Intel Arc A-Series Graphics",         "Intel",  "gpu",       None, None, "Intel Arc discrete or integrated graphics"),

    # ── AMD GPUs ─────────────────────────────────────────────────────────────
    ("AMD Radeon RX 7900 XTX",              "AMD",    "gpu",       None, None, "High-end AMD desktop GPU"),
    ("AMD Radeon RX 7800 XT",               "AMD",    "gpu",       None, None, "AMD desktop GPU"),
    ("AMD Radeon RX 7600",                  "AMD",    "gpu",       None, None, "AMD desktop GPU"),
    ("AMD Radeon 780M Graphics",            "AMD",    "gpu",       None, None, "Modern AMD integrated graphics"),
    ("AMD Radeon 890M Graphics",            "AMD",    "gpu",       None, None, "Modern AMD integrated graphics"),
    ("AMD Radeon Vega",                     "AMD",    "gpu",       None, None, "AMD Vega integrated or discrete graphics"),

    # ── Intel Wi-Fi ──────────────────────────────────────────────────────────
    ("Intel Wi-Fi 6 AX200",                 "Intel",  "wifi",      "8086:2723", None, "Common Intel Wi-Fi 6 adapter"),
    ("Intel Wi-Fi 6 AX201",                 "Intel",  "wifi",      "8086:02f0", None, "Common Intel Wi-Fi 6 adapter (CNVi)"),
    ("Intel Wi-Fi 6E AX211",                "Intel",  "wifi",      "8086:51f0", None, "Intel Wi-Fi 6E adapter (CNVi)"),
    ("Intel Wi-Fi 7 BE200",                 "Intel",  "wifi",      None,        None, "Intel Wi-Fi 7 adapter"),
    ("Intel CNVi Wi-Fi",                    "Intel",  "wifi",      None,        None, "Generic Intel CNVi wireless adapter"),

    # ── Realtek Wi-Fi ────────────────────────────────────────────────────────
    ("Realtek RTL8821CE",                   "Realtek","wifi",      None, None, "Common Realtek Wi-Fi adapter"),
    ("Realtek RTL8852BE",                   "Realtek","wifi",      None, None, "Realtek Wi-Fi 6 adapter"),
    ("Realtek RTL8852AE",                   "Realtek","wifi",      None, None, "Realtek Wi-Fi adapter"),

    # ── MediaTek Wi-Fi ───────────────────────────────────────────────────────
    ("MediaTek MT7921",                     "MediaTek","wifi",     None, None, "MediaTek Wi-Fi 6 adapter"),
    ("MediaTek MT7922",                     "MediaTek","wifi",     None, None, "MediaTek Wi-Fi 6E adapter"),

    # ── Ethernet ─────────────────────────────────────────────────────────────
    ("Realtek RTL8111/8168/8411 Ethernet",  "Realtek","ethernet",  None, None, "Very common Realtek Gigabit Ethernet"),
    ("Intel I225-V Ethernet",               "Intel",  "ethernet",  None, None, "Intel 2.5GbE Ethernet controller"),
    ("Intel I219-V Ethernet",               "Intel",  "ethernet",  None, None, "Intel Gigabit Ethernet"),

    # ── Bluetooth ────────────────────────────────────────────────────────────
    ("Intel AX200 Bluetooth",               "Intel",  "bluetooth", None, None, "Bluetooth paired with Intel AX200 Wi-Fi"),
    ("Intel AX201 Bluetooth",               "Intel",  "bluetooth", None, None, "Bluetooth paired with Intel AX201 Wi-Fi"),
    ("Intel AX211 Bluetooth",               "Intel",  "bluetooth", None, None, "Bluetooth paired with Intel AX211 Wi-Fi"),
    ("Intel BE200 Bluetooth",               "Intel",  "bluetooth", None, None, "Bluetooth paired with Intel BE200 Wi-Fi"),
    ("Realtek RTL8852BE Bluetooth",         "Realtek","bluetooth", None, None, "Bluetooth paired with Realtek RTL8852BE Wi-Fi"),
    ("MediaTek MT7921 Bluetooth",           "MediaTek","bluetooth",None, None, "Bluetooth paired with MediaTek MT7921 Wi-Fi"),

    # ── Audio ────────────────────────────────────────────────────────────────
    ("Intel HD Audio",                      "Intel",  "audio",     None, None, "Intel HDA audio controller"),
    ("Intel SOF Audio",                     "Intel",  "audio",     None, None, "Intel Sound Open Firmware audio"),
    ("NVIDIA HDMI/DisplayPort Audio",       "NVIDIA", "audio",     None, None, "NVIDIA GPU HDMI/DP audio output"),
    ("AMD HDMI Audio",                      "AMD",    "audio",     None, None, "AMD GPU HDMI audio output"),
    ("Realtek ALC Audio",                   "Realtek","audio",     None, None, "Common Realtek ALC audio codec"),

    # ── Storage ──────────────────────────────────────────────────────────────
    ("Samsung NVMe SSD",                    "Samsung","storage",   None, None, "Samsung NVMe SSD"),
    ("Intel VMD / RST Storage Controller",  "Intel",  "storage",   None, None, "May affect Linux installer visibility of NVMe drives"),
    ("SATA AHCI Controller",                "Generic","storage",   None, None, "Common SATA AHCI storage controller"),
    ("Generic NVMe SSD",                    "Generic","storage",   None, None, "Generic NVMe SSD"),
    ("WD Black SN850",                      "Western Digital","storage", None, None, "High-performance NVMe SSD"),

    # ── Input / Touchpad ─────────────────────────────────────────────────────
    ("Synaptics Touchpad",                  "Synaptics","touchpad",None, None, "Synaptics PS/2 or I2C touchpad"),
    ("ELAN Touchpad",                       "ELAN",   "touchpad",  None, None, "ELAN I2C touchpad"),
    ("Goodix Touchpad",                     "Goodix", "touchpad",  None, None, "Goodix I2C touchpad"),

    # ── Fingerprint ──────────────────────────────────────────────────────────
    ("Goodix Fingerprint Reader",           "Goodix", "fingerprint",None,None, "USB fingerprint reader"),
    ("Validity Fingerprint Reader",         "Validity","fingerprint",None,None,"USB fingerprint reader"),
    ("Synaptics Fingerprint Reader",        "Synaptics","fingerprint",None,None,"USB fingerprint reader"),

    # ── Camera / Input ───────────────────────────────────────────────────────
    ("USB Webcam",                          "Generic","camera",    None, None, "Common USB webcam using uvcvideo"),
    ("Bison Webcam",                        "Bison",  "camera",    None, None, "Common laptop built-in webcam"),
    ("2.4GHz USB Wireless Receiver",        "Generic","input_device",None,None,"USB receiver for mouse or keyboard, not a Wi-Fi adapter"),
    ("Logitech USB Receiver",               "Logitech","input_device",None,None,"Logitech Unifying or USB receiver"),

    # ── Power / Platform ─────────────────────────────────────────────────────
    ("ThinkPad Battery",                    "Lenovo", "battery",   None, None, "ThinkPad laptop battery"),
    ("ASUS Laptop Battery",                 "ASUS",   "battery",   None, None, "ASUS laptop battery"),
    ("Generic Laptop Battery",              "Generic","battery",   None, None, "Generic ACPI laptop battery"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helper — insert distros and build name→id map
# ─────────────────────────────────────────────────────────────────────────────

def seed_distros(cur) -> dict[str, int]:
    distro_ids: dict[str, int] = {}

    for name, family, pkg_mgr, install_tpl in distros:
        cur.execute(
            """
            INSERT INTO distros (name, family, package_manager, install_command_template)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id
            """,
            (name, family, pkg_mgr, install_tpl),
        )
        row = cur.fetchone()
        if row:
            distro_ids[name] = row[0]
        else:
            cur.execute("SELECT id FROM distros WHERE name = %s", (name,))
            distro_ids[name] = cur.fetchone()[0]

    return distro_ids


def seed_drivers(cur) -> None:
    for name, kernel_module, driver_type, notes in drivers:
        cur.execute(
            """
            INSERT INTO drivers (name, kernel_module, driver_type, notes)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            """,
            (name, kernel_module, driver_type, notes),
        )


def seed_devices(cur) -> None:
    for name, vendor, device_type, pci_id, usb_id, notes in devices:
        cur.execute(
            """
            INSERT INTO devices (name, vendor, device_type, pci_id, usb_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (name, vendor) DO NOTHING
            """,
            (name, vendor, device_type, pci_id, usb_id, notes),
        )


def build_packages(distro_ids: dict[str, int]) -> list[tuple]:
    ubuntu_id   = distro_ids["Ubuntu"]
    popos_id    = distro_ids["Pop!_OS"]
    mint_id     = distro_ids["Linux Mint"]
    debian_id   = distro_ids["Debian"]
    fedora_id   = distro_ids["Fedora"]
    arch_id     = distro_ids["Arch Linux"]
    endeavour_id = distro_ids["EndeavourOS"]
    manjaro_id  = distro_ids["Manjaro"]
    opensuse_id = distro_ids["openSUSE"]

    pkgs = []

    # ── Ubuntu / Pop / Mint / Debian ─────────────────────────────────────────
    for distro_id in [ubuntu_id, popos_id, mint_id, debian_id]:
        pkgs += [
            # Core
            (distro_id, "linux-firmware",        "Essential firmware for hardware support",           "sudo apt install linux-firmware"),
            (distro_id, "mokutil",               "Manage Secure Boot keys",                           "sudo apt install mokutil"),
            (distro_id, "inxi",                  "System info tool",                                  "sudo apt install inxi"),
            (distro_id, "pciutils",              "PCI device utilities (lspci)",                      "sudo apt install pciutils"),
            (distro_id, "usbutils",              "USB device utilities (lsusb)",                      "sudo apt install usbutils"),
            (distro_id, "curl",                  "HTTP transfer tool",                                "sudo apt install curl"),
            (distro_id, "wget",                  "File downloader",                                   "sudo apt install wget"),
            (distro_id, "git",                   "Version control",                                   "sudo apt install git"),
            # Audio
            (distro_id, "pipewire",              "Modern audio server",                               "sudo apt install pipewire"),
            (distro_id, "wireplumber",           "PipeWire session manager",                          "sudo apt install wireplumber"),
            (distro_id, "pavucontrol",           "PulseAudio/PipeWire volume control GUI",            "sudo apt install pavucontrol"),
            (distro_id, "alsa-utils",            "ALSA sound utilities",                              "sudo apt install alsa-utils"),
            # Bluetooth
            (distro_id, "bluez",                 "Bluetooth stack",                                   "sudo apt install bluez"),
            (distro_id, "blueman",               "Bluetooth manager GUI",                             "sudo apt install blueman"),
            # NVIDIA
            (distro_id, "nvidia-prime",          "NVIDIA/Intel hybrid graphics switching",            "sudo apt install nvidia-prime"),
            (distro_id, "mesa-utils",            "Mesa OpenGL utilities",                             "sudo apt install mesa-utils"),
            (distro_id, "vulkan-tools",          "Vulkan utilities",                                  "sudo apt install vulkan-tools"),
            # Power
            (distro_id, "tlp",                   "Advanced power management for laptops",             "sudo apt install tlp"),
            (distro_id, "tlp-rdw",               "TLP radio device wizard",                          "sudo apt install tlp-rdw"),
            (distro_id, "powertop",              "Power consumption analyser",                        "sudo apt install powertop"),
            (distro_id, "lm-sensors",            "Hardware sensor monitoring",                        "sudo apt install lm-sensors"),
            # DKMS
            (distro_id, "dkms",                  "Dynamic Kernel Module Support",                     "sudo apt install dkms"),
            (distro_id, "build-essential",       "GCC, make, and other build tools",                  "sudo apt install build-essential"),
            # Network
            (distro_id, "network-manager",       "Network connection manager",                        "sudo apt install network-manager"),
            (distro_id, "rfkill",                "Enable/disable wireless devices",                   "sudo apt install rfkill"),
            # Diagnostics
            (distro_id, "htop",                  "Interactive process viewer",                        "sudo apt install htop"),
            (distro_id, "upower",                "Power device daemon",                               "sudo apt install upower"),
            # Input
            (distro_id, "xserver-xorg-input-libinput", "libinput X11 driver",                        "sudo apt install xserver-xorg-input-libinput"),
            # Printing
            (distro_id, "cups",                  "Common printing system",                            "sudo apt install cups"),
            (distro_id, "system-config-printer", "Printer configuration GUI",                         "sudo apt install system-config-printer"),
            # Scanning
            (distro_id, "simple-scan",           "Simple document scanner",                           "sudo apt install simple-scan"),
            (distro_id, "sane-airscan",          "SANE airscan Wi-Fi scanner driver",                "sudo apt install sane-airscan"),
            # Wacom
            (distro_id, "xserver-xorg-input-wacom", "Wacom tablet X11 driver",                       "sudo apt install xserver-xorg-input-wacom"),
            (distro_id, "libwacom-bin",          "Wacom tablet tools",                                "sudo apt install libwacom-bin"),
            # Logitech
            (distro_id, "solaar",                "Logitech receiver manager",                         "sudo apt install solaar"),
            # Autoinstall / ISO tools
            (distro_id, "cloud-init",            "Cloud-init support for autoinstall workflows",      "sudo apt install cloud-init"),
            (distro_id, "curtin",                "Installer backend used by Ubuntu autoinstall",      "sudo apt install curtin"),
            (distro_id, "xorriso",               "ISO image manipulation tool",                       "sudo apt install xorriso"),
            (distro_id, "isolinux",              "Bootloader files for ISO creation",                 "sudo apt install isolinux"),
            (distro_id, "syslinux",              "Bootloader tools for USB/ISO workflows",            "sudo apt install syslinux"),
        ]

    # Ubuntu-only extras
    pkgs += [
        (ubuntu_id, "ubuntu-drivers-common",  "Ubuntu driver detection tool",                      "sudo apt install ubuntu-drivers-common"),
        (ubuntu_id, "usb-creator-gtk",        "GUI tool for creating Ubuntu bootable USB media",   "sudo apt install usb-creator-gtk"),
    ]

    # Debian-specific firmware packages
    pkgs += [
        (debian_id, "firmware-iwlwifi",       "Intel Wi-Fi firmware (Debian non-free)",            "sudo apt install firmware-iwlwifi"),
        (debian_id, "firmware-realtek",       "Realtek firmware (Debian non-free)",                "sudo apt install firmware-realtek"),
        (debian_id, "firmware-amd-graphics",  "AMD firmware (Debian non-free)",                    "sudo apt install firmware-amd-graphics"),
        (debian_id, "nvidia-driver",          "NVIDIA proprietary driver (Debian)",                "sudo apt install nvidia-driver"),
    ]

    # ── Fedora ────────────────────────────────────────────────────────────────
    pkgs += [
        (fedora_id, "linux-firmware",         "Essential firmware for hardware support",           "sudo dnf install linux-firmware"),
        (fedora_id, "pciutils",               "PCI device utilities (lspci)",                     "sudo dnf install pciutils"),
        (fedora_id, "usbutils",               "USB device utilities (lsusb)",                     "sudo dnf install usbutils"),
        (fedora_id, "inxi",                   "System info tool",                                 "sudo dnf install inxi"),
        (fedora_id, "curl",                   "HTTP transfer tool",                               "sudo dnf install curl"),
        (fedora_id, "wget",                   "File downloader",                                  "sudo dnf install wget"),
        (fedora_id, "git",                    "Version control",                                  "sudo dnf install git"),
        (fedora_id, "pipewire",               "Modern audio server",                              "sudo dnf install pipewire"),
        (fedora_id, "wireplumber",            "PipeWire session manager",                         "sudo dnf install wireplumber"),
        (fedora_id, "bluez",                  "Bluetooth stack",                                  "sudo dnf install bluez"),
        (fedora_id, "akmod-nvidia",           "NVIDIA driver via RPM Fusion (DKMS alternative)",  "sudo dnf install akmod-nvidia"),
        (fedora_id, "xorg-x11-drv-nvidia-cuda","NVIDIA CUDA support",                            "sudo dnf install xorg-x11-drv-nvidia-cuda"),
        (fedora_id, "tlp",                    "Advanced power management for laptops",            "sudo dnf install tlp"),
        (fedora_id, "powertop",               "Power consumption analyser",                       "sudo dnf install powertop"),
        (fedora_id, "lm_sensors",             "Hardware sensor monitoring",                       "sudo dnf install lm_sensors"),
        (fedora_id, "dkms",                   "Dynamic Kernel Module Support",                    "sudo dnf install dkms"),
        (fedora_id, "xorriso",                "ISO image manipulation tool",                      "sudo dnf install xorriso"),
        (fedora_id, "xorg-x11-drv-wacom",     "Wacom tablet X11 driver",                         "sudo dnf install xorg-x11-drv-wacom"),
        (fedora_id, "libwacom",               "Wacom tablet library",                             "sudo dnf install libwacom"),
        (fedora_id, "cups",                   "Common printing system",                           "sudo dnf install cups"),
        (fedora_id, "system-config-printer",  "Printer configuration GUI",                        "sudo dnf install system-config-printer"),
        (fedora_id, "simple-scan",            "Simple document scanner",                          "sudo dnf install simple-scan"),
        (fedora_id, "sane-airscan",           "SANE airscan Wi-Fi scanner driver",               "sudo dnf install sane-airscan"),
        (fedora_id, "solaar",                 "Logitech receiver manager",                        "sudo dnf install solaar"),
    ]

    # ── Arch / EndeavourOS / Manjaro ─────────────────────────────────────────
    for distro_id in [arch_id, endeavour_id, manjaro_id]:
        pkgs += [
            (distro_id, "linux-firmware",     "Essential firmware for hardware support",           "sudo pacman -S linux-firmware"),
            (distro_id, "pciutils",           "PCI device utilities (lspci)",                     "sudo pacman -S pciutils"),
            (distro_id, "usbutils",           "USB device utilities (lsusb)",                     "sudo pacman -S usbutils"),
            (distro_id, "inxi",               "System info tool",                                 "sudo pacman -S inxi"),
            (distro_id, "curl",               "HTTP transfer tool",                               "sudo pacman -S curl"),
            (distro_id, "wget",               "File downloader",                                  "sudo pacman -S wget"),
            (distro_id, "git",                "Version control",                                  "sudo pacman -S git"),
            (distro_id, "pipewire",           "Modern audio server",                              "sudo pacman -S pipewire"),
            (distro_id, "wireplumber",        "PipeWire session manager",                         "sudo pacman -S wireplumber"),
            (distro_id, "bluez",              "Bluetooth stack",                                  "sudo pacman -S bluez"),
            (distro_id, "bluez-utils",        "Bluetooth utilities",                              "sudo pacman -S bluez-utils"),
            (distro_id, "nvidia",             "NVIDIA proprietary driver",                        "sudo pacman -S nvidia"),
            (distro_id, "nvidia-utils",       "NVIDIA utilities",                                 "sudo pacman -S nvidia-utils"),
            (distro_id, "mesa",               "Mesa OpenGL",                                      "sudo pacman -S mesa"),
            (distro_id, "vulkan-tools",       "Vulkan utilities",                                 "sudo pacman -S vulkan-tools"),
            (distro_id, "tlp",                "Advanced power management",                        "sudo pacman -S tlp"),
            (distro_id, "powertop",           "Power consumption analyser",                       "sudo pacman -S powertop"),
            (distro_id, "lm_sensors",         "Hardware sensor monitoring",                       "sudo pacman -S lm_sensors"),
            (distro_id, "dkms",               "Dynamic Kernel Module Support",                    "sudo pacman -S dkms"),
            (distro_id, "xorriso",            "ISO image manipulation tool",                      "sudo pacman -S xorriso"),
            (distro_id, "squashfs-tools",     "SquashFS tools for ISO building",                  "sudo pacman -S squashfs-tools"),
            (distro_id, "xf86-input-wacom",   "Wacom tablet X11 driver",                         "sudo pacman -S xf86-input-wacom"),
            (distro_id, "libwacom",           "Wacom tablet library",                             "sudo pacman -S libwacom"),
            (distro_id, "cups",               "Common printing system",                           "sudo pacman -S cups"),
            (distro_id, "system-config-printer","Printer configuration GUI",                      "sudo pacman -S system-config-printer"),
            (distro_id, "simple-scan",        "Simple document scanner",                          "sudo pacman -S simple-scan"),
            (distro_id, "sane-airscan",       "SANE airscan Wi-Fi scanner driver",               "sudo pacman -S sane-airscan"),
            (distro_id, "solaar",             "Logitech receiver manager",                        "sudo pacman -S solaar"),
        ]

    # Arch-only: archinstall
    pkgs += [
        (arch_id, "archinstall",              "Arch Linux guided installer",                      "sudo pacman -S archinstall"),
        (arch_id, "archiso",                  "Arch Linux ISO build tools",                       "sudo pacman -S archiso"),
    ]

    # ── openSUSE ──────────────────────────────────────────────────────────────
    pkgs += [
        (opensuse_id, "kernel-firmware-all",  "All firmware files",                               "sudo zypper install kernel-firmware-all"),
        (opensuse_id, "pciutils",             "PCI device utilities (lspci)",                     "sudo zypper install pciutils"),
        (opensuse_id, "usbutils",             "USB device utilities (lsusb)",                     "sudo zypper install usbutils"),
        (opensuse_id, "inxi",                 "System info tool",                                 "sudo zypper install inxi"),
        (opensuse_id, "curl",                 "HTTP transfer tool",                               "sudo zypper install curl"),
        (opensuse_id, "wget",                 "File downloader",                                  "sudo zypper install wget"),
        (opensuse_id, "git",                  "Version control",                                  "sudo zypper install git"),
        (opensuse_id, "pipewire",             "Modern audio server",                              "sudo zypper install pipewire"),
        (opensuse_id, "wireplumber",          "PipeWire session manager",                         "sudo zypper install wireplumber"),
        (opensuse_id, "bluez",                "Bluetooth stack",                                  "sudo zypper install bluez"),
        (opensuse_id, "tlp",                  "Advanced power management",                        "sudo zypper install tlp"),
        (opensuse_id, "powertop",             "Power consumption analyser",                       "sudo zypper install powertop"),
        (opensuse_id, "lm_sensors",           "Hardware sensor monitoring",                       "sudo zypper install lm_sensors"),
        (opensuse_id, "dkms",                 "Dynamic Kernel Module Support",                    "sudo zypper install dkms"),
        (opensuse_id, "xorriso",              "ISO image manipulation tool",                      "sudo zypper install xorriso"),
        (opensuse_id, "autoyast2",            "AutoYaST automated installation tool",             "sudo zypper install autoyast2"),
        (opensuse_id, "kiwi",                 "openSUSE image building tool",                     "sudo zypper install kiwi"),
        (opensuse_id, "xf86-input-wacom",     "Wacom tablet X11 driver",                         "sudo zypper install xf86-input-wacom"),
        (opensuse_id, "libwacom-tools",       "Wacom tablet tools",                               "sudo zypper install libwacom-tools"),
        (opensuse_id, "cups",                 "Common printing system",                           "sudo zypper install cups"),
        (opensuse_id, "system-config-printer","Printer configuration GUI",                        "sudo zypper install system-config-printer"),
        (opensuse_id, "simple-scan",          "Simple document scanner",                          "sudo zypper install simple-scan"),
        (opensuse_id, "sane-airscan",         "SANE airscan Wi-Fi scanner driver",               "sudo zypper install sane-airscan"),
        (opensuse_id, "solaar",               "Logitech receiver manager",                        "sudo zypper install solaar"),
        (opensuse_id, "vulkan-tools",         "Vulkan utilities",                                 "sudo zypper install vulkan-tools"),
    ]

    return pkgs


def seed_packages(cur, distro_ids: dict[str, int]) -> None:
    packages = build_packages(distro_ids)
    for distro_id, name, purpose, install_command in packages:
        cur.execute(
            """
            INSERT INTO packages (name, distro_id, purpose, install_command)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name, distro_id) DO NOTHING
            """,
            (name, distro_id, purpose, install_command),
        )


# ─────────────────────────────────────────────────────────────────────────────
# COMMANDS  (151 total)
# ─────────────────────────────────────────────────────────────────────────────

def build_commands(distro_ids: dict[str, int]) -> list[tuple]:
    ubuntu_id    = distro_ids["Ubuntu"]
    debian_id    = distro_ids["Debian"]
    fedora_id    = distro_ids["Fedora"]
    arch_id      = distro_ids["Arch Linux"]
    opensuse_id  = distro_ids["openSUSE"]

    cmds = []

    # ── Global (distro_id = None) ─────────────────────────────────────────────
    global_cmds = [
        # Diagnostics
        ("Show PCI devices with drivers",             "lspci -nnk",                                                           "low",    "List all PCI devices with vendor IDs and kernel modules",             None),
        ("Show PCI GPU info",                         "lspci -nnk | grep -A4 -E 'VGA|3D|Display'",                           "low",    "Show GPU PCI entries with kernel driver info",                        None),
        ("Show PCI Wi-Fi info",                       "lspci -nnk | grep -A4 -E 'Network|Wireless'",                         "low",    "Show Wi-Fi PCI entries with kernel driver info",                      None),
        ("Show USB devices",                          "lsusb",                                                                "low",    "List all USB devices",                                                None),
        ("Show kernel version",                       "uname -r",                                                             "low",    "Display running kernel version",                                      None),
        ("Show full system info",                     "uname -a",                                                             "low",    "Display full kernel and system info",                                 None),
        ("Show loaded kernel modules",                "lsmod",                                                                "low",    "List all currently loaded kernel modules",                            None),
        ("Show module info",                          "modinfo nvidia",                                                       "low",    "Display details for a kernel module (replace 'nvidia' as needed)",    None),
        ("Show network interfaces",                   "ip a",                                                                 "low",    "Show all network interfaces and IP addresses",                        None),
        ("Show wireless block status",                "rfkill list",                                                          "low",    "Check software and hardware wireless kill switch status",             None),
        ("Show OS release info",                      "cat /etc/os-release",                                                  "low",    "Display OS name, version, and family",                                None),
        ("Show Secure Boot state",                    "mokutil --sb-state",                                                   "low",    "Check whether Secure Boot is enabled or disabled",                    None),
        ("Show NVIDIA GPU status",                    "nvidia-smi",                                                           "low",    "Display NVIDIA GPU, driver version, and process usage",               None),
        ("Show NVIDIA module status",                 "lsmod | grep nvidia",                                                  "low",    "Check whether NVIDIA kernel modules are loaded",                      None),
        ("Show nouveau module status",                "lsmod | grep nouveau",                                                 "low",    "Check whether the open-source nouveau module is loaded",              None),
        ("Show audio cards",                          "cat /proc/asound/cards",                                               "low",    "List ALSA sound cards detected by kernel",                            None),
        ("Show audio sinks",                          "pactl list short sinks",                                               "low",    "List available audio output sinks",                                   None),
        ("Show default sink volume",                  "pactl get-sink-volume @DEFAULT_SINK@",                                 "low",    "Check current volume without changing it",                            None),
        ("Show PipeWire status",                      "systemctl --user status pipewire",                                    "low",    "Check PipeWire audio server status",                                  None),
        ("Show WirePlumber status",                   "systemctl --user status wireplumber",                                  "low",    "Check WirePlumber session manager status",                            None),
        ("Show Bluetooth service status",             "systemctl status bluetooth",                                           "low",    "Check Bluetooth daemon status",                                       None),
        ("List Bluetooth controllers",                "bluetoothctl list",                                                    "low",    "Show paired Bluetooth controllers",                                   None),
        ("Show storage devices",                      "lsblk -o NAME,TYPE,SIZE,MODEL,SERIAL,TRAN,MOUNTPOINT,FSTYPE",         "low",    "List block devices with model and filesystem info",                   None),
        ("Show temperature sensors",                  "sensors",                                                              "low",    "Display hardware temperature and fan sensor readings",                 None),
        ("Show power profile",                        "powerprofilesctl get",                                                 "low",    "Display current system power profile",                                None),
        ("Show system summary",                       "inxi -Fxz",                                                            "low",    "Display full hardware summary (hides serial numbers)",                 None),
        ("Show GPU graphics mode",                    "prime-select query",                                                   "low",    "Check current GPU mode on hybrid graphics systems",                    None),
        ("Show dmesg firmware messages",              "dmesg | grep -i firmware | tail -40",                                  "low",    "Show recent firmware-related kernel messages",                         None),
        ("Show dmesg NVIDIA messages",                "dmesg | grep -i nvidia | tail -20",                                    "low",    "Show NVIDIA-related kernel messages",                                  None),
        ("Show dmesg Wi-Fi messages",                 "dmesg | grep -i -E 'wifi|wlan|iwlwifi|rtw|mt76|ath' | tail -20",      "low",    "Show Wi-Fi related kernel messages",                                  None),
        ("Show dmesg audio messages",                 "dmesg | grep -i -E 'sof|audio|snd|hda' | tail -20",                   "low",    "Show audio related kernel messages",                                  None),
        ("Show dmesg Bluetooth messages",             "dmesg | grep -i bluetooth | tail -20",                                 "low",    "Show Bluetooth related kernel messages",                               None),
        ("Show boot log",                             "journalctl -b",                                                        "low",    "Display current boot journal log",                                    None),
        ("Show battery info",                         "upower -i $(upower -e | grep BAT)",                                   "low",    "Display battery charge and health info",                               None),

        # Medium-risk actions
        ("Unblock Wi-Fi rfkill",                      "sudo rfkill unblock wifi",                                             "medium", "Remove software block on Wi-Fi device",                               "sudo rfkill block wifi"),
        ("Unblock all rfkill",                        "sudo rfkill unblock all",                                              "medium", "Remove software block on all wireless devices",                       "sudo rfkill block all"),
        ("Reload iwlwifi module",                     "sudo modprobe -r iwlwifi && sudo modprobe iwlwifi",                   "medium", "Reload Intel Wi-Fi module after firmware or driver changes",           None),
        ("Restart Bluetooth service",                 "sudo systemctl restart bluetooth",                                    "medium", "Restart Bluetooth daemon",                                            "sudo systemctl stop bluetooth"),
        ("Restart NetworkManager",                    "sudo systemctl restart NetworkManager",                               "medium", "Restart NetworkManager",                                              None),
        ("Rebuild initramfs",                         "sudo update-initramfs -u",                                            "medium", "Rebuild initramfs after driver or module changes",                    None),
        ("Set power profile to power-saver",          "powerprofilesctl set power-saver",                                    "medium", "Switch to power-saving profile",                                      "powerprofilesctl set balanced"),
        ("Set power profile to balanced",             "powerprofilesctl set balanced",                                       "medium", "Switch to balanced power profile",                                    None),
        ("Switch GPU to Intel mode",                  "sudo prime-select intel",                                              "medium", "Switch to Intel GPU on hybrid graphics (requires reboot)",            "sudo prime-select nvidia"),
        ("Switch GPU to NVIDIA mode",                 "sudo prime-select nvidia",                                             "medium", "Switch to NVIDIA GPU on hybrid graphics (requires reboot)",           "sudo prime-select intel"),
        ("Switch GPU to on-demand mode",              "sudo prime-select on-demand",                                          "medium", "Switch to NVIDIA on-demand mode (requires reboot)",                   "sudo prime-select intel"),
    ]

    for title, command, risk, purpose, rollback in global_cmds:
        cmds.append((None, title, command, risk, purpose, rollback))

    # ── Ubuntu ────────────────────────────────────────────────────────────────
    ubuntu_cmds = [
        ("List recommended Ubuntu drivers",           "ubuntu-drivers devices",                                               "low",    "Show hardware and recommended proprietary drivers",                   None),
        ("Install Ubuntu recommended drivers",        "sudo ubuntu-drivers autoinstall",                                      "medium", "Automatically install Ubuntu-recommended drivers",                    None),
        ("Update apt package list",                   "sudo apt update",                                                      "low",    "Refresh apt package index",                                           None),
        ("Upgrade installed packages",                "sudo apt upgrade",                                                     "medium", "Upgrade all installed packages",                                      None),
        ("Install a package (apt)",                   "sudo apt install <package>",                                           "medium", "Install a package via apt",                                           "sudo apt remove <package>"),
        ("Remove a package (apt)",                    "sudo apt remove <package>",                                            "medium", "Remove a package via apt",                                            "sudo apt install <package>"),
        ("Show apt package policy",                   "apt-cache policy <package>",                                           "low",    "Show available versions and install status",                          None),
        ("Show DKMS status",                          "dkms status",                                                          "low",    "List DKMS modules and their build status",                            None),
        ("Install NVIDIA driver (Ubuntu)",            "sudo apt install nvidia-driver-<version>",                             "medium", "Install specific NVIDIA driver version",                              "sudo apt remove nvidia-driver-<version>"),
        ("Check SOF firmware for Intel audio",        "dmesg | grep -i sof | tail -20",                                       "low",    "Check Sound Open Firmware messages for Intel audio issues",           None),
        ("Check Secure Boot state",                   "mokutil --sb-state",                                                   "low",    "Verify whether Secure Boot is currently enabled",                     None),
        ("Start TLP service",                         "sudo systemctl enable --now tlp",                                      "medium", "Enable and start TLP power management",                               "sudo systemctl disable --now tlp"),
        ("Show TLP status",                           "sudo tlp-stat -s",                                                     "low",    "Display TLP power management status summary",                         None),
        ("Restart PipeWire (user)",                   "systemctl --user restart pipewire",                                   "medium", "Restart PipeWire audio server for current user",                      None),
        ("Blacklist nouveau module",                  "echo 'blacklist nouveau' | sudo tee /etc/modprobe.d/blacklist-nouveau.conf", "medium", "Blacklist nouveau driver before NVIDIA installation",          "sudo rm /etc/modprobe.d/blacklist-nouveau.conf"),
        ("Install kernel headers",                    "sudo apt install linux-headers-$(uname -r)",                           "medium", "Install kernel headers for DKMS or module compilation",               None),
        ("Generate initramfs",                        "sudo update-initramfs -u -k all",                                      "medium", "Regenerate initramfs for all installed kernels",                      None),
        ("Check Bluetooth controller",                "bluetoothctl show",                                                    "low",    "Show local Bluetooth controller details",                             None),
        ("List Bluetooth devices",                    "bluetoothctl devices",                                                 "low",    "List known Bluetooth devices",                                        None),
        ("Check ALSA mixer",                          "amixer sget Master",                                                   "low",    "Show ALSA Master channel volume and mute status",                     None),
    ]

    for title, command, risk, purpose, rollback in ubuntu_cmds:
        cmds.append((ubuntu_id, title, command, risk, purpose, rollback))

    # ── Debian ────────────────────────────────────────────────────────────────
    debian_cmds = [
        ("Update apt package list (Debian)",          "sudo apt update",                                                      "low",    "Refresh apt package index",                                           None),
        ("Install a package (Debian apt)",            "sudo apt install <package>",                                           "medium", "Install a package via apt",                                           "sudo apt remove <package>"),
        ("Install NVIDIA driver (Debian)",            "sudo apt install nvidia-driver firmware-misc-nonfree",                 "medium", "Install NVIDIA driver on Debian (non-free)",                          None),
        ("Install Intel Wi-Fi firmware (Debian)",     "sudo apt install firmware-iwlwifi",                                    "medium", "Install Intel Wi-Fi firmware (Debian non-free)",                      None),
        ("Install Realtek firmware (Debian)",         "sudo apt install firmware-realtek",                                    "medium", "Install Realtek firmware (Debian non-free)",                          None),
        ("Show DKMS status (Debian)",                 "dkms status",                                                          "low",    "List DKMS modules and build status",                                  None),
        ("Rebuild initramfs (Debian)",                "sudo update-initramfs -u",                                             "medium", "Rebuild initramfs after driver or module changes",                    None),
        ("Install kernel headers (Debian)",           "sudo apt install linux-headers-$(uname -r)",                           "medium", "Install kernel headers for DKMS",                                     None),
    ]

    for title, command, risk, purpose, rollback in debian_cmds:
        cmds.append((debian_id, title, command, risk, purpose, rollback))

    # ── Fedora ────────────────────────────────────────────────────────────────
    fedora_cmds = [
        ("Update Fedora packages",                    "sudo dnf upgrade",                                                     "medium", "Upgrade all installed packages on Fedora",                            None),
        ("Install a package (dnf)",                   "sudo dnf install <package>",                                           "medium", "Install a package via dnf",                                           "sudo dnf remove <package>"),
        ("Enable RPM Fusion free",                    "sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm", "medium", "Enable RPM Fusion free repo", None),
        ("Enable RPM Fusion non-free",                "sudo dnf install https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm", "medium", "Enable RPM Fusion non-free repo for NVIDIA", None),
        ("Install NVIDIA driver (Fedora)",            "sudo dnf install akmod-nvidia",                                        "medium", "Install NVIDIA driver via RPM Fusion",                                None),
        ("Show DKMS status (Fedora)",                 "dkms status",                                                          "low",    "List DKMS modules and build status",                                  None),
        ("Install kernel headers (Fedora)",           "sudo dnf install kernel-devel-$(uname -r)",                            "medium", "Install kernel development headers",                                  None),
        ("Rebuild initramfs (Fedora)",                "sudo dracut --force",                                                  "medium", "Rebuild initramfs on Fedora/RHEL-based systems",                      None),
        ("Install Fedora Kickstart tools",            "sudo dnf install pykickstart",                                         "medium", "Install Kickstart file tools",                                        "sudo dnf remove pykickstart"),
        ("Validate Kickstart file",                   "ksvalidator kickstart.ks",                                             "low",    "Validate a Fedora Kickstart file",                                    None),
    ]

    for title, command, risk, purpose, rollback in fedora_cmds:
        cmds.append((fedora_id, title, command, risk, purpose, rollback))

    # ── Arch ──────────────────────────────────────────────────────────────────
    arch_cmds = [
        ("Update Arch packages",                      "sudo pacman -Syu",                                                     "medium", "Full system upgrade on Arch Linux",                                   None),
        ("Install a package (pacman)",                "sudo pacman -S <package>",                                             "medium", "Install a package via pacman",                                        "sudo pacman -R <package>"),
        ("Install NVIDIA driver (Arch)",              "sudo pacman -S nvidia nvidia-utils",                                   "medium", "Install NVIDIA proprietary driver on Arch",                           "sudo pacman -R nvidia nvidia-utils"),
        ("Show DKMS status (Arch)",                   "dkms status",                                                          "low",    "List DKMS modules and build status",                                  None),
        ("Install kernel headers (Arch)",             "sudo pacman -S linux-headers",                                         "medium", "Install kernel headers for DKMS",                                     None),
        ("Rebuild initramfs (Arch)",                  "sudo mkinitcpio -P",                                                   "medium", "Rebuild initramfs for all Arch kernels",                              None),
        ("Install Archinstall tools",                 "sudo pacman -S archinstall archiso",                                   "medium", "Installs Arch installer and ISO tools",                               "sudo pacman -R archinstall archiso"),
        ("Install ISO tools (Arch)",                  "sudo pacman -S xorriso squashfs-tools",                                "medium", "Installs ISO and SquashFS tools",                                     "sudo pacman -R xorriso squashfs-tools"),
    ]

    for title, command, risk, purpose, rollback in arch_cmds:
        cmds.append((arch_id, title, command, risk, purpose, rollback))

    # ── openSUSE ──────────────────────────────────────────────────────────────
    opensuse_cmds = [
        ("Update openSUSE packages",                  "sudo zypper update",                                                   "medium", "Update all installed packages on openSUSE",                           None),
        ("Install a package (zypper)",                "sudo zypper install <package>",                                        "medium", "Install a package via zypper",                                        "sudo zypper remove <package>"),
        ("Install NVIDIA driver (openSUSE)",          "sudo zypper install nvidia-glG05",                                     "medium", "Install NVIDIA driver on openSUSE",                                   None),
        ("Show DKMS status (openSUSE)",               "dkms status",                                                          "low",    "List DKMS modules and build status",                                  None),
        ("Install kernel headers (openSUSE)",         "sudo zypper install kernel-devel",                                     "medium", "Install kernel development headers",                                  None),
        ("Rebuild initramfs (openSUSE)",              "sudo mkinitrd",                                                        "medium", "Rebuild initramfs on openSUSE",                                       None),
        ("Install AutoYaST tools",                    "sudo zypper install autoyast2",                                        "medium", "Installs AutoYaST automated installation tools",                      "sudo zypper remove autoyast2"),
        ("Install KIWI image tools",                  "sudo zypper install kiwi xorriso",                                     "medium", "Installs openSUSE image building tools",                              "sudo zypper remove kiwi xorriso"),
    ]

    for title, command, risk, purpose, rollback in opensuse_cmds:
        cmds.append((opensuse_id, title, command, risk, purpose, rollback))

    return cmds


def seed_commands(cur, distro_ids: dict[str, int]) -> int:
    """
    Insert commands with correct NULL-safe distro_id handling.
    PostgreSQL cannot determine parameter type when comparing NULL via = %s,
    so we use separate SELECT paths for NULL and non-NULL distro_id.
    Returns count of newly inserted commands.
    """
    commands = build_commands(distro_ids)
    inserted = 0

    for distro_id_val, title, command, risk_level, purpose, rollback_command in commands:
        # Check for existing row — separate path for NULL distro_id
        if distro_id_val is None:
            cur.execute(
                """
                SELECT id FROM commands
                WHERE title = %s
                  AND distro_id IS NULL
                """,
                (title,),
            )
        else:
            cur.execute(
                """
                SELECT id FROM commands
                WHERE title = %s
                  AND distro_id = %s
                """,
                (title, distro_id_val),
            )

        if cur.fetchone():
            continue  # already exists, skip

        cur.execute(
            """
            INSERT INTO commands
                (distro_id, title, command, risk_level, purpose, rollback_command)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (distro_id_val, title, command, risk_level, purpose, rollback_command),
        )
        inserted += 1

    return inserted


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("LinuxAI Base Data Seeder")
    print("=" * 60)

    all_commands = None  # will be set after distro_ids are ready

    with get_connection() as conn:
        with conn.cursor() as cur:

            print("\nSeeding distros...")
            distro_ids = seed_distros(cur)
            print(f"  Distros: {len(distros)}")

            print("Seeding drivers...")
            seed_drivers(cur)
            print(f"  Drivers: {len(drivers)}")

            print("Seeding devices...")
            seed_devices(cur)
            print(f"  Devices: {len(devices)}")

            print("Seeding packages...")
            seed_packages(cur, distro_ids)
            packages = build_packages(distro_ids)
            print(f"  Packages: {len(packages)}")

            print("Seeding commands...")
            all_commands = build_commands(distro_ids)
            inserted_commands = seed_commands(cur, distro_ids)
            print(f"  Commands inserted (new): {inserted_commands} of {len(all_commands)}")

        conn.commit()

    print("\n" + "=" * 60)
    print("Base SQL data inserted successfully.")
    print(f"  Distros:  {len(distros)}")
    print(f"  Drivers:  {len(drivers)}")
    print(f"  Devices:  {len(devices)}")
    print(f"  Packages: {len(packages)}")
    print(f"  Commands inserted (new): {inserted_commands} of {len(all_commands)}")


if __name__ == "__main__":
    main()