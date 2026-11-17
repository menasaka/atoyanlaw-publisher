"""
Site-specific settings for atoyanlaw.com (Atoyan Law Firm).

Everything that ties this publisher to one website lives in this file.
Cloned from urologytoday-publisher; the code is the same family, only the site, topic and rules change.

Every article is published as a WordPress *post* (never a page), so it appears in the
Blog section (https://www.atoyanlaw.com/blog/), which lists all posts.
"""

SITE_NAME = "Atoyan Law"
SITE_DOMAIN = "atoyanlaw.com"
SITE_URL = "https://www.atoyanlaw.com"
PAGE_ICON = "⚖️"
BLOG_URL = "https://www.atoyanlaw.com/blog/"
FIRM_PHONE = "(888) 807-0077"
CONTACT_URL = "https://www.atoyanlaw.com/contact/"

# OpenAI model used for articles and FAQs (override with the OPENAI_MODEL secret)
DEFAULT_OPENAI_MODEL = "gpt-4o"

# ------------------------------------------------------------------------------
# WordPress categories (real IDs from https://www.atoyanlaw.com/wp-json/wp/v2/categories, 2026-11-17).
# The year/month categories (2024, 2025, January...) and Uncategorized are left out on purpose.
# ------------------------------------------------------------------------------
CATEGORY_MAP = {
    "Employee Rights": 27,
    "Wrongful termination": 24,
    "Unpaid Wages": 28,
    "Sexual Harassment": 18,
    "Sex Discrimination": 21,
    "Gender discrimination": 22,
    "Pregnancy Discrimination": 26,
    "Age discrimination": 25,
    "Paid Sick Leave": 19,
    "Breach of Contract": 23,
}
DEFAULT_CATEGORIES = ["Employee Rights"]
DEFAULT_CATEGORY_ID = 27

# OpenAI picks 1-3 of the categories above for each article (manual and news posts).
# The ones below are always added on top.
AUTO_PICK_CATEGORIES = True
MAX_CATEGORIES = 3
ALWAYS_CATEGORIES = []

CATEGORY_PICK_PROMPT = """
Pick the best WordPress categories for this California employment law blog post.

Title: "{title}"
Opening of the article:
{excerpt}

Allowed categories (use these exact names): {names}

Rules: choose 1 to {max} categories that the article is clearly about. Choose "Employee Rights" when nothing
else fits. Never invent a category.
Return ONLY JSON: {{"categories": ["..."]}}
"""

# ------------------------------------------------------------------------------
# Writing rules
# ------------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You write blog posts for Atoyan Law Firm (atoyanlaw.com), a California law firm led by attorney David Atoyan "
    "that represents workers (never employers) in employment law matters: wrongful termination, discrimination, "
    "harassment, retaliation, unpaid wages and overtime, meal and rest breaks, leave (CFRA, FMLA, paid sick leave), "
    "whistleblowing, plus workers' compensation and personal injury. Readers are California employees who may be "
    "worried about their job, pay or safety and are reading on a phone. "
    "Voice: worker-first, plain English, calm and direct. Talk to the reader as 'you'. Short paragraphs of 1 to 3 "
    "sentences, short sentences, active voice. Do NOT use em dashes, AI-style labels, hype words ('aggressive', "
    "'ironclad', 'guaranteed') or generic intros such as 'In today's world'. "
    "Length: ~1,200 words. Structure: question-based H2 headings that match what workers type into Google. "
    "Legal accuracy rules (most important): California law first (FEHA, Gov. Code § 12900 et seq.; the Labor Code; "
    "CFRA), federal law only for contrast. Cite only statutes, agencies and cases you are certain exist and say what "
    "you claim; if unsure, describe the rule without a citation. Never invent case names, verdicts, settlements, "
    "statistics, quotes, clients or attorney stories. Never promise results or say a reader 'has a case'. "
    "Never claim the firm won any amount. Use these facts only when relevant: a Civil Rights Department (CRD) "
    "complaint is generally due within 3 years of the last unlawful act, then 1 year to sue after the Right-to-Sue "
    "notice; retaliation is covered by Labor Code §§ 98.6 and 1102.5; California is an at-will state, but firing for "
    "an illegal reason is still unlawful; secretly recording confidential conversations is illegal in California "
    "(Penal Code § 632), so never suggest it. "
    "This is general information, not legal advice. "
    "CRITICAL LENGTH RULE: You MUST write 3 to 4 short, detailed paragraphs under EVERY SINGLE H2 so the article "
    "reaches 1,200+ words. No brief summaries."
)

