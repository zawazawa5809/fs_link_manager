"""Auto-tagging utility for FS Link Manager"""

import os
from typing import List


def generate_auto_tags(path: str) -> List[str]:
    """パスからファイル種別に応じた自動タグを生成

    Args:
        path: ファイルまたはフォルダのパス

    Returns:
        自動生成されたタグのリスト

    Examples:
        >>> generate_auto_tags("C:/folder")
        ["フォルダ"]
        >>> generate_auto_tags("C:/file.json")
        ["ファイル", "json"]
        >>> generate_auto_tags("C:/document.pdf")
        ["ファイル", "pdf"]
    """
    tags = []

    # パスの存在確認
    if not os.path.exists(path):
        return tags

    # フォルダ判定
    if os.path.isdir(path):
        tags.append("フォルダ")
    else:
        # ファイルの場合
        tags.append("ファイル")

        # 拡張子を取得
        _, ext = os.path.splitext(path)
        if ext:
            # ドットを除去して小文字化
            ext_tag = ext[1:].lower()
            if ext_tag:
                tags.append(ext_tag)

    return tags


def merge_tags(default_tags: str, auto_tags: List[str]) -> str:
    """デフォルトタグと自動タグをマージ

    Args:
        default_tags: デフォルトタグ(カンマ区切り文字列)
        auto_tags: 自動生成タグのリスト

    Returns:
        マージされたタグ(カンマ区切り文字列、重複なし)

    Examples:
        >>> merge_tags("重要, 作業中", ["ファイル", "json"])
        "重要, 作業中, ファイル, json"
        >>> merge_tags("", ["フォルダ"])
        "フォルダ"
        >>> merge_tags("重要, ファイル", ["ファイル", "pdf"])
        "重要, ファイル, pdf"
    """
    # デフォルトタグをリストに変換
    default_list = [tag.strip() for tag in default_tags.split(",") if tag.strip()]

    # 重複を除去しつつ順序を保持
    seen = set()
    merged = []

    for tag in default_list + auto_tags:
        if tag not in seen:
            seen.add(tag)
            merged.append(tag)

    return ", ".join(merged)
