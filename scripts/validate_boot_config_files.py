"""
scripts/validate_boot_config_files.py

Validates LinuxAI generated boot/install configuration draft files.

It checks:
- required files exist
- manifest is valid JSON
- profile_used.json is valid JSON
- safety flags are safe
- no destructive commands are present
- Ubuntu user-data YAML is valid
- Arch config JSON is valid
- openSUSE AutoYaST XML is parseable
- Fedora Kickstart / Debian preseed do not contain storage wipe directives
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / "generated" / "boot_configs"


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
    r"(^|\n)\s*storage\s*:",
    r"(^|\n)\s*wipe\s*:",
    r"(^|\n)\s*grub\s*:",
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


class ValidationResult:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


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


def check_no_patterns(
    text: str,
    patterns: list[str],
    result: ValidationResult,
    label: str,
) -> None:
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            result.error(f"{label}: blocked pattern found: {pattern}")


def check_required_files(config_dir: Path, result: ValidationResult) -> None:
    required = ["README.md", "linuxai-boot-manifest.json", "profile_used.json"]
    for filename in required:
        if not (config_dir / filename).exists():
            result.error(f"Missing required file: {filename}")


def check_manifest(config_dir: Path, result: ValidationResult) -> dict[str, Any] | None:
    manifest_path = config_dir / "linuxai-boot-manifest.json"
    if not manifest_path.exists():
        return None

    try:
        manifest = load_json(manifest_path)
    except Exception as exc:
        result.error(f"Manifest is not valid JSON: {exc}")
        return None

    safety = manifest.get("safety")
    if not isinstance(safety, dict):
        result.error("Manifest missing safety object.")
        return manifest

    for key, expected in SAFE_MANIFEST_FLAGS.items():
        actual = safety.get(key)
        if actual is not expected:
            result.error(f"Manifest safety flag {key!r} should be {expected!r}, got {actual!r}.")

    generated_files = manifest.get("generated_file_names", [])
    if generated_files and not isinstance(generated_files, list):
        result.error("Manifest generated_file_names must be a list.")

    return manifest


def check_profile(config_dir: Path, result: ValidationResult) -> None:
    profile_path = config_dir / "profile_used.json"
    if not profile_path.exists():
        return

    try:
        profile = load_json(profile_path)
    except Exception as exc:
        result.error(f"profile_used.json is not valid JSON: {exc}")
        return

    if "hardware" not in profile:
        result.warning("profile_used.json does not contain hardware section.")
    if "user_choices" not in profile:
        result.warning("profile_used.json does not contain user_choices section.")


def check_all_text_files(config_dir: Path, result: ValidationResult) -> None:
    for path in config_dir.iterdir():
        if not path.is_file():
            continue

        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".iso", ".img"}:
            result.error(f"Binary/image/ISO-like file should not be here: {path.name}")
            continue

        text = read_text(path)
        uncommented_text = strip_common_comments(text)

        check_no_patterns(text, DESTRUCTIVE_PATTERNS, result, path.name)
        check_no_patterns(uncommented_text, DANGEROUS_INSTALLER_DIRECTIVES, result, path.name)


def check_ubuntu_user_data(config_dir: Path, result: ValidationResult) -> None:
    user_data = config_dir / "user-data"
    if not user_data.exists():
        return

    try:
        import yaml
    except ImportError:
        result.warning("PyYAML is not installed; skipping YAML parse check for user-data.")
        return

    try:
        data = yaml.safe_load(read_text(user_data))
    except Exception as exc:
        result.error(f"user-data is not valid YAML: {exc}")
        return

    if not isinstance(data, dict):
        result.error("user-data YAML root is not an object.")
        return

    if "autoinstall" not in data:
        result.error("user-data missing top-level autoinstall key.")
        return

    autoinstall = data["autoinstall"]
    if not isinstance(autoinstall, dict):
        result.error("autoinstall key is not an object.")
        return

    if autoinstall.get("version") != 1:
        result.error(f"autoinstall version should be 1, got {autoinstall.get('version')!r}.")

    if "storage" in autoinstall:
        result.error("Ubuntu user-data contains storage section; this draft should omit storage.")

    if not (config_dir / "meta-data").exists():
        result.error("Ubuntu config has user-data but missing meta-data.")


def check_archinstall_json(config_dir: Path, result: ValidationResult) -> None:
    arch_json = config_dir / "archinstall-user-configuration.json"
    if not arch_json.exists():
        return

    try:
        data = load_json(arch_json)
    except Exception as exc:
        result.error(f"archinstall-user-configuration.json is not valid JSON: {exc}")
        return

    if "disk_config" in data:
        result.error("Archinstall config contains disk_config; this draft should omit disk config.")
    if "packages" not in data:
        result.warning("Archinstall config does not contain packages list.")
    if "users" not in data:
        result.warning("Archinstall config does not contain users list.")


def check_opensuse_xml(config_dir: Path, result: ValidationResult) -> None:
    autoyast = config_dir / "autoyast.xml"
    if not autoyast.exists():
        return

    try:
        ET.fromstring(read_text(autoyast))
    except Exception as exc:
        result.error(f"autoyast.xml is not valid XML: {exc}")


def check_fedora_kickstart(config_dir: Path, result: ValidationResult) -> None:
    ks = config_dir / "kickstart.ks"
    if not ks.exists():
        return

    text = read_text(ks)
    for marker in ["%packages", "%end"]:
        if marker not in text:
            result.warning(f"kickstart.ks missing marker: {marker}")


def check_debian_preseed(config_dir: Path, result: ValidationResult) -> None:
    preseed = config_dir / "preseed.cfg"
    if not preseed.exists():
        return

    text = read_text(preseed)
    if "d-i " not in text:
        result.warning("preseed.cfg does not look like a Debian preseed file.")


def validate_config_dir(config_dir: Path) -> ValidationResult:
    result = ValidationResult(config_dir)

    if not config_dir.exists():
        result.error(f"Directory does not exist: {config_dir}")
        return result

    if not config_dir.is_dir():
        result.error(f"Path is not a directory: {config_dir}")
        return result

    check_required_files(config_dir, result)
    check_manifest(config_dir, result)
    check_profile(config_dir, result)
    check_all_text_files(config_dir, result)
    check_ubuntu_user_data(config_dir, result)
    check_archinstall_json(config_dir, result)
    check_opensuse_xml(config_dir, result)
    check_fedora_kickstart(config_dir, result)
    check_debian_preseed(config_dir, result)

    return result


def find_config_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    result: list[Path] = []
    for manifest in root.glob("*/*/linuxai-boot-manifest.json"):
        result.append(manifest.parent)
    return sorted(set(result))


def print_result(result: ValidationResult) -> None:
    status = "OK" if result.ok else "FAILED"
    print("=" * 70)
    print(f"{status}: {result.path}")

    if result.errors:
        print("\nErrors:")
        for err in result.errors:
            print(f"  - {err}")

    if result.warnings:
        print("\nWarnings:")
        for warn in result.warnings:
            print(f"  - {warn}")

    if not result.errors and not result.warnings:
        print("No issues found.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate LinuxAI generated boot/install config draft files."
    )
    parser.add_argument("--path", default="", help="Specific config directory to validate.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Root folder containing generated boot configs.")

    args = parser.parse_args()

    if args.path:
        config_dirs = [Path(args.path).resolve()]
    else:
        config_dirs = find_config_dirs(Path(args.root).resolve())

    if not config_dirs:
        print("No generated boot config directories found.")
        print(f"Root checked: {Path(args.root).resolve()}")
        sys.exit(1)

    results = [validate_config_dir(path) for path in config_dirs]

    for result in results:
        print_result(result)

    failed = [result for result in results if not result.ok]

    print("=" * 70)
    print(f"Validated: {len(results)}")
    print(f"Passed:    {len(results) - len(failed)}")
    print(f"Failed:    {len(failed)}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
