import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def safe_get(url: str, timeout=15, retries=2) -> requests.Response | None:
    for attempt in range(retries + 1):
        try:
            resp = SESSION.get(url, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                return resp
        except Exception:
            pass
        time.sleep(1)
    return None


def get_soup(url: str, timeout=15) -> BeautifulSoup | None:
    resp = safe_get(url, timeout=timeout)
    if not resp:
        return None
    return BeautifulSoup(resp.text, "lxml")


def safe_post(url: str, data=None, json=None, timeout=15) -> requests.Response | None:
    try:
        resp = SESSION.post(url, data=data, json=json, timeout=timeout)
        if resp.status_code == 200:
            return resp
    except Exception:
        pass
    return None
