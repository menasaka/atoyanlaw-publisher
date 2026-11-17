import os
import random
import re
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

import site_config as cfg
from processor import extract_yoast_description
from image_maker import cleanup_local_images, IMAGE_CREDITS

load_dotenv()

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

_CATEGORY_CACHE = {}


def _wp():
    """Reads credentials at call time so Streamlit secrets loaded after import still work."""
    url = os.getenv("WP_SITE_URL", cfg.SITE_URL).rstrip('/')
    auth = HTTPBasicAuth(os.getenv("WP_USERNAME", ""), os.getenv("WP_APP_PASSWORD", ""))
    return url, auth


def get_or_create_category(category_name: str) -> int:
    """
    Finds a category ID by name (config first, then the WP REST API), creating it if needed.
    """
    clean_name = category_name.strip()
    if clean_name in cfg.CATEGORY_MAP:
        return cfg.CATEGORY_MAP[clean_name]

    cache_key = clean_name.lower()
    if cache_key in _CATEGORY_CACHE:
        return _CATEGORY_CACHE[cache_key]

    wp_url, auth = _wp()
    categories_url = f"{wp_url}/wp-json/wp/v2/categories"

    try:
        res = requests.get(categories_url, params={"search": clean_name}, auth=auth, headers=DEFAULT_HEADERS, timeout=15)
        if res.status_code == 200:
            for cat in res.json():
                if cat.get("name", "").strip().lower() == cache_key or cat.get("slug", "") == cache_key.replace(" ", "-"):
                    _CATEGORY_CACHE[cache_key] = cat["id"]
                    return cat["id"]
    except Exception as e:
        print(f"Notice: Exception searching category '{clean_name}': {e}")

    try:
        res = requests.post(categories_url, auth=auth, headers=DEFAULT_HEADERS, json={"name": clean_name}, timeout=15)
        if res.status_code == 201:
            cat_id = res.json().get("id")
            _CATEGORY_CACHE[cache_key] = cat_id
            print(f"✨ Created new WordPress category '{clean_name}' (ID: {cat_id})")
            return cat_id
        if res.status_code == 400:
            term_id = res.json().get("data", {}).get("term_id")
            if term_id:
                _CATEGORY_CACHE[cache_key] = term_id
                return term_id
    except Exception as e:
        print(f"Notice: Exception creating category '{clean_name}': {e}")

    return cfg.DEFAULT_CATEGORY_ID


def upload_image_to_wordpress(image_path: str, title: str, post_id: int = None):
    """
    Uploads an image to the Media Library, attaches it to post_id (if given) and sets
    alt text, title and caption. Returns (media_id, source_url).
    """
    if not os.path.exists(image_path):
        print(f"Warning: Image file not found: {image_path}")
        return None, None

    wp_url, auth = _wp()
    media_url = f"{wp_url}/wp-json/wp/v2/media"
    headers = {**DEFAULT_HEADERS, 'Content-Disposition': f'attachment; filename={os.path.basename(image_path)}'}

    try:
        with open(image_path, 'rb') as img_file:
            response = requests.post(media_url, auth=auth, headers=headers, files={'file': img_file}, timeout=35)

        if response.status_code == 201:
            media_data = response.json()
            media_id = media_data.get('id')
            details = {'alt_text': title, 'title': title, 'caption': title}
            credit = IMAGE_CREDITS.get(image_path) or {}
            if credit.get("landing_url"):
                by = f" by {credit['creator']}" if credit.get("creator") else ""
                details['description'] = (
                    f"Background photo: \"{credit.get('title', '')}\"{by}, via {credit.get('source', '')} "
                    f"({credit.get('license', '')}, no attribution required). Source: {credit['landing_url']}"
                )
            if post_id:
                details['post'] = post_id  # attach to the post ("Uploaded to")
            requests.post(
                f"{media_url}/{media_id}",
                auth=auth,
                headers=DEFAULT_HEADERS,
                json=details,
                timeout=15,
            )
            print(f" -> Uploaded image: {image_path} (Media ID: {media_id})")
            return media_id, media_data.get('source_url', '')

        print(f"Failed to upload image {image_path}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error uploading image {image_path}: {e}")
    return None, None


