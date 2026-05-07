"""
scripts/generate_boot_config_files.py

LinuxAI gated boot/install configuration generator.

Purpose:
  Generate distro-specific installer configuration DRAFT files from a LinuxAI
  frontend profile JSON.

Important:
  - This is NOT an ISO builder.
  - This is NOT a USB writer.
  - This does NOT modify disks.
  - This does NOT create storage/partitioning/wipe layouts.
  - This does NOT run dd, mkfs, parted, wipefs, fdisk, cryptsetup, or mount.
  - This only writes text configuration draft files into generated/boot_configs/.

Supported draft outputs:
  - Ubuntu LTS: user-data + meta-data
  - Debian: preseed.cfg
  - Fedora: kickstart.ks
  - Arch: archinstall-user-configuration.json
  - openSUSE: autoyast.xml
  - Pop!_OS / Linux Mint: manifest + README only for now
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "generated" / "boot_configs"

CONFIRMATION_PHRASE = "I_UNDERSTAND_BOOT_CONFIG_FILES_ARE_DANGEROUS"

DESTRUCTIVE_COMMAND_PATTERNS = [
    r"(^|\n|\s)(sudo\s+)?dd\s+",
    r"(^|\n|\s)(sudo\s+)?mkfs(\.|\s)",
    r"(^|\n|\s)(sudo\s+)?wipefs\s+",
    r"(^|\n|\s)(sudo\s+)?parted\s+",
    r"(^|\n|\s)(sudo\s+)?fdisk\s+",
    r"(^|\n|\s)(sudo\s+)?sfdisk\s+",
    r"(^|\n|\s)(sudo\s+)?cryptsetup\s+",
    r"(^|\n|\s)(sudo\s+)?sgdisk\s+",
    r"(^|\n|\s)(sudo\s+)?pvcreate\s+",
    r"(^|\n|\s)(sudo\s+)?vgcreate\s+",
    r"(^|\n|\s)(sudo\s+)?lvcreate\s+",
    r"(^|\n|\s)(sudo\s+)?grub-install\s+",
    r"(^|\n|\s)(sudo\s+)?mount\s+",
    r"(^|\n|\s)(sudo\s+)?umount\s+",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_slug(text: str) -> str:
    text = str(text).strip().lower()
    text = re.sub(r"[^a-z0-9_.-]+", "_", text)
    return text.strip("_") or "unknown"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Profile file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON profile: {exc}") from exc


def assert_no_destructive_content(text: str) -> None:
    lowered = text.lower()
    for pattern in DESTRUCTIVE_COMMAND_PATTERNS:
        if re.search(pattern, lowered):
            raise RuntimeError(
                f"Generated content contains blocked destructive command pattern: {pattern}"
            )


def validate_frontend_profile(profile: dict[str, Any]) -> None:
    if "hardware" not in profile or "user_choices" not in profile:
        raise ValueError(
            "Expected frontend JSON from: "
            "python scripts/collect_system_profile.py --no-db --frontend-json"
        )


def get_hardware_items(profile: dict[str, Any], section: str) -> list[dict[str, Any]]:
    items = profile.get("hardware", {}).get(section, [])
    if not isinstance(items, list):
        return []
    return [
        item
        for item in items
        if isinstance(item, dict) and item.get("selected", True)
    ]


def has_vendor(profile: dict[str, Any], section: str, vendor: str) -> bool:
    vendor = vendor.lower()
    for item in get_hardware_items(profile, section):
        text = " ".join(
            str(item.get(k, ""))
            for k in ["component_name", "detected_name", "vendor", "driver"]
        ).lower()
        if vendor in text:
            return True
    return False


def has_text(profile: dict[str, Any], section: str, needle: str) -> bool:
    needle = needle.lower()
    for item in get_hardware_items(profile, section):
        text = " ".join(
            str(item.get(k, ""))
            for k in ["component_name", "detected_name", "vendor", "driver", "pci_id", "usb_id"]
        ).lower()
        if needle in text:
            return True
    return False


def detect_flags(profile: dict[str, Any]) -> dict[str, bool]:
    return {
        "has_nvidia_gpu": has_vendor(profile, "gpus", "NVIDIA"),
        "has_intel_gpu": has_vendor(profile, "gpus", "Intel"),
        "has_amd_gpu": has_vendor(profile, "gpus", "AMD"),
        "has_intel_wifi": has_vendor(profile, "wifi_adapters", "Intel"),
        "has_realtek_wifi": has_vendor(profile, "wifi_adapters", "Realtek"),
        "has_mediatek_wifi": has_vendor(profile, "wifi_adapters", "MediaTek"),
        "has_bluetooth": len(get_hardware_items(profile, "bluetooth_devices")) > 0,
        "has_intel_vmd_or_rst": has_text(profile, "storage_devices", "VMD")
        or has_text(profile, "storage_devices", "RST"),
        "has_nvme": has_text(profile, "storage_devices", "NVMe"),
    }


def normalize_requested_distro(value: str) -> str:
    value = str(value).strip().lower()
    aliases = {
        "auto": "auto",
        "ubuntu": "ubuntu-lts",
        "ubuntu-lts": "ubuntu-lts",
        "ubuntu lts": "ubuntu-lts",
        "pop": "popos",
        "popos": "popos",
        "pop!_os": "popos",
        "pop os": "popos",
        "linux mint": "linux-mint",
        "mint": "linux-mint",
        "fedora": "fedora",
        "debian": "debian",
        "arch": "arch",
        "archlinux": "arch",
        "arch linux": "arch",
        "endeavouros": "endeavouros",
        "manjaro": "manjaro",
        "opensuse": "opensuse",
        "openSUSE": "opensuse",
        "suse": "opensuse",
    }
    return aliases.get(value, value or "auto")


def get_user_linux_preferences(profile: dict[str, Any]) -> dict[str, Any]:
    return profile.get("user_choices", {}).get("linux_preferences", {}) or {}


def recommend_distro(profile: dict[str, Any], requested_distro: str = "auto") -> dict[str, str]:
    flags = detect_flags(profile)
    prefs = get_user_linux_preferences(profile)

    requested = normalize_requested_distro(requested_distro)
    preferred = prefs.get("preferred_distros") or []
    avoid = [str(x).lower() for x in (prefs.get("avoid_distros") or [])]

    stability = str(prefs.get("stability_priority") or "").lower()
    gaming = bool(prefs.get("gaming_needed"))
    development = bool(prefs.get("development_needed"))
    ai_ml = bool(prefs.get("ai_ml_needed"))
    beginner = prefs.get("beginner_friendly")

    distro_map = {
        "ubuntu-lts": {
            "distro": "Ubuntu LTS",
            "edition": "Desktop",
            "config_type": "ubuntu-autoinstall",
            "status": "supported",
        },
        "debian": {
            "distro": "Debian",
            "edition": "Stable",
            "config_type": "debian-preseed",
            "status": "supported",
        },
        "fedora": {
            "distro": "Fedora",
            "edition": "Workstation",
            "config_type": "fedora-kickstart",
            "status": "supported",
        },
        "arch": {
            "distro": "Arch Linux",
            "edition": "Default",
            "config_type": "archinstall",
            "status": "supported",
        },
        "opensuse": {
            "distro": "openSUSE",
            "edition": "Leap/Tumbleweed depending on user preference",
            "config_type": "opensuse-autoyast",
            "status": "supported",
        },
        "popos": {
            "distro": "Pop!_OS",
            "edition": "NVIDIA edition" if flags["has_nvidia_gpu"] else "Standard edition",
            "config_type": "manifest-only",
            "status": "plan_only",
        },
        "linux-mint": {
            "distro": "Linux Mint",
            "edition": "Cinnamon",
            "config_type": "manifest-only",
            "status": "plan_only",
        },
        "endeavouros": {
            "distro": "EndeavourOS",
            "edition": "Default",
            "config_type": "manifest-only",
            "status": "plan_only",
        },
        "manjaro": {
            "distro": "Manjaro",
            "edition": "Default",
            "config_type": "manifest-only",
            "status": "plan_only",
        },
    }

    if requested != "auto":
        selected = distro_map.get(
            requested,
            {
                "distro": requested_distro,
                "edition": "user_selected",
                "config_type": "manifest-only",
                "status": "plan_only",
            },
        )
        return {**selected, "reason": "User explicitly selected this distribution.", "reliability_rank": "user_selected"}

    if preferred:
        first = normalize_requested_distro(str(preferred[0]))
        selected = distro_map.get(
            first,
            {"distro": str(preferred[0]), "edition": "user_preferred", "config_type": "manifest-only", "status": "plan_only"},
        )
        return {**selected, "reason": "Using the first user-preferred distribution.", "reliability_rank": "user_preferred"}

    if "ubuntu" not in " ".join(avoid):
        if flags["has_nvidia_gpu"]:
            reason = (
                "Reliability-first default for this hardware. Ubuntu LTS has broad hardware support, "
                "strong documentation, an official autoinstall workflow, and a known NVIDIA driver path."
            )
        elif flags["has_intel_vmd_or_rst"]:
            reason = (
                "Reliability-first default. Ubuntu LTS has broad hardware support and is a practical "
                "first target for systems with Intel VMD/RST, but storage visibility must still be checked."
            )
        elif "maximum_stability" in stability:
            reason = "Reliability-first default for stable releases and broad support."
        elif gaming or development or ai_ml or beginner is True:
            reason = (
                "Reliability-first default that balances stability, hardware support, documentation, "
                "and software availability."
            )
        else:
            reason = "Default reliability-first recommendation."

        return {
            "distro": "Ubuntu LTS",
            "edition": "Desktop",
            "config_type": "ubuntu-autoinstall",
            "status": "supported",
            "reason": reason,
            "reliability_rank": "first",
        }

    return {
        "distro": "Linux Mint",
        "edition": "Cinnamon",
        "config_type": "manifest-only",
        "status": "plan_only",
        "reason": "Ubuntu was avoided by user preference, so Linux Mint is the next beginner-friendly stable option.",
        "reliability_rank": "fallback",
    }


def get_external_devices(profile: dict[str, Any]) -> list[dict[str, Any]]:
    external = profile.get("user_choices", {}).get("external_devices", {})
    if not isinstance(external, dict):
        return []
    devices = external.get("devices", [])
    if not isinstance(devices, list):
        return []
    result: list[dict[str, Any]] = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        if device.get("name") or device.get("brand") or device.get("device_type"):
            result.append(device)
    return result


def choose_external_device_packages(profile: dict[str, Any], distro: str) -> list[str]:
    devices = get_external_devices(profile)
    distro = normalize_requested_distro(distro)
    packages: list[str] = []

    apt_like = distro in {"ubuntu-lts", "debian", "linux-mint", "popos", "ubuntu"}
    fedora_like = distro == "fedora"
    arch_like = distro == "arch"
    opensuse_like = distro == "opensuse"

    for device in devices:
        text = " ".join(
            str(device.get(k, ""))
            for k in ["name", "brand", "device_type", "connection", "user_notes"]
        ).lower()

        if "wacom" in text or "drawing_tablet" in text or "drawing tablet" in text:
            if apt_like:
                packages.extend(["xserver-xorg-input-wacom", "libwacom-bin"])
            elif fedora_like:
                packages.extend(["xorg-x11-drv-wacom", "libwacom"])
            elif arch_like:
                packages.extend(["xf86-input-wacom", "libwacom"])
            elif opensuse_like:
                packages.extend(["xf86-input-wacom", "libwacom-tools"])

        if "printer" in text or "brother" in text or "hp" in text or "canon" in text or "epson" in text:
            packages.extend(["cups", "system-config-printer"])

        if "scanner" in text:
            packages.extend(["simple-scan", "sane-airscan"])

        if "xbox" in text or "game_controller" in text or "game controller" in text:
            if apt_like:
                packages.extend(["joystick", "jstest-gtk"])
            else:
                packages.extend(["jstest-gtk"])

        if "usb_audio_interface" in text or "audio interface" in text:
            packages.extend(["alsa-utils", "pavucontrol"])

        if "logitech" in text and ("mouse" in text or "keyboard" in text):
            packages.extend(["solaar"])

    return sorted(set(packages))


def choose_packages(profile: dict[str, Any], distro_key: str) -> list[str]:
    flags = detect_flags(profile)
    distro_key = normalize_requested_distro(distro_key)

    if distro_key == "auto":
        recommended = recommend_distro(profile, "auto")
        distro_name = recommended["distro"].lower()
    else:
        distro_name = distro_key

    if "ubuntu" in distro_name:
        packages = [
            "linux-firmware", "mokutil", "inxi", "pciutils", "usbutils",
            "curl", "wget", "git", "pipewire", "wireplumber", "pavucontrol", "bluez",
        ]
        if flags["has_nvidia_gpu"]:
            packages.extend(["nvidia-prime", "mesa-utils", "vulkan-tools"])
        if flags["has_bluetooth"]:
            packages.append("blueman")
        packages.extend(choose_external_device_packages(profile, "ubuntu"))
        return sorted(set(packages))

    if "debian" in distro_name:
        packages = [
            "linux-firmware", "pciutils", "usbutils", "curl", "wget", "git",
            "pipewire", "wireplumber", "bluez",
        ]
        if flags["has_nvidia_gpu"]:
            packages.extend(["nvidia-driver", "vulkan-tools", "mesa-utils"])
        if flags["has_intel_wifi"]:
            packages.append("firmware-iwlwifi")
        if flags["has_realtek_wifi"]:
            packages.append("firmware-realtek")
        packages.extend(choose_external_device_packages(profile, "debian"))
        return sorted(set(packages))

    if "fedora" in distro_name:
        packages = [
            "linux-firmware", "pciutils", "usbutils", "curl", "wget", "git",
            "pipewire", "wireplumber", "bluez",
        ]
        if flags["has_nvidia_gpu"]:
            packages.extend(["akmod-nvidia", "xorg-x11-drv-nvidia-cuda"])
        packages.extend(choose_external_device_packages(profile, "fedora"))
        return sorted(set(packages))

    if "arch" in distro_name:
        packages = [
            "linux-firmware", "pciutils", "usbutils", "curl", "wget", "git",
            "pipewire", "wireplumber", "bluez", "bluez-utils",
        ]
        if flags["has_nvidia_gpu"]:
            packages.extend(["nvidia", "nvidia-utils", "vulkan-tools"])
        packages.extend(choose_external_device_packages(profile, "arch"))
        return sorted(set(packages))

    if "opensuse" in distro_name:
        packages = [
            "kernel-firmware-all", "pciutils", "usbutils", "curl", "wget", "git",
            "pipewire", "wireplumber", "bluez",
        ]
        if flags["has_nvidia_gpu"]:
            packages.extend(["vulkan-tools"])
        packages.extend(choose_external_device_packages(profile, "opensuse"))
        return sorted(set(packages))

    return []


def build_warnings(profile: dict[str, Any]) -> list[str]:
    flags = detect_flags(profile)
    warnings = [
        "This is a boot/install configuration draft, not a bootable ISO.",
        "This script does not write to USB drives and does not modify disks.",
        "Storage and partitioning are intentionally omitted.",
    ]
    if flags["has_nvidia_gpu"]:
        warnings.append(
            "NVIDIA GPU detected. Confirm proprietary driver needs, Secure Boot state, "
            "hybrid graphics, gaming, external monitor, and CUDA/AI requirements."
        )
    if flags["has_intel_vmd_or_rst"]:
        warnings.append(
            "Intel VMD/RST detected. Some installers may not see NVMe storage. "
            "Changing BIOS storage mode can break existing Windows boot."
        )
    if flags["has_realtek_wifi"]:
        warnings.append(
            "Realtek Wi-Fi detected. Exact chipset support should be verified before relying on Wi-Fi during installation."
        )
    if flags["has_mediatek_wifi"]:
        warnings.append(
            "MediaTek Wi-Fi detected. Use a distro with a recent kernel and firmware."
        )
    if get_external_devices(profile):
        warnings.append(
            "User-provided external devices were included. Extra driver packages should be reviewed before final media creation."
        )
    warnings.append(
        "Before generating real bootable media, confirm target disk, backup status, dual boot, "
        "encryption, Secure Boot, and whether data may be erased."
    )
    return warnings


def build_hardware_summary(profile: dict[str, Any]) -> str:
    sections = [
        ("GPUs", "gpus"), ("Wi-Fi", "wifi_adapters"), ("Ethernet", "ethernet_adapters"),
        ("Bluetooth", "bluetooth_devices"), ("Audio", "audio_devices"),
        ("Storage", "storage_devices"), ("Touchpads", "touchpads"),
        ("Cameras", "cameras"), ("Input devices", "input_devices"),
    ]
    lines: list[str] = []
    for title, key in sections:
        lines.append(f"## {title}")
        items = get_hardware_items(profile, key)
        if not items:
            lines.append("- Not detected or not provided")
            lines.append("")
            continue
        for item in items:
            name = (
                item.get("user_corrected_name")
                or item.get("component_name")
                or item.get("detected_name")
                or "Unknown"
            )
            driver = item.get("driver") or "no driver info"
            source = item.get("source") or "unknown source"
            lines.append(f"- {name} | driver: {driver} | source: {source}")
        lines.append("")
    return "\n".join(lines).strip()


def build_external_devices_summary(profile: dict[str, Any]) -> str:
    devices = get_external_devices(profile)
    if not devices:
        return "No user-provided external devices."
    lines = []
    for device in devices:
        name = device.get("name") or "Unknown external device"
        brand = device.get("brand") or "unknown brand"
        dtype = device.get("device_type") or "unknown type"
        connection = device.get("connection") or "unknown connection"
        required = device.get("required_for_install", False)
        needs_driver = device.get("needs_driver")
        notes = device.get("user_notes") or ""
        lines.append(
            f"- {brand} {name} | type: {dtype} | connection: {connection} | "
            f"required_for_install: {required} | needs_driver: {needs_driver} | notes: {notes}"
        )
    return "\n".join(lines)


def build_ubuntu_autoinstall(profile: dict[str, Any], args: argparse.Namespace) -> dict[str, str]:
    packages = choose_packages(profile, "ubuntu-lts")
    package_lines = "\n".join(f"    - {pkg}" for pkg in packages)

    hostname = args.hostname or "CHANGE_ME_HOSTNAME"
    username = args.username or "CHANGE_ME_USERNAME"
    password_hash = args.password_hash or "CHANGE_ME_PASSWORD_HASH"

    content = f"""#cloud-config
