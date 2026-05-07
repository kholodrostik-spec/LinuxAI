"""
scripts/generate_install_files.py

Gated generator for Linux installer draft files.

This script is intentionally separate from the normal chat/RAG assistant.
The normal assistant may explain installation steps and create safe install plans,
but should not generate full installer files directly in chat.

This script:
- requires explicit flags
- requires a confirmation phrase
- recommends a reliability-first Linux distro
- currently generates Ubuntu autoinstall draft files only
- does not write to USB
- does not create ISO images
- does not generate partitioning/storage layout
- only writes draft config files into generated/installers/<profile_id>/

Generated files:
- user-data.template.yaml
- meta-data
- README.md
- linuxai-manifest.json
- profile_used.json
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
OUTPUT_ROOT = PROJECT_ROOT / "generated" / "installers"

CONFIRMATION_PHRASE = "I_UNDERSTAND_INSTALLER_FILES_ARE_DANGEROUS"

SUPPORTED_INSTALLERS = ["ubuntu-autoinstall"]

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

    return [item for item in items if isinstance(item, dict) and item.get("selected", True)]


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
            for k in [
                "component_name",
                "detected_name",
                "vendor",
                "driver",
                "pci_id",
                "usb_id",
            ]
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


def get_user_linux_preferences(profile: dict[str, Any]) -> dict[str, Any]:
    return profile.get("user_choices", {}).get("linux_preferences", {}) or {}


def normalize_requested_distro(value: str) -> str:
    value = value.strip().lower()

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
        "endeavouros": "endeavouros",
        "manjaro": "manjaro",
        "opensuse": "opensuse",
        "openSUSE": "opensuse",
    }

    return aliases.get(value, value or "auto")


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
    battery = bool(prefs.get("battery_life_priority"))

    distro_map = {
        "ubuntu-lts": {
            "distro": "Ubuntu LTS",
            "edition": "Desktop",
            "installer": "ubuntu-autoinstall",
        },
        "popos": {
            "distro": "Pop!_OS",
            "edition": "NVIDIA edition" if flags["has_nvidia_gpu"] else "Standard edition",
            "installer": "plan-only",
        },
        "linux-mint": {
            "distro": "Linux Mint",
            "edition": "Cinnamon",
            "installer": "plan-only",
        },
        "fedora": {
            "distro": "Fedora",
            "edition": "Workstation",
            "installer": "plan-only",
        },
        "debian": {
            "distro": "Debian",
            "edition": "Stable",
            "installer": "plan-only",
        },
        "arch": {
            "distro": "Arch Linux",
            "edition": "Default",
            "installer": "plan-only",
        },
        "endeavouros": {
            "distro": "EndeavourOS",
            "edition": "Default",
            "installer": "plan-only",
        },
        "manjaro": {
            "distro": "Manjaro",
            "edition": "Default",
            "installer": "plan-only",
        },
        "opensuse": {
            "distro": "openSUSE",
            "edition": "Leap/Tumbleweed depending on user preference",
            "installer": "plan-only",
        },
    }

    if requested != "auto":
        selected = distro_map.get(
            requested,
            {
                "distro": requested_distro,
                "edition": "user_selected",
                "installer": "plan-only",
            },
        )
        return {
            **selected,
            "reason": "User explicitly selected this distribution.",
            "reliability_rank": "user_selected",
        }

    if preferred:
        first = normalize_requested_distro(str(preferred[0]))
        selected = distro_map.get(
            first,
            {
                "distro": str(preferred[0]),
                "edition": "user_preferred",
                "installer": "plan-only",
            },
        )
        return {
            **selected,
            "reason": "Using the first user-preferred distribution.",
            "reliability_rank": "user_preferred",
        }

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
        elif gaming or development or ai_ml or battery:
            reason = (
                "Reliability-first default that balances stability, hardware support, and software availability."
            )
        else:
            reason = "Default reliability-first recommendation."

        return {
            "distro": "Ubuntu LTS",
            "edition": "Desktop",
            "installer": "ubuntu-autoinstall",
            "reason": reason,
            "reliability_rank": "first",
        }

    return {
        "distro": "Linux Mint",
        "edition": "Cinnamon",
        "installer": "plan-only",
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
    distro_lower = distro.lower()
    packages: list[str] = []

    apt_like = any(x in distro_lower for x in ["ubuntu", "pop", "mint", "debian"])

    for device in devices:
        text = " ".join(
            str(device.get(k, ""))
            for k in ["name", "brand", "device_type", "connection", "user_notes"]
        ).lower()

        if not apt_like:
            continue

        if "wacom" in text or "drawing_tablet" in text or "drawing tablet" in text:
            packages.extend(["xserver-xorg-input-wacom", "libwacom-bin"])

        if "printer" in text or "brother" in text or "hp" in text or "canon" in text or "epson" in text:
            packages.extend(["cups", "system-config-printer"])

        if "scanner" in text:
            packages.extend(["simple-scan", "sane-airscan"])

        if "xbox" in text or "game_controller" in text or "game controller" in text:
            packages.extend(["joystick", "jstest-gtk"])

        if "usb_audio_interface" in text or "audio interface" in text:
            packages.extend(["alsa-utils", "pavucontrol"])

        if "logitech" in text and ("mouse" in text or "keyboard" in text):
            packages.extend(["solaar"])

    return sorted(set(packages))


def choose_ubuntu_packages(profile: dict[str, Any]) -> list[str]:
    flags = detect_flags(profile)

    packages = [
        "linux-firmware",
        "mokutil",
        "inxi",
        "pciutils",
        "usbutils",
        "curl",
        "wget",
        "git",
        "pipewire",
        "wireplumber",
        "pavucontrol",
        "bluez",
    ]

    if flags["has_nvidia_gpu"]:
        packages.extend(["nvidia-prime", "mesa-utils", "vulkan-tools"])

    if flags["has_bluetooth"]:
        packages.append("blueman")

    packages.extend(choose_external_device_packages(profile, "Ubuntu LTS"))

    return sorted(set(packages))


def build_hardware_summary(profile: dict[str, Any]) -> str:
    hardware = profile.get("hardware", {})

    sections = [
        ("GPUs", "gpus"),
        ("Wi-Fi", "wifi_adapters"),
        ("Ethernet", "ethernet_adapters"),
        ("Bluetooth", "bluetooth_devices"),
        ("Audio", "audio_devices"),
        ("Storage", "storage_devices"),
        ("Touchpads", "touchpads"),
        ("Cameras", "cameras"),
        ("Input devices", "input_devices"),
    ]

    lines: list[str] = []

    for title, key in sections:
        lines.append(f"## {title}")
        items = hardware.get(key, [])

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


def build_warnings(profile: dict[str, Any]) -> list[str]:
    flags = detect_flags(profile)
    warnings = [
        "This is a draft installer configuration, not a bootable ISO.",
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
            "External user-provided devices were included in the manifest. "
            "Any extra driver packages should be reviewed before creating final installer media."
        )

    warnings.append(
        "Before generating real bootable media, confirm target disk, backup status, dual boot, "
        "encryption, Secure Boot, and whether data may be erased."
    )

    return warnings


def build_manifest(profile: dict[str, Any], requested_distro: str, installer_type: str) -> dict[str, Any]:
    recommended = recommend_distro(profile, requested_distro)

    return {
        "schema_version": "0.2",
        "generated_at": now_utc(),
        "profile_id": profile.get("profile_id"),
        "requested_distro": requested_distro,
        "recommended_distro": recommended,
        "installer_type": installer_type,
        "supported_installer_generated": installer_type == "ubuntu-autoinstall",
        "hardware_flags": detect_flags(profile),
        "external_devices": get_external_devices(profile),
        "ubuntu_packages": choose_ubuntu_packages(profile),
        "warnings": build_warnings(profile),
        "safety": {
            "bootable_iso_created": False,
            "usb_written": False,
            "disk_modified": False,
            "storage_layout_generated": False,
            "destructive_commands_generated": False,
        },
        "next_stage": {
            "can_finalize_user_data_without_storage": True,
            "can_build_iso": False,
            "requires_target_disk_confirmation_for_storage": True,
            "requires_backup_confirmation_for_storage": True,
            "requires_user_review": True,
        },
    }


def build_ubuntu_user_data_template(profile: dict[str, Any]) -> str:
    packages = choose_ubuntu_packages(profile)
    package_lines = "\n".join(f"    - {pkg}" for pkg in packages)

    content = f"""#cloud-config
