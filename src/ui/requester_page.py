from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.aggregation import format_date_columns_for_display
from src.requester_view import (
    filter_requester_inquiries,
    get_requester_display_columns,
    get_requester_status_counts,
)

def show_requester_page(df: pd.DataFrame) -> None:
    """依頼者向け確認画面を表示する。"""

    st.header("依頼者向け確認")

    st.caption(
        "依頼者が、自分の問い合わせ状況を確認するための画面です。"
    )

    st.info(
        "この画面はデモ用です。本格運用ではログイン認証・権限管理を行い、"
        "本人の問い合わせのみ表示する必要があります。"
    )

    if df.empty:
        st.warning("確認できる問い合わせデータがありません。")
        return

    status_summary = get_requester_status_counts(df)

    if not status_summary.empty:
        with st.expander("依頼者向け表示対象のステータス別件数"):
            st.dataframe(
                status_summary,
                width="stretch",
                hide_index=True,
            )
    st.markdown("### 問い合わせを検索")

    with st.form("requester_search_form"):
        search_mode = st.radio(
            "検索方法",
            ["問い合わせIDで検索", "依頼者名で検索"],
            horizontal=True,
        )

        request_id_query = ""
        requester_query = ""

        if search_mode == "問い合わせIDで検索":
            request_id_query = st.text_input(
                "問い合わせID",
                placeholder="例：REQ-20260701-001",
            )
        else:
            requester_query = st.text_input(
                "依頼者名",
                placeholder="例：吉田 拓也",
            )

        search_submitted = st.form_submit_button("問い合わせ状況を確認")

    if not search_submitted:
        st.info("問い合わせIDまたは依頼者名を入力して検索してください。")
        return

    if not request_id_query.strip() and not requester_query.strip():
        st.error("検索条件を入力してください。")
        return
        if not request_id_query.strip() and not requester_query.strip():
            st.error("検索条件を入力してください。")
            return

    result_df = filter_requester_inquiries(
        df,
        request_id=request_id_query,
        requester=requester_query,
        include_hidden=False,
    )

    if result_df.empty:
        st.warning("該当する問い合わせは見つかりませんでした。")
        return

    display_columns = get_requester_display_columns(result_df)
    display_df = result_df[display_columns].copy()

    display_df = format_date_columns_for_display(display_df)

    column_config = {
        "request_id": "問い合わせID",
        "request_date": "受付日",
        "requester": "依頼者",
        "department": "部署",
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

    st.markdown("### 問い合わせ状況")

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config=column_config,
    )

    st.markdown("### 詳細確認")

    for _, row in display_df.iterrows():
        request_id = row.get("request_id", "")

        with st.expander(f"問い合わせID：{request_id}", expanded=len(display_df) == 1):
            st.write(f"**受付日**：{row.get('request_date', '')}")
            st.write(f"**依頼者**：{row.get('requester', '')}（{row.get('department', '')}）")
            st.write(f"**カテゴリ**：{row.get('category', '')} / {row.get('subcategory', '')}")
            st.write(f"**ステータス**：{row.get('status', '')}")
            st.write(f"**担当者**：{row.get('assignee', '') or '未設定'}")
            st.write(f"**希望期限**：{row.get('due_date', '')}")
            st.write(f"**完了日**：{row.get('completed_date', '') or '未完了'}")
            st.write("**問い合わせ内容**：")
            st.write(row.get("detail", ""))

            if row.get("additional_info"):
                st.write("**追加情報**：")
                st.text(row.get("additional_info", ""))

            if row.get("response_summary"):
                st.write("**管理部からの回答・対応内容**：")
                st.write(row.get("response_summary", ""))
            else:
                st.info("管理部からの回答・対応内容はまだ登録されていません。")

    with st.expander("この画面で表示しない情報"):
        st.markdown(
            """
            依頼者向け画面では、以下のような管理部内部向け情報は表示しません。

            - 管理作業時間
            - 実対応時間
            - 記録・管理上の問題
            - FAQ候補フラグ
            - FAQ回答案の下書き
            """
        )