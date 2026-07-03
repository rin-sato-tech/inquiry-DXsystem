from __future__ import annotations

import pandas as pd

from src.alerts import add_alert_columns, summarize_alerts
from src.category_fields import format_additional_info, get_category_fields
from src.db import fetch_all_inquiries
from src.faq import add_faq_columns, get_faq_candidates
from src.requester_view import (
    add_requester_view_columns,
    filter_requester_inquiries,
    get_requester_display_columns,
)
from src.summary import (
    category_additional_info_summary,
    faq_candidate_by_category,
    requester_visible_summary,
    summarize_ver2_metrics,
)
from src.tableau_export import make_tableau_dataframe


REQUIRED_VER2_COLUMNS = [
    "faq_candidate",
    "faq_title",
    "faq_answer",
    "additional_info",
    "requester_visible",
    "last_status_changed_at",
]


ALERT_COLUMNS = [
    "alert_overdue",
    "alert_due_today",
    "alert_due_soon",
    "alert_unassigned",
    "alert_info_waiting_long",
    "has_alert",
    "alert_type",
]


TABLEAU_VER2_COLUMNS = [
    "additional_info",
    "has_additional_info",
    "has_additional_info_int",
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


def assert_columns_exist(df: pd.DataFrame, columns: list[str], label: str) -> None:
    """指定した列がDataFrameに存在するか確認する。"""
    missing_columns = [col for col in columns if col not in df.columns]

    if missing_columns:
        raise AssertionError(f"{label} に不足列があります: {missing_columns}")


def check_database_columns(df: pd.DataFrame) -> None:
    """Ver.2追加カラムがDB取得結果に含まれているか確認する。"""
    assert_columns_exist(df, REQUIRED_VER2_COLUMNS, "DB取得結果")
    print("OK: Ver.2追加カラムが存在します。")


def check_alerts(df: pd.DataFrame) -> None:
    """アラート列が作成できるか確認する。"""
    alert_df = add_alert_columns(df)
    assert_columns_exist(alert_df, ALERT_COLUMNS, "アラート判定結果")

    summary_df = summarize_alerts(alert_df)

    if summary_df.empty:
        raise AssertionError("アラート集計結果が空です。")

    print("OK: アラート判定・集計が動作しています。")


def check_faq(df: pd.DataFrame) -> None:
    """FAQ候補管理の派生列・抽出が動作するか確認する。"""
    faq_df = add_faq_columns(df)

    assert_columns_exist(
        faq_df,
        ["faq_candidate", "faq_title", "faq_answer", "is_faq_candidate"],
        "FAQ候補管理結果",
    )

    candidates = get_faq_candidates(faq_df)

    if not isinstance(candidates, pd.DataFrame):
        raise AssertionError("FAQ候補抽出結果がDataFrameではありません。")

    print("OK: FAQ候補管理の補正・抽出が動作しています。")


def check_category_fields() -> None:
    """カテゴリ別入力項目の定義と整形が動作するか確認する。"""
    fields = get_category_fields("PC・システム")

    if not fields:
        raise AssertionError("PC・システムのカテゴリ別項目が取得できません。")

    additional_info = format_additional_info(
        "PC・システム",
        {
            "pc_asset_id": "PC-001",
            "occurred_at": "09:30",
            "error_detail": "ログイン時にエラーが出る",
            "reboot_done": "実施済み",
        },
    )

    if "PC管理番号" not in additional_info:
        raise AssertionError("カテゴリ別追加情報の整形に失敗しています。")

    print("OK: カテゴリ別入力項目の定義・整形が動作しています。")


def check_requester_view(df: pd.DataFrame) -> None:
    """依頼者向け確認画面用の表示制御・検索が動作するか確認する。"""
    requester_df = add_requester_view_columns(df)

    assert_columns_exist(
        requester_df,
        ["requester_visible", "is_requester_visible"],
        "依頼者向け表示結果",
    )

    filtered_df = filter_requester_inquiries(requester_df, requester="", request_id="")
    display_columns = get_requester_display_columns(requester_df)

    hidden_internal_columns = {
        "management_minutes",
        "actual_response_minutes",
        "record_issue",
        "faq_candidate",
        "faq_answer",
    }

    leaked_columns = hidden_internal_columns.intersection(display_columns)

    if leaked_columns:
        raise AssertionError(f"依頼者向け表示列に内部列が含まれています: {leaked_columns}")

    if not isinstance(filtered_df, pd.DataFrame):
        raise AssertionError("依頼者向け検索結果がDataFrameではありません。")

    print("OK: 依頼者向け表示制御・検索が動作しています。")


def check_ver2_summary(df: pd.DataFrame) -> None:
    """Ver.2集計関数が動作するか確認する。"""
    metrics = summarize_ver2_metrics(df)

    required_metric_keys = {
        "alert_count",
        "faq_candidate_count",
        "additional_info_count",
        "additional_info_rate",
        "requester_visible_count",
        "requester_hidden_count",
    }

    missing_keys = required_metric_keys.difference(metrics.keys())

    if missing_keys:
        raise AssertionError(f"Ver.2 KPIに不足キーがあります: {missing_keys}")

    category_additional_info_summary(df)
    faq_candidate_by_category(df)
    requester_visible_summary(df)

    print("OK: Ver.2集計関数が動作しています。")


def check_tableau_export(df: pd.DataFrame) -> None:
    """Tableau出力用DataFrameにVer.2列が含まれるか確認する。"""
    tableau_df = make_tableau_dataframe(df)

    assert_columns_exist(tableau_df, TABLEAU_VER2_COLUMNS, "Tableau出力DataFrame")

    print("OK: Tableau出力にVer.2列が含まれています。")


def main() -> None:
    records = fetch_all_inquiries()
    df = pd.DataFrame(records)

    if df.empty:
        raise AssertionError("問い合わせデータが空です。テスト用データを登録してください。")

    print("=== Ver.2 スモークテスト開始 ===")
    print(f"問い合わせ件数: {len(df)}")
    print()

    check_database_columns(df)
    check_alerts(df)
    check_faq(df)
    check_category_fields()
    check_requester_view(df)
    check_ver2_summary(df)
    check_tableau_export(df)

    print()
    print("=== Ver.2 スモークテスト完了 ===")


if __name__ == "__main__":
    main()