from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.auth_service import get_current_user
from src.services.requester_service import (
    filter_inquiries_for_requester,
    get_requester_summary,
)


def show_requester_home_page(df: pd.DataFrame) -> None:
    """依頼者トップ画面を表示する。"""
    current_user = get_current_user()

    st.header("依頼者トップ")

    if current_user is None:
        st.error("ログイン情報を取得できません。再ログインしてください。")
        return

    st.write(
        f'{current_user["user_name"]}さん（{current_user["department"]}）の'
        "問い合わせ確認画面です。"
    )

    requester_df = filter_inquiries_for_requester(
        df=df,
        user=current_user,
        include_hidden=False,
    )

    summary = get_requester_summary(requester_df)

    col_total, col_open, col_completed, col_overdue = st.columns(4)

    col_total.metric("自分の問い合わせ", summary["total"])
    col_open.metric("対応中・未完了", summary["open"])
    col_completed.metric("完了", summary["completed"])
    col_overdue.metric("期限超過", summary["overdue"])

    st.markdown("---")
    st.markdown("### 利用できる機能")

    col_faq, col_create, col_status = st.columns(3)

    with col_faq:
        st.markdown("#### FAQ検索")
        st.write("問い合わせ前に、よくある質問を確認できます。")
        st.caption("左メニューの「FAQ検索」から利用できます。")

    with col_create:
        st.markdown("#### 新規問い合わせ")
        st.write("FAQで解決しない場合は、新しい問い合わせを登録できます。")
        st.caption("左メニューの「新規登録」から利用できます。")

    with col_status:
        st.markdown("#### 自分の問い合わせ")
        st.write("登録済みの問い合わせ状況を確認できます。")
        st.caption("左メニューの「自分の問い合わせ」から利用できます。")

    if requester_df.empty:
        st.info("現在、あなたに紐づく表示可能な問い合わせはありません。")
        return

    st.markdown("---")
    st.markdown("### 最近の問い合わせ")

    recent_columns = [
        col
        for col in [
            "request_id",
            "request_date",
            "category",
            "subcategory",
            "status",
            "assignee",
            "due_date",
            "completed_date",
        ]
        if col in requester_df.columns
    ]

    st.dataframe(
        requester_df[recent_columns].head(5),
        width="stretch",
        hide_index=True,
    )