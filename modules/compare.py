import json
import os
from osint_agent import run_osint


def _load_data(query: str) -> dict:
    filepath = run_osint(query)
    json_path = filepath.replace(".md", "_raw.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def compare_queries(queries: list[str]) -> str:
    rows = []
    for query in queries:
        data = _load_data(query)

        gis = data.get("2gis", {}) or {}
        yandex = data.get("yandex", {}) or {}
        webpage = data.get("webpage", {}) or {}
        socials = data.get("socials", {}) or {}
        web_results = data.get("web", []) or []

        all_phones = []
        for src in [gis, yandex, webpage]:
            phones = src.get("phones", []) or []
            all_phones.extend(phones if isinstance(phones, list) else [])

        all_emails = []
        for src in [gis, webpage]:
            emails = src.get("emails", []) or []
            all_emails.extend(emails if isinstance(emails, list) else [])

        contacts = list(set(all_phones + all_emails))

        profiles = []
        if isinstance(socials, dict):
            profiles.extend(socials.keys())
        web_socials = webpage.get("socials", {}) or {}
        if isinstance(web_socials, dict):
            for k in web_socials:
                if k not in profiles:
                    profiles.append(k)

        rows.append({
            "query": query,
            "gis_name": gis.get("name", ""),
            "gis_address": gis.get("address", ""),
            "yandex_name": yandex.get("name", ""),
            "yandex_address": yandex.get("address", ""),
            "contacts": contacts,
            "socials": profiles,
            "web_count": len(web_results),
        })

    header = "| Параметр | " + " | ".join(r["query"] for r in rows) + " |"
    sep = "|" + "|".join("---" for _ in range(len(rows) + 1)) + "|"

    def _gis_cell(row):
        parts = []
        if row["gis_name"]:
            parts.append(f"✅ {row['gis_name']}")
        if row["gis_address"]:
            parts.append(f"📍 {row['gis_address']}")
        return "; ".join(parts) if parts else "❌"

    def _yandex_cell(row):
        parts = []
        if row["yandex_name"]:
            parts.append(f"✅ {row['yandex_name']}")
        if row["yandex_address"]:
            parts.append(f"📍 {row['yandex_address']}")
        return "; ".join(parts) if parts else "❌"

    def _contacts_cell(row):
        if row["contacts"]:
            return ", ".join(row["contacts"][:5])
        return "❌"

    def _socials_cell(row):
        if row["socials"]:
            return ", ".join(row["socials"])
        return "❌"

    lines = [header, sep]
    lines.append("| 2GIS | " + " | ".join(_gis_cell(r) for r in rows) + " |")
    lines.append("| Яндекс.Карты | " + " | ".join(_yandex_cell(r) for r in rows) + " |")
    lines.append("| Контакты | " + " | ".join(_contacts_cell(r) for r in rows) + " |")
    lines.append("| Соцсети | " + " | ".join(_socials_cell(r) for r in rows) + " |")
    lines.append("| Веб-результаты | " + " | ".join(str(r["web_count"]) for r in rows) + " |")

    return "\n".join(lines)
