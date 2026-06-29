from __future__ import annotations

import pandas as pd

from src.aggregation import add_derived_columns
from src.db import fetch_all_inquiries, init_db
from src.summary import (
    count_by,
    effort_by,
    overdue_table,
    response_days_by_category,
    summarize_basic_metrics,
)
from src.tableau_export import TABLEAU_COLUMNS, make_tableau_dataframe


def assert_ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    print("スモークテストを開始します。")

    init_db()
    rows = fetch_all_inquiries()

    assert_ok(len(rows) > 0, "問い合わせデータが0件です。CSV取込を確認してください。")

    df = pd.DataFrame(rows)

    required_columns = [
        "request_id",
        "request_date",
        "requester",
        "department",
        "channel",
        "category",
        "priority",
        "due_date",
        "status",
    ]

    for col in required_columns:
        assert_ok(col in df.columns, f"必要な列がありません: {col}")

    assert_ok(
        df["request_id"].is_unique,
        "request_id が重複しています。",
    )

    derived_df = add_derived_columns(df)

    derived_columns = [
        "is_completed",
        "is_open",
        "overdue_flag",
        "response_days",
        "request_month",
        "management_hours",
        "actual_response_hours",
    ]

    for col in derived_columns:
        assert_ok(col in derived_df.columns, f"派生列が作成されていません: {col}")

    metrics = summarize_basic_metrics(derived_df)

    assert_ok(
        metrics["total_count"] == len(derived_df),
        "基本KPIの問い合わせ件数がDataFrame件数と一致しません。",
    )

    category_summary = count_by(derived_df, "category", "カテゴリ")
    status_summary = count_by(derived_df, "status", "ステータス")
    assignee_effort = effort_by(derived_df, "assignee", "担当者")
    overdue_df = overdue_table(derived_df)
    response_summary = response_days_by_category(derived_df)

    assert_ok("件数" in category_summary.columns, "カテゴリ別集計に件数列がありません。")
    assert_ok("件数" in status_summary.columns, "ステータス別集計に件数列がありません。")
    assert_ok("合計時間" in assignee_effort.columns, "担当者別作業時間に合計時間列がありません。")

    tableau_df = make_tableau_dataframe(df)

    assert_ok(
        len(tableau_df) == len(df),
        "Tableau用DataFrameの行数が元データと一致しません。",
    )

    for col in TABLEAU_COLUMNS:
        assert_ok(col in tableau_df.columns, f"Tableau出力列が不足しています: {col}")

    print("集計対象件数:", len(df))
    print("期限超過件数:", int(derived_df["overdue_flag"].sum()))
    print("カテゴリ別集計行数:", len(category_summary))
    print("ステータス別集計行数:", len(status_summary))
    print("期限超過一覧行数:", len(overdue_df))
    print("対応日数集計行数:", len(response_summary))
    print("Tableau出力列数:", len(tableau_df.columns))

    print("スモークテストが正常に完了しました。")


if __name__ == "__main__":
    main()