from __future__ import annotations

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
from src.services.auth_service import (
    get_available_page_labels,
    get_current_role,
    get_page_key_by_label,
    has_permission,
    initialize_auth_state,
    is_logged_in,
)
from src.ui.auth_components import show_login_status
from src.ui.login_page import show_login_page
from src.ui.faq_public_page import show_faq_public_page

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
    initialize_auth_state()

    st.title("社内問い合わせ管理システム")
    st.caption("管理部に寄せられる社内問い合わせ・依頼対応を一元管理するためのデモアプリです。")

    if not is_logged_in():
        show_login_page()
        return

    show_login_status()

    role = get_current_role()
    if role is None:
        st.error("ロール情報を取得できません。再ログインしてください。")
        return

    page_labels = get_available_page_labels(role)
    selected_label = st.sidebar.radio("メニュー", page_labels)
    page_key = get_page_key_by_label(role, selected_label)

    if not has_permission(page_key, role):
        st.error("この画面を利用する権限がありません。")
        return

    df = load_inquiries()

    if page_key == "alert":
        show_alert_page(df)

    elif page_key == "inquiry_list":
        show_inquiry_list_page(df)

    elif page_key == "inquiry_create":
        show_inquiry_create_page()

    elif page_key == "inquiry_update":
        show_inquiry_update_page(df)

    elif page_key == "faq_admin":
        show_faq_admin_page(df)

    elif page_key == "requester_inquiries":
        show_requester_page(df)

    elif page_key == "report":
        show_report_page(df)

    elif page_key == "requester_home":
        st.header("依頼者トップ")
        st.info("依頼者トップ画面はWBS5で本格実装します。")
        st.markdown("- FAQ検索")
        st.markdown("- 新規問い合わせ")
        st.markdown("- 自分の問い合わせ確認")

    elif page_key == "faq_public":
        show_faq_public_page()

    else:
        st.error(f"未対応のページです: {page_key}")


if __name__ == "__main__":
    main()