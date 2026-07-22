from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from src.alerts import add_alert_columns
from src.faq import add_faq_columns
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
    "days_until_due",
    "days_overdue",
    "response_days",
    "management_minutes",
    "actual_response_minutes",
    "management_hours",
    "actual_response_hours",
    "total_work_hours",
    "detail",
    "missing_info",
    "additional_info",
    "has_additional_info",
    "has_additional_info_int",
    "response_summary",
    "record_issue",
    "faq_candidate",
    "faq_candidate_int",
    "faq_title",
    "faq_answer",
    "requester_visible",
    "requester_visible_int",
    "requester_visible_label",
    "alert_overdue",
    "alert_due_today",
    "alert_due_soon",
    "alert_unassigned",
    "alert_info_waiting_long",
    "has_alert",
    "alert_type",
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
    result = add_alert_columns(result, today=today)
    result = add_faq_columns(result)

    today_ts = pd.Timestamp(today or date.today()).normalize()

    # 空欄をTableau上で扱いやすくする
    for col in [
        "assignee",
        "subcategory",
        "missing_info",
        "additional_info",
        "response_summary",
        "record_issue",
        "faq_title",
        "faq_answer",
        "alert_type",
    ]:
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

    # Ver.2: 追加情報の入力有無
    if "additional_info" not in result.columns:
        result["additional_info"] = ""

    result["has_additional_info"] = (
        result["additional_info"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
    )
    result["has_additional_info_int"] = (
        result["has_additional_info"].astype(int)
    )

    # Ver.2: FAQ候補
    if "faq_candidate" not in result.columns:
        result["faq_candidate"] = 0

    result["faq_candidate"] = (
        pd.to_numeric(result["faq_candidate"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    result["faq_candidate_int"] = result["faq_candidate"]

    # Ver.2: 依頼者向け表示制御
    if "requester_visible" not in result.columns:
        result["requester_visible"] = 1

    result["requester_visible"] = (
        pd.to_numeric(result["requester_visible"], errors="coerce")
        .fillna(1)
        .astype(int)
    )
    result["requester_visible_int"] = result["requester_visible"]
    result["requester_visible_label"] = result["requester_visible"].map(
        {
            1: "依頼者向け表示",
            0: "依頼者向け非表示",
        }
    ).fillna("依頼者向け非表示")

    # Ver.2: アラート列をTableauで集計しやすい0/1にそろえる
    for col in [
        "alert_overdue",
        "alert_due_today",
        "alert_due_soon",
        "alert_unassigned",
        "alert_info_waiting_long",
        "has_alert",
    ]:
        if col not in result.columns:
            result[col] = False

        result[col] = result[col].fillna(False).astype(bool)

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


def export_ver3_tableau_csvs(
    dataframes: dict[str, pd.DataFrame],
    output_dir: Path = Path("data"),
) -> list[Path]:
    """Ver.3追加テーブルをTableau用CSVとして出力する。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths: list[Path] = []

    for name, df in dataframes.items():
        output_path = output_dir / f"{name}.csv"
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        output_paths.append(output_path)

    return output_paths