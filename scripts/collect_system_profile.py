"""
scripts/collect_system_profile.py

Collects real hardware data from the current machine and stores it in:
  - system_reports table (raw lspci/lsusb/kernel output)
  - document_chunks table (searchable vector chunks)
  - devices table (identified hardware devices)

Run this once after setting up the project, and again after hardware changes.
Safe to run multiple times — duplicates are skipped via chunk_hash.

Usage:
    python scripts/collect_system_profile.py
"""
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.db import get_connection
from app.embedding import embed_text


# ─────────────────────────────────────────────────────────────────────────────
# Commands to collect hardware info
# ─────────────────────────────────────────────────────────────────────────────

DIAGNOSTIC_COMMANDS: list[tuple[str, str]] = [
    # (label, shell command)
    ("lspci -nnk",              "lspci -nnk"),
    ("lsusb",                   "lsusb"),
    ("uname -a",                "uname -a"),
    ("lsmod",                   "lsmod"),
    ("rfkill list",             "rfkill list"),
    ("ip a",                    "ip a"),
    ("os-release",              "cat /etc/os-release"),
    ("dmesg firmware",          "dmesg | grep -i firmware | tail -40"),
    ("dmesg nvidia",            "dmesg | grep -i nvidia | tail -20"),
    ("dmesg wifi",              "dmesg | grep -i -E 'wifi|wlan|iwlwifi|rtw|mt76|ath' | tail -20"),
    ("dmesg audio",             "dmesg | grep -i -E 'sof|audio|snd|hda' | tail -20"),
    ("inxi",                    "inxi -Fxxx --no-host 2>/dev/null || echo 'inxi not installed'"),
]

CHUNK_TOPIC = "system_profile"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_command(label: str, cmd: str) -> str:
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr:
            output += f"\n[stderr]: {result.stderr.strip()}"
        return output if output else f"[no output from: {cmd}]"
    except subprocess.TimeoutExpired:
        return f"[timeout running: {cmd}]"
    except Exception as exc:
        return f"[error running {cmd}]: {exc}"


def collect_all() -> dict[str, str]:
    """Run all diagnostic commands and return label → output."""
    results = {}
    for label, cmd in DIAGNOSTIC_COMMANDS:
        print(f"  Running: {label}...")
        results[label] = run_command(label, cmd)
    return results


def build_report_text(collected: dict[str, str]) -> str:
    """Combine all outputs into a single report text."""
    parts = [f"=== LinuxAI System Profile ===", f"Collected: {datetime.now(timezone.utc).isoformat()}", ""]
    for label, output in collected.items():
        parts.append(f"--- {label} ---")
        parts.append(output)
        parts.append("")
    return "\n".join(parts)


def build_chunks(collected: dict[str, str]) -> list[tuple[str, str]]:
    """
    Build searchable chunks from collected data.
    Each chunk = one command output, labelled with its topic.
    Returns list of (title, chunk_text).
    """
    chunks = []
    for label, output in collected.items():
        if not output or "[no output" in output or "[error" in output:
            continue
        title = f"System profile: {label}"
        text  = f"[{label}]\n{output}"
        chunks.append((title, text))
    return chunks


