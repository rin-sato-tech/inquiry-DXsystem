from __future__ import annotations

from typing import Any

import pandas as pd

from src.db import (
    fetch_all_inquiry_comments,
    fetch_all_status_history,
    fetch_faq_items,
    fetch_notification_logs,
    fetch_operation_logs,
)


def _to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    """dictリストをDataFrameに変換する。"""
    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def summarize_ver3_metrics() -> dict[str, int | float]:
    """Ver.3追加機能の主要指標を集計する。"""
    faq_df = _to_dataframe(fetch_faq_items(is_public=None))
    comments_df = _to_dataframe(fetch_all_inquiry_comments())
    status_history_df = _to_dataframe(fetch_all_status_history())
    operation_logs_df = _to_dataframe(fetch_operation_logs(limit=1000))
    notification_logs_df = _to_dataframe(fetch_notification_logs(limit=1000))

    total_faq = int(len(faq_df))
    public_faq = 0
    private_faq = 0
    total_view_count = 0
    total_helpful_count = 0

    if not faq_df.empty:
        public_faq = int(faq_df["is_public"].fillna(0).astype(int).sum())
        private_faq = int(total_faq - public_faq)
        total_view_count = int(faq_df["view_count"].fillna(0).astype(int).sum())
        total_helpful_count = int(faq_df["helpful_count"].fillna(0).astype(int).sum())

    helpful_rate = 0.0
    if total_view_count > 0:
        helpful_rate = round(total_helpful_count / total_view_count * 100, 1)

    requester_comment_count = 0
    internal_comment_count = 0

    if not comments_df.empty and "visibility" in comments_df.columns:
        visibility = comments_df["visibility"].fillna("").astype(str)
        requester_comment_count = int((visibility == "requester").sum())
        internal_comment_count = int((visibility == "internal").sum())

    return {
        "total_faq": total_faq,
        "public_faq": public_faq,
        "private_faq": private_faq,
        "total_view_count": total_view_count,
        "total_helpful_count": total_helpful_count,
        "helpful_rate": helpful_rate,
        "comment_count": int(len(comments_df)),
        "requester_comment_count": requester_comment_count,
        "internal_comment_count": internal_comment_count,
        "status_history_count": int(len(status_history_df)),
        "operation_log_count": int(len(operation_logs_df)),
        "notification_log_count": int(len(notification_logs_df)),
    }


def summarize_faq_by_category() -> pd.DataFrame:
    """カテゴリ別FAQ指標を集計する。"""
    faq_df = _to_dataframe(fetch_faq_items(is_public=None))

    if faq_df.empty:
        return pd.DataFrame(
            columns=[
                "category",
                "faq_count",
                "public_faq_count",
                "private_faq_count",
                "view_count",
                "helpful_count",
                "helpful_rate",
            ]
        )

    faq_df = faq_df.copy()
    faq_df["is_public"] = faq_df["is_public"].fillna(0).astype(int)
    faq_df["view_count"] = faq_df["view_count"].fillna(0).astype(int)
    faq_df["helpful_count"] = faq_df["helpful_count"].fillna(0).astype(int)

    summary = (
        faq_df.groupby("category", dropna=False)
        .agg(
            faq_count=("faq_id", "count"),
            public_faq_count=("is_public", "sum"),
            view_count=("view_count", "sum"),
            helpful_count=("helpful_count", "sum"),
        )
        .reset_index()
    )

    summary["private_faq_count"] = summary["faq_count"] - summary["public_faq_count"]
    summary["helpful_rate"] = summary.apply(
        lambda row: round(row["helpful_count"] / row["view_count"] * 100, 1)
        if row["view_count"] > 0
        else 0.0,
        axis=1,
    )

    return summary[
        [
            "category",
            "faq_count",
            "public_faq_count",
            "private_faq_count",
            "view_count",
            "helpful_count",
            "helpful_rate",
        ]
    ]


def summarize_comments_by_visibility() -> pd.DataFrame:
    """コメント表示区分別件数を集計する。"""
    comments_df = _to_dataframe(fetch_all_inquiry_comments())

    if comments_df.empty or "visibility" not in comments_df.columns:
        return pd.DataFrame(columns=["visibility", "comment_count"])

    return (
        comments_df["visibility"]
        .fillna("未設定")
        .astype(str)
        .value_counts()
        .rename_axis("visibility")
        .reset_index(name="comment_count")
    )


def summarize_status_history_by_new_status() -> pd.DataFrame:
    """変更後ステータス別の履歴件数を集計する。"""
    status_df = _to_dataframe(fetch_all_status_history())

    if status_df.empty or "new_status" not in status_df.columns:
        return pd.DataFrame(columns=["new_status", "change_count"])

    return (
        status_df["new_status"]
        .fillna("未設定")
        .astype(str)
        .value_counts()
        .rename_axis("new_status")
        .reset_index(name="change_count")
    )


def summarize_operation_logs_by_action() -> pd.DataFrame:
    """操作種別別件数を集計する。"""
    logs_df = _to_dataframe(fetch_operation_logs(limit=1000))

    if logs_df.empty or "action" not in logs_df.columns:
        return pd.DataFrame(columns=["action", "operation_count"])

    return (
        logs_df["action"]
        .fillna("未設定")
        .astype(str)
        .value_counts()
        .rename_axis("action")
        .reset_index(name="operation_count")
    )


def summarize_notification_logs_by_type() -> pd.DataFrame:
    """通知種別別件数を集計する。"""
    logs_df = _to_dataframe(fetch_notification_logs(limit=1000))

    if logs_df.empty or "notification_type" not in logs_df.columns:
        return pd.DataFrame(columns=["notification_type", "notification_count"])

    return (
        logs_df["notification_type"]
        .fillna("未設定")
        .astype(str)
        .value_counts()
        .rename_axis("notification_type")
        .reset_index(name="notification_count")
    )


def summarize_notification_logs_by_status() -> pd.DataFrame:
    """通知状態別件数を集計する。"""
    logs_df = _to_dataframe(fetch_notification_logs(limit=1000))

    if logs_df.empty or "status" not in logs_df.columns:
        return pd.DataFrame(columns=["status", "notification_count"])

    return (
        logs_df["status"]
        .fillna("未設定")
        .astype(str)
        .value_counts()
        .rename_axis("status")
        .reset_index(name="notification_count")
    )


def get_ver3_export_dataframes() -> dict[str, pd.DataFrame]:
    """Ver.3追加テーブルのTableau出力用DataFrameを取得する。"""
    return {
        "tableau_faq_items": _to_dataframe(fetch_faq_items(is_public=None)),
        "tableau_inquiry_comments": _to_dataframe(fetch_all_inquiry_comments()),
        "tableau_status_history": _to_dataframe(fetch_all_status_history()),
        "tableau_operation_logs": _to_dataframe(fetch_operation_logs(limit=1000)),
        "tableau_notification_logs": _to_dataframe(fetch_notification_logs(limit=1000)),
    }