import os
import sys
import json
import threading
from datetime import datetime
from io import BytesIO

import mistune
from flask import Flask, render_template, request, send_file, url_for

sys.path.insert(0, os.path.dirname(__file__))

from config import RESULTS_DIR, HISTORY_DB
from osint_agent import run_osint
from modules.phone_lookup import lookup_phone
from modules.email_lookup import lookup_email
from modules.ip_domain import lookup_ip_domain
from modules.name_search import search_name
from modules.telegram_search import search_telegram
from modules.marketplace import search_wildberries, search_ozon
from modules.avito_yula import search_avito, search_yula
from modules.youtube_api import search_youtube
from modules.compare import compare_queries
from modules.visualize import graph_from_query
from modules.pdf_generator import generate_pdf_from_query
from modules.excel_export import export_to_excel_from_query
from modules.history import init_db, add_search, get_history

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

init_db(HISTORY_DB)

os.makedirs(RESULTS_DIR, exist_ok=True)

MODULES = [
    ("search", "OSINT Поиск", "Поиск информации о компании或个人 в интернете, 2GIS, Яндекс.Картах"),
    ("phone", "Пробив номера", "Регион, оператор, отзывы о номере телефона"),
    ("email", "Email утечки", "Проверка email в утечках паролей и поиск в сети"),
    ("ip", "IP / Домен", "WHOIS, DNS, IP геолокация"),
    ("name", "Поиск человека", "Поиск по имени и фамилии в VK, OK, Facebook"),
    ("telegram", "Telegram", "Поиск пользователей и каналов в Telegram"),
    ("marketplace", "Маркетплейсы", "Поиск товаров на Wildberries и Ozon"),
    ("avito", "Avito / Юла", "Поиск объявлений на Avito и Юле"),
    ("youtube", "YouTube", "Поиск каналов и видео на YouTube"),
    ("compare", "Сравнение", "Сравнение двух компаний по OSINT данным"),
    ("graph", "Граф связей", "Визуализация связей в виде графа"),
    ("history", "История", "Просмотр истории запросов"),
    ("mass", "Массовый пробив", "Массовый пробив номеров из .txt файла"),
]


def log_history(query, module, result_path=""):
    try:
        add_search(HISTORY_DB, query, module, result_path)
    except Exception:
        pass


@app.route("/")
def index():
    return render_template("index.html", modules=MODULES)


@app.route("/search", methods=["GET", "POST"])
def search():
    result = None
    result_html = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                filepath = run_osint(query)
                with open(filepath, "r", encoding="utf-8") as f:
                    result = f.read()
                result_html = mistune.html(result)
                log_history(query, "search", filepath)
            except Exception as e:
                result = f"Ошибка: {e}"
                result_html = f"<div class='alert alert-danger'>{e}</div>"
    return render_template("search.html", query=query, result=result, result_html=result_html)


@app.route("/phone", methods=["GET", "POST"])
def phone():
    result = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                result = lookup_phone(query)
                log_history(query, "phone")
            except Exception as e:
                result = {"error": str(e)}
    return render_template("phone.html", query=query, result=result)


@app.route("/email", methods=["GET", "POST"])
def email():
    result = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                result = lookup_email(query)
                log_history(query, "email")
            except Exception as e:
                result = {"error": str(e)}
    return render_template("email.html", query=query, result=result)


@app.route("/ip", methods=["GET", "POST"])
def ip():
    result = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                result = lookup_ip_domain(query)
                log_history(query, "ip")
            except Exception as e:
                result = {"error": str(e)}
    return render_template("ip.html", query=query, result=result)


@app.route("/name", methods=["GET", "POST"])
def name():
    result = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                result = search_name(query)
                log_history(query, "name")
            except Exception as e:
                result = {"error": str(e)}
    return render_template("name.html", query=query, result=result)


@app.route("/telegram", methods=["GET", "POST"])
def telegram():
    result = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                result = search_telegram(query)
                log_history(query, "telegram")
            except Exception as e:
                result = {"error": str(e)}
    return render_template("telegram.html", query=query, result=result)