#
# LinuxAI Ubuntu autoinstall DRAFT TEMPLATE
# Generated at: {now_utc()}
#
# This is intentionally not a final unattended installer.
# Storage/partitioning is intentionally omitted.
# Review linuxai-manifest.json and README.md before using this file.
#
autoinstall:
  version: 1

  locale: en_US.UTF-8
  keyboard:
    layout: us

  identity:
    hostname: CHANGE_ME_HOSTNAME
    username: CHANGE_ME_USERNAME
    # Use a SHA-512 password hash, not plain text.
    password: CHANGE_ME_PASSWORD_HASH

  ssh:
    install-server: false

  updates: security

  drivers:
    install: true

  packages:
{package_lines}

  late-commands:
    - curtin in-target --target=/target -- bash -lc 'echo LinuxAI draft install completed > /root/linuxai-install-note.txt'

  # Storage is intentionally omitted.
  # Do not add storage layout until target disk, backup status, dual boot,
  # encryption, Secure Boot, and erase permissions are confirmed.
"""

    assert_no_destructive_content(content)
    return content


def build_meta_data(profile: dict[str, Any]) -> str:
    profile_id = safe_slug(profile.get("profile_id", "unknown_profile"))

    content = f"""instance-id: linuxai-{profile_id}
local-hostname: linuxai-target
"""

    assert_no_destructive_content(content)
    return content


def build_readme(profile: dict[str, Any], requested_distro: str, installer_type: str) -> str:
    manifest = build_manifest(profile, requested_distro, installer_type)
    recommended = manifest["recommended_distro"]

    warnings = "\n".join(f"- {w}" for w in manifest["warnings"])
    hardware = build_hardware_summary(profile)
    external = build_external_devices_summary(profile)

    content = f"""# LinuxAI generated installer draft

