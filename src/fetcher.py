"""
RSS フィードを取得し、記事一覧を返すモジュール
"""

import feedparser
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import re
import time

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))


def _fetch_with_requests(url: str, name: str) -> "feedparser.FeedParserDict | None":
    """requests で取得してから feedparser に渡す（文字コード問題の回避）"""
    try:
        import requests as req
        resp = req.get(url, timeout=15, headers={"User-Agent": "NewsAggregator/1.0"})
        resp.raise_for_status()
        # Shift-JIS / EUC-JP の省庁サイト対応
        content = resp.content
        for enc in ("utf-8", "shift_jis", "euc-jp", "iso-8859-1"):
            try:
                text = content.decode(enc)
                # 不正な文字を除去してから再パース
                text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
                parsed = feedparser.parse(text)
                if parsed.entries:
                    logger.info(f"[{name}] requests fallback 成功 ({enc})")
                    return parsed
            except (UnicodeDecodeError, Exception):
                continue
    except Exception as e:
        logger.debug(f"[{name}] requests fallback 失敗: {e}")
    return None


def fetch_feed(url: str, name: str, lang: str = "ja", timeout: int = 15) -> list[dict]:
    """
    単一のRSSフィードを取得してパース済み記事リストを返す
    """
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "NewsAggregator/1.0"})

        if feed.bozo:
            if not feed.entries:
                # エントリが取れない場合は requests で再試行（不正XML対策）
                fallback = _fetch_with_requests(url, name)
                if fallback is not None:
                    feed = fallback
                else:
                    logger.warning(f"[{name}] フィード取得エラー（スキップ）: {feed.bozo_exception}")
                    return []
            else:
                # bozo でもエントリが取れていればそのまま続行
                logger.debug(f"[{name}] 軽微な XML エラーあり（エントリ取得は成功）")

        articles = []
        for entry in feed.entries:
            article = _parse_entry(entry, name, lang)
            if article:
                articles.append(article)

        logger.info(f"[{name}] {len(articles)}件 取得")
        return articles

    except Exception as e:
        logger.error(f"[{name}] 取得失敗: {e}")
        return []


def _parse_entry(entry, source_name: str, lang: str) -> Optional[dict]:
    """feedparser のエントリを統一フォーマットに変換"""
    title = _clean_text(getattr(entry, "title", ""))
    if not title:
        return None

    link = getattr(entry, "link", "")
    summary = _extract_summary(entry)
    published = _parse_date(entry)
    article_id = _make_id(link or title)

    return {
        "id": article_id,
        "title": title,
        "link": link,
        "summary": summary,
        "published": published.isoformat() if published else None,
        "source": source_name,
        "lang": lang,
    }


def _extract_summary(entry) -> str:
    """記事本文・要約を抽出（最大 800文字）"""
    text = ""
    if hasattr(entry, "content") and entry.content:
        text = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        text = entry.summary
    elif hasattr(entry, "description"):
        text = entry.description

    text = re.sub(r"<[^>]+>", "", text)  # HTMLタグ除去
    text = re.sub(r"\s+", " ", text).strip()
    return text[:800]


def _parse_date(entry) -> Optional[datetime]:
    """公開日時をパース"""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                dt = datetime(*val[:6], tzinfo=timezone.utc)
                return dt.astimezone(JST)
            except Exception:
                pass
    return datetime.now(JST)


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _make_id(source: str) -> str:
    return hashlib.md5(source.encode()).hexdigest()


def fetch_all(config: dict) -> dict[str, list[dict]]:
    """
    config["categories"] の全フィードを取得し、
    カテゴリ名 → 記事リスト の辞書を返す
    """
    results: dict[str, list[dict]] = {}

    for cat_key, cat_conf in config["categories"].items():
        articles = []
        for feed_conf in cat_conf.get("feeds", []):
            fetched = fetch_feed(
                url=feed_conf["url"],
                name=feed_conf["name"],
                lang=feed_conf.get("lang", "ja"),
            )
            articles.extend(fetched)
            time.sleep(0.5)  # 各サイトへの連続アクセスを避ける

        results[cat_key] = articles

    return results
