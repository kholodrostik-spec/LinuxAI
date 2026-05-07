"""
scripts/prepare_iso_workspace.py

Prepares a LinuxAI ISO workspace from already generated and validated
boot/install configuration draft files.

Important:
  - This is NOT an ISO builder.
  - This does NOT download ISO files.
  - This does NOT write to USB.
  - This does NOT modify disks.
  - This does NOT create storage/partitioning/wipe layouts.
  - This only prepares a safe workspace folder for a later ISO-building step.

Input:
  generated/boot_configs/<profile_id>/<distro_slug>/

Output:
  generated/iso_workspaces/<profile_id>/<distro_slug>/
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

BOOT_CONFIG_ROOT = PROJECT_ROOT / "generated" / "boot_configs"
ISO_WORKSPACE_ROOT = PROJECT_ROOT / "generated" / "iso_workspaces"

CONFIRMATION_PHRASE = "I_UNDERSTAND_ISO_WORKSPACE_IS_NOT_A_BOOTABLE_ISO"

BLOCKED_FILE_SUFFIXES = {".iso", ".img", ".raw", ".qcow2", ".vdi", ".vmdk"}

DESTRUCTIVE_PATTERNS = [
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

DANGEROUS_INSTALLER_DIRECTIVES = [
    r"(^|\n)\s*storage\s*:",
    r"(^|\n)\s*wipe\s*:",
    r"(^|\n)\s*grub\s*:",
    r"(^|\n)\s*clearpart\b",
    r"(^|\n)\s*autopart\b",
    r"(^|\n)\s*part\s+",
    r"(^|\n)\s*partition\s+",
    r"(^|\n)\s*ignoredisk\b",
    r"(^|\n)\s*bootloader\b",
    r"partman-auto",
    r"partman/confirm",
    r"partman-auto/disk",
    r"partman-auto/method",
    r"partman-auto/choose_recipe",
    r"partman-lvm",
    r"partman-crypto",
    r'"disk_config"\s*:',
    r'"disk_layouts"\s*:',
    r'"mountpoint"\s*:',
    r'"wipe"\s*:',
    r"<partitioning",
    r"<drive>",
    r"<initialize\b",
]

SAFE_MANIFEST_FLAGS = {
    "bootable_iso_created": False,
    "usb_written": False,
    "disk_modified": False,
    "storage_layout_generated": False,
    "destructive_commands_generated": False,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_slug(text: str) -> str:
    text = str(text).strip().lower()
    text = re.sub(r"[^a-z0-9_.-]+", "_", text)
    return text.strip("_") or "unknown"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def strip_common_comments(text: str) -> str:
    cleaned_lines: list[str] = []
    in_xml_comment = False

    for line in text.splitlines():
        stripped = line.strip()

        if in_xml_comment:
            if "-->" in stripped:
                in_xml_comment = False
            continue

        if stripped.startswith("<!--"):
            if "-->" not in stripped:
                in_xml_comment = True
            continue

        if stripped.startswith("#"):
            continue

        if stripped.startswith("//"):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def assert_no_patterns(text: str, patterns: list[str], label: str) -> None:
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise RuntimeError(f"{label}: blocked pattern found: {pattern}")


def assert_safe_text_file(path: Path) -> None:
    text = read_text(path)
    uncommented = strip_common_comments(text)
    assert_no_patterns(text, DESTRUCTIVE_PATTERNS, path.name)
    assert_no_patterns(uncommented, DANGEROUS_INSTALLER_DIRECTIVES, path.name)


def validate_source_dir(source_dir: Path) -> dict[str, Any]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Boot config directory not found: {source_dir}")

    if not source_dir.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {source_dir}")

    manifest_path = source_dir / "linuxai-boot-manifest.json"
    profile_path = source_dir / "profile_used.json"
    readme_path = source_dir / "README.md"

    if not manifest_path.exists():
        raise FileNotFoundError("Missing linuxai-boot-manifest.json")
    if not profile_path.exists():
        raise FileNotFoundError("Missing profile_used.json")
    if not readme_path.exists():
        raise FileNotFoundError("Missing README.md")

    manifest = load_json(manifest_path)

    safety = manifest.get("safety")
    if not isinstance(safety, dict):
        raise RuntimeError("Manifest missing safety object.")

    for key, expected in SAFE_MANIFEST_FLAGS.items():
        actual = safety.get(key)
        if actual is not expected:
            raise RuntimeError(
                f"Unsafe manifest flag: {key} should be {expected}, got {actual}"
            )

    for path in source_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() in BLOCKED_FILE_SUFFIXES:
            raise RuntimeError(f"Blocked image/ISO-like file in config dir: {path.name}")
        assert_safe_text_file(path)

    return manifest


def detect_config_files(source_dir: Path) -> list[Path]:
    known_names = [
        "user-data", "meta-data", "preseed.cfg", "kickstart.ks",
        "archinstall-user-configuration.json", "autoyast.xml",
    ]
    result: list[Path] = []
    for name in known_names:
        path = source_dir / name
        if path.exists() and path.is_file():
            result.append(path)
    return result


def build_workspace_status(
    source_dir: Path,
    output_dir: Path,
    manifest: dict[str, Any],
    copied_config_files: list[Path],
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "created_at": now_utc(),
        "source_boot_config_dir": str(source_dir),
        "workspace_dir": str(output_dir),
        "profile_id": manifest.get("profile_id"),
        "recommended_distro": manifest.get("recommended_distro"),
        "generated_file_names": [path.name for path in copied_config_files],
        "safety": {
            "bootable_iso_created": False,
            "usb_written": False,
            "disk_modified": False,
            "storage_layout_generated": False,
            "destructive_commands_generated": False,
            "iso_downloaded": False,
            "iso_modified": False,
        },
        "next_stage": {
            "can_download_iso": False,
            "can_build_iso": False,
            "requires_official_iso_url": True,
            "requires_checksum_verification": True,
            "requires_user_review": True,
            "requires_storage_confirmation_for_unattended_install": True,
        },
    }


def build_checklist(manifest: dict[str, Any]) -> str:
    distro = manifest.get("recommended_distro", {}).get("distro", "Unknown distro")
    config_type = manifest.get("recommended_distro", {}).get("config_type", "unknown")

    return f"""# Checklist before ISO build

