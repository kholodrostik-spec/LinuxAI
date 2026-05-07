"""
scripts/create_config_artifact.py

Creates a single safe LinuxAI config artifact file from a prepared ISO workspace.

Input:
  generated/iso_workspaces/<profile_id>/<distro_slug>/

Output:
  generated/artifacts/<profile_id>/<distro_slug>/
    linuxai_<profile_id>_<distro_slug>_config_bundle.tar.gz
    ARTIFACT_STATUS.json

Important:
  - This is NOT a bootable ISO.
  - This is NOT an OS image.
  - This does NOT download ISO files.
  - This does NOT write to USB.
  - This does NOT modify disks.
  - This only packages already validated workspace files into one archive artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ISO_WORKSPACE_ROOT = PROJECT_ROOT / "generated" / "iso_workspaces"
ARTIFACT_ROOT      = PROJECT_ROOT / "generated" / "artifacts"

CONFIRMATION_PHRASE = "I_UNDERSTAND_THIS_IS_A_CONFIG_ARTIFACT_NOT_BOOTABLE_ISO"

BLOCKED_FILE_SUFFIXES = {".iso", ".img", ".raw", ".qcow2", ".vdi", ".vmdk"}

REQUIRED_WORKSPACE_FILES = [
    "README.md",
    "CHECKLIST_BEFORE_ISO_BUILD.md",
    "manifests/WORKSPACE_STATUS.json",
    "manifests/linuxai-boot-manifest.json",
    "profile/profile_used.json",
]

SAFE_STATUS_FLAGS = {
    "bootable_iso_created": False,
    "usb_written": False,
    "disk_modified": False,
    "storage_layout_generated": False,
    "destructive_commands_generated": False,
    "iso_downloaded": False,
    "iso_modified": False,
}

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


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_slug(text: str) -> str:
    text = str(text).strip().lower()
    text = re.sub(r"[^a-z0-9_.-]+", "_", text)
    return text.strip("_") or "unknown"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def assert_workspace_safe(workspace: Path) -> dict[str, Any]:
    if not workspace.exists():
        raise FileNotFoundError(f"Workspace not found: {workspace}")

    if not workspace.is_dir():
        raise NotADirectoryError(f"Workspace path is not a directory: {workspace}")

    for required in REQUIRED_WORKSPACE_FILES:
        path = workspace / required
        if not path.exists():
            raise FileNotFoundError(f"Workspace missing required file: {required}")

    status_path = workspace / "manifests" / "WORKSPACE_STATUS.json"
    status = load_json(status_path)

    safety = status.get("safety")
    if not isinstance(safety, dict):
        raise RuntimeError("WORKSPACE_STATUS.json missing safety object.")

    for key, expected in SAFE_STATUS_FLAGS.items():
        actual = safety.get(key)
        if actual is not expected:
            raise RuntimeError(
                f"Unsafe workspace status flag: {key} should be {expected}, got {actual}"
            )

    for path in workspace.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"Symlinks are not allowed in workspace: {path}")
        if not path.is_file():
            continue
        if path.suffix.lower() in BLOCKED_FILE_SUFFIXES:
            raise RuntimeError(f"Blocked ISO/image-like file in workspace: {path}")
        assert_safe_text_file(path)

    return status


def latest_workspace_dir() -> Path:
    statuses = sorted(
        ISO_WORKSPACE_ROOT.glob("*/*/manifests/WORKSPACE_STATUS.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not statuses:
        raise FileNotFoundError(
            f"No ISO workspace status files found under {ISO_WORKSPACE_ROOT}"
        )

    return statuses[0].parents[1]


def collect_workspace_files(workspace: Path) -> list[Path]:
    return sorted(path for path in workspace.rglob("*") if path.is_file())


def create_tar_gz(workspace: Path, artifact_path: Path) -> None:
    files = collect_workspace_files(workspace)
    with tarfile.open(artifact_path, "w:gz") as tar:
        for file_path in files:
            arcname = Path(workspace.name) / file_path.relative_to(workspace)
            tar.add(file_path, arcname=arcname)


def create_zip(workspace: Path, artifact_path: Path) -> None:
    files = collect_workspace_files(workspace)
    with zipfile.ZipFile(artifact_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            arcname = Path(workspace.name) / file_path.relative_to(workspace)
            zf.write(file_path, arcname=arcname)


def build_artifact_status(
    workspace: Path,
    artifact_path: Path,
    workspace_status: dict[str, Any],
    artifact_format: str,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "created_at": now_utc(),
        "workspace_dir": str(workspace),
        "artifact_path": str(artifact_path),
        "artifact_name": artifact_path.name,
        "artifact_format": artifact_format,
        "artifact_sha256": sha256_file(artifact_path),
        "artifact_size_bytes": artifact_path.stat().st_size,
        "profile_id": workspace_status.get("profile_id"),
        "recommended_distro": workspace_status.get("recommended_distro"),
        "source_safety": workspace_status.get("safety"),
        "safety": {
            "bootable_iso_created": False,
            "os_image_created": False,
            "usb_written": False,
            "disk_modified": False,
            "storage_layout_generated": False,
            "destructive_commands_generated": False,
            "iso_downloaded": False,
            "iso_modified": False,
            "config_archive_created": True,
        },
        "next_stage": {
            "can_download_iso": False,
            "can_build_bootable_iso": False,
            "requires_official_iso_url": True,
            "requires_checksum_verification": True,
            "requires_user_review": True,
        },
    }


def create_artifact(
    workspace: Path,
    output_dir: Path | None,
    artifact_format: str,
    overwrite: bool,
) -> tuple[Path, dict[str, Any]]:
    workspace_status = assert_workspace_safe(workspace)

    profile_id  = safe_slug(workspace_status.get("profile_id", "unknown_profile"))
    distro      = workspace_status.get("recommended_distro", {}).get("distro", workspace.name)
    distro_slug = safe_slug(distro)

    if output_dir is None:
        output_dir = ARTIFACT_ROOT / profile_id / distro_slug

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
                f"Output artifact directory already exists: {output_dir}. "
                "Use --overwrite to replace it."
            )
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"linuxai_{profile_id}_{distro_slug}_config_bundle"

    if artifact_format == "tar.gz":
        artifact_path = output_dir / f"{base_name}.tar.gz"
        create_tar_gz(workspace, artifact_path)
    elif artifact_format == "zip":
        artifact_path = output_dir / f"{base_name}.zip"
        create_zip(workspace, artifact_path)
    else:
        raise ValueError(f"Unsupported artifact format: {artifact_format}")

    status = build_artifact_status(
        workspace=workspace,
        artifact_path=artifact_path,
        workspace_status=workspace_status,
        artifact_format=artifact_format,
    )

    write_json(output_dir / "ARTIFACT_STATUS.json", status)

    for path in output_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() in BLOCKED_FILE_SUFFIXES:
            raise RuntimeError(f"Blocked ISO/image-like artifact created: {path}")
        if path.name == artifact_path.name:
            continue
        assert_safe_text_file(path)

    return artifact_path, status


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a LinuxAI config artifact archive from an ISO workspace."
    )
    parser.add_argument("--workspace", default="", help="ISO workspace directory.")
    parser.add_argument("--output-dir", default="", help="Output directory.")
    parser.add_argument("--format", default="tar.gz", choices=["tar.gz", "zip"])
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--allow-config-artifact", action="store_true", help="Required safety gate.")
    parser.add_argument("--confirm", default="", help=f"Required confirmation phrase: {CONFIRMATION_PHRASE}")

    args = parser.parse_args()

    try:
        if not args.allow_config_artifact:
            raise PermissionError("Missing required flag: --allow-config-artifact")

        if args.confirm != CONFIRMATION_PHRASE:
            raise PermissionError(
                f"Missing or wrong confirmation phrase. Required: {CONFIRMATION_PHRASE}"
            )

        if args.workspace:
            workspace = Path(args.workspace).resolve()
        else:
            workspace = latest_workspace_dir().resolve()

        output_dir = Path(args.output_dir).resolve() if args.output_dir else None

        artifact_path, status = create_artifact(
            workspace=workspace,
            output_dir=output_dir,
            artifact_format=args.format,
            overwrite=args.overwrite,
        )

        print("Config artifact created successfully.")
        print(f"Workspace: {workspace}")
        print(f"Artifact:  {artifact_path}")
        print()
        print("SHA256:")
        print(status["artifact_sha256"])
        print()
        print("Important:")
        print("  This is not a bootable ISO.")
        print("  This is not an OS image.")
        print("  No USB was written.")
        print("  No disk was modified.")
        print("  Storage/partitioning remains omitted.")

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
