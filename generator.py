import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv

import site_config as cfg

load_dotenv()

_client = None


def _get_client() -> OpenAI:
    # Created lazily so Streamlit secrets are already loaded into the environment
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _model() -> str:
    # "or": an empty OPENAI_MODEL (e.g. unset GitHub secret) falls back to the default
    return os.getenv("OPENAI_MODEL") or cfg.DEFAULT_OPENAI_MODEL


def generate_article_content(topic_title: str, news: dict = None) -> str:
    """
    Generates a ~1,200+ word California employment law blog post with question-based H2 headings.
    news: optional {"headline", "source"} for articles based on a news report.
    All site-specific rules come from site_config.py.
    """
    user_prompt = cfg.ARTICLE_PROMPT_TEMPLATE.format(topic=topic_title)
    if news:
        user_prompt += cfg.NEWS_ARTICLE_EXTRA.format(headline=news["headline"], source=news.get("source") or "a news outlet")
    response = _get_client().chat.completions.create(
        model=_model(),
        messages=[
            {"role": "system", "content": cfg.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4200,
        temperature=0.7,
    )
    return response.choices[0].message.content


def _plain_text(html_or_md: str, limit: int = 12000) -> str:
    text = re.sub(r'<[^>]+>', ' ', html_or_md or "")
    text = re.sub(r'[ \t]+', ' ', text)
    return re.sub(r'\n\s*\n+', '\n\n', text).strip()[:limit]


def generate_faqs(topic_title: str, article: str = "") -> list:
    """
    Generates page-specific Q&A pairs from the article text (2-3 sentence answers) as JSON.
    Raises if generation fails, rather than publishing FAQs that don't match the article.
    """
    count = cfg.FAQ_COUNT
    response = _get_client().chat.completions.create(
        model=_model(),
        messages=[
            {"role": "system", "content": cfg.FAQ_SYSTEM_PROMPT},
            {"role": "user", "content": cfg.FAQ_PROMPT_TEMPLATE.format(
                topic=topic_title, article=_plain_text(article) or topic_title, count=count)},
        ],
        response_format={"type": "json_object"},
        max_tokens=3000,
        temperature=0.5,
    )

    data = json.loads(response.choices[0].message.content)

    parsed_faqs = []
    for item in data.get("faqs", []):
        clean_q = str(item.get("question", "")).strip()
        clean_a = re.sub(r'\s*\n\s*', ' ', str(item.get("answer", "")).strip())
        clean_a = clean_a.replace("—", "-")
        if clean_q and clean_a:
            parsed_faqs.append({"question": clean_q, "answer": clean_a})

    if not parsed_faqs:
        raise ValueError(f"FAQ generation returned no usable questions for: {topic_title}")

    return parsed_faqs[:count]


def choose_categories(title: str, article: str = "", extra: list = None) -> list:
    """
    Lets OpenAI pick 1-MAX_CATEGORIES of the site's categories for the post.
    Returns category names (always valid keys of CATEGORY_MAP), plus ALWAYS_CATEGORIES and `extra`.
    """
    names = []
    if cfg.AUTO_PICK_CATEGORIES:
        try:
            response = _get_client().chat.completions.create(
                model=_model(),
                messages=[{"role": "user", "content": cfg.CATEGORY_PICK_PROMPT.format(
                    title=title,
                    excerpt=_plain_text(article, 1500),
                    names=", ".join(f'"{n}"' for n in cfg.CATEGORY_MAP),
                    max=cfg.MAX_CATEGORIES,
                )}],
                response_format={"type": "json_object"},
                max_tokens=200,
                temperature=0.1,
            )
            data = json.loads(response.choices[0].message.content)
            lookup = {n.lower(): n for n in cfg.CATEGORY_MAP}
            for n in data.get("categories", []):
                real = lookup.get(str(n).strip().lower())
                if real and real not in names:
                    names.append(real)
            names = names[:cfg.MAX_CATEGORIES]
        except Exception as e:
            print(f"Notice: category selection failed ({e}); using the defaults.")
    for n in list(extra or []) + list(cfg.ALWAYS_CATEGORIES):
        if n in cfg.CATEGORY_MAP and n not in names:
            names.append(n)
    return names or list(cfg.DEFAULT_CATEGORIES)


def generate_photo_queries(topic_title: str) -> list:
    """
    Asks OpenAI for short, visual stock-photo search phrases for the topic.
    Falls back to generic workplace phrases if anything goes wrong.
    """
    try:
        response = _get_client().chat.completions.create(
            model=_model(),
            messages=[{"role": "user", "content": cfg.PHOTO_QUERY_PROMPT.format(topic=topic_title)}],
            response_format={"type": "json_object"},
            max_tokens=200,
            temperature=0.4,
        )
        data = json.loads(response.choices[0].message.content)
        queries = [str(q).strip().lower() for q in data.get("queries", []) if str(q).strip()]
        if queries:
            # Always keep generic fallbacks at the end
            return queries[:6] + [q for q in cfg.DEFAULT_PHOTO_QUERIES if q not in queries]
    except Exception as e:
        print(f"Notice: photo query generation failed ({e}); using defaults.")
    return list(cfg.DEFAULT_PHOTO_QUERIES)


# Backward compatibility alias
generate_faq_items = generate_faqs
