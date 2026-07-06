from __future__ import annotations

import io
from typing import Any

import pandas as pd


FAQ_DISPLAY_COLUMNS = [
    "request_id",
    "completed_date",
    "category",
    "subcategory",
    "detail",
    "response_summary",
    "faq_title",
    "faq_answer",
]


def _to_dataframe(data: pd.DataFrame | list[dict[str, Any]]) -> pd.DataFrame:
    """DataFrameまたは辞書リストをDataFrameに変換する。"""
    return pd.DataFrame(data).copy()


def add_faq_columns(
    data: pd.DataFrame | list[dict[str, Any]],
) -> pd.DataFrame:
    """
    FAQ候補管理に必要な列を補正する。

    追加・補正する列:
    - faq_candidate
    - faq_title
    - faq_answer
    - is_faq_candidate
    """

    result = _to_dataframe(data)

    if result.empty:
        result["faq_candidate"] = pd.Series(dtype="int")
        result["faq_title"] = pd.Series(dtype="str")
        result["faq_answer"] = pd.Series(dtype="str")
        result["is_faq_candidate"] = pd.Series(dtype="bool")
        return result

    if "faq_candidate" not in result.columns:
        result["faq_candidate"] = 0

    if "faq_title" not in result.columns:
        result["faq_title"] = ""

    if "faq_answer" not in result.columns:
        result["faq_answer"] = ""

    result["faq_candidate"] = (
        pd.to_numeric(result["faq_candidate"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    result["faq_title"] = result["faq_title"].fillna("").astype(str).str.strip()
    result["faq_answer"] = result["faq_answer"].fillna("").astype(str).str.strip()

    result["is_faq_candidate"] = result["faq_candidate"].eq(1)

    return result


def get_completed_inquiries(
    data: pd.DataFrame | list[dict[str, Any]],
) -> pd.DataFrame:
    """完了済み問い合わせだけを取得する。"""

    df = add_faq_columns(data)

    if df.empty or "status" not in df.columns:
        return df.iloc[0:0].copy()

    status = df["status"].fillna("").astype(str).str.strip()

    return df[status.eq("完了")].copy()


def get_faq_candidates(
    data: pd.DataFrame | list[dict[str, Any]],
) -> pd.DataFrame:
    """FAQ候補に設定された問い合わせだけを取得する。"""

    df = add_faq_columns(data)

    if df.empty:
        return df

    return df[df["is_faq_candidate"]].copy()


def summarize_faq_candidates(
    data: pd.DataFrame | list[dict[str, Any]],
) -> pd.DataFrame:
    """カテゴリ別のFAQ候補件数を集計する。"""

    candidates = get_faq_candidates(data)

    if candidates.empty or "category" not in candidates.columns:
        return pd.DataFrame(columns=["category", "count"])

    summary = (
        candidates.groupby("category", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    return summary


def get_faq_display_columns(df: pd.DataFrame) -> list[str]:
    """FAQ候補一覧で表示する列を返す。存在する列だけ返す。"""

    return [col for col in FAQ_DISPLAY_COLUMNS if col in df.columns]


def make_faq_csv_dataframe(
    data: pd.DataFrame | list[dict[str, Any]],
) -> pd.DataFrame:
    """FAQ候補CSV出力用のDataFrameを作る。"""

    candidates = get_faq_candidates(data)

    output_columns = [
        "request_id",
        "category",
        "subcategory",
        "detail",
        "response_summary",
        "faq_title",
        "faq_answer",
        "completed_date",
    ]

    existing_columns = [col for col in output_columns if col in candidates.columns]

    return candidates[existing_columns].copy()


def to_faq_csv_bytes(
    data: pd.DataFrame | list[dict[str, Any]],
) -> bytes:
    """FAQ候補CSVをbytesで返す。"""

    output_df = make_faq_csv_dataframe(data)

    buffer = io.StringIO()
    output_df.to_csv(buffer, index=False, encoding="utf-8-sig")

    return buffer.getvalue().encode("utf-8-sig")