#
# LinuxAI Ubuntu autoinstall DRAFT
# Generated at: {now_utc()}
#
# Storage/partitioning is intentionally omitted.
#
autoinstall:
  version: 1

  locale: {args.locale}
  keyboard:
    layout: {args.keyboard}

  identity:
    hostname: {hostname}
    username: {username}
    password: {password_hash}

  ssh:
    install-server: false

  updates: security

  drivers:
    install: true

  packages:
{package_lines}

  late-commands:
    - curtin in-target --target=/target -- bash -lc 'echo LinuxAI install config draft completed > /root/linuxai-install-note.txt'

  # Storage is intentionally omitted.
  # Do not add storage layout until target disk, backup status, dual boot,
  # encryption, Secure Boot, and erase permissions are confirmed.
"""

    meta = f"""instance-id: linuxai-{safe_slug(args.profile_id)}
local-hostname: {hostname}
"""

    assert_no_destructive_content(content)
    assert_no_destructive_content(meta)
    return {"user-data": content, "meta-data": meta}


def build_debian_preseed(profile: dict[str, Any], args: argparse.Namespace) -> dict[str, str]:
    packages = choose_packages(profile, "debian")
    package_line = " ".join(packages)
    hostname = args.hostname or "CHANGE_ME_HOSTNAME"
    username = args.username or "CHANGE_ME_USERNAME"

    content = f"""# LinuxAI Debian preseed DRAFT