def detect_distro(collected: dict[str, str]) -> str | None:
    """Extract distro name from os-release output."""
    release = collected.get("os-release", "")
    for line in release.splitlines():
        if line.startswith("NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def detect_kernel(collected: dict[str, str]) -> str | None:
    """Extract kernel version from uname output."""
    uname = collected.get("uname -a", "")
    parts = uname.split()
    return parts[2] if len(parts) > 2 else None


def detect_devices(collected: dict[str, str]) -> list[tuple]:
    """
    Parse lspci output to extract detected devices.
    Returns list of (name, vendor, device_type, pci_id, notes) tuples.
    """
    devices = []
    lspci = collected.get("lspci -nnk", "")

    gpu_keywords    = ["VGA", "3D controller", "Display controller"]
    wifi_keywords   = ["Network controller", "Wireless"]
    eth_keywords    = ["Ethernet controller"]
    audio_keywords  = ["Audio device", "Multimedia audio"]
    usb_keywords    = ["USB controller"]

    current_device  = None
    current_driver  = None
    current_pci_id  = None

    for line in lspci.splitlines():
        # New device line: "00:02.0 VGA compatible controller [8086:46a8] (rev 0c)"
        if line and not line.startswith("\t") and not line.startswith(" "):
            # Save previous device
            if current_device:
                dtype, vendor = _classify_device(current_device, gpu_keywords, wifi_keywords, eth_keywords, audio_keywords)
                if dtype:
                    devices.append((
                        current_device[:120],
                        vendor,
                        dtype,
                        current_pci_id,
                        f"Kernel driver: {current_driver}" if current_driver else None,
                    ))
            current_device = line
            current_driver = None
            # Extract PCI ID like [8086:46a8]
            import re
            m = re.search(r'\[([0-9a-f]{4}:[0-9a-f]{4})\]', line, re.IGNORECASE)
            current_pci_id = m.group(1) if m else None

        elif "Kernel driver in use:" in line:
            current_driver = line.split(":", 1)[1].strip()

    # Last device
    if current_device:
        dtype, vendor = _classify_device(current_device, gpu_keywords, wifi_keywords, eth_keywords, audio_keywords)
        if dtype:
            devices.append((
                current_device[:120],
                vendor,
                dtype,
                current_pci_id,
                f"Kernel driver: {current_driver}" if current_driver else None,
            ))

    return devices


def _classify_device(
    line: str,
    gpu_kw: list, wifi_kw: list, eth_kw: list, audio_kw: list
) -> tuple[str | None, str | None]:
    """Return (device_type, vendor) or (None, None) if not recognized."""
    line_lower = line.lower()

    if any(k.lower() in line_lower for k in gpu_kw):
        dtype = "gpu"
    elif any(k.lower() in line_lower for k in wifi_kw):
        dtype = "wifi"
    elif any(k.lower() in line_lower for k in eth_kw):
        dtype = "ethernet"
    elif any(k.lower() in line_lower for k in audio_kw):
        dtype = "audio"
    else:
        return None, None

    # Guess vendor from device name
    vendor = None
    for v in ["NVIDIA", "Intel", "AMD", "Realtek", "MediaTek", "Qualcomm", "Broadcom"]:
        if v.lower() in line_lower:
            vendor = v
            break

    return dtype, vendor


def main() -> None:
    print("=" * 60)
    print("LinuxAI System Profile Collector")
    print("=" * 60)

    print("\nCollecting hardware data...")
    collected = collect_all()

    distro_name    = detect_distro(collected)
    kernel_version = detect_kernel(collected)
    report_text    = build_report_text(collected)
    chunks         = build_chunks(collected)
    devices        = detect_devices(collected)

    print(f"\nDetected distro:  {distro_name or 'unknown'}")
    print(f"Detected kernel:  {kernel_version or 'unknown'}")
    print(f"Chunks to store:  {len(chunks)}")
    print(f"Devices detected: {len(devices)}")

    inserted_chunks  = 0
    skipped_chunks   = 0
    inserted_devices = 0

    with get_connection() as conn:
        with conn.cursor() as cur:

            # ── 1. Store raw report in system_reports ─────────────────────
            cur.execute(
                """
                INSERT INTO system_reports
                    (report_text, distro_name, kernel_version)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (report_text, distro_name, kernel_version),
            )
            report_id = cur.fetchone()[0]
            print(f"\nSystem report saved (id={report_id}).")

            # ── 2. Store source record for this profile ───────────────────
            source_title = f"System profile — {distro_name or 'Linux'} — {datetime.now(timezone.utc).date()}"
            cur.execute(
                """
                INSERT INTO sources
                    (title, source_type, topic, trust_level, notes)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (title, source_type) DO NOTHING
                RETURNING id
                """,
                (source_title, "system_profile", CHUNK_TOPIC, "high",
                 f"Auto-collected from local machine. Report id={report_id}."),
            )
            row = cur.fetchone()
            if row:
                source_id = row[0]
            else:
                cur.execute(
                    "SELECT id FROM sources WHERE title = %s AND source_type = %s",
                    (source_title, "system_profile"),
                )
                source_id = cur.fetchone()[0]

            # ── 3. Store chunks with embeddings ───────────────────────────
            print("\nBuilding embeddings for profile chunks...")
            for title, chunk_text in chunks:
                chunk_hash = sha256(chunk_text)

                cur.execute(
                    "SELECT id FROM document_chunks WHERE chunk_hash = %s",
                    (chunk_hash,),
                )
                if cur.fetchone():
                    skipped_chunks += 1
                    continue

                embedding = embed_text(chunk_text)
                cur.execute(
                    """
                    INSERT INTO document_chunks
                        (source_id, title, chunk_text, chunk_hash, topic, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_hash) DO NOTHING
                    """,
                    (source_id, title, chunk_text, chunk_hash, CHUNK_TOPIC, embedding),
                )
                inserted_chunks += 1

            # ── 4. Store detected devices ─────────────────────────────────
            print("Storing detected devices...")
            for name, vendor, dtype, pci_id, notes in devices:
                cur.execute(
                    """
                    INSERT INTO devices
                        (name, vendor, device_type, pci_id, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name, vendor) DO NOTHING
                    """,
                    (name, vendor, dtype, pci_id, notes),
                )
                if cur.rowcount:
                    inserted_devices += 1

        conn.commit()

    print("\n" + "=" * 60)
    print("System profile collected successfully.")
    print(f"  Chunks added:    {inserted_chunks}")
    print(f"  Chunks skipped:  {skipped_chunks}")
    print(f"  Devices added:   {inserted_devices}")
    print("\nNext: run python scripts/create_vector_index.py if not done yet.")


if __name__ == "__main__":
    main()