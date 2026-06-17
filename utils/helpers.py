import re


def extract_phones(text: str) -> list[str]:
    patterns = [
        r'\+996\s?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?\d{2}',
        r'\+7\s?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
        r'8\s?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
        r'\+?\d{1,4}\s?\(?\d{1,4}\)?[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,4}',
    ]
    phones = []
    for pat in patterns:
        matches = re.findall(pat, text)
        for m in matches:
            cleaned = re.sub(r'\s+', ' ', m).strip()
            if cleaned and cleaned not in phones:
                phones.append(cleaned)
    return phones


def extract_emails(text: str) -> list[str]:
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)
    return list(dict.fromkeys([e for e in emails if not e.endswith(('.png', '.jpg', '.gif'))]))


def extract_social_links(text: str) -> dict[str, str]:
    socials = {}
    patterns = {
        "Instagram": r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+',
        "Telegram": r'https?://(?:t\.me|telegram\.me)/[a-zA-Z0-9_]+',
        "WhatsApp": r'https?://wa\.me/\d+',
        "YouTube": r'https?://(?:www\.)?youtube\.com/(?:c/|channel/|@)[a-zA-Z0-9_-]+',
        "Facebook": r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9.]+',
        "VK": r'https?://(?:www\.)?vk\.com/[a-zA-Z0-9_]+',
        "TikTok": r'https?://(?:www\.)?tiktok\.com/@[a-zA-Z0-9_.]+',
        "Odnoklassniki": r'https?://(?:www\.)?ok\.ru/[a-zA-Z0-9_.]+',
    }
    for name, pat in patterns.items():
        matches = re.findall(pat, text)
        if matches:
            socials[name] = matches[0]
    return socials


def clean_phone(phone: str) -> str:
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    return cleaned


def format_phone_basic(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10:
        return f"+7 ({digits[:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:]}"
    if len(digits) == 11:
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        return f"+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:]}"
    if len(digits) == 12 and digits.startswith("996"):
        return f"+{digits[:3]} ({digits[3:6]}) {digits[6:8]}-{digits[8:10]}-{digits[10:]}"
    return phone