def generate_faq_accordion_html(faq_items: list, uid: str = None) -> str:
    """
    Builds the FAQ as plain HTML in the same card style as the site's Easy Accordion FAQs.

    atoyanlaw.com's theme does NOT run shortcodes in blog posts (an [sp_easyaccordion] shortcode shows up
    as raw text), and Easy Accordion's CSS is not loaded there, so everything is inline: styles on each
    element, closed answers hidden with display:none. The "WP Content Autopilot Bridge" plugin's footer
    script opens/closes `.ea-header` cards inside `.sp-ea-single`, so no other script is needed.
    Answers may be plain text or HTML.
    """
    if not faq_items:
        return ""
    uid = uid or str(random.randint(100000, 999999))
    card = 'margin-bottom: 10px; border: 1px solid #e2e2e2; background: #eee;'
    head = 'margin: 0; padding: 0; font-size: 18px; line-height: 1.5;'
    link = ('display: block; padding: 15px; color: #444; font-weight: 600; text-decoration: none; cursor: pointer;')
    icon = 'display: inline-block; width: 18px; margin-right: 6px; font-style: normal; color: #444;'
    body = 'background: #fff; color: #444; padding: 15px; font-size: 16px; line-height: 1.6;'

    html = f'<div id="sp-ea-{uid}" class="sp-ea-one sp-easy-accordion atoyan-inline-faq">'
    for n, item in enumerate(faq_items):
        q = str(item.get("question", "")).strip()
        a = str(item.get("answer", "")).strip()
        if not a.startswith("<"):
            a = f"<p>{a}</p>"
        is_open = n == 0
        cid = f"{uid}{n}"
        html += (
            f'<div class="ea-card{" ea-expand" if is_open else ""} sp-ea-single" style="{card}">'
            f'<h3 class="ea-header" style="{head}"><a class="{"" if is_open else "collapsed"}" id="ea-header-{cid}" '
            f'role="button" aria-controls="collapse{cid}" href="#" aria-expanded="{"true" if is_open else "false"}" '
            f'tabindex="0" style="{link}"><i aria-hidden="true" class="ea-expand-icon" style="{icon}">'
            f'{"−" if is_open else "+"}</i> {q}</a></h3>'
            f'<div class="sp-collapse spcollapse{" show" if is_open else ""}" id="collapse{cid}" role="region" '
            f'aria-labelledby="ea-header-{cid}" style="display: {"block" if is_open else "none"};">'
            f'<div class="ea-body" style="{body}">{a}</div></div></div>'
        )
    html += '</div>'
    return f'\n{cfg.H2_OPEN_TAG}{cfg.FAQ_HEADING}</h2>\n{html}\n'


def generate_faq_schema_jsonld(faq_items: list) -> str:
    """
    Builds Google-compliant FAQPage JSON-LD.
    """
    if not faq_items:
        return ""

    def safe(text: str) -> str:
        # The site's force-meta endpoint strips backslashes twice, so the JSON must not
        # contain any: use curly quotes, drop backslashes, flatten whitespace.
        text = re.sub(r'\s+', ' ', str(text)).strip().replace('\\', '')
        text = re.sub(r'"(?=\w)', '“', text)
        return text.replace('"', '”').replace('</', '<​/')

    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": safe(item.get("question", "")),
                "acceptedAnswer": {"@type": "Answer", "text": safe(item.get("answer", ""))},
            }
            for item in faq_items
        ],
    }
    return f'<script type="application/ld+json">\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n</script>'




def save_head_script(wp_url: str, auth, post_id: int, script: str) -> bool:
    """
    Saves the script into the post's "Insert Script to <head>" box through the site's
    WP Content Autopilot Bridge plugin: POST autopilot/v1/head-script {"post_id", "script"}.
    """
    try:
        res = requests.post(
            wp_url + cfg.HEAD_SCRIPT_PATH,
            auth=auth, headers=DEFAULT_HEADERS, json={'post_id': post_id, 'script': script}, timeout=25,
        )
        if res.status_code == 200 and res.json().get('saved'):
            print("✨ FAQ schema saved to 'Insert Script to <head>' (autopilot bridge)")
            return True
        print(f"Notice: head-script endpoint returned {res.status_code} - {res.text[:200]}")
    except Exception as e:
        print(f"Notice: head-script request failed: {e}")

    print("⚠️ FAQ schema was NOT saved to <head>. Check that the 'WP Content Autopilot Bridge' plugin is active "
          "and WP_USERNAME can edit pages.")
    return False


