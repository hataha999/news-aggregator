"""
静的 HTML ポータルページを生成するモジュール
GitHub Pages にデプロイされる docs/index.html を出力する
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "index.html"
ARCHIVE_PATH = Path(__file__).parent.parent / "data" / "archive.json"
MAX_ARCHIVE = 200  # 保持する最大記事数


def load_archive() -> list[dict]:
    if ARCHIVE_PATH.exists():
        try:
            return json.loads(ARCHIVE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_archive(archive: list[dict]) -> None:
    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # 日付降順・上限管理
    archive.sort(key=lambda a: a.get("published", ""), reverse=True)
    ARCHIVE_PATH.write_text(
        json.dumps(archive[:MAX_ARCHIVE], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_to_archive(filtered: dict[str, list[dict]], config: dict) -> list[dict]:
    """新着記事をアーカイブに追加し保存する"""
    archive = load_archive()
    existing_ids = {a["id"] for a in archive}

    categories = config["categories"]
    for cat_key, articles in filtered.items():
        cat_conf = categories.get(cat_key, {})
        for article in articles:
            if article["id"] not in existing_ids:
                article_copy = dict(article)
                article_copy["category_key"] = cat_key
                article_copy["category_name"] = cat_conf.get("name", cat_key)
                article_copy["category_emoji"] = cat_conf.get("emoji", "📰")
                article_copy["category_priority"] = cat_conf.get("priority", 99)
                archive.append(article_copy)
                existing_ids.add(article["id"])

    save_archive(archive)
    return archive


def generate_html(archive: list[dict], config: dict) -> None:
    """アーカイブ全体から静的 HTML を生成する"""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    categories = config["categories"]

    # カテゴリ別にグループ化
    grouped: dict[str, list[dict]] = {}
    for article in archive:
        cat_key = article.get("category_key", "other")
        grouped.setdefault(cat_key, []).append(article)

    # 優先度順のカテゴリリスト
    sorted_cats = sorted(
        categories.items(), key=lambda x: x[1].get("priority", 99)
    )

    html = _build_html(sorted_cats, grouped, categories, now_str)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    logger.info(f"ポータル HTML 生成完了: {OUTPUT_PATH}")


def _build_html(sorted_cats, grouped, categories, now_str) -> str:
    cat_nav = "\n".join(
        f'<a href="#{key}" class="nav-link">'
        f'{conf["emoji"]} {conf["name"]}</a>'
        for key, conf in sorted_cats
    )

    sections_html = ""
    for cat_key, cat_conf in sorted_cats:
        articles = grouped.get(cat_key, [])
        cards_html = ""
        for a in articles:
            published = a.get("published", "")
            date_str = ""
            if published:
                try:
                    dt = datetime.fromisoformat(published)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_str = published[:16]

            ai_summary = a.get("ai_summary", a.get("summary", ""))
            title = a.get("title", "")
            link = a.get("link", "#")
            source = a.get("source", "")

            cards_html += f"""
            <article class="card">
                <div class="card-meta">
                    <span class="source">{source}</span>
                    <span class="date">{date_str}</span>
                </div>
                <h3 class="card-title">{title}</h3>
                <p class="card-summary">{ai_summary}</p>
                <a href="{link}" target="_blank" rel="noopener" class="card-link">
                    元記事を開く →
                </a>
            </article>"""

        if not cards_html:
            cards_html = '<p class="no-articles">記事はまだありません</p>'

        sections_html += f"""
        <section id="{cat_key}" class="category-section">
            <h2 class="category-title">
                {cat_conf["emoji"]} {cat_conf["name"]}
            </h2>
            <div class="cards-grid">{cards_html}</div>
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My News Portal</title>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Hiragino Kaku Gothic ProN", sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }}
        header {{
            background: #1e293b;
            padding: 1rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-bottom: 1px solid #334155;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .site-title {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #f8fafc;
        }}
        .updated {{ font-size: 0.8rem; color: #94a3b8; }}
        nav {{ display: flex; gap: 0.75rem; flex-wrap: wrap; padding: 0.5rem 2rem; background: #1e293b; border-bottom: 1px solid #334155; }}
        .nav-link {{
            text-decoration: none;
            color: #94a3b8;
            font-size: 0.85rem;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            border: 1px solid #334155;
            transition: all 0.2s;
        }}
        .nav-link:hover {{ color: #f8fafc; border-color: #64748b; background: #334155; }}
        main {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
        .category-section {{ margin-bottom: 3rem; }}
        .category-title {{
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #334155;
            color: #f1f5f9;
        }}
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1rem;
        }}
        .card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 0.75rem;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
            transition: border-color 0.2s;
        }}
        .card:hover {{ border-color: #64748b; }}
        .card-meta {{
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: #64748b;
        }}
        .source {{ font-weight: 600; color: #94a3b8; }}
        .card-title {{
            font-size: 0.95rem;
            font-weight: 600;
            color: #f1f5f9;
            line-height: 1.4;
        }}
        .card-summary {{ font-size: 0.85rem; color: #94a3b8; flex: 1; }}
        .card-link {{
            font-size: 0.8rem;
            color: #60a5fa;
            text-decoration: none;
            margin-top: auto;
        }}
        .card-link:hover {{ text-decoration: underline; }}
        .no-articles {{ color: #475569; font-size: 0.9rem; }}
        @media (max-width: 640px) {{
            main {{ padding: 1rem; }}
            .cards-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <header>
        <span class="site-title">📰 My News Portal</span>
        <span class="updated">最終更新: {now_str}</span>
    </header>
    <nav>{cat_nav}</nav>
    <main>{sections_html}</main>
</body>
</html>"""