Generated at: {now_utc()}

## Recommended distro

- Distro: {recommended["distro"]}
- Edition: {recommended["edition"]}
- Installer support: {recommended["installer"]}
- Reason: {recommended["reason"]}
- Reliability rank: {recommended["reliability_rank"]}

## Files

- `user-data.template.yaml`
- `meta-data`
- `linuxai-manifest.json`
- `profile_used.json`

## Safety

{warnings}

## Hardware summary

{hardware}

## User-provided external devices

{external}

## Important

The normal LinuxAI assistant should not generate full installer files directly in chat.
Use this gated script only after the user explicitly confirms installer-file generation.

This folder does not contain a bootable ISO.
This script did not write to USB.
This script did not modify disks.
Storage and partitioning are intentionally omitted.
"""

    assert_no_destructive_content(content)
    return content


def validate_request(args: argparse.Namespace) -> None:
    if not args.allow_installer_files:
        raise PermissionError("Missing required flag: --allow-installer-files")

    if args.confirm != CONFIRMATION_PHRASE:
        raise PermissionError(
            f"Missing or wrong confirmation phrase. Required: {CONFIRMATION_PHRASE}"
        )

    if args.installer not in SUPPORTED_INSTALLERS:
        raise ValueError(
            f"Unsupported installer: {args.installer}. Supported: {', '.join(SUPPORTED_INSTALLERS)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate gated installer draft files.")
    parser.add_argument("--profile", required=True, help="Path to frontend profile JSON.")
    parser.add_argument(
        "--installer",
        default="ubuntu-autoinstall",
        choices=SUPPORTED_INSTALLERS,
        help="Installer type.",
    )
    parser.add_argument(
        "--distro",
        default="auto",
        help="Target distro. Use 'auto' for reliability-first recommendation.",
    )
    parser.add_argument("--allow-installer-files", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--overwrite", action="store_true")

    args = parser.parse_args()

    try:
        validate_request(args)

        profile_path = Path(args.profile).resolve()
        profile = load_json(profile_path)
        validate_frontend_profile(profile)

        recommended = recommend_distro(profile, args.distro)

        if recommended["installer"] != "ubuntu-autoinstall":
            print(
                f"Warning: recommended distro is {recommended['distro']}, "
                "but this generator currently creates Ubuntu autoinstall draft files only. "
                "A manifest will record the recommendation.",
                file=sys.stderr,
            )

        profile_id = safe_slug(profile.get("profile_id", "unknown_profile"))

        if args.output_dir:
            output_dir = Path(args.output_dir).resolve()
        else:
            output_dir = OUTPUT_ROOT / profile_id / args.installer

        if output_dir.exists():
            if not args.overwrite:
                raise FileExistsError(
                    f"Output directory already exists: {output_dir}. Use --overwrite to replace it."
                )
            shutil.rmtree(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        manifest = build_manifest(profile, args.distro, args.installer)

        files = {
            "user-data.template.yaml": build_ubuntu_user_data_template(profile),
            "meta-data": build_meta_data(profile),
            "README.md": build_readme(profile, args.distro, args.installer),
            "linuxai-manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2),
            "profile_used.json": json.dumps(profile, ensure_ascii=False, indent=2),
        }

        for filename, content in files.items():
            assert_no_destructive_content(content)
            (output_dir / filename).write_text(content, encoding="utf-8")

        print("Installer draft files generated successfully.")
        print(f"Output directory: {output_dir}")
        print()
        print("Recommendation:")
        print(f"  Distro: {recommended['distro']}")
        print(f"  Edition: {recommended['edition']}")
        print(f"  Reason: {recommended['reason']}")
        print()
        print("Files:")
        for filename in files:
            print(f"- {output_dir / filename}")

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