ARTICLE_PROMPT_TEMPLATE = """
Write an in-depth, trustworthy blog post for Atoyan Law (California employment law) about: "{topic}".

Strict Article Requirements:
1. Open with 2 to 3 short paragraphs (no heading) that name the reader's problem and say what the article covers.
2. Every major section must start with a question-based H2 heading ending in a question mark
   (e.g., '## Can My Employer Fire Me for Taking Sick Leave in California?').
3. Include 6 to 8 question-based H2 sections.
4. Under EVERY SINGLE H2 heading, write 3 to 4 short paragraphs (1 to 3 sentences each). Use at least two
   bulleted or numbered lists in the article (for example evidence to keep, or steps to take).
5. Cover, as they fit the topic: what California law says, how it differs from federal law, real-world examples
   at work, what employers often say or do, retaliation for complaining, how to document and keep evidence
   (personnel file under Labor Code § 1198.5, pay records under § 226(b); never secret recordings),
   where and when to file (CRD, Labor Commissioner, EEOC, court) and deadlines.
6. One H2 section must explain when to talk to an employment lawyer and why deadlines matter.
7. Keep sentences short, natural and clear. No em dashes (—), no filler, no artificial AI introductions.
8. Do not include an FAQ section, a disclaimer, a phone number or a "contact us" section in this body
   (those are added automatically).
9. Total word count must be 1,200+ words.
"""

FAQ_SYSTEM_PROMPT = (
    "You are a careful legal writer who writes page-specific FAQ sections for a California employment law firm's blog. "
    "You answer only from the article you are given and California law you are certain about. "
    "You always reply with valid JSON."
)

# FAQs are built from the article itself, so every post gets its own questions (never generic site-wide ones).
FAQ_PROMPT_TEMPLATE = """
Write {count} frequently asked questions and answers for this blog post.

Title: "{topic}"

Article text:
\"\"\"
{article}
\"\"\"

Strict Specifications:
1. Every question must be specific to THIS article's topic: the questions a California worker reading it would
   ask next. No generic questions that could sit on any page (nothing like "What is this article about?",
   "Is this legal advice?" or "How do I contact the firm?").
2. Answers come from the article and well-established California law only. Never invent statutes, case names,
   deadlines, dollar amounts, verdicts, settlements or guarantees. Never tell the reader they "have a case".
3. Every answer: 2 to 3 sentences, plain English, short sentences, active voice, no em dashes.
4. The last question is about when to talk to an employment lawyer about this specific issue, and its answer
   mentions that deadlines apply.

Return ONLY a JSON object of this shape:
{{"faqs": [{{"question": "...", "answer": "..."}}, ...]}}
with exactly {count} items.
"""
FAQ_COUNT = 8

# Sample topics for the quick-select buttons
SAMPLE_TOPICS = [
    "Can My Employer Fire Me for Taking Sick Leave in California?",
    "What Counts as a Hostile Work Environment Under California Law?",
    "Unpaid Overtime in California: How to Calculate What You Are Owed",
    "Fired After Reporting Harassment? How California Retaliation Law Protects You",
]

# ------------------------------------------------------------------------------
# Formatting (matches the existing posts on atoyanlaw.com)
# ------------------------------------------------------------------------------
H2_OPEN_TAG = '<h2 class="h2dav">'
FAQ_HEADING = "Frequently Asked Questions"

# No content-block shortcodes are inserted into the body
SHORTCODES_LIST = []

KEYWORDS_TO_BOLD = [
    "California law",
    "Civil Rights Department",
    "Labor Commissioner",
    "Right-to-Sue",
    "retaliation",
    "wrongful termination",
    "unpaid wages",
    "overtime",
    "meal and rest breaks",
    "deadline",
    "personnel file",
    "employment lawyer",
    "FEHA",
    "CFRA",
    "workers' compensation",
    "document everything",
]

