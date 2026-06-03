"""
記事の要約を整形するモジュール
※ 外部APIは一切使用しない。RSSフィードに含まれる要約文をそのまま活用する。
"""

import re


def clean_summary(text: str, max_length: int = 200) -> str:
    """
    RSS フィードの要約文をクリーニングして返す
    - HTML タグ除去
    - 余分な空白除去
    - max_length 文字でカット
    """
    text = re.sub(r"<[^>]+>", "", text)          # HTMLタグ除去
    text = re.sub(r"&[a-z]+;", " ", text)         # HTMLエンティティ除去
    text = re.sub(r"\s+", " ", text).strip()      # 空白正規化
    if len(text) > max_length:
        text = text[:max_length].rsplit("。", 1)[0] + "。"  # 文末で自然にカット
    return text


def summarize_batch(articles: list[dict]) -> list[dict]:
    """
    記事リストの summary を整形して ai_summary フィールドに格納する
    （外部API呼び出しなし・完全無料）
    """
    for article in articles:
        raw = article.get("summary", "") or article.get("title", "")
        article["ai_summary"] = clean_summary(raw)
    return articles