# Generated at: {now_utc()}
#
# Storage/partitioning is intentionally omitted.
#
d-i debian-installer/locale string {args.locale}
d-i keyboard-configuration/xkb-keymap select {args.keyboard}

d-i netcfg/get_hostname string {hostname}
d-i netcfg/get_domain string local

d-i passwd/user-fullname string {username}
d-i passwd/username string {username}

tasksel tasksel/first multiselect standard, desktop
d-i pkgsel/include string {package_line}
d-i pkgsel/upgrade select safe-upgrade

popularity-contest popularity-contest/participate boolean false

# Storage is intentionally omitted.
"""

    assert_no_destructive_content(content)
    return {"preseed.cfg": content}


def build_fedora_kickstart(profile: dict[str, Any], args: argparse.Namespace) -> dict[str, str]:
    packages = choose_packages(profile, "fedora")
    package_lines = "\n".join(packages)
    hostname = args.hostname or "CHANGE_ME_HOSTNAME"
    username = args.username or "CHANGE_ME_USERNAME"

    content = f"""# LinuxAI Fedora Kickstart DRAFT
# Generated at: {now_utc()}
#
# Storage/partitioning is intentionally omitted.
#
lang {args.locale}
keyboard {args.keyboard}
timezone UTC --utc

network --bootproto=dhcp --hostname={hostname}