def create_faq_accordion(title: str, faq_items: list) -> str:
    """
    Creates an Easy Accordion (sp_easy_accordion) holding the FAQs, through the bridge plugin, so the FAQ
    looks exactly like the existing posts. Returns the shortcode, or "" if it failed.
    """
    if not (cfg.USE_EASY_ACCORDION and faq_items):
        return ""
    wp_url, auth = _wp()
    try:
        res = requests.post(
            wp_url + cfg.ACCORDION_PATH,
            auth=auth, headers=DEFAULT_HEADERS, timeout=30,
            # No "city"/"topic": the plugin would otherwise append its own CTA to the last answer.
            json={
                'title': f"FAQ: {title}"[:190],
                'faqs': [{'question': f['question'], 'answer': f"<p>{f['answer']}</p>"} for f in faq_items],
            },
        )
        if res.status_code == 200 and res.json().get('shortcode'):
            data = res.json()
            print(f"✨ Easy Accordion FAQ created (ID {data.get('id')}, {data.get('count')} questions)")
            return data['shortcode']
        print(f"Notice: accordion endpoint returned {res.status_code} - {res.text[:200]}")
    except Exception as e:
        print(f"Notice: accordion request failed: {e}")
    return ""


def purge_cache(post_id: int) -> None:
    """Clears WP Rocket's cache for the post (and with it the blog listing) through the bridge plugin."""
    wp_url, auth = _wp()
    try:
        requests.post(wp_url + cfg.PURGE_CACHE_PATH, auth=auth, headers=DEFAULT_HEADERS,
                      json={'post_id': post_id}, timeout=20)
    except Exception as e:
        print(f"Notice: cache purge failed: {e}")


