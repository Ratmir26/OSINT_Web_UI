import re
import json
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from utils.web_scraper import safe_get, get_soup


def _search_ddg(query: str) -> list[dict]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    soup = get_soup(url)
    results = []
    if not soup:
        return results
    for item in soup.select("div.result"):
        title_el = item.select_one("h2 a")
        snippet_el = item.select_one("a.result__snippet")
        link = ""
        title = ""
        if title_el:
            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            if link.startswith("//"):
                link = "https:" + link
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        if title or link:
            results.append({"title": title, "link": link, "snippet": snippet})
    return results


def _parse_youtube_links(results: list[dict]) -> tuple[list[dict], list[dict]]:
    channels = []
    videos = []
    for r in results:
        link = r.get("link", "")
        title = r.get("title", "")
        snippet = r.get("snippet", "")

        channel_match = re.search(
            r"(?:youtube\.com/(?:c/|channel/|@))([a-zA-Z0-9_-]+)", link
        )
        video_match = re.search(
            r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)", link
        )

        if channel_match:
            channels.append({
                "id": channel_match.group(1),
                "title": title,
                "url": link,
                "description": snippet,
            })
        elif video_match:
            videos.append({
                "id": video_match.group(1),
                "title": title,
                "url": link,
                "channel": "",
                "description": snippet,
                "published": "",
            })
    return channels, videos


def _parse_channel_page(channel_url: str) -> dict:
    resp = safe_get(channel_url)
    if not resp:
        return {}
    soup = BeautifulSoup(resp.text, "lxml")

    title = ""
    description = ""
    subscribers = ""
    videos = ""

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"]

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        description = og_desc["content"]

    text = soup.get_text(separator=" ", strip=True)

    sub_match = re.search(r"([\d.,]+)\s*подписчиков", text, re.I)
    if sub_match:
        subscribers = sub_match.group(1)

    vid_match = re.search(r"([\d.,]+)\s*видео", text, re.I)
    if vid_match:
        videos = vid_match.group(1)

    return {
        "title": title,
        "url": channel_url,
        "subscribers": subscribers,
        "videos": videos,
        "description": description,
    }


def _api_search(query: str, api_key: str, max_results: int) -> dict:
    search_url = (
        f"https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&q={quote_plus(query)}"
        f"&type=channel,video&maxResults={max_results}&key={api_key}"
    )
    resp = safe_get(search_url)
    if not resp:
        return {}

    try:
        data = resp.json()
    except json.JSONDecodeError:
        return {}

    items = data.get("items", [])
    channels = []
    videos = []
    channel_ids = []

    for item in items:
        id_info = item.get("id", {})
        snippet = item.get("snippet", {})

        if id_info.get("kind") == "youtube#channel":
            channel_id = id_info.get("channelId", "")
            channel_ids.append(channel_id)
            channels.append({
                "channelId": channel_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            })
        elif id_info.get("kind") == "youtube#video":
            videos.append({
                "videoId": id_info.get("videoId", ""),
                "title": snippet.get("title", ""),
                "channelTitle": snippet.get("channelTitle", ""),
                "description": snippet.get("description", ""),
                "publishedAt": snippet.get("publishedAt", ""),
            })

    if channel_ids:
        stats_url = (
            f"https://www.googleapis.com/youtube/v3/channels"
            f"?part=statistics&id={','.join(channel_ids)}&key={api_key}"
        )
        stats_resp = safe_get(stats_url)
        if stats_resp:
            try:
                stats_data = stats_resp.json()
                stats_items = stats_data.get("items", [])
                stats_map = {}
                for s in stats_items:
                    sid = s.get("id", "")
                    stat = s.get("statistics", {})
                    stats_map[sid] = {
                        "subscriberCount": stat.get("subscriberCount", ""),
                        "videoCount": stat.get("videoCount", ""),
                    }
                for ch in channels:
                    sid = ch["channelId"]
                    if sid in stats_map:
                        ch["subscriberCount"] = stats_map[sid]["subscriberCount"]
                        ch["videoCount"] = stats_map[sid]["videoCount"]
            except json.JSONDecodeError:
                pass

    result_channels = []
    for ch in channels:
        result_channels.append({
            "title": ch["title"],
            "url": f"https://www.youtube.com/channel/{ch['channelId']}",
            "subscribers": ch.get("subscriberCount", ""),
            "videos": ch.get("videoCount", ""),
            "description": ch["description"],
        })

    result_videos = []
    for v in videos:
        result_videos.append({
            "title": v["title"],
            "url": f"https://www.youtube.com/watch?v={v['videoId']}",
            "channel": v["channelTitle"],
            "views": "",
            "published": v["publishedAt"],
        })

    return {
        "channels": result_channels,
        "videos": result_videos,
    }


def _ddg_fallback(query: str) -> dict:
    raw = _search_ddg(f"{query} YouTube channel")
    channels, videos = _parse_youtube_links(raw)

    parsed_channels = []
    for ch in channels[:5]:
        info = _parse_channel_page(ch["url"])
        if info.get("title"):
            parsed_channels.append(info)
        else:
            parsed_channels.append(ch)

    if not parsed_channels:
        raw2 = _search_ddg(f"{query} YouTube video")
        more_v, _ = _parse_youtube_links(raw2)
        videos.extend(more_v)

    result_channels = []
    for ch in parsed_channels:
        result_channels.append({
            "title": ch.get("title", ""),
            "url": ch.get("url", ""),
            "subscribers": ch.get("subscribers", ""),
            "videos": ch.get("videos", ""),
            "description": ch.get("description", ""),
        })

    result_videos = []
    for v in videos[:5]:
        result_videos.append({
            "title": v.get("title", ""),
            "url": v.get("url", ""),
            "channel": v.get("channel", ""),
            "views": "",
            "published": v.get("published", ""),
        })

    return {
        "channels": result_channels,
        "videos": result_videos,
    }


def search_youtube(query: str, api_key: str = "", max_results: int = 5) -> dict:
    if api_key:
        try:
            result = _api_search(query, api_key, max_results)
            if result.get("channels") or result.get("videos"):
                result["query"] = query
                return result
        except Exception:
            pass

    fallback = _ddg_fallback(query)
    fallback["query"] = query
    return fallback
