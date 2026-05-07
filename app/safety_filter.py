import re
from dataclasses import dataclass


@dataclass
class SafetyIssue:
    level: str
    pattern: str
    message: str


HIGH_RISK_PATTERNS = [
    r"(^|\n|\s)(sudo\s+)?rm\s+-rf\s+",
    r"(^|\n|\s)(sudo\s+)?dd\s+",
    r"(^|\n|\s)(sudo\s+)?mkfs(\.|\s)",
    r"(^|\n|\s)(sudo\s+)?wipefs\s+",
    r"(^|\n|\s)(sudo\s+)?fdisk\s+",
    r"(^|\n|\s)(sudo\s+)?sfdisk\s+",
    r"(^|\n|\s)(sudo\s+)?parted\s+",
    r"(^|\n|\s)(sudo\s+)?cryptsetup\s+",
    r"(^|\n|\s)(sudo\s+)?sgdisk\s+",
    r"(^|\n|\s)(sudo\s+)?pvcreate\s+",
    r"(^|\n|\s)(sudo\s+)?vgcreate\s+",
    r"(^|\n|\s)(sudo\s+)?lvcreate\s+",
    r"(^|\n|\s)(sudo\s+)?mokutil\s+--disable-validation\b",
    r"(^|\n|\s)(sudo\s+)?mokutil\s+--enable-validation\b",
    r"(^|\n|\s)(sudo\s+)?update-grub\b",
    r"(^|\n|\s)(sudo\s+)?grub-mkconfig\b",
    r"(^|\n|\s)(sudo\s+)?grub-install\b",
    r"/etc/default/grub",
    r"(^|\n|\s)(sudo\s+)?systemctl\s+mask\b",
]

DANGEROUS_PACKAGE_NAMES = [
    r"linux-firmware",
    r"firmware-iwlwifi",
    r"firmware-realtek",
    r"linux-image",
    r"kernel",
    r"grub",
    r"systemd",
    r"network-manager",
    r"NetworkManager",
]

REMOVAL_VERBS = re.compile(
    r"\b(apt(-get)?\s+(remove|purge)|dnf\s+remove|pacman\s+-R|zypper\s+remove)\b",
    flags=re.IGNORECASE,
)

MEDIUM_RISK_PATTERNS = [
    r"\bmodprobe\s+-r\b",
    r"\brmmod\b",
    r"\bupdate-initramfs\b",
    r"/etc/modprobe\.d/",
    r"\bblacklist\s+\w+",
    r"\bsystemctl\s+disable\b",
    r"\bsystemctl\s+restart\b",
    r"\bprime-select\s+(nvidia|intel|on-demand)\b",
    r"\brfkill\s+unblock\b",
]

PACKAGE_VERSION_PIN_PATTERNS = [
    r"\bapt(-get)?\s+install\s+[a-zA-Z0-9_.:+-]+=",
    r"\bdnf\s+install\s+[a-zA-Z0-9_.:+-]+-([0-9]+\.)",
]


def _find_patterns(text: str, patterns: list[str]) -> list[str]:
    return [p for p in patterns if re.search(p, text, flags=re.IGNORECASE)]


def scan_answer(answer: str) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []

    for pattern in _find_patterns(answer, HIGH_RISK_PATTERNS):
        issues.append(
            SafetyIssue(
                level="high",
                pattern=pattern,
                message=(
                    "High-risk command detected. Should not be suggested without "
                    "explicit confirmation and strong diagnostics."
                ),
            )
        )

    if REMOVAL_VERBS.search(answer):
        for package_pattern in DANGEROUS_PACKAGE_NAMES:
            if re.search(package_pattern, answer, flags=re.IGNORECASE):
                issues.append(
                    SafetyIssue(
                        level="high",
                        pattern=package_pattern,
                        message=(
                            f"Removal of critical package detected: '{package_pattern}'. "
                            "This can break boot, networking, or the kernel."
                        ),
                    )
                )

    for pattern in _find_patterns(answer, MEDIUM_RISK_PATTERNS):
        issues.append(
            SafetyIssue(
                level="medium",
                pattern=pattern,
                message=(
                    "System-changing command detected. Should be justified by prior diagnostics."
                ),
            )
        )

    for pattern in _find_patterns(answer, PACKAGE_VERSION_PIN_PATTERNS):
        issues.append(
            SafetyIssue(
                level="medium",
                pattern=pattern,
                message=(
                    "Specific package version detected. The model should not invent exact versions."
                ),
            )
        )

    return issues


def format_safety_warning(issues: list[SafetyIssue]) -> str:
    if not issues:
        return ""

    high   = [i for i in issues if i.level == "high"]
    medium = [i for i in issues if i.level == "medium"]

    lines = ["\n\n---", "⚠ Safety filter warning:"]

    if high:
        lines.append("HIGH risk:")
        for issue in high:
            lines.append(f"  - {issue.message}  (pattern: {issue.pattern})")

    if medium:
        lines.append("MEDIUM risk:")
        for issue in medium:
            lines.append(f"  - {issue.message}  (pattern: {issue.pattern})")

    lines.append("Review diagnostics before running any medium/high-risk command.")
    return "\n".join(lines)