from __future__ import annotations

import streamlit as st

from src.services.auth_service import get_current_user, logout_user


def show_login_status() -> None:
    """ログイン中ユーザー情報をサイドバーに表示する。"""
    user = get_current_user()

    if user is None:
        return

    st.sidebar.markdown("### ログイン中")
    st.sidebar.write(f'氏名: {user["user_name"]}')
    st.sidebar.write(f'部署: {user["department"]}')
    st.sidebar.write(f'ロール: {user["role"]}')

    if st.sidebar.button("ログアウト"):
        logout_user()
        st.rerun()