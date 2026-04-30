import re
from dataclasses import dataclass


@dataclass
class SafetyIssue:
    level: str
    pattern: str
    message: str


# Immediately destructive — disk wipe, partition, bootloader changes
HIGH_RISK_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bdd\b",
    r"\bmkfs\b",
    r"\bwipefs\b",
    r"\bfdisk\b",
    r"\bparted\b",
    r"\bcryptsetup\b",
    r"\bmokutil\s+--disable-validation\b",
    r"\bmokutil\s+--enable-validation\b",
    r"\bupdate-grub\b",
    r"\bgrub-mkconfig\b",
    r"/etc/default/grub",
    r"\bsystemctl\s+mask\b",
]

# Removing these packages can break boot, networking, or the kernel
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

# Medium risk — reversible but system-changing
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

# Model should not invent exact package versions
PACKAGE_VERSION_PIN_PATTERNS = [
    r"\bapt(-get)?\s+install\s+[a-zA-Z0-9_.:+-]+=",
    r"\bdnf\s+install\s+[a-zA-Z0-9_.:+-]+-([0-9]+\.)",
]


def _find_patterns(text: str, patterns: list[str]) -> list[str]:
    return [
        p for p in patterns
        if re.search(p, text, flags=re.IGNORECASE)
    ]


def scan_answer(answer: str) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []

    # High risk: destructive commands
    for pattern in _find_patterns(answer, HIGH_RISK_PATTERNS):
        issues.append(SafetyIssue(
            level="high",
            pattern=pattern,
            message="High-risk command detected. Should not be suggested without explicit confirmation and strong diagnostics.",
        ))

    # High risk: removal of dangerous packages only
    # Safe removals like 'apt remove mesa-utils' do NOT trigger this
    if REMOVAL_VERBS.search(answer):
        for package_pattern in DANGEROUS_PACKAGE_NAMES:
            if re.search(package_pattern, answer, flags=re.IGNORECASE):
                issues.append(SafetyIssue(
                    level="high",
                    pattern=package_pattern,
                    message=f"Removal of critical package detected: '{package_pattern}'. "
                            "This can break boot, networking, or the kernel.",
                ))

    # Medium risk: reversible but system-changing
    for pattern in _find_patterns(answer, MEDIUM_RISK_PATTERNS):
        issues.append(SafetyIssue(
            level="medium",
            pattern=pattern,
            message="System-changing command detected. Should be justified by prior diagnostics.",
        ))

    # Medium risk: invented package versions
    for pattern in _find_patterns(answer, PACKAGE_VERSION_PIN_PATTERNS):
        issues.append(SafetyIssue(
            level="medium",
            pattern=pattern,
            message="Specific package version detected. The model should not invent exact versions.",
        ))

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
