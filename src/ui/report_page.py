from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.alerts import add_alert_columns, summarize_alerts
from src.aggregation import format_date_columns_for_display
from src.summary import (
    count_by,
    effort_by,
    overdue_table,
    response_days_by_category,
    summarize_basic_metrics,
    category_additional_info_summary,
    faq_candidate_by_category,
    requester_visible_summary,
    summarize_ver2_metrics,
)
from src.tableau_export import export_tableau_csv, make_tableau_dataframe, to_csv_bytes, export_ver3_tableau_csvs
from src.services.report_service import (
    get_ver3_export_dataframes,
    summarize_comments_by_visibility,
    summarize_faq_by_category,
    summarize_notification_logs_by_status,
    summarize_notification_logs_by_type,
    summarize_operation_logs_by_action,
    summarize_status_history_by_new_status,
    summarize_ver3_metrics,
)

def show_tableau_export_section(df: pd.DataFrame) -> None:
    """Tableau連携用CSVの出力UIを表示する。"""
    st.markdown("### Tableau用CSV出力")
    st.caption(
        "Tableauで可視化しやすいように、期限超過フラグ、完了フラグ、対応日数、作業時間などの派生列を追加して出力します。"
    )

    tableau_df = make_tableau_dataframe(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("出力行数", f"{len(tableau_df)}行")
    col2.metric("出力列数", f"{len(tableau_df.columns)}列")
    col3.metric("出力ファイル", "tableau_output.csv")

    with st.expander("出力列を確認する"):
        columns_df = pd.DataFrame(
            {
                "列名": tableau_df.columns.tolist(),
            }
        )
        st.dataframe(columns_df, width="stretch", hide_index=True)

    with st.expander("出力データのプレビュー"):
        st.dataframe(
            tableau_df.head(20),
            width="stretch",
            hide_index=True,
        )

    col_download, col_save = st.columns(2)

    with col_download:
        st.download_button(
            label="Tableau用CSVをダウンロード",
            data=to_csv_bytes(df),
            file_name="tableau_output.csv",
            mime="text/csv",
        )

    with col_save:
        if st.button("data/tableau_output.csv に保存"):
            try:
                output_path = export_tableau_csv(df)
                st.success(f"CSVを保存しました: {output_path}")
            except Exception as exc:
                st.error("CSVの保存に失敗しました。")
                st.exception(exc)


def show_ver3_report_section() -> None:
    """Ver.3追加機能の集計UIを表示する。"""

    st.markdown("### Ver.3追加機能の集計")
    st.caption(
        "公開FAQ、コメント履歴、ステータス履歴、操作ログ、通知ログの状況を確認します。"
    )

    metrics = summarize_ver3_metrics()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("公開FAQ", metrics["public_faq"])
    col2.metric("非公開FAQ", metrics["private_faq"])
    col3.metric("FAQ閲覧数", metrics["total_view_count"])
    col4.metric("FAQ役立ち率", f'{metrics["helpful_rate"]}%')

    col5, col6, col7, col8 = st.columns(4)

    col5.metric("コメント履歴", metrics["comment_count"])
    col6.metric("ステータス履歴", metrics["status_history_count"])
    col7.metric("操作ログ", metrics["operation_log_count"])
    col8.metric("通知ログ", metrics["notification_log_count"])

    st.markdown("#### FAQカテゴリ別集計")
    faq_category_df = summarize_faq_by_category()

    if faq_category_df.empty:
        st.info("FAQ集計対象がありません。")
    else:
        st.dataframe(faq_category_df, width="stretch", hide_index=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### コメント表示区分別件数")
        comments_df = summarize_comments_by_visibility()

        if comments_df.empty:
            st.info("コメント履歴はまだありません。")
        else:
            st.dataframe(comments_df, width="stretch", hide_index=True)

        st.markdown("#### 操作種別別件数")
        operation_df = summarize_operation_logs_by_action()

        if operation_df.empty:
            st.info("操作ログはまだありません。")
        else:
            st.dataframe(operation_df, width="stretch", hide_index=True)

    with col_b:
        st.markdown("#### 変更後ステータス別件数")
        status_df = summarize_status_history_by_new_status()

        if status_df.empty:
            st.info("ステータス履歴はまだありません。")
        else:
            st.dataframe(status_df, width="stretch", hide_index=True)

        st.markdown("#### 通知種別別件数")
        notification_type_df = summarize_notification_logs_by_type()

        if notification_type_df.empty:
            st.info("通知ログはまだありません。")
        else:
            st.dataframe(notification_type_df, width="stretch", hide_index=True)

    st.markdown("#### 通知状態別件数")
    notification_status_df = summarize_notification_logs_by_status()

    if notification_status_df.empty:
        st.info("通知ログはまだありません。")
    else:
        st.dataframe(notification_status_df, width="stretch", hide_index=True)


def show_ver3_tableau_export_section() -> None:
    """Ver.3追加テーブルのTableau用CSV出力UIを表示する。"""
    st.divider()
    st.markdown("### Ver.3 Tableau用CSV出力")
    st.caption(
        "Ver.3で追加したFAQ・コメント履歴・ステータス履歴・操作ログ・通知ログを、"
        "Tableauで扱いやすいようにテーブル別CSVとして出力します。"
    )

    export_dataframes = get_ver3_export_dataframes()

    summary_rows = [
        {
            "出力ファイル": f"{name}.csv",
            "行数": len(df),
            "列数": len(df.columns),
        }
        for name, df in export_dataframes.items()
    ]

    st.dataframe(
        pd.DataFrame(summary_rows),
        width="stretch",
        hide_index=True,
    )

    with st.expander("Ver.3出力データのプレビュー"):
        selected_name = st.selectbox(
            "プレビューするテーブル",
            list(export_dataframes.keys()),
        )

        preview_df = export_dataframes[selected_name]

        if preview_df.empty:
            st.info("このテーブルにはまだデータがありません。")
        else:
            st.dataframe(
                preview_df.head(20),
                width="stretch",
                hide_index=True,
            )

    if st.button("Ver.3 Tableau用CSVを保存"):
        output_paths = export_ver3_tableau_csvs(export_dataframes)

        st.success("Ver.3 Tableau用CSVを保存しました。")

        for path in output_paths:
            st.write(f"- {path}")


def show_report_page(df: pd.DataFrame) -> None:
    """集計・CSV出力画面を表示する。"""
    st.header("集計・CSV出力")

    if df.empty:
        st.warning("集計できるデータがありません。")
        return

    st.subheader("基本集計")
    st.caption("問い合わせ管理の状況を、件数・期限超過・担当者負荷・作業時間の観点から確認します。")

    metrics = summarize_basic_metrics(df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("問い合わせ件数", f"{metrics['total_count']}件")
    col2.metric("未完了件数", f"{metrics['open_count']}件")
    col3.metric("期限超過件数", f"{metrics['overdue_count']}件")
    col4.metric("平均対応日数", f"{metrics['avg_response_days']:.1f}日")

    col5, col6, col7 = st.columns(3)
    col5.metric("管理作業時間", f"{metrics['total_management_hours']:.1f}時間")
    col6.metric("実対応時間", f"{metrics['total_actual_response_hours']:.1f}時間")
    col7.metric(
        "問い合わせ関連時間",
        f"{metrics['total_management_hours'] + metrics['total_actual_response_hours']:.1f}時間",
    )

    st.divider()

    st.markdown("### 期限超過案件")
    overdue_df = overdue_table(df)

    if overdue_df.empty:
        st.success("期限超過案件はありません。")
    else:
        display_overdue_df = format_date_columns_for_display(overdue_df)
        st.dataframe(
            display_overdue_df,
            width="stretch",
            hide_index=True,
        )

    st.divider()

    st.markdown("### 件数集計")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### カテゴリ別件数")
        st.dataframe(
            count_by(df, "category", "カテゴリ"),
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### 担当者別件数")
        st.dataframe(
            count_by(df, "assignee", "担当者"),
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### 部署別件数")
        st.dataframe(
            count_by(df, "department", "部署"),
            width="stretch",
            hide_index=True,
        )

    with col_b:
        st.markdown("#### ステータス別件数")
        st.dataframe(
            count_by(df, "status", "ステータス"),
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### 受付経路別件数")
        st.dataframe(
            count_by(df, "channel", "受付経路"),
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### 優先度別件数")
        st.dataframe(
            count_by(df, "priority", "優先度"),
            width="stretch",
            hide_index=True,
        )

    st.divider()

    st.markdown("### 作業時間集計")

    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("#### 担当者別 作業時間")
        st.dataframe(
            effort_by(df, "assignee", "担当者"),
            width="stretch",
            hide_index=True,
        )

    with col_d:
        st.markdown("#### カテゴリ別 作業時間")
        st.dataframe(
            effort_by(df, "category", "カテゴリ"),
            width="stretch",
            hide_index=True,
        )

    st.divider()

    st.markdown("### 対応日数")

    response_summary = response_days_by_category(df)

    if response_summary.empty:
        st.info("完了日が登録された案件がないため、対応日数はまだ集計できません。")
    else:
        st.dataframe(
            response_summary,
            width="stretch",
            hide_index=True,
        )

    st.divider()

    st.markdown("### Ver.2追加機能の集計")

    ver2_metrics = summarize_ver2_metrics(df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("要対応アラート", ver2_metrics["alert_count"])
    col2.metric("FAQ候補", ver2_metrics["faq_candidate_count"])
    col3.metric("追加情報あり", ver2_metrics["additional_info_count"])
    col4.metric("追加情報入力率", f'{ver2_metrics["additional_info_rate"]}%')

    col5, col6 = st.columns(2)
    col5.metric("依頼者向け表示", ver2_metrics["requester_visible_count"])
    col6.metric("依頼者向け非表示", ver2_metrics["requester_hidden_count"])

    st.markdown("#### アラート種別別件数")
    alert_summary_df = summarize_alerts(add_alert_columns(df))
    st.dataframe(
        alert_summary_df,
        width="stretch",
        hide_index=True,
    )

    st.markdown("#### カテゴリ別FAQ候補件数")
    faq_category_df = faq_candidate_by_category(df)

    if faq_category_df.empty:
        st.info("FAQ候補はまだ登録されていません。")
    else:
        st.dataframe(
            faq_category_df,
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### カテゴリ別追加情報入力率")
    additional_info_summary_df = category_additional_info_summary(df)

    if additional_info_summary_df.empty:
        st.info("追加情報の集計対象がありません。")
    else:
        st.dataframe(
            additional_info_summary_df,
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### 依頼者向け表示制御")
    st.dataframe(
        requester_visible_summary(df),
        width="stretch",
        hide_index=True,
    )

    st.divider()

    show_ver3_report_section()

    show_tableau_export_section(df)

    show_ver3_tableau_export_section()