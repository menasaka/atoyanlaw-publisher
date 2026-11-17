# ⚖️ Atoyan Law – Blog Autopilot

Writes ~1,200-word California employment-law blog posts with OpenAI and publishes them to
**https://www.atoyanlaw.com** as WordPress **posts**, so every new article appears in the
**Blog** section (https://www.atoyanlaw.com/blog/), never as a page.

Two ways to publish:

1. **Manually** from the Streamlit app (`app.py`): type a title (or load a Google Sheet of titles) → publish.
2. **Automatically** with GitHub Actions (`autopublish.py`): twice a day it picks a fresh California
   employment-law headline from Google News and writes an original article about it.

Cloned from `urologytoday-publisher` (same pipeline, schedule and catch-up logic); photo search from
`allfordiabetes-publisher` (Pixabay → Pexels → Openverse).

## What each post gets

| Part | How |
|---|---|
| Body | Question-style `<h2 class="h2dav">` headings (same class as the existing posts), short paragraphs, lists |
| Internal links | 3–4 links to atoyanlaw.com practice-area pages (22 targets, all checked HTTP 200) |
| CTA box | "Talk to a California employment lawyer" + (888) 807-0077 + contact page, in the site's own callout style |
| FAQ | 8 questions written **from the article itself** (page-specific), shown as an **Easy Accordion** like the existing posts |
| FAQ schema | FAQPage JSON-LD saved to the post's "Insert Script to `<head>`" box |
| Featured image | Topic photo with a dark title strip and the title in capitals (same look as the existing posts) |
| Categories | OpenAI picks 1–3 of the site's real categories (Employee Rights, Wrongful termination, Unpaid Wages…); news posts always include **Employee Rights** |
| Yoast | SEO title + meta description (needs the small snippet below); description is also saved as the excerpt |
| Disclaimer | "General information, not legal advice… Attorney advertising." |
| Cache | WP Rocket is purged for the post after publishing |

Legal-accuracy rules in the prompts: California law first, no invented statutes/cases/verdicts/settlements,
never "you have a case", no promises of results, news articles only use what the headline says.
All of it is in **`site_config.py`**.

## WordPress setup (atoyanlaw.com)

Already in place on the site: the **WP Content Autopilot Bridge** plugin (`/wp-json/autopilot/v1/…`), which the
publisher uses for the Easy Accordion FAQ, the `<head>` schema and the WP Rocket purge.

1. **Application password** – WP Admin → Users → an **Administrator** → *Application Passwords* →
   name it `Blog Autopilot` → copy it. (Administrator so the `<head>` script is not stripped.)
2. **Yoast fields (optional but recommended)** – WP Admin → Snippets → Add New → paste
   `wordpress/atoyanlaw-publisher-meta.php` (everything below `<?php`) → *Run everywhere* → Save and Activate.
   Without it posts still publish; Yoast uses its defaults.

## Run locally

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then fill in the values
streamlit run app.py
```

## Streamlit Community Cloud (manual posting)

1. Push this folder to its own GitHub repo, e.g. `menasaka/atoyanlaw-publisher`.
2. https://share.streamlit.io → **Create app** → that repo, branch `main`, file `app.py`.
3. **Advanced settings → Secrets**: paste `.streamlit/secrets.toml.example` with real values.
4. Deploy.

## Daily news autopilot (GitHub Actions)

| Time (California) | What happens |
|---|---|
| **9:00 am** | Newest California employment-law headline from Google News (last 24h) → blog post published live |
| **2:00 pm** | Next newest headline not yet covered → blog post published live |

1. Searches Google News for `NEWS_QUERY` (California + employment law, wrongful termination, discrimination,
   harassment, wage theft, overtime, workers' compensation…), last 24 hours, 3 days if nothing new.
2. OpenAI keeps only stories that matter to workers' rights (drops crime, gossip, stock news, opinion)
   and writes an original, worker-focused title.
3. Skips anything already covered on atoyanlaw.com.
4. Writes the article, FAQs, photo, categories, and a **Source:** link to the news report.
5. Never more than 1 post for the 9am slot or 2 per day, even if re-run.

The workflow runs **every hour** at :23 during the day; each run publishes whichever slot is due but
not done yet, until 5:59pm (`LAST_CATCH_UP_HOUR`), because GitHub often starts scheduled runs late.

**Secrets** (repo → Settings → Secrets and variables → Actions): either one `AUTOMATION` secret
(lines like `OPENAI_API_KEY = "..."`), or `OPENAI_API_KEY`, `WP_USERNAME`, `WP_APP_PASSWORD`,
optional `PIXABAY_API_KEY`, `PEXELS_API_KEY`, `OPENAI_MODEL`.

**Test / run now:** repo → Actions → "Daily news auto-publish (atoyanlaw.com blog)" → Run workflow →
`dry_run` = only show which headline it would pick; `slot` = 1 to publish one now.

## Command line

```bash
python main.py "Can My Employer Fire Me for Taking Sick Leave in California?"
python autopublish.py --dry-run
```
