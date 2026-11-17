"""
Google News headlines for the daily auto-publisher.

Fetches the Google News RSS search feed (same results as news.google.com search),
keeps only news that matters to California workers' rights (OpenAI judges relevance, because
words like "harassment" or "overtime" also show up in crime, sports and business stories), newest first.
"""
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

import site_config as cfg

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; atoyanlaw-publisher/1.0)"}


def fetch_google_news(query: str = None, when: str = None) -> list:
    """Returns feed items: [{headline, source, link, published (UTC datetime)}], newest first."""
    query = query or cfg.NEWS_QUERY
    when = when or cfg.NEWS_WINDOW
    url = (
        "https://news.google.com/rss/search?q="
        + quote_plus(f"{query} when:{when}")
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    # Google News sometimes answers 503/429 to cloud servers (GitHub Actions); retry with a pause.
    waits = [10, 30, 60, 120]
    for attempt in range(len(waits) + 1):
        try:
            res = requests.get(url, headers=HEADERS, timeout=20)
            if res.status_code not in (429, 500, 502, 503, 504):
                break
            problem = f"HTTP {res.status_code}"
        except requests.RequestException as e:
            res, problem = None, str(e)
        if attempt == len(waits):
            raise RuntimeError(f"Google News unavailable after {attempt + 1} tries ({problem})")
        print(f"Google News: {problem}, retrying in {waits[attempt]}s...")
        time.sleep(waits[attempt])
    res.raise_for_status()
    root = ET.fromstring(res.content)

    items, seen = [], set()
    for it in root.findall(".//item"):
        title = (it.findtext("title") or "").strip()
        source = (it.findtext("source") or "").strip()
        # Google appends " - Publisher" to titles
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3].strip()
        if not title or title.lower() in seen:
            continue
        if source.lower() in [s.lower() for s in cfg.NEWS_SOURCE_BLOCKLIST]:
            continue
        seen.add(title.lower())
        try:
            published = parsedate_to_datetime(it.findtext("pubDate"))
        except Exception:
            published = datetime.now(timezone.utc)
        items.append({
            "headline": title,
            "source": source,
            "link": (it.findtext("link") or "").strip(),
            "published": published,
        })

    # Google sometimes returns old stories despite "when:"; drop anything older than NEWS_MAX_AGE_DAYS.
    max_age = getattr(cfg, "NEWS_MAX_AGE_DAYS", None)
    if max_age:
        cutoff = datetime.now(timezone.utc).timestamp() - max_age * 86400
        items = [i for i in items if i["published"].timestamp() >= cutoff]

    items.sort(key=lambda x: x["published"], reverse=True)
    return items


def _keyword_filter(items: list) -> list:
    """Fallback when OpenAI is unavailable: headline must contain an employment-law keyword."""
    legal = re.compile(
        r"\b(employment law|employees?|workers?|workplace|wrongful(ly)? (termination|terminated|fired)|"
        r"discriminat\w*|harass\w*|retaliat\w*|wages?|overtime|labor (code|law|commissioner)|"
        r"workers'? comp\w*|EEOC|Civil Rights Department|Cal/OSHA|paid sick leave)\b",
        re.I,
    )
    return [dict(i, title=i["headline"]) for i in items if legal.search(i["headline"])]


def pick_medical_headlines(items: list, limit: int = 10) -> list:  # name kept from the publisher family
    """
    Keeps only headlines that matter to California workers' rights, newest first.
    Adds 'title': an original, SEO-friendly blog title for atoyanlaw.com.
    """
    if not items:
        return []
    candidates = items[:40]
    listing = "\n".join(f"{n}. {i['headline']} ({i['source']})" for n, i in enumerate(candidates))

    try:
        from generator import _get_client, _model
        response = _get_client().chat.completions.create(
            model=_model(),
            messages=[{"role": "user", "content": cfg.NEWS_PICK_PROMPT.format(listing=listing)}],
            response_format={"type": "json_object"},
            max_tokens=1500,
            temperature=0.2,
        )
        data = json.loads(response.choices[0].message.content)
        picked = []
        for p in data.get("picks", []):
            idx = int(p.get("index", -1))
            if 0 <= idx < len(candidates) and p.get("title"):
                picked.append(dict(candidates[idx], title=str(p["title"]).strip().replace("—", "-")))
        picked.sort(key=lambda x: x["published"], reverse=True)
        return picked[:limit]
    except Exception as e:
        print(f"Notice: OpenAI headline selection failed ({e}); using keyword filter.")
        return _keyword_filter(candidates)[:limit]
