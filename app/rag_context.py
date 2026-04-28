from app.sql_search import sql_search
from app.vector_search import vector_search


# Column names per SQL section — keeps the LLM prompt readable
_COLUMNS: dict[str, list[str]] = {
    "devices":  ["id", "name", "vendor", "device_type", "pci_id", "usb_id", "notes"],
    "drivers":  ["id", "name", "kernel_module", "driver_type", "notes"],
    "packages": ["id", "name", "distro", "purpose", "install_command"],
    "commands": ["id", "title", "distro", "command", "risk_level", "purpose"],
}


def _format_rows(section: str, rows: list[tuple]) -> list[str]:
    lines = [f"\n[{section.upper()}]"]

    if not rows:
        lines.append("  No results.")
        return lines

    cols = _COLUMNS.get(section, [])
    for row in rows:
        if cols:
            # Format as "key: value" pairs, skip None/empty values
            pairs = ", ".join(
                f"{k}: {v}"
                for k, v in zip(cols, row)
                if v is not None and str(v).strip()
            )
            lines.append(f"  - {pairs}")
        else:
            lines.append(f"  - {row}")

    return lines


def build_rag_context(
    query: str,
    vector_limit: int = 5,
    min_similarity: float = 0.40,
) -> str:
    sql_results    = sql_search(query)
    vector_results = vector_search(query, limit=vector_limit)

    parts = ["=== SQL FACTS ==="]

    for section, rows in sql_results.items():
        parts.extend(_format_rows(section, rows))

    parts.append("\n=== VECTOR DOCUMENTS ===")

    filtered = [
        item for item in vector_results
        if item.get("similarity", 0) >= min_similarity
    ]

    if not filtered:
        parts.append("  No relevant vector results above similarity threshold.")
    else:
        for index, item in enumerate(filtered, start=1):
            parts.append(
                f"\nDocument {index}:\n"
                f"  Title:      {item['title']}\n"
                f"  Topic:      {item['topic']}\n"
                f"  Similarity: {item['similarity']:.4f}\n"
                f"  Text:\n{item['text']}"
            )

    return "\n".join(parts)
