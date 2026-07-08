from __future__ import annotations

import streamlit as st

from src.services.auth_service import get_active_users, login_user


def show_login_page() -> None:
    """ユーザー選択式の簡易ログイン画面を表示する。"""
    st.header("ログイン")

    st.info(
        "Ver.3では、ポートフォリオ用の簡易ログインとして、"
        "ユーザー選択式でロール別表示を確認します。"
    )

    users = get_active_users()

    if not users:
        st.error("ログイン可能なユーザーが登録されていません。")
        st.caption("先に python -m src.check_db を実行して初期ユーザーを登録してください。")
        return

    user_options = {
        f'{user["user_id"]}: {user["user_name"]}（{user["department"]} / {user["role"]}）': user["user_id"]
        for user in users
    }

    id_to_user = {
        user["user_id"]: user
        for user in users
    }

    selected_label = st.selectbox(
        "ログインユーザー",
        list(user_options.keys()),
    )

    selected_user_id = user_options[selected_label]
    selected_user = id_to_user.get(selected_user_id)

    st.markdown("### 選択中ユーザー")
    st.write(f'ユーザーID: {selected_user["user_id"]}')
    st.write(f'氏名: {selected_user["user_name"]}')
    st.write(f'部署: {selected_user["department"]}')
    st.write(f'ロール: {selected_user["role"]}')

    if st.button("このユーザーでログイン", type="primary"):
        try:
            login_user(selected_user_id)
        except ValueError as error:
            st.error(str(error))
            return

        st.rerun()