def build_post_body(title: str, content: str, faq_items: list = None, extra_html: str = ""):
    """
    Article + CTA box + FAQ (Easy Accordion shortcode, or a <details> accordion as fallback)
    + optional extra HTML (news source line) + legal disclaimer. Returns (body, faq_mode).
    The FAQ is inline HTML by default (see generate_faq_accordion_html).
    """
    body = re.sub(r'<script\b[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE).rstrip()
    body += f"\n\n{cfg.CTA_HTML}\n"
    faq_mode = "none"
    if faq_items:
        shortcode = create_faq_accordion(title, faq_items)  # only if USE_EASY_ACCORDION (off: theme skips shortcodes)
        if shortcode:
            body += f"\n{cfg.H2_OPEN_TAG}{cfg.FAQ_HEADING}</h2>\n{shortcode}\n"
            faq_mode = "easy-accordion"
        else:
            body += generate_faq_accordion_html(faq_items)
            faq_mode = "inline-accordion"
    if extra_html:
        body += f"\n{extra_html}\n"
    body += f"\n{cfg.MEDICAL_DISCLAIMER_HTML}\n"
    return body, faq_mode


def publish_wordpress_post(
    title: str,
    content: str,
    image_paths: list = None,
    faq_items: list = None,
    category_name: str = None,
    category_id: int = None,
    category_ids: list = None,
    status: str = "publish",
    extra_html: str = "",
):
    """
    Publishes the article as a WordPress POST (never a page), so it is listed in the Blog section:
    - Uploads the image; it becomes the featured image.
    - Adds the CTA box, FAQ accordion, FAQ JSON-LD in <head>, and the legal disclaimer.
    - Sets the excerpt and Yoast title/meta description
      (Yoast fields only save if wordpress/atoyanlaw-publisher-meta.php is installed).
    """
    wp_url, auth = _wp()
    posts_url = f"{wp_url}/wp-json/wp/v2/posts"

    if category_ids:
        target_category_ids = [int(c) for c in category_ids]
    elif category_id is not None:
        target_category_ids = [int(category_id)]
    elif category_name:
        target_category_ids = [get_or_create_category(n) for n in category_name.split(",") if n.strip()]
    else:
        target_category_ids = [cfg.DEFAULT_CATEGORY_ID]

    body, faq_mode = build_post_body(title, content, faq_items, extra_html)
    schema_script = generate_faq_schema_jsonld(faq_items) if faq_items else ""
    if schema_script and cfg.INCLUDE_FAQ_SCHEMA_IN_BODY:
        body += f"\n{schema_script}\n"

    yoast_metadesc = extract_yoast_description(content)

    # Step 1: create the post as a draft (so the image can be attached to it)
    payload = {
        'title': title,
        'content': body,
        'excerpt': yoast_metadesc,
        'status': 'draft',
        'categories': target_category_ids,
        'meta': {
            '_yoast_wpseo_title': f"{title} | {cfg.SITE_NAME}",
            '_yoast_wpseo_metadesc': yoast_metadesc,
        },
    }

    try:
        response = requests.post(posts_url, auth=auth, headers=DEFAULT_HEADERS, json=payload, timeout=35)
        if response.status_code == 400 and 'meta' in response.text:
            # Some sites reject the whole request when meta keys are not registered; retry without them.
            payload.pop('meta')
            response = requests.post(posts_url, auth=auth, headers=DEFAULT_HEADERS, json=payload, timeout=35)

        if response.status_code == 201:
            post_data = response.json()
            post_id = post_data.get('id')
            edit_url = f"{wp_url}/wp-admin/post.php?post={post_id}&action=edit"
            saved_meta = post_data.get('meta', {}) or {}

            # Step 2: upload image(s) attached to this post
            media_ids = []
            for path in image_paths or []:
                m_id, _ = upload_image_to_wordpress(path, title, post_id)
                if m_id:
                    media_ids.append(m_id)
            featured_media_id = media_ids[0] if media_ids else 0

            # Step 3: FAQ schema -> "Insert Script to <head>"
            schema_in_head = save_head_script(wp_url, auth, post_id, schema_script) if schema_script else False

            # Step 4: set the featured image and the final status
            update = {'status': status}
            if featured_media_id:
                update['featured_media'] = featured_media_id
            upd = requests.post(f"{posts_url}/{post_id}", auth=auth, headers=DEFAULT_HEADERS, json=update, timeout=35)
            if upd.status_code == 200:
                post_data = upd.json()
            else:
                print(f"⚠️ Could not set featured image/status: {upd.status_code} - {upd.text}")

            featured_ok = bool(featured_media_id) and post_data.get('featured_media') == featured_media_id
            if featured_media_id and not featured_ok:
                print(f"⚠️ Featured image {featured_media_id} was uploaded but not set on post {post_id}")

            purge_cache(post_id)

            yoast_saved = '_yoast_wpseo_metadesc' in saved_meta
            print(f"\n✅ Post created (ID: {post_id}, status: {post_data.get('status', status)})")
            print(f"🖼️ Featured image: {featured_media_id or 'none'} ({'set' if featured_ok else 'NOT set'})")
            print(f"❓ FAQ: {faq_mode}")
            print(f"📝 Edit URL: {edit_url}")
            if not yoast_saved:
                print("⚠️ Yoast meta was not saved. Install wordpress/atoyanlaw-publisher-meta.php on the site.")

            cleanup_local_images(image_paths)

            post_data.update({
                'edit_url': edit_url,
                'preview_url': post_data.get('link', ''),
                'yoast_metadesc': yoast_metadesc,
                'yoast_saved': yoast_saved,
                'media_ids': media_ids,
                'featured_media_id': featured_media_id,
                'featured_ok': featured_ok,
                'schema_in_head': schema_in_head,
                'faq_mode': faq_mode,
                'category_ids': target_category_ids,
                'schema_script': schema_script,
            })
            return post_data

        print(f"❌ Failed to publish post: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception during WordPress publication: {e}")

    cleanup_local_images(image_paths)
    return None
