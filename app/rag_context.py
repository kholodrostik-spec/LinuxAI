from __future__ import annotations

import json
from typing import Any

from app.db import get_connection
from app.embedding import embed_text


MAX_SQL_FACTS = 20
MAX_VECTOR_CHUNKS = 8


def _rows_to_dicts(rows: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for row in rows:
        if isinstance(row, dict):
            result.append(row)
        elif hasattr(row, "_asdict"):
            result.append(dict(row._asdict()))
        else:
            try:
                result.append(dict(row))
            except Exception:
                result.append({"value": str(row)})

    return result


def search_sql_facts(question: str, limit: int = MAX_SQL_FACTS) -> dict[str, Any]:
    q = f"%{question.lower()}%"

    result: dict[str, Any] = {
        "distros": [],
        "drivers": [],
        "devices": [],
        "packages": [],
        "commands": [],
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, family, package_manager, install_command_template
                FROM distros
                WHERE LOWER(name) LIKE %s
                   OR LOWER(COALESCE(family, '')) LIKE %s
                ORDER BY name
                LIMIT %s
                """,
                (q, q, limit),
            )
            result["distros"] = _rows_to_dicts(cur.fetchall())

            cur.execute(
                """
                SELECT name, kernel_module, driver_type, notes
                FROM drivers
                WHERE LOWER(name) LIKE %s
                   OR LOWER(COALESCE(kernel_module, '')) LIKE %s
                   OR LOWER(COALESCE(driver_type, '')) LIKE %s
                   OR LOWER(COALESCE(notes, '')) LIKE %s
                ORDER BY name
                LIMIT %s
                """,
                (q, q, q, q, limit),
            )
            result["drivers"] = _rows_to_dicts(cur.fetchall())

            cur.execute(
                """
                SELECT name, vendor, device_type, pci_id, usb_id, notes
                FROM devices
                WHERE LOWER(name) LIKE %s
                   OR LOWER(COALESCE(vendor, '')) LIKE %s
                   OR LOWER(COALESCE(device_type, '')) LIKE %s
                   OR LOWER(COALESCE(pci_id, '')) LIKE %s
                   OR LOWER(COALESCE(usb_id, '')) LIKE %s
                   OR LOWER(COALESCE(notes, '')) LIKE %s
                ORDER BY vendor, name
                LIMIT %s
                """,
                (q, q, q, q, q, q, limit),
            )
            result["devices"] = _rows_to_dicts(cur.fetchall())

            cur.execute(
                """
                SELECT p.name, d.name AS distro, p.purpose, p.install_command
                FROM packages p
                LEFT JOIN distros d ON d.id = p.distro_id
                WHERE LOWER(p.name) LIKE %s
                   OR LOWER(COALESCE(p.purpose, '')) LIKE %s
                   OR LOWER(COALESCE(p.install_command, '')) LIKE %s
                   OR LOWER(COALESCE(d.name, '')) LIKE %s
                ORDER BY d.name, p.name
                LIMIT %s
                """,
                (q, q, q, q, limit),
            )
            result["packages"] = _rows_to_dicts(cur.fetchall())

            cur.execute(
                """
                SELECT c.title, c.command, c.risk_level, c.purpose, d.name AS distro
                FROM commands c
                LEFT JOIN distros d ON d.id = c.distro_id
                WHERE LOWER(c.command) LIKE %s
                   OR LOWER(COALESCE(c.purpose, '')) LIKE %s
                   OR LOWER(COALESCE(c.title, '')) LIKE %s
                   OR LOWER(COALESCE(d.name, '')) LIKE %s
                ORDER BY c.risk_level, c.command
                LIMIT %s
                """,
                (q, q, q, q, limit),
            )
            result["commands"] = _rows_to_dicts(cur.fetchall())

    return result


def search_vector_chunks(question: str, limit: int = MAX_VECTOR_CHUNKS) -> list[dict[str, Any]]:
    embedding = embed_text(question)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH query_vec AS (
                    SELECT %s::vector AS vec
                )
                SELECT
                    s.title,
                    s.url,
                    s.source_type,
                    s.trust_level,
                    dc.chunk_text,
                    dc.topic,
                    1 - (dc.embedding <=> qv.vec) AS similarity
                FROM document_chunks dc
                JOIN sources s ON s.id = dc.source_id
                CROSS JOIN query_vec qv
                WHERE dc.embedding IS NOT NULL
                  AND dc.is_active = TRUE
                ORDER BY dc.embedding <=> qv.vec
                LIMIT %s
                """,
                (embedding, limit),
            )
            rows = cur.fetchall()

    chunks: list[dict[str, Any]] = []

    for row in rows:
        if isinstance(row, dict):
            item = row
        else:
            try:
                item = dict(row)
            except Exception:
                continue

        chunks.append(
            {
                "title":       item.get("title"),
                "url":         item.get("url"),
                "source_type": item.get("source_type"),
                "trust_level": item.get("trust_level"),
                "chunk_text":  item.get("chunk_text"),
                "topic":       item.get("topic"),
                "similarity":  float(item["similarity"]) if item.get("similarity") is not None else None,
            }
        )

    return chunks


def build_rag_context(question: str) -> str:
    sql_facts     = search_sql_facts(question)
    vector_chunks = search_vector_chunks(question)

    context = {
        "sql_facts": sql_facts,
        "vector_chunks": vector_chunks,
        "context_rules": [
            "Prefer high trust manual notes over broad web chunks.",
            "Use SQL facts for distro, driver, device, package, and command names.",
            "Use vector chunks for explanations and troubleshooting patterns.",
            "If retrieved context conflicts, prefer safer diagnostic-first guidance.",
            "Do not invent exact package versions, device support claims, or destructive commands.",
        ],
    }

    return json.dumps(context, ensure_ascii=False, indent=2, default=str)