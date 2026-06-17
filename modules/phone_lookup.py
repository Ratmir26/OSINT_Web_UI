import re
from bs4 import BeautifulSoup
from utils.web_scraper import safe_get, get_soup
from utils.helpers import extract_phones, clean_phone, format_phone_basic


def _extract_def_code(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('7') and len(digits) >= 4:
        return digits[1:4]
    if digits.startswith('8') and len(digits) >= 4:
        return digits[1:4]
    if len(digits) >= 3:
        return digits[:3]
    return ''


def _extract_number_part(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('7') and len(digits) >= 7:
        return digits[1:7]
    if digits.startswith('8') and len(digits) >= 7:
        return digits[1:7]
    return digits[:6]


def _parse_mysmsbox(phone: str) -> dict:
    result = {"region": "", "source_urls": []}
    code = _extract_def_code(phone)
    if not code:
        return result

    url = f"https://mysmsbox.ru/phone-search/{code}"
    soup = get_soup(url)
    if not soup:
        return result

    result["source_urls"].append(url)
    region_el = soup.select_one(".region-info, .phone-info, .info-text")
    if region_el:
        result["region"] = region_el.get_text(strip=True)
    return result


def _parse_phoneregion(phone: str) -> dict:
    result = {"region": "", "operator": "", "source_urls": []}
    part = _extract_number_part(phone)
    if not part:
        return result

    url = f"https://phoneregion.ru/number/{part}"
    soup = get_soup(url)
    if not soup:
        return result

    result["source_urls"].append(url)
    for row in soup.select("table tr, .info-row"):
        cells = row.find_all("td") if row.name == "tr" else row.find_all(["dt", "dd"])
        text = row.get_text(" ", strip=True).lower()
        if "оператор" in text or "operator" in text:
            vals = [c.get_text(strip=True) for c in cells]
            if len(vals) > 1:
                result["operator"] = vals[-1]
        if "регион" in text or "region" in text or "город" in text:
            vals = [c.get_text(strip=True) for c in cells]
            if len(vals) > 1:
                result["region"] = vals[-1]

    info_el = soup.select_one(".number-info, .phone-info")
    if info_el:
        text = info_el.get_text(" ", strip=True)
        if not result["operator"]:
            m = re.search(r'оператор[:\s]+(.+?)(?:,|\.|$)', text, re.I)
            if m:
                result["operator"] = m.group(1).strip()
        if not result["region"]:
            m = re.search(r'регион[:\s]+(.+?)(?:,|\.|$)', text, re.I)
            if m:
                result["region"] = m.group(1).strip()

    return result


def _parse_nomernoi(phone: str) -> dict:
    result = {"reviews": [], "source_urls": []}
    cleaned = clean_phone(phone)
    url = f"https://nomernoi.ru/number/{cleaned}"
    soup = get_soup(url)
    if not soup:
        return result

    result["source_urls"].append(url)
    for block in soup.select(".comment, .review, .otzuv, .message"):
        text = block.get_text(" ", strip=True)
        if text and len(text) > 5:
            result["reviews"].append(text)

    for item in soup.select("li, .review-item, .comment-item"):
        text = item.get_text(" ", strip=True)
        if text and len(text) > 5:
            result["reviews"].append(text)

    return result


def _parse_kodysu(phone: str) -> dict:
    result = {"region": "", "operator": "", "source_urls": []}
    code = _extract_def_code(phone)
    if not code:
        return result

    url = f"https://kody.su/code/{code}"
    soup = get_soup(url)
    if not soup:
        return result

    result["source_urls"].append(url)
    content = soup.get_text(" ", strip=True)
    m_region = re.search(r'(?:регион|город|страна)[:\s]+([^\n,.]+)', content, re.I)
    if m_region:
        result["region"] = m_region.group(1).strip()
    m_operator = re.search(r'(?:оператор|провайдер)[:\s]+([^\n,.]+)', content, re.I)
    if m_operator:
        result["operator"] = m_operator.group(1).strip()

    if not result["operator"]:
        for el in soup.select(".code-info, .info-block, .def-info"):
            text = el.get_text(" ", strip=True).lower()
            if "оператор" in text or "провайдер" in text:
                result["operator"] = el.get_text(" ", strip=True)
                break

    if not result["region"]:
        for el in soup.select(".code-info, .info-block, .def-info"):
            text = el.get_text(" ", strip=True).lower()
            if "регион" in text or "город" in text:
                result["region"] = el.get_text(" ", strip=True)
                break

    return result


def lookup_phone(phone: str) -> dict:
    result = {
        "phone": phone,
        "region": "",
        "operator": "",
        "reviews": [],
        "source_urls": [],
    }

    mysmsbox = _parse_mysmsbox(phone)
    if mysmsbox["region"]:
        result["region"] = mysmsbox["region"]
    result["source_urls"].extend(mysmsbox["source_urls"])

    phoneregion = _parse_phoneregion(phone)
    if phoneregion["region"] and not result["region"]:
        result["region"] = phoneregion["region"]
    if phoneregion["operator"]:
        result["operator"] = phoneregion["operator"]
    result["source_urls"].extend(phoneregion["source_urls"])

    nomernoi = _parse_nomernoi(phone)
    if nomernoi["reviews"]:
        result["reviews"] = nomernoi["reviews"]
    result["source_urls"].extend(nomernoi["source_urls"])

    kodysu = _parse_kodysu(phone)
    if kodysu["region"] and not result["region"]:
        result["region"] = kodysu["region"]
    if kodysu["operator"] and not result["operator"]:
        result["operator"] = kodysu["operator"]
    result["source_urls"].extend(kodysu["source_urls"])

    result["source_urls"] = list(dict.fromkeys(result["source_urls"]))

    return result
