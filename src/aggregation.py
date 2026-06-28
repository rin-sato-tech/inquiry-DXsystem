from __future__ import annotations

from datetime import date

import pandas as pd


def add_derived_columns(df: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    """
    問い合わせデータに表示・集計用の派生列を追加する。

    追加する主な列:
    - overdue_flag: 期限超過フラグ
    - is_completed: 完了済みフラグ
    - is_open: 未完了フラグ
    - response_days: 対応日数
    - request_month: 受付月
    - management_hours: 管理作業時間
    - actual_response_hours: 実対応時間
    """
    if df.empty:
        return df.copy()

    result = df.copy()

    for col in ["request_date", "due_date", "completed_date"]:
        if col in result.columns:
            result[col] = pd.to_datetime(result[col], errors="coerce")

    today_ts = pd.Timestamp(today or date.today()).normalize()

    result["is_completed"] = result["status"].eq("完了")
    result["is_open"] = ~result["is_completed"]

    result["overdue_flag"] = (
        result["is_open"]
        & result["due_date"].notna()
        & (result["due_date"] < today_ts)
    )

    result["response_days"] = (
        result["completed_date"] - result["request_date"]
    ).dt.days

    result["request_month"] = result["request_date"].dt.strftime("%Y-%m")

    result["management_minutes"] = pd.to_numeric(
        result.get("management_minutes", 0),
        errors="coerce"
    ).fillna(0).astype(int)

    result["actual_response_minutes"] = pd.to_numeric(
        result.get("actual_response_minutes", 0),
        errors="coerce"
    ).fillna(0).astype(int)

    result["management_hours"] = result["management_minutes"] / 60
    result["actual_response_hours"] = result["actual_response_minutes"] / 60

    return result


def format_date_columns_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Streamlit表示用に日付列をYYYY-MM-DD形式の文字列へ変換する。"""
    result = df.copy()

    for col in ["request_date", "due_date", "completed_date"]:
        if col in result.columns:
            result[col] = pd.to_datetime(result[col], errors="coerce").dt.strftime("%Y-%m-%d")
            result[col] = result[col].fillna("")

    return result