rootpw --lock
user --name={username} --groups=wheel

services --enabled=NetworkManager,bluetooth

%packages
@^workstation-product-environment
{package_lines}
%end

%post
echo "LinuxAI install config draft completed" > /root/linuxai-install-note.txt
%end

# Storage is intentionally omitted.
"""

    assert_no_destructive_content(content)
    return {"kickstart.ks": content}


def build_archinstall_config(profile: dict[str, Any], args: argparse.Namespace) -> dict[str, str]:
    packages = choose_packages(profile, "arch")
    hostname = args.hostname or "CHANGE_ME_HOSTNAME"
    username = args.username or "CHANGE_ME_USERNAME"

    config = {
        "_linuxai_notice": "DRAFT only. Storage/disk_config is intentionally omitted.",
        "hostname": hostname,
        "locale_config": {"kb_layout": args.keyboard, "sys_lang": args.locale},
        "network_config": {"type": "nm"},
        "profile_config": {"profile": {"main": "Desktop", "details": ["GNOME"]}},
        "packages": packages,
        "users": [{"username": username, "sudo": True}],
        "services": ["NetworkManager", "bluetooth"],
    }

    content = json.dumps(config, ensure_ascii=False, indent=2)
    assert_no_destructive_content(content)
    return {"archinstall-user-configuration.json": content}


def build_opensuse_autoyast(profile: dict[str, Any], args: argparse.Namespace) -> dict[str, str]:
    packages = choose_packages(profile, "opensuse")
    package_lines = "\n".join(f"      <package>{pkg}</package>" for pkg in packages)
    hostname = args.hostname or "CHANGE_ME_HOSTNAME"
    username = args.username or "CHANGE_ME_USERNAME"

    content = f"""<?xml version="1.0"?>
