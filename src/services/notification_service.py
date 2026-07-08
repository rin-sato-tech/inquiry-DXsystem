from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from src.db import (
    fetch_notification_logs,
    insert_notification_log,
    insert_operation_log,
    update_notification_status,
)


OPEN_STATUS_EXCLUDE = {"完了"}

NOTIFICATION_TYPE_LABELS = {
    "before_due": "期限前",
    "overdue": "期限超過",
    "unassigned": "担当者未設定",
    "waiting_too_long": "情報待ち長期化",
    "status_changed": "ステータス変更",
    "completed": "完了",
}

NOTIFICATION_STATUSES = {"created", "reviewed", "skipped", "sent"}


def _today() -> pd.Timestamp:
    """今日の日付をTimestampで返す。"""
    return pd.Timestamp(date.today())


def _to_datetime_series(series: pd.Series) -> pd.Series:
    """日付文字列をdatetimeに変換する。"""
    return pd.to_datetime(series, errors="coerce")


def _normalize_text(value: Any) -> str:
    """文字列化して前後空白を除去する。"""
    if value is None:
        return ""

    return str(value).strip()


def _is_open_status(status: Any) -> bool:
    """未完了ステータスかどうかを判定する。"""
    return _normalize_text(status) not in OPEN_STATUS_EXCLUDE


def _prepare_inquiry_df(df: pd.DataFrame) -> pd.DataFrame:
    """通知対象抽出用にDataFrameを整える。"""
    if df.empty:
        return df.copy()

    result = df.copy()

    if "due_date" in result.columns:
        result["due_date_dt"] = _to_datetime_series(result["due_date"])
    else:
        result["due_date_dt"] = pd.NaT

    if "last_status_changed_at" in result.columns:
        result["last_status_changed_at_dt"] = _to_datetime_series(
            result["last_status_changed_at"]
        )
    else:
        result["last_status_changed_at_dt"] = pd.NaT

    if "updated_at" in result.columns:
        result["updated_at_dt"] = _to_datetime_series(result["updated_at"])
    else:
        result["updated_at_dt"] = pd.NaT

    if "request_date" in result.columns:
        result["request_date_dt"] = _to_datetime_series(result["request_date"])
    else:
        result["request_date_dt"] = pd.NaT

    if "status" in result.columns:
        result["is_open"] = result["status"].apply(_is_open_status)
    else:
        result["is_open"] = True

    if "assignee" not in result.columns:
        result["assignee"] = ""

    return result


def _row_to_target(row: pd.Series, notification_type: str, reason: str) -> dict[str, Any]:
    """問い合わせ行を通知対象dictに変換する。"""
    request_id = _normalize_text(row.get("request_id", ""))
    message = generate_notification_message(
        notification_type=notification_type,
        inquiry=row.to_dict(),
        reason=reason,
    )

    return {
        "request_id": request_id,
        "notification_type": notification_type,
        "notification_label": NOTIFICATION_TYPE_LABELS[notification_type],
        "reason": reason,
        "message": message,
        "requester": _normalize_text(row.get("requester", "")),
        "department": _normalize_text(row.get("department", "")),
        "category": _normalize_text(row.get("category", "")),
        "status": _normalize_text(row.get("status", "")),
        "assignee": _normalize_text(row.get("assignee", "")),
        "due_date": _normalize_text(row.get("due_date", "")),
        "priority": _normalize_text(row.get("priority", "")),
    }


def extract_before_due_targets(
    df: pd.DataFrame,
    days_before: int = 3,
) -> list[dict[str, Any]]:
    """期限が近い未完了問い合わせを抽出する。"""
    prepared = _prepare_inquiry_df(df)

    if prepared.empty:
        return []

    today = _today()
    upper = today + pd.Timedelta(days=days_before)

    targets = prepared[
        prepared["is_open"]
        & prepared["due_date_dt"].notna()
        & (prepared["due_date_dt"] >= today)
        & (prepared["due_date_dt"] <= upper)
    ].copy()

    return [
        _row_to_target(
            row,
            "before_due",
            f"希望期限が{days_before}日以内です。",
        )
        for _, row in targets.iterrows()
    ]


def extract_overdue_targets(df: pd.DataFrame) -> list[dict[str, Any]]:
    """期限超過の未完了問い合わせを抽出する。"""
    prepared = _prepare_inquiry_df(df)

    if prepared.empty:
        return []

    today = _today()

    targets = prepared[
        prepared["is_open"]
        & prepared["due_date_dt"].notna()
        & (prepared["due_date_dt"] < today)
    ].copy()

    return [
        _row_to_target(
            row,
            "overdue",
            "希望期限を過ぎています。",
        )
        for _, row in targets.iterrows()
    ]