# Internal links (all checked: return HTTP 200 on 2026-11-17)
_PA = "https://www.atoyanlaw.com/practice-areas/employment-law"
_WC = "https://www.atoyanlaw.com/workers-compensation"
INTERNAL_LINKS = [
    {"keywords": ["wrongful termination", "wrongfully terminated", "wrongfully fired"],
     "html": f'<a href="{_PA}/wrongful-termination/">wrongful termination</a>'},
    {"keywords": ["unlawful termination", "illegally fired", "fired for an illegal reason"],
     "html": f'<a href="{_PA}/unlawful-vs-wrongful-termination/">unlawful termination</a>'},
    {"keywords": ["retaliation", "retaliate", "retaliated"],
     "html": f'<a href="{_PA}/work-retaliation/">retaliation</a>'},
    {"keywords": ["whistleblower", "whistleblowing", "whistleblowers"],
     "html": f'<a href="{_PA}/whistleblowing-laws/">whistleblower protections</a>'},
    {"keywords": ["sexual harassment"],
     "html": f'<a href="{_PA}/sexual-harassment/">sexual harassment</a>'},
    {"keywords": ["hostile work environment"],
     "html": f'<a href="{_PA}/hostile-work-environment/">hostile work environment</a>'},
    {"keywords": ["workplace discrimination", "employment discrimination", "discrimination"],
     "html": f'<a href="{_PA}/workplace-discrimination/">workplace discrimination</a>'},
    {"keywords": ["age discrimination"],
     "html": f'<a href="{_PA}/age-discrimination/">age discrimination</a>'},
    {"keywords": ["pregnancy discrimination", "pregnant"],
     "html": f'<a href="{_PA}/pregnancy-discrimination/">pregnancy discrimination</a>'},
    {"keywords": ["gender discrimination"],
     "html": f'<a href="{_PA}/gender-discrimination/">gender discrimination</a>'},
    {"keywords": ["race discrimination", "racial discrimination"],
     "html": f'<a href="{_PA}/race-discrimination/">race discrimination</a>'},
    {"keywords": ["religious discrimination", "religion"],
     "html": f'<a href="{_PA}/religion-discrimination/">religious discrimination</a>'},
    {"keywords": ["reasonable accommodation", "reasonable accommodations", "accommodation"],
     "html": f'<a href="{_PA}/failure-to-provide-reasonable-accommodations/">reasonable accommodations</a>'},
    {"keywords": ["medical leave", "disability leave", "CFRA leave", "family leave"],
     "html": f'<a href="{_PA}/medical-disability-leave/">medical and disability leave</a>'},
    {"keywords": ["unpaid wages", "wage theft", "final paycheck"],
     "html": f'<a href="{_PA}/unpaid-wages/">unpaid wages</a>'},
    {"keywords": ["overtime pay", "unpaid overtime", "overtime"],
     "html": f'<a href="{_PA}/overtime-pay/">overtime pay</a>'},
    {"keywords": ["meal and rest breaks", "meal breaks", "rest breaks", "wage and hour"],
     "html": f'<a href="{_PA}/wage-hour-violations/">wage and hour violations</a>'},
    {"keywords": ["breach of contract", "employment contract"],
     "html": f'<a href="{_PA}/breach-of-contract/">breach of contract</a>'},
    {"keywords": ["EEOC"],
     "html": f'<a href="{_PA}/understanding-employment-discrimination-eeoc/">the EEOC</a>'},
    {"keywords": ["workers' compensation", "workers' comp", "workers comp"],
     "html": f'<a href="{_WC}/">workers\' compensation</a>'},
    {"keywords": ["workplace injury", "injured at work", "hurt at work"],
     "html": f'<a href="{_WC}/workplace-injury/">workplace injury</a>'},
    {"keywords": ["independent contractor", "misclassified", "misclassification"],
     "html": f'<a href="{_WC}/independent-contractors-workers-compensation/">independent contractors</a>'},
]

FALLBACK_LINK_SENTENCE = (
    '<p>Want to learn more? Read our guides to '
    f'<a href="{_PA}/wrongful-termination/">wrongful termination</a> and '
    f'<a href="{_PA}/work-retaliation/">workplace retaliation</a> in California.</p>'
)

