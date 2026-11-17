import os
import io
import time
import requests
import streamlit as st
import pandas as pd
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

# Bridge Streamlit Cloud secrets into environment variables (before other modules read them)
try:
    for k, v in st.secrets.items():
        if isinstance(v, str):
            os.environ[k] = v
except Exception:
    pass

import site_config as cfg
from generator import generate_article_content, generate_faqs, choose_categories
from processor import process_and_format_article
from image_maker import create_unique_images
from wp_publisher import publish_wordpress_post

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

st.set_page_config(
    page_title=f"SEO Blog Publisher | {cfg.SITE_NAME}",
    page_icon=cfg.PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 800; color: #18345C; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1rem; color: #64748B; margin-bottom: 1.5rem; }
    .status-badge { display: inline-block; padding: 4px 12px; background-color: #E6F4F5; color: #1F6F7A;
                    border-radius: 9999px; font-size: 0.85rem; font-weight: 600; margin-right: 8px; }
    .success-card { background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 20px; margin: 15px 0; }
</style>
""", unsafe_allow_html=True)


def get_env_status():
    wp_url = os.getenv("WP_SITE_URL", cfg.SITE_URL).rstrip('/')
    wp_user = os.getenv("WP_USERNAME", "")
    return {
        "wp_url": wp_url,
        "wp_user": wp_user,
        "has_openai": bool(os.getenv("OPENAI_API_KEY")),
        "has_wp": bool(wp_url and wp_user and os.getenv("WP_APP_PASSWORD")),
    }


AUTO_LABEL = "✨ Let AI choose"


def category_picker(label: str, key: str):
    """Returns (names, ids); names == [AUTO_LABEL] and ids == None means OpenAI picks after writing."""
    names = st.multiselect(
        label,
        options=[AUTO_LABEL] + list(cfg.CATEGORY_MAP.keys()),
        default=[AUTO_LABEL] if cfg.AUTO_PICK_CATEGORIES else cfg.DEFAULT_CATEGORIES,
        key=key,
        help="Pick categories, or keep 'Let AI choose' to have OpenAI pick 1-3 from the article.",
    )
    real = [n for n in names if n != AUTO_LABEL]
    if real:
        return real, [cfg.CATEGORY_MAP[n] for n in real]
    if names:
        return [AUTO_LABEL], None
    return list(cfg.DEFAULT_CATEGORIES), [cfg.CATEGORY_MAP[n] for n in cfg.DEFAULT_CATEGORIES]


def run_pipeline(title: str, category_names, category_ids, status: str = "publish", report=None):
    def step(msg, pct):
        if report:
            report(msg, pct)

    step("🧠 [1/5] Writing the article with OpenAI...", 15)
    raw_content = generate_article_content(title)

    step(f"❓ [2/5] Article drafted ({len(raw_content.split())} words). Writing page-specific FAQs...", 35)
    faq_items = generate_faqs(title, raw_content)
    if category_ids is None:
        category_names = choose_categories(title, raw_content)
        category_ids = [cfg.CATEGORY_MAP[n] for n in category_names]

    step("⚙️ [3/5] Formatting headings, bolding keywords, adding internal links...", 55)
    formatted = process_and_format_article(raw_content)

    step("🎨 [4/5] Creating the featured image...", 75)
    images = create_unique_images(title)

    step("🚀 [5/5] Uploading image and publishing the blog post...", 90)
    post = publish_wordpress_post(
        title=title,
        content=formatted,
        image_paths=images,
        faq_items=faq_items,
        category_name=", ".join(category_names),
        category_ids=category_ids,
        status=status,
    )
    if post:
        post["category_names"] = list(category_names)
    return post, raw_content, formatted, faq_items


def main():
    # Password gate
    app_password = os.getenv("APP_PASSWORD", "")
    if app_password:
        entered = st.text_input("🔑 Enter Access Password", type="password")
        if not entered:
            st.warning("🔒 Please enter the access password to use this application.")
            st.stop()
        elif entered != app_password:
            st.error("❌ Incorrect password. Access denied.")
            st.stop()

    env = get_env_status()

    with st.sidebar:
        st.header("⚙️ System Status")
        if env["has_wp"]:
            st.success(f"Connected to WordPress:\n`{env['wp_url']}`")
            st.caption(f"Authenticated as: **{env['wp_user']}**")
        else:
            st.error("WordPress credentials missing (WP_USERNAME / WP_APP_PASSWORD)")
        if env["has_openai"]:
            st.success(f"OpenAI API: Connected ({os.getenv('OPENAI_MODEL', cfg.DEFAULT_OPENAI_MODEL)})")
        else:
            st.error("OPENAI_API_KEY missing")

        st.divider()
        st.subheader("🛠️ Publishing Parameters")
        st.markdown("""
        - **Target Word Count:** ~1,200+ words
        - **Headings:** Question-based `H2`
        - **Density:** 3–4 paragraphs per H2
        - **Internal Links:** 3–4 atoyanlaw.com practice pages
        - **Yoast SEO:** Title + meta description
        - **FAQ Module:** 8 page-specific Q&As (Easy Accordion) + JSON-LD schema
        - **CTA box + legal disclaimer:** added to every post
        - **Featured image:** 1 per post
        - **Section:** WordPress *post* → listed on /blog/
        """)

    st.markdown(f'<div class="main-header">{cfg.PAGE_ICON} {cfg.SITE_NAME}</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Blog post generator & publisher for atoyanlaw.com: every post goes to the Blog section</div>', unsafe_allow_html=True)
    st.markdown(
        '<div>'
        '<span class="status-badge">OpenAI</span>'
        '<span class="status-badge">Featured Image Engine</span>'
        '<span class="status-badge">WordPress REST API</span>'
        '<span class="status-badge">Yoast SEO & FAQ Schema</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    tab_single, tab_batch, tab_inspect = st.tabs(["📝 Single Post Generator", "📊 Google Sheets Batch Queue", "🔍 Post Meta Inspector"])

    with tab_single:
        st.subheader("Generate & Publish Single Article")
        st.caption("Quick Select Sample Topics:")
        cols = st.columns(len(cfg.SAMPLE_TOPICS))
        for idx, topic in enumerate(cfg.SAMPLE_TOPICS):
            if cols[idx].button(f"Topic {idx + 1}", key=f"topic_btn_{idx}", help=topic):
                st.session_state["blog_title"] = topic

        title_input = st.text_input(
            "Blog Post Title",
            value=st.session_state.get("blog_title", cfg.SAMPLE_TOPICS[0]),
            placeholder="Enter exact blog post title...",
        )
        category_names, category_ids = category_picker("📁 Select WordPress Categories", "single_cats")
        status = "publish"

        if st.button("🚀 Generate & Publish Live to the Blog", type="primary", use_container_width=True):
            if not title_input.strip():
                st.warning("Please enter a valid blog post title.")
                return

            progress_bar = st.progress(0)
            status_box = st.empty()

            def report(msg, pct):
                status_box.info(msg)
                progress_bar.progress(pct)

            try:
                post_data, raw_content, formatted, faq_items = run_pipeline(
                    title_input, category_names, category_ids, status, report
                )
                progress_bar.progress(100)

                if not post_data:
                    status_box.error("❌ Failed to create the WordPress post. Check the logs and credentials.")
                    return

                status_box.empty()
                post_id = post_data.get("id")
                edit_url = post_data["edit_url"]
                preview_url = post_data.get("preview_url", "")
                label = "Published LIVE" if post_data.get("status") == "publish" else f"saved as {post_data.get('status', '').upper()}"

                st.markdown(f"""
                <div class="success-card">
                    <h3 style="color: #15803D; margin-top: 0;">🎉 Blog Post {label}!</h3>
                    <p><strong>Post ID:</strong> {post_id} | <strong>Categories:</strong> {', '.join(post_data.get('category_names', category_names))}</p>
                    <p><strong>Blog:</strong> <a href="{cfg.BLOG_URL}" target="_blank">{cfg.BLOG_URL}</a></p>
                    <p><strong>WordPress Edit URL:</strong> <a href="{edit_url}" target="_blank">{edit_url}</a></p>
                    <p><strong>Article URL:</strong> <a href="{preview_url}" target="_blank">{preview_url}</a></p>
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                c1.link_button("📝 Open Post in WordPress Editor", edit_url, use_container_width=True)
                c2.link_button("🌐 Open Article", preview_url, use_container_width=True)

                st.divider()
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Article Words", len(raw_content.split()))
                m2.metric("FAQs", len(faq_items))
                m3.metric("Status", str(post_data.get("status", "")).upper())
                m4.metric("Featured Image", "✅ Set" if post_data.get("featured_ok") else "❌ Missing")
                if not post_data.get("featured_ok"):
                    st.warning("The featured image was not set. Check the app logs (Manage app → logs) for the WordPress error.")

                with st.expander("🔍 Yoast SEO & Meta Details", expanded=True):
                    st.markdown(f"**SEO Title:** `{title_input} | {cfg.SITE_NAME}`")
                    st.markdown("**Meta Description:**")
                    st.info(post_data.get("yoast_metadesc", ""))
                    if not post_data.get("yoast_saved"):
                        st.warning(
                            "Yoast fields were not saved by WordPress. Install the snippet in "
                            "`wordpress/atoyanlaw-publisher-meta.php` (see README). "
                            "The meta description was still saved as the post excerpt."
                        )

                if post_data.get("schema_in_head"):
                    st.success("✅ FAQ schema saved to the post's \"Insert Script to <head>\" box.")
                else:
                    st.warning(
                        "FAQ schema was NOT saved to \"Insert Script to <head>\". Make sure the "
                        "\"WP Content Autopilot Bridge\" plugin is active and WP_USERNAME is an Administrator. "
                        "You can also paste the schema below into that box by hand."
                    )

                with st.expander("❓ FAQ Accordion & JSON-LD Schema"):
                    for idx, item in enumerate(faq_items, 1):
                        st.markdown(f"**{idx}. {item.get('question')}**")
                        st.write(item.get('answer'))
                    st.code(post_data.get("schema_script", ""), language="html")

                with st.expander("📄 Full HTML Body Content"):
                    st.code(formatted, language="html")

            except Exception as ex:
                status_box.error(f"❌ An error occurred during pipeline execution: {ex}")
                st.exception(ex)

    with tab_batch:
        st.subheader("Batch Publish from Google Sheet")
        st.markdown("Titles in column A of a sheet shared as **Anyone with the link can view**. Posts run one after another with a short cooldown.")

        b1, b2 = st.columns([2, 1])
        with b1:
            sheet_id_input = st.text_input("Google Sheet ID", value=os.getenv("GOOGLE_SHEET_ID", ""))
        with b2:
            batch_names, batch_ids = category_picker("Batch Categories", "batch_cats")
        batch_status_value = "publish"

        if st.button("📥 Load Sheet & Start Batch", type="secondary"):
            if not sheet_id_input.strip():
                st.warning("Enter a Google Sheet ID first.")
                return
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id_input.strip()}/export?format=csv"
            try:
                resp = requests.get(csv_url, timeout=15)
                if resp.status_code != 200:
                    st.error(f"Could not load Google Sheet (HTTP {resp.status_code}). Check the sharing setting.")
                    return

                df = pd.read_csv(io.StringIO(resp.text))
                raw_titles = df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
                titles = [t for t in raw_titles if t and t.lower() not in ["title", "titles", "topic", "topics"]]
                st.success(f"Found {len(titles)} titles in queue!")

                batch_progress = st.progress(0)
                batch_box = st.empty()
                for idx, topic in enumerate(titles, start=1):
                    batch_box.info(f"Processing ({idx}/{len(titles)}): **{topic}**...")
                    try:
                        post, *_ = run_pipeline(topic, batch_names, batch_ids, batch_status_value)
                    except Exception as e:
                        post = None
                        st.write(f"⚠️ Error on '{topic}': {e}")
                    if post:
                        st.write(f"✅ **[{idx}/{len(titles)}] Published LIVE:** {topic} — [View]({post.get('preview_url', '')}) · [Edit]({post['edit_url']})")
                    else:
                        st.write(f"⚠️ **[{idx}/{len(titles)}] Failed:** {topic}")
                    batch_progress.progress(int(idx / len(titles) * 100))
                    if idx < len(titles):
                        time.sleep(5)

                batch_box.success("🏁 All batch titles processed!")
            except Exception as e:
                st.error(f"Error processing sheet: {e}")

    with tab_inspect:
        st.subheader("🔍 WordPress Post Meta Inspector")
        st.markdown("Inspect the raw metadata, categories and content of any post via the WordPress REST API.")

        inspect_post_id = st.number_input("WordPress Post ID", min_value=1, value=3818, step=1)

        if st.button("🔎 Fetch Post Metadata", type="primary"):
            wp_url = env["wp_url"]
            with st.spinner(f"Fetching Post {inspect_post_id}..."):
                try:
                    resp = requests.get(
                        f"{wp_url}/wp-json/wp/v2/posts/{inspect_post_id}?context=edit",
                        auth=HTTPBasicAuth(os.getenv("WP_USERNAME", ""), os.getenv("WP_APP_PASSWORD", "")),
                        headers=BROWSER_HEADERS,
                        timeout=20,
                    )
                    if resp.status_code != 200:
                        st.error(f"❌ HTTP {resp.status_code} - {resp.text}")
                        return

                    post_json = resp.json()
                    st.success(f"✅ Retrieved Post ID: **{inspect_post_id}**")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Post Status", post_json.get("status", "").upper())
                    c2.metric("Categories", str(post_json.get("categories", [])))
                    c3.metric("Featured Media ID", post_json.get("featured_media", 0))

                    st.markdown(f"**Post Title:** `{post_json.get('title', {}).get('raw', '')}`")
                    st.markdown(f"**Edit URL:** [Open in Editor]({wp_url}/wp-admin/post.php?post={inspect_post_id}&action=edit)")
                    st.divider()
                    st.subheader("Registered Post Meta")
                    st.json(post_json.get("meta", {}))
                    with st.expander("View Full Raw Body Content"):
                        st.code(post_json.get("content", {}).get("raw", ""), language="html")
                except Exception as e:
                    st.error(f"Error: {e}")


if __name__ == "__main__":
    main()
