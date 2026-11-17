"""
Repairs published blog posts:
1. Replaces [sp_easyaccordion id="N"] shortcodes with the inline HTML FAQ.
2. Replaces news.google.com redirect links in the "Source:" line with the publisher's direct URL
   (nofollow), found with news.find_direct_link.

Why: atoyanlaw.com's theme does not run shortcodes in blog posts, so visitors see the raw
"[sp_easyaccordion id=...]" text instead of the FAQ. The questions and answers are read from the
Easy Accordion record (GET /wp-json/autopilot/v1/accordion/<id>, bridge plugin) and written into
the post as HTML, in the same card style (see wp_publisher.generate_faq_accordion_html).

Usage:
    python repair_faq.py --posts 4942,4938 --dry-run   # show what would change
    python repair_faq.py --posts 4942,4938             # update the posts
"""
import argparse
import os
import re
import sys

import html

import requests

from autopublish import load_combined_secret  # noqa: F401  (loads the AUTOMATION secret on import)
import site_config as cfg
import news
from wp_publisher import _wp, DEFAULT_HEADERS, generate_faq_accordion_html, purge_cache

SHORTCODE_RE = re.compile(r'\[sp_easyaccordion\s+id=["“”″]?(\d+)["“”″]?\s*\]')


def accordion_faqs(acc_id: int) -> list:
    wp_url, _ = _wp()
    res = requests.get(f"{wp_url}/wp-json/autopilot/v1/accordion/{acc_id}", headers=DEFAULT_HEADERS, timeout=20)
    res.raise_for_status()
    upload = res.json().get("upload_options") or {}
    while isinstance(upload, list) and upload:  # records made by the bridge are stored wrapped in a list
        upload = upload[0]
    items = []
    for it in (upload or {}).get("accordion_content_source", []) or []:
        q = (it.get("accordion_content_title") or "").strip()
        a = (it.get("accordion_content_description") or "").strip()
        if q and a:
            items.append({"question": q, "answer": a})
    return items


SOURCE_RE = re.compile(
    r'<a href="(https://news\.google\.com/[^"]+)"[^>]*>(.*?)</a>\s*\(([^)]*)\)', re.S)


def fix_source_links(post_id: int, raw: str) -> str:
    def repl(m):
        headline = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        source = html.unescape(m.group(3)).strip()
        direct = news.find_direct_link({"headline": headline, "source": source})
        if not direct:
            print(f"   Post {post_id}: no direct link found for '{headline}'; source link left as is.")
            return m.group(0)
        print(f"   Post {post_id}: source link -> {direct}")
        return (f'<a href="{html.escape(direct)}" target="_blank" rel="nofollow noopener noreferrer">'
                f'{m.group(2)}</a> ({m.group(3)})')
    return SOURCE_RE.sub(repl, raw)


def repair(post_id: int, dry_run: bool) -> bool:
    wp_url, auth = _wp()
    res = requests.get(f"{wp_url}/wp-json/wp/v2/posts/{post_id}", params={"context": "edit"},
                       auth=auth, headers=DEFAULT_HEADERS, timeout=30)
    if res.status_code != 200:
        print(f"❌ Post {post_id}: HTTP {res.status_code} {res.text[:200]}")
        return False
    raw = res.json()["content"]["raw"]
    new = fix_source_links(post_id, raw)
    matches = list(SHORTCODE_RE.finditer(new))
    if not matches and new == raw:
        print(f"✔ Post {post_id}: nothing to repair.")
        return True

    heading = f"{cfg.H2_OPEN_TAG}{cfg.FAQ_HEADING}</h2>"
    for m in matches:
        faqs = accordion_faqs(int(m.group(1)))
        if not faqs:
            print(f"❌ Post {post_id}: accordion {m.group(1)} has no questions; left as is.")
            return False
        block = generate_faq_accordion_html(faqs, uid=m.group(1)).strip()
        # Our posts already have the FAQ heading right before the shortcode; don't add a second one.
        before = new[:new.find(m.group(0))].rstrip()
        if before.endswith(heading) or before.lower().endswith("frequently asked questions</h2>"):
            block = block[block.find("</h2>") + 5:].strip()
        new = new.replace(m.group(0), block, 1)
        print(f"   Post {post_id}: accordion {m.group(1)} -> {len(faqs)} inline questions")

    if dry_run:
        print(f"(dry run) Post {post_id} would be updated.")
        return True
    upd = requests.post(f"{wp_url}/wp-json/wp/v2/posts/{post_id}", json={"content": new},
                        auth=auth, headers=DEFAULT_HEADERS, timeout=40)
    if upd.status_code != 200:
        print(f"❌ Post {post_id}: update failed HTTP {upd.status_code} {upd.text[:200]}")
        return False
    purge_cache(post_id)
    print(f"✅ Post {post_id} updated: {upd.json().get('link')}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--posts", required=True, help="comma-separated post IDs")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    ids = [int(x) for x in re.findall(r"\d+", args.posts)]
    ok = all([repair(i, args.dry_run) for i in ids])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