# Call-to-action box added after the article body (uses the site's own callout classes)
CTA_HTML = (
    '<div class="txt-hlt bg-bx ulk-bg pd_v-30 pd_h-30">'
    '<p><strong>Talk to a California employment lawyer.</strong> If you think your rights at work were violated, '
    f'time limits apply. Call Atoyan Law at <a href="tel:+18888070077"><strong>{FIRM_PHONE}</strong></a> or '
    f'<a href="{CONTACT_URL}">contact us online</a> for a free, confidential case evaluation.</p>'
    '</div>'
)

# Added at the end of every post (after the FAQ)
MEDICAL_DISCLAIMER_HTML = (  # name kept from the family; on this site it is the legal disclaimer
    '<p style="font-size: 14px; color: #666666; border-top: 1px solid #e0e0e0; padding-top: 12px; margin-top: 25px;">'
    '<em>This article is general information about California law, not legal advice. Reading it does not create an '
    'attorney-client relationship. Laws change and every case is different, so talk with a lawyer about your '
    'situation. Attorney advertising.</em></p>'
)

# ------------------------------------------------------------------------------
# Yoast meta description
# ------------------------------------------------------------------------------
META_DESC_SUFFIX = "Learn your rights from Atoyan Law."
META_DESC_FALLBACK = "Plain-English guide to California employee rights, deadlines and next steps."
META_DESC_MAX_CHARS = 160

# ------------------------------------------------------------------------------
# atoyanlaw.com specifics: the "WP Content Autopilot Bridge" plugin (already active on the site)
# exposes autopilot/v1 endpoints that this publisher uses:
#   GET  /wp-json/autopilot/v1/accordion/<id> -> FAQ data of an Easy Accordion (used by repair_faq.py)
#   POST /wp-json/autopilot/v1/head-script  -> FAQ JSON-LD into "Insert Script to <head>"
#   POST /wp-json/autopilot/v1/purge-cache  -> clears WP Rocket for the post
# ------------------------------------------------------------------------------
# Off: the theme prints shortcodes in posts as raw text, so the FAQ is written into the post as HTML
# (same card look; opened/closed by the bridge plugin's script). See repair_faq.py for old posts.
USE_EASY_ACCORDION = False
ACCORDION_PATH = "/wp-json/autopilot/v1/accordion"
HEAD_SCRIPT_PATH = "/wp-json/autopilot/v1/head-script"
PURGE_CACHE_PATH = "/wp-json/autopilot/v1/purge-cache"
INCLUDE_FAQ_SCHEMA_IN_BODY = False
THEME_POST_META = {}

# ------------------------------------------------------------------------------
# Images (same look as the existing posts: photo with a dark title strip on top, title in capitals)
# ------------------------------------------------------------------------------
IMAGE_COUNT = 1
IMAGE_SIZE = (1200, 800)
TITLE_CARD_COLORS = ((14, 16, 26), (44, 52, 84))  # dark navy gradient for the no-photo fallback
TITLE_UPPERCASE = True
GRAYSCALE_IMAGES = False

USE_OPEN_PHOTOS = True
OPENVERSE_API = "https://api.openverse.org/v1/images/"
OPENVERSE_SOURCES = ["stocksnap"]
OPENVERSE_FALLBACK_SOURCES = ["stocksnap", "flickr", "wikimedia"]
OPENVERSE_LICENSE = "cc0,pdm"
OPENVERSE_GENERIC_QUERIES = ["office worker", "business meeting", "stressed employee", "office desk", "lawyer", "handshake"]
PHOTO_OVERLAY_ALPHA = 20
TITLE_BAR_RATIO = 0.20
TITLE_BAR_ALPHA = 150
TITLE_MAX_FONT = 44
SHOW_DOMAIN_ON_IMAGE = False

