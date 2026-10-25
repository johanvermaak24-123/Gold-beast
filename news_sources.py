"""Bounded RSS fetching with UTC filtering, deduplication and diagnostics."""
import asyncio
import calendar
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from html import unescape
import os
import re
from urllib.parse import urlsplit, urlunsplit

import feedparser
import httpx

UTC = timezone.utc
# Reuters' legacy endpoint may be unavailable. Override it with a licensed feed.
FEEDS = {
    "reuters": "https://feeds.reuters.com/reuters/businessNews",
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    
    "forexlive": "https://www.forexlive.com/feed/news",
    "investing": "https://www.investing.com/rss/news_25.rss",
}
KEYWORDS = re.compile(
    r"\b(gold|xauusd|xau|federal reserve|fed|inflation|cpi|pce|dollar index|dxy|"
    r"treasury yields?|real yields?|rate hike|rate cut|safe.haven|geopolitical|"
    r"war|conflict|recession|payrolls?|jobs report|debt|deficit|debasement|fiscal|dollar|sanctions|ceasefire|peace|banking|bullion)\b", re.I
)
CREDIBILITY = {"reuters": 1.0, "cnbc": 1.0, "yahoo": .85,
               "forexlive": .8, "investing": .8}


def clean(text):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]*>", " ", text or ""))).strip()


def normalize(title):
    return re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()


def deduplicate(items):
    """Keep the most credible copy; do not count syndication as independent evidence."""
    kept = []
    for item in sorted(items, key=lambda h: CREDIBILITY.get(h["source"], .65), reverse=True):
        title = normalize(item["title"])
        parts = urlsplit(item["url"])
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        if any(url == old[0] or SequenceMatcher(None, title, old[1]).ratio() >= .88
               for old in kept):
            continue
        kept.append((url, title, item))
    return sorted((x[2] for x in kept), key=lambda h: h["published_at"], reverse=True)


async def _rss(client, source, cutoff, now):
    url = os.getenv(f"RSS_{source.upper()}_URL", FEEDS[source])
    try:
        async with asyncio.timeout(15):
            response = await client.get(url)
            response.raise_for_status()
            if len(response.content) > 2_000_000:
                raise ValueError("Feed exceeds size limit")
            parsed = await asyncio.to_thread(feedparser.parse, response.content)
        if not parsed.entries:
            raise ValueError("Empty or invalid RSS feed")
        rows, undated = [], 0
        for entry in parsed.entries[:250]:
            title, summary = clean(entry.get("title")), clean(entry.get("summary"))
            if not KEYWORDS.search(title + " " + summary):
                continue
            stamp = entry.get("published_parsed") or entry.get("updated_parsed")
            if not stamp:
                undated += 1
                continue  # Never pretend undated stories are fresh.
            published = datetime.fromtimestamp(calendar.timegm(stamp), UTC)
            link = entry.get("link", "")
            if not cutoff <= published <= now or urlsplit(link).scheme not in {"http", "https"}:
                continue
            rows.append(dict(title=title, source=source, url=link,
                             published_at=published.isoformat(), summary=summary[:1000]))
        return rows, dict(source=source, status="ok", count=len(rows), undated_skipped=undated)
    except Exception as exc:
        # Do not leak URLs, keys or provider response bodies to clients.
        return [], dict(source=source, status="unavailable", error=type(exc).__name__)


async def _newsapi(client, selected, cutoff, now):
    domains = {"reuters": "reuters.com", "cnbc": "cnbc.com", "yahoo": "finance.yahoo.com",
               "forexlive": "forexlive.com,investinglive.com", "investing": "investing.com"}
    try:
        response = await client.get("https://newsapi.org/v2/everything", params={
            "q": 'gold OR XAUUSD OR "Federal Reserve" OR inflation OR "Treasury yield"',
            "domains": ",".join(domains[s] for s in selected),
            "from": cutoff.isoformat(), "to": now.isoformat(), "language": "en",
            "sortBy": "publishedAt", "pageSize": 100,
        }, headers={"X-Api-Key": os.environ["NEWSAPI_KEY"]})
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "ok":
            raise ValueError("NewsAPI failure")
        rows = []
        for item in payload.get("articles", []):
            title, summary = clean(item.get("title")), clean(item.get("description"))
            link = item.get("url") or ""
            host = (urlsplit(link).hostname or "").lower()
            source = next((s for s in selected if any(host == d or host.endswith("." + d)
                          for d in domains[s].split(","))), None)
            try:
                published = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
                valid = published.tzinfo and cutoff <= published <= now
            except (KeyError, ValueError, TypeError):
                valid = False
            if source and valid and urlsplit(link).scheme in {"http", "https"} and KEYWORDS.search(title + " " + summary):
                rows.append(dict(title=title, source=source, url=link,
                                 published_at=published.isoformat(), summary=summary[:1000]))
        return rows, {"source": "newsapi", "status": "ok", "count": len(rows),
                      "possibly_truncated": payload.get("totalResults", 0) > 100}
    except Exception as exc:
        return [], {"source": "newsapi", "status": "unavailable", "error": type(exc).__name__}


async def fetch_news(hours=24, sources=None):
    """Returns {headlines: [...], source_status: [...]}; sources are allowlisted IDs."""
    if not 1 <= hours <= 72:
        raise ValueError("hours must be between 1 and 72")
    selected = list(dict.fromkeys(sources if sources is not None else FEEDS))
    if not selected or any(s not in FEEDS for s in selected):
        raise ValueError("Unknown sources; use: " + ", ".join(FEEDS))
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=hours)
    async with httpx.AsyncClient(timeout=10, follow_redirects=True,
                                 headers={"User-Agent": "GoldNewsScanner/1.0"}) as client:
        results = await asyncio.gather(*(_rss(client, s, cutoff, now) for s in selected))
        rows = [h for batch, _ in results for h in batch]
        statuses = [status for _, status in results]
        failed = [s["source"] for s in statuses if s["status"] != "ok"]
        if os.getenv("NEWSAPI_KEY") and (failed or not rows):
            extra, status = await _newsapi(client, failed or selected, cutoff, now)
            rows.extend(extra)
            statuses.append(status)
    return {"headlines": deduplicate(rows)[:200], "source_status": statuses}
