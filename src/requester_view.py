from __future__ import annotations

from typing import Any

import pandas as pd


REQUESTER_DISPLAY_COLUMNS = [
    "request_id",
    "request_date",
    "requester",
    "department",
    "category",
    "subcategory",
    "detail",
    "additional_info",
    "status",
    "assignee",
    "due_date",
    "completed_date",
    "response_summary",
]


def _to_dataframe(data: pd.DataFrame | list[dict[str, Any]]) -> pd.DataFrame:
    """DataFrameまたは辞書リストをDataFrameに変換する。"""
    return pd.DataFrame(data).copy()


def add_requester_view_columns(
    data: pd.DataFrame | list[dict[str, Any]],
) -> pd.DataFrame:
    """
    依頼者向け確認画面で使う列を補正する。

    追加・補正する列:
    - requester_visible
    - is_requester_visible
    """

    result = _to_dataframe(data)

    if result.empty:
        result["requester_visible"] = pd.Series(dtype="int")
        result["is_requester_visible"] = pd.Series(dtype="bool")
        return result

    if "requester_visible" not in result.columns:
        result["requester_visible"] = 1

    result["requester_visible"] = (
        pd.to_numeric(result["requester_visible"], errors="coerce")
        .fillna(1)
        .astype(int)
    )

    result["is_requester_visible"] = result["requester_visible"].eq(1)

    return result


def filter_requester_inquiries(
    data: pd.DataFrame | list[dict[str, Any]],
    request_id: str = "",
    requester: str = "",
    include_hidden: bool = False,
) -> pd.DataFrame:
    """
    依頼者向け確認画面用に問い合わせを検索する。

    - request_id が指定されている場合は、問い合わせIDで部分一致検索する
    - requester が指定されている場合は、依頼者名で部分一致検索する
    - include_hidden=False の場合、requester_visible=1 のみ表示する
    """

    df = add_requester_view_columns(data)

    if df.empty:
        return df

    result = df.copy()

    if not include_hidden:
        result = result[result["is_requester_visible"]].copy()

    request_id = request_id.strip()
    requester = requester.strip()

    if request_id and "request_id" in result.columns:
        result = result[
            result["request_id"]
            .fillna("")
            .astype(str)
            .str.contains(request_id, case=False, na=False)
        ].copy()

    if requester and "requester" in result.columns:
        result = result[
            result["requester"]
            .fillna("")
            .astype(str)
            .str.contains(requester, case=False, na=False)
        ].copy()

    return result


def get_requester_display_columns(df: pd.DataFrame) -> list[str]:
    """依頼者向け画面で表示する列を返す。存在する列だけ返す。"""

    return [col for col in REQUESTER_DISPLAY_COLUMNS if col in df.columns]


def get_requester_status_counts(
    data: pd.DataFrame | list[dict[str, Any]],
) -> pd.DataFrame:
    """依頼者向けにステータス別件数を集計する。"""

    df = add_requester_view_columns(data)

    if df.empty or "status" not in df.columns:
        return pd.DataFrame(columns=["status", "count"])

    visible_df = df[df["is_requester_visible"]].copy()

    if visible_df.empty:
        return pd.DataFrame(columns=["status", "count"])

    return (
        visible_df.groupby("status", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )