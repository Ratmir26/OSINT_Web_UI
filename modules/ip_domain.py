import re
import socket
import whois
import dns.resolver
import ipinfo
from utils.web_scraper import safe_get

IPINFO_TOKEN = None

try:
    from config import IPINFO_TOKEN as _token
    IPINFO_TOKEN = _token
except Exception:
    pass

IP_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)


def _is_ip(query: str) -> bool:
    return bool(IP_RE.match(query.strip()))


def _resolve_domain_ips(domain: str) -> list[str]:
    ips = []
    try:
        answers = dns.resolver.resolve(domain, "A")
        ips = [r.to_text() for r in answers]
    except Exception:
        pass
    return ips


def _dns_lookup(domain: str, record: str) -> list[str]:
    try:
        answers = dns.resolver.resolve(domain, record)
        return [r.to_text() for r in answers]
    except Exception:
        return []


def _reverse_dns(ip: str) -> str | None:
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except Exception:
        return None


def _get_ipinfo_via_http(ip: str) -> dict:
    url = f"https://ipinfo.io/{ip}/json"
    try:
        resp = safe_get(url, timeout=10)
        if resp:
            data = resp.json()
            return {
                "ip": data.get("ip", ip),
                "city": data.get("city", ""),
                "region": data.get("region", ""),
                "country": data.get("country", ""),
                "org": data.get("org", ""),
                "asn": data.get("asn", ""),
                "isp": data.get("isp", ""),
            }
    except Exception:
        pass
    return {}


def _get_ipinfo_via_library(ip: str) -> dict:
    if not IPINFO_TOKEN:
        return {}
    try:
        handler = ipinfo.handler(access_token=IPINFO_TOKEN)
        details = handler.getDetails(ip)
        data = details.all if hasattr(details, "all") else details
        if isinstance(data, dict):
            return {
                "ip": data.get("ip", ip),
                "city": data.get("city", ""),
                "region": data.get("region", ""),
                "country": data.get("country", ""),
                "org": data.get("org", ""),
                "asn": data.get("asn", ""),
                "isp": data.get("isp", ""),
            }
    except Exception:
        pass
    return {}


def lookup_ip_domain(query: str) -> dict:
    result = {
        "query": query,
        "type": "ip" if _is_ip(query) else "domain",
        "whois": {
            "registrar": "",
            "creation_date": "",
            "expiration_date": "",
            "name_servers": [],
        },
        "dns": {"a": [], "aaaa": [], "mx": [], "ns": [], "txt": []},
        "ip_info": {},
    }

    if result["type"] == "domain":
        domain = query.strip().lower()

        try:
            w = whois.whois(domain)
            result["whois"]["registrar"] = str(w.registrar or "")
            creation = w.creation_date
            if isinstance(creation, list):
                creation = creation[0] if creation else ""
            result["whois"]["creation_date"] = str(creation or "")
            expiration = w.expiration_date
            if isinstance(expiration, list):
                expiration = expiration[0] if expiration else ""
            result["whois"]["expiration_date"] = str(expiration or "")
            ns = w.name_servers
            if isinstance(ns, list):
                result["whois"]["name_servers"] = [str(n) for n in ns if n]
            elif ns:
                result["whois"]["name_servers"] = [str(ns)]
        except Exception:
            pass

        result["dns"]["a"] = _dns_lookup(domain, "A")
        result["dns"]["aaaa"] = _dns_lookup(domain, "AAAA")
        result["dns"]["mx"] = _dns_lookup(domain, "MX")
        result["dns"]["ns"] = _dns_lookup(domain, "NS")
        result["dns"]["txt"] = _dns_lookup(domain, "TXT")

        ips = result["dns"]["a"] or _resolve_domain_ips(domain)
        if ips:
            ip_info = _get_ipinfo_via_http(ips[0])
            if not ip_info:
                ip_info = _get_ipinfo_via_library(ips[0])
            result["ip_info"] = ip_info

    else:
        ip = query.strip()

        ip_info = _get_ipinfo_via_library(ip)
        if not ip_info:
            ip_info = _get_ipinfo_via_http(ip)
        result["ip_info"] = ip_info

        ptr = _reverse_dns(ip)
        if ptr:
            domain = ptr
            try:
                w = whois.whois(domain)
                result["whois"]["registrar"] = str(w.registrar or "")
                creation = w.creation_date
                if isinstance(creation, list):
                    creation = creation[0] if creation else ""
                result["whois"]["creation_date"] = str(creation or "")
                expiration = w.expiration_date
                if isinstance(expiration, list):
                    expiration = expiration[0] if expiration else ""
                result["whois"]["expiration_date"] = str(expiration or "")
                ns = w.name_servers
                if isinstance(ns, list):
                    result["whois"]["name_servers"] = [str(n) for n in ns if n]
                elif ns:
                    result["whois"]["name_servers"] = [str(ns)]
            except Exception:
                pass

            result["dns"]["a"] = _dns_lookup(domain, "A")
            result["dns"]["aaaa"] = _dns_lookup(domain, "AAAA")
            result["dns"]["mx"] = _dns_lookup(domain, "MX")
            result["dns"]["ns"] = _dns_lookup(domain, "NS")
            result["dns"]["txt"] = _dns_lookup(domain, "TXT")

    return result