@app.route("/marketplace", methods=["GET", "POST"])
def marketplace():
    wb_result = None
    ozon_result = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                wb_result = search_wildberries(query)
            except Exception as e:
                wb_result = {"error": str(e)}
            try:
                ozon_result = search_ozon(query)
            except Exception as e:
                ozon_result = {"error": str(e)}
            log_history(query, "marketplace")
    return render_template("marketplace.html", query=query, wb_result=wb_result, ozon_result=ozon_result)


@app.route("/avito", methods=["GET", "POST"])
def avito():
    avito_result = None
    yula_result = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                avito_result = search_avito(query)
            except Exception as e:
                avito_result = {"error": str(e)}
            try:
                yula_result = search_yula(query)
            except Exception as e:
                yula_result = {"error": str(e)}
            log_history(query, "avito")
    return render_template("avito_yula.html", query=query, avito_result=avito_result, yula_result=yula_result)


@app.route("/youtube", methods=["GET", "POST"])
def youtube():
    result = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                result = search_youtube(query)
                log_history(query, "youtube")
            except Exception as e:
                result = {"error": str(e)}
    return render_template("youtube.html", query=query, result=result)


@app.route("/compare", methods=["GET", "POST"])
def compare():
    result = None
    query1 = ""
    query2 = ""
    if request.method == "POST":
        query1 = request.form.get("query1", "").strip()
        query2 = request.form.get("query2", "").strip()
        if query1 and query2:
            try:
                result = compare_queries(query1, query2)
                log_history(f"{query1} | {query2}", "compare")
            except Exception as e:
                result = {"error": str(e)}
    return render_template("compare.html", query1=query1, query2=query2, result=result)


@app.route("/graph", methods=["GET", "POST"])
def graph():
    image_url = None
    query = ""
    error = None
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in query).strip()[:30]
                filename = f"graph_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                output_path = os.path.join(RESULTS_DIR, filename)
                graph_from_query(query, output_path)
                image_url = url_for("download_file", filename=filename)
                log_history(query, "graph", output_path)
            except Exception as e:
                error = str(e)
    return render_template("graph.html", query=query, image_url=image_url, error=error)


@app.route("/export/pdf", methods=["POST"])
def export_pdf():
    query = request.form.get("query", "").strip()
    if not query:
        return "Укажи запрос", 400
    try:
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in query).strip()[:30]
        filename = f"report_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(RESULTS_DIR, filename)
        generate_pdf_from_query(query, output_path)
        log_history(query, "export_pdf", output_path)
        return send_file(output_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return str(e), 500


@app.route("/export/excel", methods=["POST"])
def export_excel():
    query = request.form.get("query", "").strip()
    if not query:
        return "Укажи запрос", 400
    try:
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in query).strip()[:30]
        filename = f"report_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        output_path = os.path.join(RESULTS_DIR, filename)
        export_to_excel_from_query(query, output_path)
        log_history(query, "export_excel", output_path)
        return send_file(output_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return str(e), 500


@app.route("/download/<path:filename>")
def download_file(filename):
    filepath = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(filepath):
        return "Файл не найден", 404
    return send_file(filepath)


@app.route("/history")
def history():
    limit = request.args.get("limit", 50, type=int)
    records = []
    try:
        records = get_history(HISTORY_DB, limit=limit)
    except Exception as e:
        records = []
    return render_template("history.html", records=records)


@app.route("/mass", methods=["GET", "POST"])
def mass():
    results = []
    query = ""
    if request.method == "POST":
        if "file" in request.files:
            file = request.files["file"]
            if file and file.filename.endswith(".txt"):
                content = file.read().decode("utf-8")
                numbers = [line.strip() for line in content.splitlines() if line.strip()]
                for num in numbers:
                    try:
                        res = lookup_phone(num)
                        results.append({"number": num, "result": res, "error": None})
                    except Exception as e:
                        results.append({"number": num, "result": None, "error": str(e)})
            else:
                query = request.form.get("query", "").strip()
                if query:
                    numbers = [n.strip() for n in query.replace(",", " ").split() if n.strip()]
                    for num in numbers:
                        try:
                            res = lookup_phone(num)
                            results.append({"number": num, "result": res, "error": None})
                        except Exception as e:
                            results.append({"number": num, "result": None, "error": str(e)})
    return render_template("mass.html", results=results)


if __name__ == "__main__":
    print(f"OSINT Web UI запущен: http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