Distro: {distro}
Config type: {config_type}

Before any ISO build step, confirm:

- Official ISO URL is selected.
- ISO checksum URL is selected.
- ISO checksum is verified from an official source.
- User reviewed all generated config files.
- User understands this workspace is not a bootable ISO.
- User understands no USB has been written.
- User understands no disk has been modified.
- Target disk is NOT guessed.
- Backup status is confirmed.
- Dual boot requirement is confirmed.
- Encryption preference is confirmed.
- Secure Boot preference is confirmed.
- Storage/partitioning layout is still omitted unless explicitly confirmed later.

Current safety state:

- bootable_iso_created: false
- usb_written: false
- disk_modified: false
- storage_layout_generated: false
- destructive_commands_generated: false

Do not proceed to a real ISO builder unless the next script performs checksum verification and safety checks again.
"""


def build_readme(manifest: dict[str, Any]) -> str:
    distro = manifest.get("recommended_distro", {}).get("distro", "Unknown distro")
    config_type = manifest.get("recommended_distro", {}).get("config_type", "unknown")

    return f"""# LinuxAI ISO workspace

This workspace was prepared from validated LinuxAI boot/install configuration draft files.

Distro: {distro}
Config type: {config_type}

## What this is

This is a workspace folder for a later ISO preparation/build step.

## What this is not

This is not a bootable ISO.
This is not a USB image.
This did not write to USB.
This did not modify disks.
This does not contain storage/partitioning/wipe layout.

## Folders

- `config/` — copied boot/install config draft files
- `profile/` — copied hardware profile
- `manifests/` — copied and generated manifests

## Next safe step

