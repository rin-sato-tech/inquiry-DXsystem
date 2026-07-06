from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.aggregation import format_date_columns_for_display


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
        "additional_info",
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
        "additional_info": "カテゴリ別追加情報",
        "response_summary": "対応内容",
    }

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config=column_config,
    )


def show_inquiry_list_page(df: pd.DataFrame) -> None:
    """問い合わせ一覧画面を表示する。"""
    st.header("問い合わせ一覧")

    if df.empty:
        st.warning("問い合わせデータがありません。")
        return

    st.markdown("### 絞り込み条件")

    col1, col2, col3 = st.columns(3)

    with col1:
        departments = st.multiselect(
            "部署",
            get_options(df, "department"),
        )
        categories = st.multiselect(
            "カテゴリ",
            get_options(df, "category"),
        )

    with col2:
        assignees = st.multiselect(
            "担当者",
            get_options(df, "assignee"),
        )
        statuses = st.multiselect(
            "ステータス",
            get_options(df, "status"),
        )

    with col3:
        priorities = st.multiselect(
            "優先度",
            get_options(df, "priority"),
        )
        show_overdue_only = st.checkbox("期限超過のみ表示")

    filtered_df = apply_filters(
        df,
        departments=departments,
        categories=categories,
        assignees=assignees,
        statuses=statuses,
        priorities=priorities,
        show_overdue_only=show_overdue_only,
    )

    st.markdown("### KPI")
    st.caption("現在の絞り込み条件に基づく件数です。")
    show_kpi_cards(filtered_df)

    st.markdown("### 問い合わせ一覧")
    show_inquiry_table(filtered_df)