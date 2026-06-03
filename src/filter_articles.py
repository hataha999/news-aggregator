"""
取得した記事をカテゴリキーワードでフィルタリングし、
既投稿済みIDを除いて新着のみを返すモジュール
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
POSTED_IDS_FILE = Path(__file__).parent.parent / "data" / "posted_ids.json"
MAX_POSTED_IDS = 2000  # 保持する最大ID数


def load_posted_ids() -> set[str]:
    """投稿済みIDセットをロード"""
    if POSTED_IDS_FILE.exists():
        try:
            data = json.loads(POSTED_IDS_FILE.read_text(encoding="utf-8"))
            return set(data.get("ids", []))
        except Exception as e:
            logger.warning(f"posted_ids 読み込み失敗: {e}")
    return set()


def save_posted_ids(ids: set[str]) -> None:
    """投稿済みIDセットを保存（上限を超えた分は古いものから削除）"""
    POSTED_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    id_list = list(ids)[-MAX_POSTED_IDS:]  # 上限管理
    POSTED_IDS_FILE.write_text(
        json.dumps({"ids": id_list, "updated": datetime.now(JST).isoformat()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def filter_new_articles(
    articles: list[dict],
    keywords: list[str],
    posted_ids: set[str],
    max_per_run: int = 5,
) -> list[dict]:
    """
    キーワードマッチ + 未投稿フィルタリングを行い、新着記事を返す
    優先度: キーワード一致数が多い順
    """
    matched = []
    for article in articles:
        if article["id"] in posted_ids:
            continue

        score = _score_article(article, keywords)
        if score > 0:
            article["_score"] = score
            matched.append(article)

    # スコア降順 → 日付降順 でソート
    matched.sort(key=lambda a: (a["_score"], a.get("published", "")), reverse=True)
    return matched[:max_per_run]


def _score_article(article: dict, keywords: list[str]) -> int:
    """タイトル・要約にキーワードが何個含まれるかをカウント"""
    text = f"{article['title']} {article['summary']}".lower()
    return sum(1 for kw in keywords if kw.lower() in text)


def filter_all_categories(
    fetched: dict[str, list[dict]],
    config: dict,
    posted_ids: set[str],
    max_per_category: int = 5,
) -> dict[str, list[dict]]:
    """
    全カテゴリの記事をフィルタリングし、優先度順にソートされた辞書を返す
    """
    result = {}
    categories = config["categories"]

    # 優先度でソート
    sorted_cats = sorted(categories.items(), key=lambda x: x[1]["priority"])

    for cat_key, cat_conf in sorted_cats:
        articles = fetched.get(cat_key, [])
        keywords = cat_conf.get("keywords", [])

        new_articles = filter_new_articles(
            articles, keywords, posted_ids, max_per_run=max_per_category
        )
        if new_articles:
            result[cat_key] = new_articles
            logger.info(f"[{cat_conf['name']}] 新着 {len(new_articles)}件")
        else:
            logger.info(f"[{cat_conf['name']}] 新着なし")

    return result
