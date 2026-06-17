import os
import sys
import json
from datetime import datetime
from fpdf import FPDF


def _find_unicode_font() -> str | None:
    candidates = [
        "C:/Windows/Fonts/DejaVuSans.ttf",
        "C:/Windows/Fonts/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/times.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    for root, dirs, files in os.walk("C:/Windows/Fonts"):
        for f in files:
            if f.lower().endswith(".ttf"):
                return os.path.join(root, f)
    return None


def generate_pdf_report(data: dict, query: str, output_path: str) -> str:
    pdf = FPDF()
    pdf.add_page()

    font_path = _find_unicode_font()
    if font_path:
        pdf.add_font("UniFont", "", font_path, uni=True)
        pdf.set_font("UniFont", "", 12)
        fname = "UniFont"
    else:
        pdf.set_font("Helvetica", "", 12)
        fname = "Helvetica"

    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    pdf.set_font(fname, "B", 18)
    pdf.cell(0, 12, f"OSINT Досье: {query}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fname, "", 10)
    pdf.cell(0, 8, f"Дата отчёта: {now}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    web_results = data.get("web", [])
    if web_results:
        pdf.set_font(fname, "B", 14)
        pdf.cell(0, 10, "Поиск в интернете", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font(fname, "", 11)
        for r in web_results[:10]:
            title = r.get("title", "")
            link = r.get("link", "")
            snippet = r.get("snippet", "")
            pdf.set_font(fname, "B", 11)
            pdf.multi_cell(0, 7, title[:200] if title else "")
            pdf.set_font(fname, "", 9)
            pdf.multi_cell(0, 5, link[:120] if link else "")
            if snippet:
                pdf.set_font(fname, "", 10)
                pdf.multi_cell(0, 6, snippet[:300])
            pdf.ln(3)
        pdf.ln(4)

    gis = data.get("2gis", {})
    if gis:
        pdf.set_font(fname, "B", 14)
        pdf.cell(0, 10, "2GIS Данные", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font(fname, "", 11)
        fields = [
            ("Название", gis.get("name", "—")),
            ("Адрес", gis.get("address", "—")),
            ("Рейтинг", gis.get("rating", "—")),
            ("Кол-во отзывов", str(gis.get("reviews_count", ""))),
            ("Телефоны", ", ".join(gis.get("phones", [])) if gis.get("phones") else "—"),
            ("Сайт", gis.get("website", "—")),
        ]
        for label, value in fields:
            if value and value != "—":
                pdf.set_font(fname, "B", 11)
                pdf.cell(0, 7, f"{label}: ", new_x="END")
                pdf.set_font(fname, "", 11)
                pdf.multi_cell(0, 7, value)
        if gis.get("emails"):
            pdf.set_font(fname, "B", 11)
            pdf.cell(0, 7, "Email: ", new_x="END")
            pdf.set_font(fname, "", 11)
            pdf.multi_cell(0, 7, ", ".join(gis["emails"]))
        if gis.get("socials"):
            pdf.set_font(fname, "B", 11)
            pdf.cell(0, 7, "Соцсети:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(fname, "", 11)
            for sname, surl in gis["socials"].items():
                pdf.multi_cell(0, 7, f"  {sname}: {surl}")
        pdf.ln(4)

    yndx = data.get("yandex", {})
    if yndx:
        pdf.set_font(fname, "B", 14)
        pdf.cell(0, 10, "Яндекс.Карты", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font(fname, "", 11)
        fields = [
            ("Название", yndx.get("name", "—")),
            ("Адрес", yndx.get("address", "—")),
            ("Телефоны", ", ".join(yndx.get("phones", [])) if yndx.get("phones") else "—"),
            ("Часы работы", yndx.get("hours", "—")),
            ("Рейтинг", yndx.get("rating", "—")),
        ]
        for label, value in fields:
            if value and value != "—":
                pdf.set_font(fname, "B", 11)
                pdf.cell(0, 7, f"{label}: ", new_x="END")
                pdf.set_font(fname, "", 11)
                pdf.multi_cell(0, 7, value)
        if yndx.get("url"):
            pdf.set_font(fname, "B", 11)
            pdf.cell(0, 7, "Ссылка: ", new_x="END")
            pdf.set_font(fname, "", 11)
            pdf.multi_cell(0, 7, yndx["url"])
        pdf.ln(4)

    web = data.get("webpage", {})
    if web:
        pdf.set_font(fname, "B", 14)
        pdf.cell(0, 10, "Контакты (с сайта)", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font(fname, "", 11)
        phones = web.get("phones", [])
        if phones:
            pdf.set_font(fname, "B", 11)
            pdf.cell(0, 7, "Телефоны: ", new_x="END")
            pdf.set_font(fname, "", 11)
            pdf.multi_cell(0, 7, ", ".join(phones))
        emails = web.get("emails", [])
        if emails:
            pdf.set_font(fname, "B", 11)
            pdf.cell(0, 7, "Email: ", new_x="END")
            pdf.set_font(fname, "", 11)
            pdf.multi_cell(0, 7, ", ".join(emails))
        if web.get("socials"):
            pdf.set_font(fname, "B", 11)
            pdf.cell(0, 7, "Соцсети (на сайте):", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(fname, "", 11)
            for sname, surl in web["socials"].items():
                pdf.multi_cell(0, 7, f"  {sname}: {surl}")
        pdf.ln(4)

    soc = data.get("socials", {})
    if soc:
        pdf.set_font(fname, "B", 14)
        pdf.cell(0, 10, "Социальные сети", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font(fname, "", 11)
        for name, url in soc.items():
            pdf.multi_cell(0, 7, f"{name}: {url}")
        pdf.ln(4)

    pdf.ln(10)
    pdf.set_font(fname, "", 9)
    pdf.cell(0, 7, "---", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "Сгенерировано OSINT Agent", new_x="LMARGIN", new_y="NEXT")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    pdf.output(output_path)
    return output_path


def generate_pdf_from_query(query: str, output_path: str) -> str:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from osint_agent import run_osint

    filepath = run_osint(query)
    json_path = filepath.replace(".md", "_raw.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    return generate_pdf_report(data, query, output_path)
