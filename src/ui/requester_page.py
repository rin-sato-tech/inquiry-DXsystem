from __future__ import annotations

import pandas as pd
import streamlit as st

from src.aggregation import format_date_columns_for_display
from src.services.auth_service import get_current_user, get_current_role
from src.services.requester_service import (
    filter_inquiries_for_requester,
    filter_requester_inquiries_by_status,
    get_requester_summary,
)


def show_requester_page(df: pd.DataFrame) -> None:
    """ログイン中依頼者本人の問い合わせ状況を表示する。"""
    st.header("自分の問い合わせ")

    current_user = get_current_user()
    current_role = get_current_role()

    if current_user is None:
        st.error("ログイン情報を取得できません。再ログインしてください。")
        return

    if current_role not in {"requester", "admin"}:
        st.error("この画面を利用する権限がありません。")
        return

    if df.empty:
        st.warning("確認できる問い合わせデータがありません。")
        return

    requester_df = filter_inquiries_for_requester(
        df=df,
        user=current_user,
        include_hidden=False,
    )

    st.caption(
        f'{current_user["user_name"]}さん（{current_user["department"]}）に'
        "紐づく問い合わせのみ表示しています。"
    )

    summary = get_requester_summary(requester_df)

    col_total, col_open, col_completed, col_overdue = st.columns(4)

    col_total.metric("表示対象", summary["total"])
    col_open.metric("対応中・未完了", summary["open"])
    col_completed.metric("完了", summary["completed"])
    col_overdue.metric("期限超過", summary["overdue"])

    if requester_df.empty:
        st.info("あなたに紐づく表示可能な問い合わせはありません。")
        return

    st.markdown("### 絞り込み")

    status_options = ["すべて"]
    if "status" in requester_df.columns:
        status_options += sorted(
            [
                status
                for status in requester_df["status"].dropna().astype(str).unique().tolist()
                if status
            ]
        )

    selected_status = st.selectbox("ステータス", status_options)

    display_df = filter_requester_inquiries_by_status(
        requester_df,
        selected_status,
    )

    display_columns = [
        col
        for col in [
            "request_id",
            "request_date",
            "category",
            "subcategory",
            "detail",
            "additional_info",
            "status",
            "assignee",
            "due_date",
            "completed_date",
            "response_summary",
        ]
        if col in display_df.columns
    ]

    if display_df.empty:
        st.warning("条件に一致する問い合わせはありません。")
        return

    display_df = display_df[display_columns].copy()
    display_df = format_date_columns_for_display(display_df)

    column_config = {
        "request_id": "問い合わせID",
        "request_date": "受付日",
        "category": "カテゴリ",
        "subcategory": "小分類",
        "detail": "問い合わせ内容",
        "additional_info": "追加情報",
        "status": "ステータス",
        "assignee": "担当者",
        "due_date": "希望期限",
        "completed_date": "完了日",
        "response_summary": "管理部からの回答・対応内容",
    }

    st.markdown("### 問い合わせ一覧")

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config=column_config,
    )

    st.markdown("### 詳細確認")

    for _, row in display_df.iterrows():
        request_id = row.get("request_id", "")

        with st.expander(
            f"問い合わせID：{request_id}",
            expanded=len(display_df) == 1,
        ):
            st.write(f"**受付日**：{row.get('request_date', '')}")
            st.write(f"**カテゴリ**：{row.get('category', '')} / {row.get('subcategory', '')}")
            st.write(f"**ステータス**：{row.get('status', '')}")
            st.write(f"**担当者**：{row.get('assignee', '') or '未設定'}")
            st.write(f"**希望期限**：{row.get('due_date', '')}")
            st.write(f"**完了日**：{row.get('completed_date', '') or '未完了'}")

            st.markdown("#### 問い合わせ内容")
            st.write(row.get("detail", ""))

            additional_info = row.get("additional_info", "")
            if additional_info:
                st.markdown("#### 追加情報")
                st.write(additional_info)

            response_summary = row.get("response_summary", "")
            if response_summary:
                st.markdown("#### 管理部からの回答・対応内容")
                st.write(response_summary)