from __future__ import annotations

from typing import Any

import pandas as pd


def get_requester_identity(user: dict[str, Any] | None) -> tuple[str, str]:
    """ログイン中ユーザーから依頼者名・部署を取得する。"""
    if user is None:
        return "", ""

    requester_name = str(user.get("user_name", "")).strip()
    department = str(user.get("department", "")).strip()

    return requester_name, department


def filter_inquiries_for_requester(
    df: pd.DataFrame,
    user: dict[str, Any] | None,
    include_hidden: bool = False,
) -> pd.DataFrame:
    """
    ログイン中依頼者本人の問い合わせだけを抽出する。

    現時点では inquiries に requester_user_id がないため、
    requester名とdepartmentで本人判定する。
    """
    if df.empty or user is None:
        return pd.DataFrame(columns=df.columns)

    requester_name, department = get_requester_identity(user)

    if not requester_name or not department:
        return pd.DataFrame(columns=df.columns)

    result = df.copy()

    if "requester" not in result.columns or "department" not in result.columns:
        return pd.DataFrame(columns=df.columns)

    result = result[
        (result["requester"].fillna("").astype(str).str.strip() == requester_name)
        & (result["department"].fillna("").astype(str).str.strip() == department)
    ].copy()

    if not include_hidden and "requester_visible" in result.columns:
        result = result[result["requester_visible"].fillna(0).astype(int) == 1].copy()

    return result


def get_requester_summary(df: pd.DataFrame) -> dict[str, int]:
    """依頼者本人の問い合わせサマリーを作成する。"""
    if df.empty:
        return {
            "total": 0,
            "open": 0,
            "completed": 0,
            "overdue": 0,
        }

    status = df["status"].fillna("").astype(str) if "status" in df.columns else pd.Series([], dtype=str)

    completed_mask = status == "完了"
    open_mask = ~completed_mask

    overdue_count = 0
    if "is_overdue" in df.columns:
        overdue_count = int(df["is_overdue"].fillna(False).astype(bool).sum())

    return {
        "total": int(len(df)),
        "open": int(open_mask.sum()),
        "completed": int(completed_mask.sum()),
        "overdue": overdue_count,
    }


def filter_requester_inquiries_by_status(
    df: pd.DataFrame,
    status_filter: str,
) -> pd.DataFrame:
    """依頼者向け問い合わせをステータスで絞り込む。"""
    if df.empty or status_filter == "すべて":
        return df

    if "status" not in df.columns:
        return df

    return df[df["status"] == status_filter].copy()