def extract_unassigned_targets(df: pd.DataFrame) -> list[dict[str, Any]]:
    """担当者未設定の未完了問い合わせを抽出する。"""
    prepared = _prepare_inquiry_df(df)

    if prepared.empty:
        return []

    assignee = prepared["assignee"].fillna("").astype(str).str.strip()

    targets = prepared[
        prepared["is_open"]
        & ((assignee == "") | (assignee == "未設定"))
    ].copy()

    return [
        _row_to_target(
            row,
            "unassigned",
            "担当者が未設定です。",
        )
        for _, row in targets.iterrows()
    ]


def extract_waiting_too_long_targets(
    df: pd.DataFrame,
    waiting_days: int = 5,
) -> list[dict[str, Any]]:
    """情報待ちが長期化している問い合わせを抽出する。"""
    prepared = _prepare_inquiry_df(df)

    if prepared.empty:
        return []

    today = _today()

    base_date = prepared["last_status_changed_at_dt"]
    base_date = base_date.fillna(prepared["updated_at_dt"])
    base_date = base_date.fillna(prepared["request_date_dt"])

    elapsed_days = (today - base_date).dt.days

    status = prepared["status"].fillna("").astype(str).str.strip()

    targets = prepared[
        prepared["is_open"]
        & (status == "情報待ち")
        & base_date.notna()
        & (elapsed_days >= waiting_days)
    ].copy()

    return [
        _row_to_target(
            row,
            "waiting_too_long",
            f"情報待ちになってから{waiting_days}日以上経過しています。",
        )
        for _, row in targets.iterrows()
    ]


def extract_notification_targets(
    df: pd.DataFrame,
    days_before: int = 3,
    waiting_days: int = 5,
) -> list[dict[str, Any]]:
    """通知対象をまとめて抽出する。"""
    targets: list[dict[str, Any]] = []

    targets.extend(extract_overdue_targets(df))
    targets.extend(extract_before_due_targets(df, days_before=days_before))
    targets.extend(extract_unassigned_targets(df))
    targets.extend(extract_waiting_too_long_targets(df, waiting_days=waiting_days))

    return targets


def generate_notification_message(
    notification_type: str,
    inquiry: dict[str, Any],
    reason: str = "",
) -> str:
    """通知種別に応じた通知文を生成する。"""
    request_id = _normalize_text(inquiry.get("request_id", ""))
    requester = _normalize_text(inquiry.get("requester", ""))
    department = _normalize_text(inquiry.get("department", ""))
    category = _normalize_text(inquiry.get("category", ""))
    status = _normalize_text(inquiry.get("status", ""))
    assignee = _normalize_text(inquiry.get("assignee", "")) or "未設定"
    due_date = _normalize_text(inquiry.get("due_date", "")) or "未設定"
    priority = _normalize_text(inquiry.get("priority", "")) or "未設定"

    label = NOTIFICATION_TYPE_LABELS.get(notification_type, notification_type)

    if notification_type == "completed":
        return (
            f"【{label}通知】問い合わせ {request_id} は完了しました。\n"
            f"依頼者: {requester}（{department}）\n"
            f"カテゴリ: {category}\n"
            f"対応状況: {status}"
        )

    if notification_type == "status_changed":
        return (
            f"【{label}通知】問い合わせ {request_id} のステータスが変更されました。\n"
            f"依頼者: {requester}（{department}）\n"
            f"カテゴリ: {category}\n"
            f"現在のステータス: {status}\n"
            f"担当者: {assignee}"
        )

    return (
        f"【{label}通知】問い合わせ {request_id} を確認してください。\n"
        f"理由: {reason}\n"
        f"依頼者: {requester}（{department}）\n"
        f"カテゴリ: {category}\n"
        f"ステータス: {status}\n"
        f"担当者: {assignee}\n"
        f"希望期限: {due_date}\n"
        f"優先度: {priority}"
    )


def save_notification_target(
    target: dict[str, Any],
    user_id: str = "",
) -> str:
    """通知対象をnotification_logsに保存する。"""
    notification_id = insert_notification_log(
        request_id=target["request_id"],
        notification_type=target["notification_type"],
        recipient_user_id="",
        message=target["message"],
        status="created",
    )

    insert_operation_log(
        action="create_notification",
        target_table="notification_logs",
        target_id=notification_id,
        user_id=user_id,
        detail=(
            f'問い合わせ {target["request_id"]} の'
            f'{target["notification_label"]}通知文を生成'
        ),
    )

    return notification_id


def get_notification_logs(limit: int = 100) -> list[dict[str, Any]]:
    """通知ログを取得する。"""
    return fetch_notification_logs(limit=limit)


def change_notification_status(
    notification_id: str,
    status: str,
    user_id: str = "",
) -> None:
    """通知ログの状態を変更する。"""
    if status not in NOTIFICATION_STATUSES:
        raise ValueError(f"不正な通知状態です: {status}")

    update_notification_status(
        notification_id=notification_id,
        status=status,
    )

    insert_operation_log(
        action="update_notification_status",
        target_table="notification_logs",
        target_id=notification_id,
        user_id=user_id,
        detail=f"通知ログの状態を {status} に変更",
    )