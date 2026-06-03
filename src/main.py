"""
ニュースアグリゲーター メインエントリーポイント

実行フロー:
1. RSSフィードを全カテゴリ取得
2. キーワードフィルタ + 既投稿除外
3. Claude API で日本語要約
4. Discord Webhook に投稿
5. 静的HTMLポータル更新
6. 投稿済みIDを保存
"""

import logging
import os
import sys
import yaml
from pathlib import Path

# src/ を sys.path に追加
sys.path.insert(0, str(Path(__file__).parent))

from fetcher import fetch_all
from filter_articles import load_posted_ids, save_posted_ids, filter_all_categories
from summarizer import summarize_batch
from discord_poster import post_all
from portal_generator import add_to_archive, generate_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")

CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yml"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    logger.info("=== ニュースアグリゲーター 起動 ===")

    # 設定読み込み
    config = load_config()

    # Discord Webhook URL
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL が未設定です（Discord投稿はスキップ）")

    # 1. RSS取得
    logger.info("--- フィード取得開始 ---")
    fetched = fetch_all(config)

    # 2. フィルタリング（既投稿除外 + キーワードマッチ）
    logger.info("--- フィルタリング開始 ---")
    posted_ids = load_posted_ids()
    filtered = filter_all_categories(
        fetched, config, posted_ids, max_per_category=5
    )

    if not filtered:
        logger.info("新着記事なし。終了します。")
        return

    total = sum(len(v) for v in filtered.values())
    logger.info(f"新着記事合計: {total}件")

    # 3. 要約整形（RSS本文をそのまま活用・API不要）
    logger.info("--- 要約整形 ---")
    for cat_key, articles in filtered.items():
        filtered[cat_key] = summarize_batch(articles)

    # 4. Discord 投稿
    if webhook_url:
        logger.info("--- Discord 投稿開始 ---")
        new_posted_ids = post_all(webhook_url, filtered, config)
    else:
        new_posted_ids = [a["id"] for arts in filtered.values() for a in arts]

    # 5. ポータル HTML 更新
    logger.info("--- ポータル HTML 生成 ---")
    archive = add_to_archive(filtered, config)
    generate_html(archive, config)

    # 6. 投稿済みID を保存
    posted_ids.update(new_posted_ids)
    save_posted_ids(posted_ids)

    logger.info(f"=== 完了: {len(new_posted_ids)}件 投稿・アーカイブ済み ===")


if __name__ == "__main__":
    main()