PHOTO_QUERY_PROMPT = """
Suggest stock photo search phrases for the featured image of a California employment law blog post titled: "{topic}".

Rules:
- 6 phrases, best first. Each is 1 to 3 plain visual words that a free stock photo site would tag
  (for example: "stressed employee", "office meeting", "boss employee", "warehouse worker", "paycheck",
  "woman office", "construction worker", "lawyer client", "packing box office", "hr meeting").
- Show the worker's situation, photographed realistically. No text, no logos, no brand names, no courtroom drama.
- Mix specific phrases with broader fallbacks.

Return ONLY JSON: {{"queries": ["...", "..."]}}
"""
DEFAULT_PHOTO_QUERIES = ["stressed employee", "office meeting", "boss employee", "office worker", "lawyer client", "business people"]

PHOTO_TITLE_BLOCKLIST = [
    "quote", "typography", "text", "logo", "sign", "advert", "poster", "dog", "cat",
    "chart", "graph", "map", "diagram", "screenshot", "etching", "engraving", "illustration",
]
PEXELS_ALT_BLOCKLIST = ["text", "logo", "sign", "poster", "illustration", "cartoon", "drawing", "3d", "render", "dog", "cat"]

# ------------------------------------------------------------------------------
# Daily news auto-publisher (autopublish.py, run by GitHub Actions)
# ------------------------------------------------------------------------------
TIMEZONE = "America/Los_Angeles"
PUBLISH_HOURS = [9, 14]          # local times: 9am = 1st headline, 2pm = 2nd headline
LAST_CATCH_UP_HOUR = 17          # a missed slot is made up by the hourly runs until 5:59pm
NEWS_QUERY = (
    'California ("employment law" OR "wrongful termination" OR "workplace discrimination" OR "sexual harassment" '
    'OR "wage theft" OR "unpaid wages" OR overtime OR "workers\' compensation" OR "labor law" OR "employee rights")'
)
NEWS_WINDOW = "1d"
NEWS_FALLBACK_WINDOW = "3d"
NEWS_MAX_AGE_DAYS = 7           # ignore older stories Google sometimes returns anyway
NEWS_SOURCE_BLOCKLIST = ["YouTube", "TikTok", "Facebook", "Instagram", "Reddit"]
NEWS_CATEGORY_NAMES = ["Employee Rights"]  # always added to news posts (OpenAI adds 1-2 topical ones)

NEWS_PICK_PROMPT = """
Below are recent news headlines found by searching Google News for California employment law topics.

{listing}

Keep ONLY headlines that matter to California WORKERS and their rights at work: new or proposed California or
federal employment laws and rules, court rulings, agency actions (Civil Rights Department, Labor Commissioner,
EEOC, Cal/OSHA, DOL), lawsuits or settlements about discrimination, harassment, retaliation, wrongful
termination, wages, overtime, breaks, leave, misclassification, workplace safety or workers' compensation.
The story must happen in California or be about a federal law, rule, agency action or court ruling that applies
to California workers. REJECT lawsuits, accidents or employer news from other states (check the place names,
outlet and agency: e.g. an Ohio or Texas employer, a state labor department outside California).
REJECT: press releases or marketing by other law firms (e.g. \"attorneys file lawsuit\" on PR Newswire),
stories mainly about people or crimes unrelated to work rights, celebrity gossip, stock or earnings news,
union politics without a legal angle, product promotions, opinion pieces, and non-English headlines.

For each kept headline write an original, accurate, SEO-friendly blog title for Atoyan Law, written for workers
(55-75 characters, plain English, often a question a worker would ask, no clickbait, no em dashes, do not copy
the headline word for word, do not name private individuals, do not state allegations as facts).

Return ONLY JSON: {{"picks": [{{"index": <number>, "title": "..."}}]}}
Return an empty list if none qualify.
"""

NEWS_ARTICLE_EXTRA = """
News context: this article is prompted by a recent news report.
- Headline: "{headline}"
- Published by: {source}

How to use it:
- In the opening, briefly say what the news report covers, using ONLY what the headline states.
  You have not read the report, so do NOT invent details, numbers, names, dates, quotes, rulings or outcomes.
  Use cautious wording such as "a recent report from {source} says..." and treat lawsuit claims as allegations.
- Then write a helpful, accurate explainer for California workers on the wider legal topic: what the law
  already says, what this may mean for employees, and practical next steps.
- Do not include a link or a sources list (one is added automatically).
"""