<!--
LinuxAI openSUSE AutoYaST DRAFT
Generated at: {now_utc()}

Storage/partitioning is intentionally omitted.
-->
<profile xmlns="http://www.suse.com/1.0/yast2ns"
         xmlns:config="http://www.suse.com/1.0/configns">

  <general>
    <mode>
      <confirm config:type="boolean">true</confirm>
    </mode>
  </general>

  <language>
    <language>{args.locale}</language>
  </language>

  <keyboard>
    <keymap>{args.keyboard}</keymap>
  </keyboard>

  <networking>
    <dns>
      <hostname>{hostname}</hostname>
    </dns>
  </networking>

  <users config:type="list">
    <user>
      <username>{username}</username>
      <fullname>{username}</fullname>
    </user>
  </users>

  <software>
    <packages config:type="list">
{package_lines}
    </packages>
  </software>

  <!--
  Storage is intentionally omitted.
  Do not add partitioning until target disk, backup status, dual boot,
  encryption, and erase permissions are confirmed.
  -->
</profile>
"""

    assert_no_destructive_content(content)
    return {"autoyast.xml": content}


def build_manifest(
    profile: dict[str, Any],
    args: argparse.Namespace,
    recommendation: dict[str, str],
    files: dict[str, str],
) -> dict[str, Any]:
    distro_key = normalize_requested_distro(args.distro)
    if distro_key == "auto":
        distro_key = normalize_requested_distro(recommendation["distro"])

    return {
        "schema_version": "0.1",
        "generated_at": now_utc(),
        "profile_id": args.profile_id,
        "requested_distro": args.distro,
        "recommended_distro": recommendation,
        "generated_file_names": sorted(files.keys()),
        "hardware_flags": detect_flags(profile),
        "external_devices": get_external_devices(profile),
        "packages": choose_packages(profile, distro_key),
        "warnings": build_warnings(profile),
        "safety": {
            "bootable_iso_created": False,
            "usb_written": False,
            "disk_modified": False,
            "storage_layout_generated": False,
            "destructive_commands_generated": False,
        },
        "next_stage": {
            "can_build_iso": False,
            "requires_user_review": True,
            "requires_iso_checksum_verification": True,
            "requires_target_disk_confirmation_for_storage": True,
            "requires_backup_confirmation_for_storage": True,
            "requires_storage_layout_before_unattended_install": True,
        },
    }


def build_readme(
    profile: dict[str, Any],
    args: argparse.Namespace,
    recommendation: dict[str, str],
    generated_files: dict[str, str],
) -> str:
    warnings = "\n".join(f"- {w}" for w in build_warnings(profile))
    hardware = build_hardware_summary(profile)
    external = build_external_devices_summary(profile)
    file_list = "\n".join(f"- `{name}`" for name in sorted(generated_files.keys()))

    content = f"""# LinuxAI boot/install configuration draft

