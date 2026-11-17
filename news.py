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


# ------------------------------------------------------------------------------
# Direct link to the original article
# Google News RSS links are news.google.com redirects. The post must link the publisher directly,
# so the headline is looked up in Bing's public RSS search, whose results carry the real URL.
# ------------------------------------------------------------------------------
BROWSER_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"}
_REDIRECT_HOSTS = ("news.google.", "bing.com", "msn.com", "yahoo.com")


def _words(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower())) - {"the", "a", "an", "of", "to", "in", "for", "and", "on", "over", "by"}


def _host(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).netloc.lower().removeprefix("www.")


def _bing_rss(url: str) -> list:
    """Returns [(title, real_url, source)] from a Bing RSS search."""
    from urllib.parse import urlparse, parse_qs
    import html as _html
    try:
        res = requests.get(url, headers=BROWSER_HEADERS, timeout=20)
        if res.status_code != 200:
            return []
        root = ET.fromstring(res.content)
    except Exception as e:
        print(f"Notice: Bing lookup failed ({e})")
        return []
    out = []
    for it in root.findall(".//item"):
        link = _html.unescape(it.findtext("link") or "")
        real = parse_qs(urlparse(link).query).get("url", [link])[0]  # Bing News wraps it as ?url=
        src = ""
        for child in it:
            if child.tag.lower().endswith("source"):
                src = (child.text or "").strip()
        out.append((_html.unescape(it.findtext("title") or ""), real, src))
    return out


def find_direct_link(item: dict) -> str:
    """
    Finds the publisher's own URL for a Google News item (never a Google/Bing/MSN redirect).
    Returns "" if no confident match is found.
    """
    headline = item["headline"]
    want = _words(headline)
    if not want:
        return ""
    candidates = _bing_rss(f"https://www.bing.com/news/search?q={quote_plus(headline)}&format=rss")
    if not candidates and item.get("source"):
        candidates = _bing_rss(f"https://www.bing.com/news/search?q={quote_plus(headline + ' ' + item['source'])}&format=rss")
    best, best_score = "", 0.0
    source_words = _words(item.get("source", ""))
    for title, url, src in candidates:
        if not url.startswith("http") or any(h in _host(url) for h in _REDIRECT_HOSTS):
            continue
        got = _words(title)
        score = len(want & got) / len(want)
        # Same outlet (by name or domain) is a strong sign it's the same story.
        if source_words and (source_words & _words(src) or any(w in _host(url) for w in source_words if len(w) > 3)):
            score += 0.15
        if score > best_score:
            best, best_score = url, score
    if best_score >= 0.75:
        print(f"   Direct link: {best} (match {best_score:.2f})")
        return best
    print(f"   No direct link found for: {headline} (best match {best_score:.2f})")
    return ""
