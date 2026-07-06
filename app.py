from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.aggregation import add_derived_columns
from src.db import fetch_all_inquiries, init_db

from src.ui.inquiry_create_page import show_inquiry_create_page
from src.ui.inquiry_update_page import show_inquiry_update_page
from src.ui.alert_page import show_alert_page
from src.ui.faq_admin_page import show_faq_admin_page
from src.ui.inquiry_list_page import show_inquiry_list_page
from src.ui.requester_page import show_requester_page
from src.ui.report_page import show_report_page

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


def main() -> None:
    st.title("社内問い合わせ管理システム")
    st.caption("管理部に寄せられる社内問い合わせ・依頼対応を一元管理するためのデモアプリです。")

    df = load_inquiries()

    tab_alert, tab_list, tab_create, tab_update, tab_faq, tab_requester, tab_summary = st.tabs(
        [
            "要対応アラート",
            "問い合わせ一覧",
            "新規登録",
            "ステータス更新",
            "FAQ候補管理",
            "依頼者向け確認",
            "集計・CSV出力",
        ]
    )

    with tab_alert:
        show_alert_page(df)

    with tab_list:
        show_inquiry_list_page(df)

    with tab_create:
        show_inquiry_create_page()

    with tab_update:
        show_inquiry_update_page(df)

    with tab_faq:
        show_faq_admin_page(df)

    with tab_requester:
        show_requester_page(df)

    with tab_summary:
        show_report_page(df)


if __name__ == "__main__":
    main()