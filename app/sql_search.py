from app.db import get_connection


def _keywords(query: str) -> list[str]:
    words = []

    for word in query.lower().replace("-", " ").replace("_", " ").split():
        word = word.strip()

        if len(word) >= 3:
            words.append(word)

    return list(dict.fromkeys(words))


def sql_search(query: str, limit: int = 10) -> dict:
    keywords = _keywords(query)

    results = {
        "devices": [],
        "drivers": [],
        "packages": [],
        "commands": [],
    }

    if not keywords:
        return results

    with get_connection() as conn:
        with conn.cursor() as cur:
            for keyword in keywords:
                q = f"%{keyword}%"

                cur.execute(
                    """
                    SELECT id, name, vendor, device_type, pci_id, usb_id, notes
                    FROM devices
                    WHERE lower(name) LIKE %s
                       OR lower(coalesce(vendor, '')) LIKE %s
                       OR lower(coalesce(device_type, '')) LIKE %s
                       OR lower(coalesce(pci_id, '')) LIKE %s
                       OR lower(coalesce(usb_id, '')) LIKE %s
                    LIMIT %s
                    """,
                    (q, q, q, q, q, limit)
                )
                results["devices"].extend(cur.fetchall())

                cur.execute(
                    """
                    SELECT id, name, kernel_module, driver_type, notes
                    FROM drivers
                    WHERE lower(name) LIKE %s
                       OR lower(coalesce(kernel_module, '')) LIKE %s
                       OR lower(coalesce(driver_type, '')) LIKE %s
                    LIMIT %s
                    """,
                    (q, q, q, limit)
                )
                results["drivers"].extend(cur.fetchall())

                cur.execute(
                    """
                    SELECT p.id, p.name, d.name AS distro, p.purpose, p.install_command
                    FROM packages p
                    LEFT JOIN distros d ON p.distro_id = d.id
                    WHERE lower(p.name) LIKE %s
                       OR lower(coalesce(p.purpose, '')) LIKE %s
                       OR lower(coalesce(d.name, '')) LIKE %s
                    LIMIT %s
                    """,
                    (q, q, q, limit)
                )
                results["packages"].extend(cur.fetchall())

                cur.execute(
                    """
                    SELECT c.id, c.title, d.name AS distro, c.command, c.risk_level, c.purpose
                    FROM commands c
                    LEFT JOIN distros d ON c.distro_id = d.id
                    WHERE lower(c.title) LIKE %s
                       OR lower(c.command) LIKE %s
                       OR lower(coalesce(c.purpose, '')) LIKE %s
                       OR lower(coalesce(d.name, '')) LIKE %s
                    LIMIT %s
                    """,
                    (q, q, q, q, limit)
                )
                results["commands"].extend(cur.fetchall())

    for key in results:
        results[key] = list(dict.fromkeys(results[key]))[:limit]

    return results