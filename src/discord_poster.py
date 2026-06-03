"""
Discord Webhook に記事を投稿するモジュール
カテゴリごとに Embed を分けて見やすく投稿する
"""

import logging
import os
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

# Discord の Embed カラー（カテゴリ別）
CATEGORY_COLORS = {
    "money":    0xF1C40F,   # ゴールド
    "security": 0xE74C3C,   # レッド
    "ai":       0x3498DB,   # ブルー
    "robotics": 0x2ECC71,   # グリーン
    "radio":    0x9B59B6,   # パープル
}

MAX_ARTICLES_PER_EMBED = 5   # 1 Embed あたりの最大記事数
MAX_EMBEDS_PER_REQUEST = 10  # Discord の1リクエストあたり上限


def post_category(
    webhook_url: str,
    cat_key: str,
    cat_conf: dict,
    articles: list[dict],
) -> bool:
    """
    カテゴリの記事を Discord に Embed 形式で投稿する
    記事が多い場合は複数回に分割して送信する
    """
    if not articles:
        return True

    emoji = cat_conf.get("emoji", "📰")
    name = cat_conf.get("name", cat_key)
    color = CATEGORY_COLORS.get(cat_key, 0x95A5A6)

    # 記事を MAX_ARTICLES_PER_EMBED 件ずつに分割
    for i in range(0, len(articles), MAX_ARTICLES_PER_EMBED):
        chunk = articles[i:i + MAX_ARTICLES_PER_EMBED]
        embeds = []

        for article in chunk:
            embed = _build_embed(article, emoji, name, color)
            embeds.append(embed)

        payload = {
            "username": "NewsBot 📰",
            "embeds": embeds,
        }

        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info(f"[{name}] Discord 投稿成功: {len(chunk)}件")
        except requests.HTTPError as e:
            logger.error(f"[{name}] Discord 投稿失敗 HTTP {e.response.status_code}: {e}")
            return False
        except Exception as e:
            logger.error(f"[{name}] Discord 投稿失敗: {e}")
            return False

    return True


def _build_embed(article: dict, emoji: str, category_name: str, color: int) -> dict:
    """Discord Embed オブジェクトを構築する"""
    title = article.get("title", "（タイトルなし）")
    link = article.get("link", "")
    source = article.get("source", "")
    ai_summary = article.get("ai_summary", "")
    published = article.get("published", "")

    # 日時を読みやすい形式に変換
    date_str = ""
    if published:
        try:
            dt = datetime.fromisoformat(published)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            date_str = published[:16]

    description_parts = []
    if ai_summary:
        description_parts.append(ai_summary)
    if date_str:
        description_parts.append(f"\n🕐 {date_str}　📰 {source}")

    embed = {
        "title": f"{emoji} {title}"[:256],
        "description": "\n".join(description_parts)[:4096],
        "color": color,
        "footer": {"text": f"#{category_name}"},
    }

    if link:
        embed["url"] = link

    return embed


def post_all(
    webhook_url: str,
    filtered: dict[str, list[dict]],
    config: dict,
) -> list[str]:
    """
    全カテゴリを優先度順に Discord へ投稿し、
    投稿成功した記事の ID リストを返す
    """
    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL が未設定です")
        return []

    categories = config["categories"]
    # 優先度でソート
    sorted_cats = sorted(
        [(k, v) for k, v in filtered.items()],
        key=lambda x: categories.get(x[0], {}).get("priority", 99),
    )

    posted_ids = []
    for cat_key, articles in sorted_cats:
        cat_conf = categories.get(cat_key, {})
        success = post_category(webhook_url, cat_key, cat_conf, articles)
        if success:
            posted_ids.extend(a["id"] for a in articles)

    return posted_ids