Generated at: {now_utc()}

## Recommended distro

- Distro: {recommendation["distro"]}
- Edition: {recommendation["edition"]}
- Config type: {recommendation["config_type"]}
- Status: {recommendation["status"]}
- Reason: {recommendation["reason"]}
- Reliability rank: {recommendation["reliability_rank"]}

## Generated files

{file_list}
- `linuxai-boot-manifest.json`
- `profile_used.json`
- `README.md`

## Safety

{warnings}

## Hardware summary

{hardware}

## User-provided external devices

{external}

## Important

This folder does not contain a bootable ISO.
This script did not write to USB.
This script did not modify disks.
Storage and partitioning are intentionally omitted.
"""

    assert_no_destructive_content(content)
    return content


def generate_config_files(
    profile: dict[str, Any],
    args: argparse.Namespace,
    recommendation: dict[str, str],
) -> dict[str, str]:
    config_type = recommendation["config_type"]

    if config_type == "ubuntu-autoinstall":
        return build_ubuntu_autoinstall(profile, args)
    if config_type == "debian-preseed":
        return build_debian_preseed(profile, args)
    if config_type == "fedora-kickstart":
        return build_fedora_kickstart(profile, args)
    if config_type == "archinstall":
        return build_archinstall_config(profile, args)
    if config_type == "opensuse-autoyast":
        return build_opensuse_autoyast(profile, args)
    return {}


def validate_request(args: argparse.Namespace) -> None:
    if not args.allow_boot_config_files:
        raise PermissionError("Missing required flag: --allow-boot-config-files")
    if args.confirm != CONFIRMATION_PHRASE:
        raise PermissionError(
            f"Missing or wrong confirmation phrase. Required: {CONFIRMATION_PHRASE}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate gated Linux boot/install configuration draft files."
    )
    parser.add_argument("--profile", required=True, help="Path to frontend profile JSON.")
    parser.add_argument("--distro", default="auto")
    parser.add_argument("--hostname", default="CHANGE_ME_HOSTNAME")
    parser.add_argument("--username", default="CHANGE_ME_USERNAME")
    parser.add_argument("--password-hash", default="CHANGE_ME_PASSWORD_HASH")
    parser.add_argument("--locale", default="en_US.UTF-8")
    parser.add_argument("--keyboard", default="us")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--allow-boot-config-files", action="store_true")
    parser.add_argument("--confirm", default="")

    args = parser.parse_args()

    try:
        validate_request(args)

        profile_path = Path(args.profile).resolve()
        profile = load_json(profile_path)
        validate_frontend_profile(profile)

        args.profile_id = profile.get("profile_id") or "unknown_profile"

        recommendation = recommend_distro(profile, args.distro)
        profile_id = safe_slug(args.profile_id)
        distro_slug = safe_slug(recommendation["distro"])

        if args.output_dir:
            output_dir = Path(args.output_dir).resolve()
        else:
            output_dir = OUTPUT_ROOT / profile_id / distro_slug

        dangerous_dirs = {
            Path(".").resolve(),
            PROJECT_ROOT.resolve(),
            PROJECT_ROOT.parent.resolve(),
            Path("/").resolve(),
        }

        if output_dir.resolve() in dangerous_dirs:
            raise RuntimeError(f"Refusing to use dangerous output directory: {output_dir}")

        if output_dir.exists():
            if not args.overwrite:
                raise FileExistsError(
                    f"Output directory already exists: {output_dir}. Use --overwrite to replace it."
                )
            shutil.rmtree(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        generated_files = generate_config_files(profile, args, recommendation)
        manifest = build_manifest(profile, args, recommendation, generated_files)
        readme = build_readme(profile, args, recommendation, generated_files)

        files = {
            **generated_files,
            "linuxai-boot-manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2),
            "profile_used.json": json.dumps(profile, ensure_ascii=False, indent=2),
            "README.md": readme,
        }

        for filename, content in files.items():
            assert_no_destructive_content(content)
            (output_dir / filename).write_text(content, encoding="utf-8")

        print("Boot/install configuration draft files generated successfully.")
        print(f"Output directory: {output_dir}")
        print()
        print("Recommendation:")
        print(f"  Distro: {recommendation['distro']}")
        print(f"  Edition: {recommendation['edition']}")
        print(f"  Config type: {recommendation['config_type']}")
        print(f"  Status: {recommendation['status']}")
        print(f"  Reason: {recommendation['reason']}")
        print()
        print("Files:")
        for filename in sorted(files.keys()):
            print(f"- {output_dir / filename}")

        if recommendation["status"] != "supported":
            print()
            print("Note: This distro currently has manifest-only support in this script.")

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
