"""
scripts/collect_system_profile.py

LinuxAI system profile collector.

Purpose:
  Collect read-only hardware/system diagnostics and produce a JSON profile for
  LinuxAI installer recommendation and boot config generation.

Important:
  - This script does not change system settings.
  - This script does not install packages.
  - This script does not write to USB.
  - This script does not modify disks.
  - This script collects diagnostics only.

Recommended frontend mode:
  python scripts/collect_system_profile.py --no-db --frontend-json > /tmp/linuxai_frontend_profile.json

In frontend-json mode:
  - JSON profile is printed to stdout.
  - logs/status messages are printed to stderr.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = PROJECT_ROOT / "data" / "system_profiles"

SCHEMA_VERSION = "0.5"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:8]


def log(message: str, frontend_json: bool = False) -> None:
    stream = sys.stderr if frontend_json else sys.stdout
    print(message, file=stream)


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def run_command(
    name: str,
    command: list[str] | str,
    shell: bool = False,
    timeout: int = 12,
    frontend_json: bool = False,
) -> dict[str, Any]:
    log(f"  Running {platform.system()} command: {name}", frontend_json=frontend_json)

    if isinstance(command, list):
        executable = command[0]
    else:
        executable = command.split()[0] if command else ""

    if executable and not shell and not command_exists(executable):
        return {
            "name": name,
            "command": command if isinstance(command, str) else " ".join(command),
            "ok": False,
            "stdout": "",
            "stderr": f"Command not found: {executable}",
            "returncode": None,
        }

    try:
        proc = subprocess.run(
            command,
            shell=shell,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "name": name,
            "command": command if isinstance(command, str) else " ".join(command),
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "command": command if isinstance(command, str) else " ".join(command),
            "ok": False,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "returncode": None,
        }
    except Exception as exc:
        return {
            "name": name,
            "command": command if isinstance(command, str) else " ".join(command),
            "ok": False,
            "stdout": "",
            "stderr": str(exc),
            "returncode": None,
        }


def parse_os_release(text: str) -> dict[str, str | None]:
    data: dict[str, str] = {}

    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"')

    return {
        "name": data.get("NAME"),
        "version": data.get("VERSION"),
        "id": data.get("ID"),
        "id_like": data.get("ID_LIKE"),
    }


def parse_lscpu(text: str) -> dict[str, str | None]:
    result: dict[str, str | None] = {
        "model_name": None,
        "architecture": None,
        "cpu_cores": None,
        "threads_per_core": None,
    }

    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        lk = key.lower()

        if lk == "model name":
            result["model_name"] = value
        elif lk == "architecture":
            result["architecture"] = value
        elif lk == "cpu(s)":
            result["cpu_cores"] = value
        elif lk == "thread(s) per core":
            result["threads_per_core"] = value

    return result


def parse_lsmod_modules(text: str) -> set[str]:
    modules: set[str] = set()

    for line in text.splitlines()[1:]:
        parts = line.split()
        if parts:
            modules.add(parts[0])

    return modules


def clean_component_name(raw: str) -> str:
    name = raw.strip()
    name = re.sub(r"^\S+\s+", "", name)
    name = re.sub(r"\s*\(rev\s+[0-9a-fA-F]+\)\s*$", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def vendor_from_name(name: str) -> str | None:
    lowered = name.lower()

    vendors = {
        "nvidia": "NVIDIA",
        "intel": "Intel",
        "advanced micro devices": "AMD",
        "amd": "AMD",
        "realtek": "Realtek",
        "mediatek": "MediaTek",
        "qualcomm": "Qualcomm",
        "atheros": "Atheros",
        "broadcom": "Broadcom",
        "samsung": "Samsung",
        "western digital": "Western Digital",
        "sandisk": "SanDisk",
        "logitech": "Logitech",
        "bison": "Bison",
        "synaptics": "Synaptics",
        "goodix": "Goodix",
        "validity": "Validity",
        "elantech": "ELAN",
        "wacom": "Wacom",
    }

    for needle, vendor in vendors.items():
        if needle in lowered:
            return vendor

    if " corporation " in f" {lowered} ":
        return name.split(" Corporation")[0].strip()

    if " inc." in lowered:
        return name.split(" Inc.")[0].strip()

    if " co., ltd" in lowered:
        return name.split(" Co., Ltd")[0].strip()

    return None


def infer_component_name(detected_name: str, component_type: str) -> str:
    name = detected_name

    replacements = [
        ("Intel Corporation ", "Intel "),
        ("NVIDIA Corporation ", "NVIDIA "),
        ("Advanced Micro Devices, Inc. [AMD/ATI] ", "AMD "),
        ("Realtek Semiconductor Co., Ltd. ", "Realtek "),
        ("Samsung Electronics Co Ltd ", "Samsung "),
    ]

    for old, new in replacements:
        name = name.replace(old, new)

    if "GeForce RTX 4050" in name:
        return "NVIDIA GeForce RTX 4050 Max-Q / Mobile"
    if "UHD Graphics" in name:
        return "Intel UHD Graphics"
    if "CNVi WiFi" in name or "CNVi Wi-Fi" in name:
        return "Intel CNVi Wi-Fi"
    if "AX211 Bluetooth" in name:
        return "Intel AX211 Bluetooth"
    if "RTL8111" in name or "RTL8168" in name or "RTL8411" in name:
        return "Realtek RTL8111/8168/8411 Ethernet"
    if "High Definition Audio Controller" in name and "Intel" in name:
        return "Intel HD Audio"
    if component_type == "audio" and "NVIDIA" in name:
        return "NVIDIA HDMI/DisplayPort Audio"
    if "Volume Management Device" in name or "VMD" in name:
        return "Intel VMD / RST Storage Controller"
    if "SATA AHCI" in name:
        return "SATA AHCI Storage Controller"
    if "NVMe SSD" in name or "NVMe" in name:
        if "Samsung" in name:
            return "Samsung NVMe SSD"
        return "NVMe SSD"
    if component_type == "camera":
        return re.sub(r"^\S+\s+", "", name).strip() or name

    return clean_component_name(name)


def make_component(
    *,
    detected_name: str,
    component_type: str,
    source: str,
    pci_id: str | None = None,
    usb_id: str | None = None,
    driver: str | None = None,
    kernel_modules: list[str] | None = None,
) -> dict[str, Any]:
    vendor = vendor_from_name(detected_name)

    return {
        "component_name": infer_component_name(detected_name, component_type),
        "detected_name": detected_name,
        "component_group": component_type,
        "vendor": vendor,
        "type": component_type,
        "pci_id": pci_id,
        "usb_id": usb_id,
        "driver": driver,
        "kernel_modules": kernel_modules or [],
        "source": source,
        "selected": True,
        "user_corrected_name": "",
        "user_notes": "",
    }


def classify_pci_device(line: str) -> str | None:
    lowered = line.lower()

    if any(x in lowered for x in ["vga compatible controller", "3d controller", "display controller"]):
        return "gpu"
    if "network controller" in lowered or "wireless" in lowered or "wi-fi" in lowered or "wifi" in lowered:
        return "wifi"
    if "ethernet controller" in lowered:
        return "ethernet"
    if "audio device" in lowered or "multimedia audio" in lowered:
        return "audio"
    if any(x in lowered for x in ["non-volatile memory controller", "sata controller", "raid bus controller", "volume management device"]):
        if "sata" in lowered:
            return "storage_controller"
        return "storage"

    return None


def extract_pci_id(text: str) -> str | None:
    matches = re.findall(r"\[([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\]", text)
    return matches[-1].lower() if matches else None


def parse_lspci(text: str) -> dict[str, list[dict[str, Any]]]:
    hardware = {
        "gpus": [],
        "wifi_adapters": [],
        "ethernet_adapters": [],
        "audio_devices": [],
        "storage_devices": [],
    }

    current_line: str | None = None
    current_type: str | None = None
    current_driver: str | None = None
    current_modules: list[str] = []

    def flush() -> None:
        nonlocal current_line, current_type, current_driver, current_modules

        if not current_line or not current_type:
            current_line = None
            current_type = None
            current_driver = None
            current_modules = []
            return

        detected = clean_component_name(current_line)
        pci_id = extract_pci_id(current_line)

        component = make_component(
            detected_name=detected,
            component_type=current_type,
            source="lspci",
            pci_id=pci_id,
            driver=current_driver,
            kernel_modules=current_modules,
        )

        if current_type == "gpu":
            hardware["gpus"].append(component)
        elif current_type == "wifi":
            hardware["wifi_adapters"].append(component)
        elif current_type == "ethernet":
            hardware["ethernet_adapters"].append(component)
        elif current_type == "audio":
            hardware["audio_devices"].append(component)
        elif current_type in {"storage", "storage_controller"}:
            hardware["storage_devices"].append(component)

        current_line = None
        current_type = None
        current_driver = None
        current_modules = []

    for line in text.splitlines():
        if not line.strip():
            continue

        if not line.startswith("\t") and re.match(r"^[0-9a-fA-F:.]+", line):
            flush()
            current_line = line
            current_type = classify_pci_device(line)
            current_driver = None
            current_modules = []
            continue

        if current_line and line.startswith("\t"):
            stripped = line.strip()

            if stripped.startswith("Kernel driver in use:"):
                current_driver = stripped.split(":", 1)[1].strip()

            if stripped.startswith("Kernel modules:"):
                modules = stripped.split(":", 1)[1].strip()
                current_modules = [m.strip() for m in modules.split(",") if m.strip()]

    flush()
    return hardware


def classify_usb_device(name: str) -> str | None:
    lowered = name.lower()

    if "bluetooth" in lowered:
        return "bluetooth"
    if "webcam" in lowered or "camera" in lowered:
        return "camera"
    if "wireless" in lowered or "wifi" in lowered or "wi-fi" in lowered or "802.11" in lowered:
        return "wifi"
    if "keyboard" in lowered or "mouse" in lowered or "receiver" in lowered or "2.4g" in lowered:
        return "input"
    if "audio" in lowered or "sound" in lowered or "headset" in lowered:
        return "audio"

    return None


def parse_lsusb(text: str) -> dict[str, list[dict[str, Any]]]:
    hardware = {
        "wifi_adapters": [],
        "bluetooth_devices": [],
        "audio_devices": [],
        "cameras": [],
        "input_devices": [],
    }

    for line in text.splitlines():
        match = re.search(r"ID\s+([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\s+(.+)$", line)
        if not match:
            continue

        usb_id = match.group(1).lower()
        detected = match.group(2).strip()
        dtype = classify_usb_device(detected)

        if not dtype:
            continue

        component = make_component(
            detected_name=detected,
            component_type=dtype,
            source="lsusb",
            usb_id=usb_id,
        )

        if dtype == "wifi":
            hardware["wifi_adapters"].append(component)
        elif dtype == "bluetooth":
            hardware["bluetooth_devices"].append(component)
        elif dtype == "audio":
            hardware["audio_devices"].append(component)
        elif dtype == "camera":
            hardware["cameras"].append(component)
        elif dtype == "input":
            hardware["input_devices"].append(component)

    return hardware


def parse_batteries_from_upower(text: str) -> list[dict[str, Any]]:
    batteries: list[dict[str, Any]] = []

    for line in text.splitlines():
        if "battery" in line.lower():
            batteries.append(
                {
                    "component_name": "Battery",
                    "detected_name": line.strip(),
                    "component_group": "battery",
                    "vendor": None,
                    "type": "battery",
                    "source": "upower",
                    "selected": True,
                    "user_corrected_name": "",
                    "user_notes": "",
                }
            )

    return batteries


def collect_linux(frontend_json: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    commands: dict[str, Any] = {}

    linux_commands: list[tuple[str, list[str] | str, bool]] = [
        ("os-release",        ["cat", "/etc/os-release"],                                                                  False),
        ("uname -a",          ["uname", "-a"],                                                                             False),
        ("lspci -nnk",        ["lspci", "-nnk"],                                                                           False),
        ("lsusb",             ["lsusb"],                                                                                   False),
        ("lsblk",             ["lsblk", "-o", "NAME,TYPE,SIZE,MODEL,SERIAL,TRAN,MOUNTPOINT,FSTYPE"],                       False),
        ("lscpu",             ["lscpu"],                                                                                   False),
        ("lsmod",             ["lsmod"],                                                                                   False),
        ("rfkill list",       ["rfkill", "list"],                                                                          False),
        ("ip a",              ["ip", "a"],                                                                                 False),
        ("iw dev",            ["iw", "dev"],                                                                               False),
        ("bluetoothctl list", ["bluetoothctl", "list"],                                                                    False),
        ("audio cards",       ["cat", "/proc/asound/cards"],                                                               False),
        ("pipewire status",   ["systemctl", "--user", "status", "pipewire", "--no-pager"],                                 False),
        ("wireplumber status",["systemctl", "--user", "status", "wireplumber", "--no-pager"],                              False),
        ("audio sinks",       ["pactl", "list", "short", "sinks"],                                                        False),
        ("secure boot",       ["mokutil", "--sb-state"],                                                                   False),
        ("nvidia-smi",        ["nvidia-smi"],                                                                              False),
        ("power profile",     ["powerprofilesctl", "get"],                                                                 False),
        ("sensors",           ["sensors"],                                                                                 False),
        ("upower batteries",  "upower -e | grep -i battery",                                                              True),
        ("dmesg firmware",    "dmesg | grep -i firmware | tail -80",                                                       True),
        ("dmesg nvidia",      "dmesg | grep -i nvidia | tail -80",                                                         True),
        ("dmesg wifi",        "dmesg | grep -i -E 'wifi|wlan|iwlwifi|rtw|mt76|ath|firmware' | tail -80",                  True),
        ("dmesg bluetooth",   "dmesg | grep -i bluetooth | tail -80",                                                      True),
        ("dmesg audio",       "dmesg | grep -i -E 'sof|audio|snd|hda' | tail -80",                                        True),
        ("inxi",              "inxi -Fxxx --no-host 2>/dev/null || echo 'inxi not installed'",                             True),
    ]

    for name, cmd, shell in linux_commands:
        commands[name] = run_command(
            name=name,
            command=cmd,
            shell=shell,
            frontend_json=frontend_json,
        )

    os_info  = parse_os_release(commands["os-release"]["stdout"])
    cpu_info = parse_lscpu(commands["lscpu"]["stdout"])
    modules  = parse_lsmod_modules(commands["lsmod"]["stdout"])

    pci_hw = parse_lspci(commands["lspci -nnk"]["stdout"])
    usb_hw = parse_lsusb(commands["lsusb"]["stdout"])

    hardware = {
        "gpus":              pci_hw.get("gpus", []),
        "wifi_adapters":     pci_hw.get("wifi_adapters", []) + usb_hw.get("wifi_adapters", []),
        "ethernet_adapters": pci_hw.get("ethernet_adapters", []),
        "bluetooth_devices": usb_hw.get("bluetooth_devices", []),
        "audio_devices":     pci_hw.get("audio_devices", []) + usb_hw.get("audio_devices", []),
        "storage_devices":   pci_hw.get("storage_devices", []),
        "touchpads":         [],
        "cameras":           usb_hw.get("cameras", []),
        "input_devices":     usb_hw.get("input_devices", []),
        "batteries":         parse_batteries_from_upower(commands["upower batteries"]["stdout"]),
    }

    for section_items in hardware.values():
        if not isinstance(section_items, list):
            continue
        for item in section_items:
            driver = item.get("driver")
            if driver and driver in modules and driver not in item.get("kernel_modules", []):
                item.setdefault("kernel_modules", []).append(driver)

    profile = {
        "os": {
            "family":        "linux",
            "name":          os_info.get("name"),
            "version":       os_info.get("version"),
            "id":            os_info.get("id"),
            "id_like":       os_info.get("id_like"),
            "kernel":        commands["uname -a"]["stdout"],
            "architecture":  cpu_info.get("architecture"),
            "user_corrected_os": "",
        },
        "machine": {
            "manufacturer":     read_sys_file("/sys/class/dmi/id/sys_vendor"),
            "model":            read_sys_file("/sys/class/dmi/id/product_name"),
            "system_type":      None,
            "user_device_type": "",
            "user_laptop_model": "",
            "user_cpu":         cpu_info.get("model_name") or "",
            "user_ram_gb":      "",
        },
        "hardware": hardware,
        "raw_diagnostics": {
            name: {
                "command":    item["command"],
                "ok":         item["ok"],
                "stdout":     item["stdout"],
                "stderr":     item["stderr"],
                "returncode": item["returncode"],
            }
            for name, item in commands.items()
        },
    }

    command_status = {
        name: {
            "command": item["command"],
            "ok":      item["ok"],
            "stderr":  item["stderr"],
        }
        for name, item in commands.items()
    }

    return profile, command_status


def read_sys_file(path: str) -> str | None:
    try:
        p = Path(path)
        if p.exists():
            value = p.read_text(encoding="utf-8", errors="replace").strip()
            return value or None
    except Exception:
        return None
    return None


def collect_windows(frontend_json: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    commands: dict[str, Any] = {}

    windows_commands: list[tuple[str, list[str] | str, bool]] = [
        ("systeminfo",                   ["systeminfo"],                                                                                        False),
        ("wmic computersystem",          ["wmic", "computersystem", "get", "manufacturer,model,systemtype"],                                    False),
        ("wmic cpu",                     ["wmic", "cpu", "get", "name"],                                                                        False),
        ("wmic path win32_VideoController", ["wmic", "path", "win32_VideoController", "get", "name,pnpdeviceid"],                               False),
        ("wmic nic",                     ["wmic", "nic", "get", "name,manufacturer,pnpdeviceid"],                                               False),
        ("wmic diskdrive",               ["wmic", "diskdrive", "get", "model,interfacetype,size"],                                              False),
        ("wmic sounddev",                ["wmic", "sounddev", "get", "name,manufacturer,pnpdeviceid"],                                          False),
    ]

    for name, cmd, shell in windows_commands:
        commands[name] = run_command(
            name=name,
            command=cmd,
            shell=shell,
            frontend_json=frontend_json,
        )

    hardware = {
        "gpus":              parse_windows_wmic_devices(commands["wmic path win32_VideoController"]["stdout"], "gpu"),
        "wifi_adapters":     parse_windows_wmic_devices(commands["wmic nic"]["stdout"], "wifi"),
        "ethernet_adapters": parse_windows_wmic_devices(commands["wmic nic"]["stdout"], "ethernet"),
        "bluetooth_devices": parse_windows_wmic_devices(commands["wmic nic"]["stdout"], "bluetooth"),
        "audio_devices":     parse_windows_wmic_devices(commands["wmic sounddev"]["stdout"], "audio"),
        "storage_devices":   parse_windows_wmic_devices(commands["wmic diskdrive"]["stdout"], "storage"),
        "touchpads":         [],
        "cameras":           [],
        "input_devices":     [],
        "batteries":         [],
    }

    profile = {
        "os": {
            "family":        "windows",
            "name":          platform.system(),
            "version":       platform.version(),
            "id":            "windows",
            "id_like":       None,
            "kernel":        platform.platform(),
            "architecture":  platform.machine(),
            "user_corrected_os": "",
        },
        "machine": {
            "manufacturer":     None,
            "model":            None,
            "system_type":      None,
            "user_device_type": "",
            "user_laptop_model": "",
            "user_cpu":         "",
            "user_ram_gb":      "",
        },
        "hardware": hardware,
        "raw_diagnostics": {
            name: {
                "command":    item["command"],
                "ok":         item["ok"],
                "stdout":     item["stdout"],
                "stderr":     item["stderr"],
                "returncode": item["returncode"],
            }
            for name, item in commands.items()
        },
    }

    command_status = {
        name: {
            "command": item["command"],
            "ok":      item["ok"],
            "stderr":  item["stderr"],
        }
        for name, item in commands.items()
    }

    return profile, command_status


def parse_windows_wmic_devices(text: str, component_type: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for line in text.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue

        lowered = line.lower()

        if component_type == "wifi" and not any(x in lowered for x in ["wi-fi", "wifi", "wireless", "802.11"]):
            continue
        if component_type == "ethernet" and not any(x in lowered for x in ["ethernet", "gbe", "gigabit"]):
            continue
        if component_type == "bluetooth" and "bluetooth" not in lowered:
            continue

        items.append(
            make_component(
                detected_name=line,
                component_type=component_type,
                source="wmic",
            )
        )

    return items


def base_user_choices() -> dict[str, Any]:
    return {
        "install_target": {
            "target_device":                 "",
            "install_type":                  "",
            "dual_boot_with_windows":        None,
            "replace_existing_os":           None,
            "keep_existing_files":           None,
            "disk_encryption_wanted":        None,
            "automatic_partitioning_wanted": None,
        },
        "linux_preferences": {
            "preferred_distros":    [],
            "avoid_distros":        [],
            "desktop_environment":  "",
            "stability_priority":   "",
            "release_model":        "",
            "beginner_friendly":    None,
            "gaming_needed":        None,
            "development_needed":   None,
            "ai_ml_needed":         None,
            "battery_life_priority": None,
            "nvidia_priority":      "",
        },
        "hardware_preferences": {
            "use_nvidia_driver":          None,
            "nvidia_mode_preference":     "",
            "wifi_must_work_during_install": True,
            "bluetooth_required":         None,
            "touchpad_required":          None,
            "fingerprint_required":       None,
            "external_monitor_required":  None,
            "printer_required":           None,
        },
        "external_devices": {
            "devices": [
                {
                    "name":                 "",
                    "brand":                "",
                    "device_type":          "",
                    "connection":           "",
                    "required_for_install": False,
                    "needs_driver":         None,
                    "user_notes":           "",
                }
            ],
            "device_type_options": [
                "mouse", "keyboard", "printer", "scanner", "drawing_tablet",
                "usb_audio_interface", "webcam", "capture_card",
                "external_wifi_adapter", "bluetooth_adapter", "usb_c_dock",
                "external_monitor", "game_controller", "other",
            ],
            "connection_options": [
                "usb", "bluetooth", "2.4ghz_receiver", "usb_c",
                "hdmi", "displayport", "ethernet", "other",
            ],
        },
        "bios_firmware_permissions": {
            "can_change_secure_boot":  None,
            "can_change_storage_mode": None,
            "can_update_bios":         None,
            "can_disable_fast_boot":   None,
        },
        "software_needed": {
            "browsers":             [],
            "code_editors":         [],
            "gaming_tools":         [],
            "creative_tools":       [],
            "school_or_work_apps":  [],
            "virtualization_tools": [],
            "ai_tools":             [],
            "other":                [],
        },
        "special_needs": {
            "language":                        "",
            "accessibility":                   [],
            "low_storage_mode":                None,
            "low_ram_mode":                    None,
            "offline_install_needed":          None,
            "must_be_stable_for_school_or_work": None,
            "notes":                           "",
        },
    }


def frontend_options() -> dict[str, Any]:
    return {
        "device_types": [
            "laptop", "desktop_pc", "mini_pc", "server",
            "virtual_machine", "unknown",
        ],
        "install_types": [
            "try_live_usb_only", "full_install", "dual_boot",
            "replace_os", "external_drive_install",
            "virtual_machine_install", "not_sure",
        ],
        "distros": [
            "Ubuntu", "Pop!_OS", "Linux Mint", "Fedora", "Debian",
            "Arch", "Manjaro", "EndeavourOS", "openSUSE", "Other", "Not sure",
        ],
        "desktop_environments": [
            "GNOME", "KDE Plasma", "Cinnamon", "XFCE",
            "MATE", "COSMIC", "Not sure",
        ],
        "stability_priority": [
            "maximum_stability", "balanced", "newer_packages",
            "latest_hardware_support", "not_sure",
        ],
        "release_models": [
            "fixed_release", "rolling_release", "semi_rolling", "not_sure",
        ],
        "nvidia_modes": [
            "battery_saving_integrated_gpu", "hybrid_on_demand",
            "nvidia_performance", "not_sure",
        ],
        "permission_options": ["yes", "no", "not_sure"],
    }


def build_profile(frontend_json: bool = False) -> dict[str, Any]:
    system = platform.system().lower()

    if "windows" in system:
        collected, command_status = collect_windows(frontend_json=frontend_json)
        detected_platform = "Windows"
    else:
        collected, command_status = collect_linux(frontend_json=frontend_json)
        detected_platform = "Linux"

    identity_text = json.dumps(
        {
            "time":     now_utc(),
            "platform": detected_platform,
            "machine":  collected.get("machine", {}),
            "os":       collected.get("os", {}),
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    profile_id = f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{short_hash(identity_text)}"

    profile = {
        "profile_id":       profile_id,
        "created_at":       now_utc(),
        "schema_version":   SCHEMA_VERSION,
        "os":               collected["os"],
        "machine":          collected["machine"],
        "hardware":         collected["hardware"],
        "user_choices":     base_user_choices(),
        "frontend_options": frontend_options(),
        "command_status":   command_status,
        "review_required": [
            "Check that GPU names are correct.",
            "Check that Wi-Fi and Bluetooth adapters are correct.",
            "Check audio devices.",
            "Check storage mode / NVMe / Intel RST before Linux installation.",
            "Add laptop or motherboard model manually if it was not detected.",
            "Choose install target and whether dual boot is needed.",
            "Choose whether Secure Boot or storage mode changes are allowed.",
            "Add external devices manually if they were not detected or need special drivers.",
        ],
        "privacy_note": (
            "This profile may contain hardware identifiers, hostnames, driver versions, "
            "device IDs, storage models, serial-like fields, and command outputs. "
            "Review before sharing."
        ),
    }

    return profile


def save_profile(profile: dict[str, Any]) -> Path:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    path = PROFILE_DIR / f"{profile['profile_id']}.json"
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect LinuxAI system profile.")
    parser.add_argument("--no-db",        action="store_true", help="Do not write to database.")
    parser.add_argument("--frontend-json", action="store_true", help="Print clean frontend JSON to stdout.")
    parser.add_argument("--output",        default="",          help="Optional output JSON path.")

    args = parser.parse_args()

    log("=" * 70, frontend_json=args.frontend_json)
    log("LinuxAI System Profile Collector", frontend_json=args.frontend_json)
    log("=" * 70, frontend_json=args.frontend_json)
    log(f"Detected platform: {platform.system()}", frontend_json=args.frontend_json)
    log("This script collects diagnostics only. It does not change system settings.", frontend_json=args.frontend_json)
    log("", frontend_json=args.frontend_json)

    profile = build_profile(frontend_json=args.frontend_json)

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        saved_path = output_path
    else:
        saved_path = save_profile(profile)

    log("", frontend_json=args.frontend_json)
    log("=" * 70, frontend_json=args.frontend_json)
    log("Profile JSON saved.", frontend_json=args.frontend_json)
    log(f"Saved to: {saved_path}", frontend_json=args.frontend_json)
    log("=" * 70, frontend_json=args.frontend_json)

    if args.frontend_json:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(profile, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()