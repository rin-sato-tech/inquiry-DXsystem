from __future__ import annotations

import pandas as pd


def count_by(df: pd.DataFrame, column: str, label_name: str) -> pd.DataFrame:
    """
    指定列ごとの件数を集計する。
    空欄は「未設定」として扱う。
    """
    if df.empty or column not in df.columns:
        return pd.DataFrame(columns=[label_name, "件数"])

    values = (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", "未設定")
    )

    return (
        values
        .value_counts()
        .rename_axis(label_name)
        .reset_index(name="件数")
    )


def summarize_basic_metrics(df: pd.DataFrame) -> dict[str, float | int]:
    """
    集計画面上部に表示する基本KPIを作る。
    """
    if df.empty:
        return {
            "total_count": 0,
            "open_count": 0,
            "completed_count": 0,
            "overdue_count": 0,
            "avg_response_days": 0.0,
            "total_management_hours": 0.0,
            "total_actual_response_hours": 0.0,
        }

    completed_response_days = pd.to_numeric(
        df.loc[df["is_completed"], "response_days"],
        errors="coerce",
    ).dropna()

    avg_response_days = (
        float(completed_response_days.mean())
        if not completed_response_days.empty
        else 0.0
    )

    return {
        "total_count": int(len(df)),
        "open_count": int(df["is_open"].sum()),
        "completed_count": int(df["is_completed"].sum()),
        "overdue_count": int(df["overdue_flag"].sum()),
        "avg_response_days": avg_response_days,
        "total_management_hours": float(df["management_hours"].sum()),
        "total_actual_response_hours": float(df["actual_response_hours"].sum()),
    }


def effort_by(df: pd.DataFrame, group_col: str, label_name: str) -> pd.DataFrame:
    """
    指定列ごとに件数・管理作業時間・実対応時間を集計する。
    """
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(
            columns=[
                label_name,
                "件数",
                "管理作業時間",
                "実対応時間",
                "合計時間",
            ]
        )

    work_df = df.copy()

    work_df[group_col] = (
        work_df[group_col]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", "未設定")
    )

    summary = (
        work_df
        .groupby(group_col, dropna=False)
        .agg(
            件数=("request_id", "count"),
            管理作業時間=("management_hours", "sum"),
            実対応時間=("actual_response_hours", "sum"),
        )
        .reset_index()
        .rename(columns={group_col: label_name})
    )

    summary["合計時間"] = summary["管理作業時間"] + summary["実対応時間"]

    for col in ["管理作業時間", "実対応時間", "合計時間"]:
        summary[col] = summary[col].round(2)

    return summary.sort_values("件数", ascending=False)


def overdue_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    期限超過案件の一覧を作る。
    """
    if df.empty or "overdue_flag" not in df.columns:
        return pd.DataFrame()

    columns = [
        "request_id",
        "request_date",
        "requester",
        "department",
        "category",
        "priority",
        "due_date",
        "assignee",
        "status",
        "detail",
    ]

    existing_columns = [col for col in columns if col in df.columns]

    result = (
        df[df["overdue_flag"]]
        .copy()
        .sort_values(["due_date", "priority"], ascending=[True, True])
    )

    return result[existing_columns]


def response_days_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    完了案件について、カテゴリ別の平均対応日数を集計する。
    """
    if df.empty:
        return pd.DataFrame(columns=["カテゴリ", "完了件数", "平均対応日数"])

    completed = df[df["is_completed"]].copy()

    if completed.empty:
        return pd.DataFrame(columns=["カテゴリ", "完了件数", "平均対応日数"])

    completed["response_days"] = pd.to_numeric(
        completed["response_days"],
        errors="coerce",
    )

    summary = (
        completed
        .dropna(subset=["response_days"])
        .groupby("category")
        .agg(
            完了件数=("request_id", "count"),
            平均対応日数=("response_days", "mean"),
        )
        .reset_index()
        .rename(columns={"category": "カテゴリ"})
    )

    summary["平均対応日数"] = summary["平均対応日数"].round(1)

    return summary.sort_values("平均対応日数", ascending=False)