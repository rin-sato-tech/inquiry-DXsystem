from __future__ import annotations

import pandas as pd
import streamlit as st

from src.aggregation import add_derived_columns, format_date_columns_for_display
from src.db import fetch_all_inquiries, init_db


st.set_page_config(
    page_title="社内問い合わせ管理システム",
    layout="wide",
)


@st.cache_data(ttl=10)
def load_inquiries() -> pd.DataFrame:
    """SQLiteから問い合わせデータを読み込み、派生列を追加する。"""
    init_db()
    rows = fetch_all_inquiries()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = add_derived_columns(df)
    return df


def get_options(df: pd.DataFrame, column: str) -> list[str]:
    """フィルタ用の選択肢を作る。"""
    if df.empty or column not in df.columns:
        return []

    values = (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return sorted([v for v in values.unique().tolist() if v])


def apply_filters(
    df: pd.DataFrame,
    departments: list[str],
    categories: list[str],
    assignees: list[str],
    statuses: list[str],
    priorities: list[str],
    show_overdue_only: bool,
) -> pd.DataFrame:
    """画面で選択された条件に従ってDataFrameを絞り込む。"""
    filtered = df.copy()

    if departments:
        filtered = filtered[filtered["department"].isin(departments)]

    if categories:
        filtered = filtered[filtered["category"].isin(categories)]

    if assignees:
        filtered = filtered[filtered["assignee"].isin(assignees)]

    if statuses:
        filtered = filtered[filtered["status"].isin(statuses)]

    if priorities:
        filtered = filtered[filtered["priority"].isin(priorities)]

    if show_overdue_only:
        filtered = filtered[filtered["overdue_flag"]]

    return filtered


def show_kpi_cards(df: pd.DataFrame) -> None:
    """主要KPIを表示する。"""
    total_count = len(df)

    if df.empty:
        open_count = 0
        overdue_count = 0
        completed_count = 0
        management_hours = 0.0
    else:
        open_count = int(df["is_open"].sum())
        overdue_count = int(df["overdue_flag"].sum())
        completed_count = int(df["is_completed"].sum())
        management_hours = float(df["management_hours"].sum())

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("問い合わせ件数", f"{total_count}件")
    col2.metric("未完了件数", f"{open_count}件")
    col3.metric("完了件数", f"{completed_count}件")
    col4.metric("期限超過件数", f"{overdue_count}件")
    col5.metric("管理作業時間", f"{management_hours:.1f}時間")


def show_inquiry_table(df: pd.DataFrame) -> None:
    """問い合わせ一覧を表示する。"""
    if df.empty:
        st.warning("表示できる問い合わせデータがありません。")
        return

    display_columns = [
        "request_id",
        "request_date",
        "request_time",
        "requester",
        "department",
        "channel",
        "category",
        "subcategory",
        "priority",
        "due_date",
        "assignee",
        "status",
        "overdue_flag",
        "detail",
        "response_summary",
    ]

    existing_columns = [col for col in display_columns if col in df.columns]
    display_df = df[existing_columns].copy()

    display_df = format_date_columns_for_display(display_df)

    if "overdue_flag" in display_df.columns:
        display_df["overdue_flag"] = display_df["overdue_flag"].map(
            {True: "期限超過", False: ""}
        )

    column_config = {
        "request_id": "問い合わせID",
        "request_date": "受付日",
        "request_time": "受付時刻",
        "requester": "依頼者",
        "department": "部署",
        "channel": "受付経路",
        "category": "カテゴリ",
        "subcategory": "小分類",
        "priority": "優先度",
        "due_date": "希望期限",
        "assignee": "担当者",
        "status": "ステータス",
        "overdue_flag": "期限超過",
        "detail": "問い合わせ内容",
        "response_summary": "対応内容",
    }

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )


def show_simple_summary(df: pd.DataFrame) -> None:
    """確認用の簡易集計を表示する。正式な集計画面は後続フェーズで拡張する。"""
    if df.empty:
        st.warning("集計できるデータがありません。")
        return

    st.subheader("簡易集計")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### カテゴリ別件数")
        category_summary = (
            df["category"]
            .value_counts()
            .rename_axis("カテゴリ")
            .reset_index(name="件数")
        )
        st.dataframe(category_summary, use_container_width=True, hide_index=True)

        st.markdown("#### 担当者別件数")
        assignee_summary = (
            df["assignee"]
            .fillna("未設定")
            .replace("", "未設定")
            .value_counts()
            .rename_axis("担当者")
            .reset_index(name="件数")
        )
        st.dataframe(assignee_summary, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("#### ステータス別件数")
        status_summary = (
            df["status"]
            .value_counts()
            .rename_axis("ステータス")
            .reset_index(name="件数")
        )
        st.dataframe(status_summary, use_container_width=True, hide_index=True)

        st.markdown("#### 受付経路別件数")
        channel_summary = (
            df["channel"]
            .value_counts()
            .rename_axis("受付経路")
            .reset_index(name="件数")
        )
        st.dataframe(channel_summary, use_container_width=True, hide_index=True)


def main() -> None:
    st.title("社内問い合わせ管理システム")
    st.caption("管理部に寄せられる社内問い合わせ・依頼対応を一元管理するためのデモアプリです。")

    df = load_inquiries()

    tab_list, tab_create, tab_update, tab_summary = st.tabs(
        [
            "問い合わせ一覧",
            "新規登録",
            "ステータス更新",
            "集計・CSV出力",
        ]
    )

    with tab_list:
        st.header("問い合わせ一覧")

        if df.empty:
            st.warning("問い合わせデータがありません。先にCSVをSQLiteへ取り込んでください。")
            st.code("python -m src.import_csv", language="bash")
            return

        st.markdown("### 絞り込み条件")

        filter_col1, filter_col2, filter_col3 = st.columns(3)

        with filter_col1:
            selected_departments = st.multiselect(
                "部署",
                options=get_options(df, "department"),
            )

            selected_categories = st.multiselect(
                "カテゴリ",
                options=get_options(df, "category"),
            )

        with filter_col2:
            selected_assignees = st.multiselect(
                "担当者",
                options=get_options(df, "assignee"),
            )

            selected_statuses = st.multiselect(
                "ステータス",
                options=get_options(df, "status"),
            )

        with filter_col3:
            selected_priorities = st.multiselect(
                "優先度",
                options=get_options(df, "priority"),
            )

            show_overdue_only = st.checkbox("期限超過のみ表示")

        filtered_df = apply_filters(
            df=df,
            departments=selected_departments,
            categories=selected_categories,
            assignees=selected_assignees,
            statuses=selected_statuses,
            priorities=selected_priorities,
            show_overdue_only=show_overdue_only,
        )

        st.markdown("### KPI")
        st.caption("現在の絞り込み条件に基づく件数です。")
        show_kpi_cards(filtered_df)

        st.markdown("### 問い合わせ一覧")
        show_inquiry_table(filtered_df)

    with tab_create:
        st.header("新規登録")
        st.info("この画面は次フェーズで実装します。現在は問い合わせ一覧表示までを実装しています。")

    with tab_update:
        st.header("ステータス更新")
        st.info("この画面は次フェーズで実装します。担当者・ステータス・対応内容の更新機能を追加予定です。")

    with tab_summary:
        st.header("集計・CSV出力")
        st.info("正式なCSV出力機能は後続フェーズで実装します。ここでは確認用の簡易集計を表示します。")
        show_simple_summary(df)


if __name__ == "__main__":
    main()