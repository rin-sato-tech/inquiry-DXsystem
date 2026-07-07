from __future__ import annotations

from typing import Any

from src.db import (
    create_faq_item_from_candidate,
    fetch_faq_categories,
    fetch_faq_item_by_id,
    fetch_faq_items,
    increment_faq_helpful_count,
    increment_faq_view_count,
    insert_operation_log,
    update_faq_item,
)


def search_public_faqs(
    keyword: str = "",
    category: str = "",
) -> list[dict[str, Any]]:
    """公開FAQを検索する。"""
    normalized_keyword = keyword.strip()
    normalized_category = category.strip()

    return fetch_faq_items(
        is_public=True,
        category=normalized_category if normalized_category else None,
        keyword=normalized_keyword if normalized_keyword else None,
    )


def get_public_faq_categories() -> list[str]:
    """公開FAQのカテゴリ一覧を取得する。"""
    return fetch_faq_categories(is_public=True)


def get_admin_faq_items() -> list[dict[str, Any]]:
    """管理者向けに全FAQを取得する。"""
    return fetch_faq_items(is_public=None)


def get_faq_detail(
    faq_id: str,
) -> dict[str, Any]:
    """FAQ詳細を取得する。"""
    faq = fetch_faq_item_by_id(faq_id)

    if faq is None:
        raise ValueError(f"FAQが見つかりません: {faq_id}")

    return faq


def get_faq_detail_with_view_count(
    faq_id: str,
    count_view: bool = True,
) -> dict[str, Any]:
    """
    FAQ詳細を取得する。

    count_view=True の場合のみ閲覧数を加算する。
    """
    if count_view:
        increment_faq_view_count(faq_id)

    return get_faq_detail(faq_id)


def mark_faq_helpful(faq_id: str) -> None:
    """FAQの役立ち件数を加算する。"""
    increment_faq_helpful_count(faq_id)


def create_public_faq_draft_from_candidate(
    request_id: str,
    user_id: str = "",
) -> tuple[str, bool]:
    """FAQ候補から公開FAQ下書きを作成する。"""
    faq_id, created = create_faq_item_from_candidate(
        request_id=request_id,
        created_by=user_id,
    )

    if created:
        insert_operation_log(
            action="create_faq",
            target_table="faq_items",
            target_id=faq_id,
            user_id=user_id,
            detail=f"FAQ候補 {request_id} から公開FAQ下書きを作成",
        )

    return faq_id, created


def save_faq_item(
    faq_id: str,
    title: str,
    answer: str,
    category: str,
    is_public: bool,
    user_id: str = "",
) -> bool:
    """
    FAQの内容・公開状態を保存する。

    戻り値:
        True  = 内容を更新した
        False = 既存内容と同じため更新しなかった
    """
    normalized_title = title.strip()
    normalized_answer = answer.strip()
    normalized_category = category.strip()

    if not normalized_title:
        raise ValueError("FAQタイトルは必須です。")

    if not normalized_answer:
        raise ValueError("FAQ回答は必須です。")

    if not normalized_category:
        raise ValueError("カテゴリは必須です。")

    before = fetch_faq_item_by_id(faq_id)
    if before is None:
        raise ValueError(f"FAQが見つかりません: {faq_id}")

    before_title = str(before["title"]).strip()
    before_answer = str(before["answer"]).strip()
    before_category = str(before["category"]).strip()
    before_is_public = bool(before["is_public"])

    is_same_content = (
        before_title == normalized_title
        and before_answer == normalized_answer
        and before_category == normalized_category
        and before_is_public == is_public
    )

    if is_same_content:
        return False

    update_faq_item(
        faq_id=faq_id,
        title=normalized_title,
        answer=normalized_answer,
        category=normalized_category,
        is_public=is_public,
        updated_by=user_id,
    )

    if before_is_public != is_public:
        action = "publish_faq" if is_public else "unpublish_faq"
    else:
        action = "update_faq"

    insert_operation_log(
        action=action,
        target_table="faq_items",
        target_id=faq_id,
        user_id=user_id,
        detail="FAQ内容または公開状態を更新",
    )

    return True