from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from src.aggregation import add_derived_columns
from src.db import DATA_DIR


DEFAULT_OUTPUT_PATH = DATA_DIR / "tableau_output.csv"


TABLEAU_COLUMNS = [
    "request_id",
    "request_date",
    "request_month",
    "requester",
    "department",
    "channel",
    "category",
    "subcategory",
    "priority",
    "due_date",
    "assignee",
    "status",
    "status_group",
    "completed_date",
    "is_completed",
    "is_completed_int",
    "is_open",
    "is_open_int",
    "overdue_flag",
    "overdue_int",
    "overdue_label",
    "days_overdue",
    "response_days",
    "management_minutes",
    "actual_response_minutes",
    "management_hours",
    "actual_response_hours",
    "total_work_hours",
    "detail",
    "missing_info",
    "response_summary",
    "record_issue",
]


def _format_date_column(series: pd.Series) -> pd.Series:
    """日付列をTableauで扱いやすいYYYY-MM-DD文字列に整える。"""
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d").fillna("")


def make_tableau_dataframe(df: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    """
    Tableau出力用のDataFrameを作成する。

    DBの生データに対して、以下の列を追加・整形する。
    - request_month
    - is_completed / is_completed_int
    - is_open / is_open_int
    - overdue_flag / overdue_int / overdue_label
    - days_overdue
    - response_days
    - management_hours
    - actual_response_hours
    - total_work_hours
    """
    if df.empty:
        return pd.DataFrame(columns=TABLEAU_COLUMNS)

    result = add_derived_columns(df, today=today)

    today_ts = pd.Timestamp(today or date.today()).normalize()

    # 空欄をTableau上で扱いやすくする
    for col in ["assignee", "subcategory", "missing_info", "response_summary", "record_issue"]:
        if col in result.columns:
            result[col] = (
                result[col]
                .fillna("")
                .astype(str)
                .str.strip()
                .replace("", "未設定" if col in {"assignee", "subcategory"} else "")
            )

    # 完了・未完了の分類
    result["status_group"] = result["is_completed"].map(
        {True: "完了", False: "未完了"}
    )

    # Tableauで集計しやすいように 0/1 列も持たせる
    result["is_completed_int"] = result["is_completed"].fillna(False).astype(int)
    result["is_open_int"] = result["is_open"].fillna(False).astype(int)
    result["overdue_int"] = result["overdue_flag"].fillna(False).astype(int)

    result["overdue_label"] = result["overdue_flag"].map(
        {True: "期限超過", False: "期限内・完了"}
    )

    due_ts = pd.to_datetime(result["due_date"], errors="coerce")
    days_overdue = (today_ts - due_ts).dt.days
    result["days_overdue"] = days_overdue.where(result["overdue_flag"], 0).fillna(0).astype(int)

    result["response_days"] = pd.to_numeric(
        result["response_days"],
        errors="coerce",
    )

    result["management_minutes"] = pd.to_numeric(
        result["management_minutes"],
        errors="coerce",
    ).fillna(0).astype(int)

    result["actual_response_minutes"] = pd.to_numeric(
        result["actual_response_minutes"],
        errors="coerce",
    ).fillna(0).astype(int)

    result["management_hours"] = pd.to_numeric(
        result["management_hours"],
        errors="coerce",
    ).fillna(0).round(2)

    result["actual_response_hours"] = pd.to_numeric(
        result["actual_response_hours"],
        errors="coerce",
    ).fillna(0).round(2)

    result["total_work_hours"] = (
        result["management_hours"] + result["actual_response_hours"]
    ).round(2)

    # 日付列をCSV出力向けに整形
    for col in ["request_date", "due_date", "completed_date"]:
        if col in result.columns:
            result[col] = _format_date_column(result[col])

    if "request_month" not in result.columns:
        result["request_month"] = pd.to_datetime(
            result["request_date"],
            errors="coerce",
        ).dt.strftime("%Y-%m")

    # 不足列があれば補う
    for col in TABLEAU_COLUMNS:
        if col not in result.columns:
            result[col] = ""

    return result[TABLEAU_COLUMNS].copy()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Streamlitのdownload_button用にCSVをbytesへ変換する。"""
    tableau_df = make_tableau_dataframe(df)
    return tableau_df.to_csv(index=False).encode("utf-8-sig")


def export_tableau_csv(
    df: pd.DataFrame,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Tableau用CSVをファイルとして出力する。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tableau_df = make_tableau_dataframe(df)
    tableau_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    return output_path