The next step should be an ISO download / checksum verification workspace, not USB writing.
"""


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def prepare_workspace(source_dir: Path, output_dir: Path, overwrite: bool) -> Path:
    manifest = validate_source_dir(source_dir)

    dangerous_dirs = {
        Path(".").resolve(),
        PROJECT_ROOT.resolve(),
        PROJECT_ROOT.parent.resolve(),
        Path("/").resolve(),
    }

    if output_dir.resolve() in dangerous_dirs:
        raise RuntimeError(f"Refusing to use dangerous output directory: {output_dir}")

    if output_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"Output workspace already exists: {output_dir}. Use --overwrite to replace it."
            )
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    config_dir   = output_dir / "config"
    profile_dir  = output_dir / "profile"
    manifests_dir = output_dir / "manifests"

    config_dir.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    config_files = detect_config_files(source_dir)

    for src in config_files:
        copy_file(src, config_dir / src.name)

    copy_file(source_dir / "profile_used.json",           profile_dir  / "profile_used.json")
    copy_file(source_dir / "linuxai-boot-manifest.json",  manifests_dir / "linuxai-boot-manifest.json")
    copy_file(source_dir / "README.md",                   manifests_dir / "BOOT_CONFIG_README.md")

    workspace_status = build_workspace_status(
        source_dir=source_dir,
        output_dir=output_dir,
        manifest=manifest,
        copied_config_files=config_files,
    )

    write_json(manifests_dir / "WORKSPACE_STATUS.json", workspace_status)

    (output_dir / "CHECKLIST_BEFORE_ISO_BUILD.md").write_text(
        build_checklist(manifest), encoding="utf-8"
    )

    (output_dir / "README.md").write_text(
        build_readme(manifest), encoding="utf-8"
    )

    for path in output_dir.rglob("*"):
        if path.is_file():
            if path.suffix.lower() in BLOCKED_FILE_SUFFIXES:
                raise RuntimeError(f"Blocked image/ISO-like file created: {path}")
            assert_safe_text_file(path)

    return output_dir


def latest_boot_config_dir() -> Path:
    manifests = sorted(
        BOOT_CONFIG_ROOT.glob("*/*/linuxai-boot-manifest.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not manifests:
        raise FileNotFoundError(f"No boot config manifests found under {BOOT_CONFIG_ROOT}")

    return manifests[0].parent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a safe LinuxAI ISO workspace from generated boot config files."
    )
    parser.add_argument("--source", default="", help="Boot config directory.")
    parser.add_argument("--output-dir", default="", help="Output workspace directory.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--allow-iso-workspace", action="store_true", help="Required safety gate.")
    parser.add_argument("--confirm", default="", help=f"Required confirmation phrase: {CONFIRMATION_PHRASE}")

    args = parser.parse_args()

    try:
        if not args.allow_iso_workspace:
            raise PermissionError("Missing required flag: --allow-iso-workspace")

        if args.confirm != CONFIRMATION_PHRASE:
            raise PermissionError(
                f"Missing or wrong confirmation phrase. Required: {CONFIRMATION_PHRASE}"
            )

        if args.source:
            source_dir = Path(args.source).resolve()
        else:
            source_dir = latest_boot_config_dir().resolve()

        manifest = validate_source_dir(source_dir)
        profile_id  = safe_slug(manifest.get("profile_id", "unknown_profile"))
        distro_name = manifest.get("recommended_distro", {}).get("distro", "unknown_distro")
        distro_slug = safe_slug(distro_name)

        if args.output_dir:
            output_dir = Path(args.output_dir).resolve()
        else:
            output_dir = ISO_WORKSPACE_ROOT / profile_id / distro_slug

        workspace = prepare_workspace(
            source_dir=source_dir,
            output_dir=output_dir,
            overwrite=args.overwrite,
        )

        print("ISO workspace prepared successfully.")
        print(f"Source:    {source_dir}")
        print(f"Workspace: {workspace}")
        print()
        print("Important:")
        print("  This is not a bootable ISO.")
        print("  No USB was written.")
        print("  No disk was modified.")
        print("  Storage/partitioning remains omitted.")
        print()
        print("Files:")
        for path in sorted(workspace.rglob("*")):
            if path.is_file():
                print(f"- {path}")

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
