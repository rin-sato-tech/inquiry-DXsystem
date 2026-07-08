from __future__ import annotations

from typing import Any

from src.db import (
    fetch_comments_by_request_id,
    fetch_operation_logs,
    fetch_status_history_by_request_id,
    insert_inquiry_comment,
    insert_operation_log,
    insert_status_history,
)


COMMENT_VISIBILITIES = {"internal", "requester"}


def get_user_id(user: dict[str, Any] | None) -> str:
    """ログイン中ユーザー情報からuser_idを取り出す。"""
    if user is None:
        return ""

    return str(user.get("user_id", "")).strip()


def normalize_text(value: Any) -> str:
    """比較用に文字列化・前後空白除去する。"""
    if value is None:
        return ""

    return str(value).strip()


def get_changed_fields(
    before: dict[str, Any],
    updates: dict[str, Any],
) -> list[str]:
    """更新前後で値が変わった項目名を返す。"""
    changed_fields: list[str] = []

    for key, after_value in updates.items():
        before_value = before.get(key, "")

        if normalize_text(before_value) != normalize_text(after_value):
            changed_fields.append(key)

    return changed_fields


def add_inquiry_comment(
    request_id: str,
    comment_body: str,
    visibility: str,
    user_id: str = "",
) -> str:
    """問い合わせコメントを追加し、操作ログも保存する。"""
    normalized_body = comment_body.strip()

    if not normalized_body:
        raise ValueError("コメント本文を入力してください。")

    if visibility not in COMMENT_VISIBILITIES:
        raise ValueError(f"不正な表示区分です: {visibility}")

    comment_id = insert_inquiry_comment(
        request_id=request_id,
        comment_body=normalized_body,
        visibility=visibility,
        created_by=user_id,
    )

    insert_operation_log(
        action="add_comment",
        target_table="inquiry_comments",
        target_id=comment_id,
        user_id=user_id,
        detail=f"問い合わせ {request_id} にコメントを追加",
    )

    return comment_id


def get_comments_for_staff(request_id: str) -> list[dict[str, Any]]:
    """管理部向けに、内部・依頼者向けコメントをすべて取得する。"""
    return fetch_comments_by_request_id(request_id)


def get_comments_for_requester(request_id: str) -> list[dict[str, Any]]:
    """依頼者向けコメントのみ取得する。"""
    comments = fetch_comments_by_request_id(request_id)

    return [
        comment
        for comment in comments
        if comment.get("visibility") == "requester"
    ]


def record_status_history_if_changed(
    request_id: str,
    old_status: str,
    new_status: str,
    user_id: str = "",
) -> str | None:
    """ステータスが変わった場合だけ、ステータス履歴を保存する。"""
    normalized_old_status = normalize_text(old_status)
    normalized_new_status = normalize_text(new_status)

    if normalized_old_status == normalized_new_status:
        return None

    history_id = insert_status_history(
        request_id=request_id,
        old_status=normalized_old_status,
        new_status=normalized_new_status,
        changed_by=user_id,
    )

    insert_operation_log(
        action="change_status",
        target_table="status_history",
        target_id=history_id,
        user_id=user_id,
        detail=(
            f"問い合わせ {request_id} のステータスを "
            f"{normalized_old_status} から {normalized_new_status} に変更"
        ),
    )

    return history_id


def record_inquiry_update_history(
    request_id: str,
    before: dict[str, Any],
    updates: dict[str, Any],
    user_id: str = "",
) -> list[str]:
    """
    問い合わせ更新時の履歴を保存する。

    戻り値:
        変更されたフィールド名の一覧。
    """
    changed_fields = get_changed_fields(before, updates)

    if not changed_fields:
        return []

    old_status = normalize_text(before.get("status", ""))
    new_status = normalize_text(updates.get("status", old_status))

    record_status_history_if_changed(
        request_id=request_id,
        old_status=old_status,
        new_status=new_status,
        user_id=user_id,
    )

    old_assignee = normalize_text(before.get("assignee", ""))
    new_assignee = normalize_text(updates.get("assignee", old_assignee))

    if old_assignee != new_assignee:
        insert_operation_log(
            action="change_assignee",
            target_table="inquiries",
            target_id=request_id,
            user_id=user_id,
            detail=(
                f"担当者を "
                f"{old_assignee or '未設定'} から {new_assignee or '未設定'} に変更"
            ),
        )

    insert_operation_log(
        action="update_inquiry",
        target_table="inquiries",
        target_id=request_id,
        user_id=user_id,
        detail="更新項目: " + ", ".join(changed_fields),
    )

    return changed_fields


def record_inquiry_created(
    request_id: str,
    user_id: str = "",
) -> None:
    """問い合わせ作成の操作ログを保存する。"""
    insert_operation_log(
        action="create_inquiry",
        target_table="inquiries",
        target_id=request_id,
        user_id=user_id,
        detail=f"問い合わせ {request_id} を作成",
    )


def get_status_history(request_id: str) -> list[dict[str, Any]]:
    """問い合わせIDに紐づくステータス履歴を取得する。"""
    return fetch_status_history_by_request_id(request_id)


def get_operation_logs(
    limit: int = 100,
    target_id: str | None = None,
) -> list[dict[str, Any]]:
    """操作ログを取得する。必要に応じて対象IDで絞り込む。"""
    logs = fetch_operation_logs(limit=limit)

    if target_id is None:
        return logs

    return [
        log
        for log in logs
        if log.get("target_id") == target_id
        or target_id in str(log.get("detail", ""))
    ]


def get_inquiry_history_bundle(request_id: str) -> dict[str, list[dict[str, Any]]]:
    """問い合わせごとのコメント・ステータス履歴・操作ログをまとめて取得する。"""
    return {
        "comments": get_comments_for_staff(request_id),
        "status_history": get_status_history(request_id),
        "operation_logs": get_operation_logs(target_id=request_id),
    }