from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.auth_service import get_current_role
from src.services.history_service import (
    get_comments_for_staff,
    get_inquiry_history_bundle,
    get_operation_logs,
    get_status_history,
)


def show_history_page(df: pd.DataFrame) -> None:
    """管理者向け履歴確認画面を表示する。"""
    st.header("履歴確認")

    current_role = get_current_role()

    if current_role != "admin":
        st.error("この画面を利用する権限がありません。")
        return

    st.caption(
        "問い合わせごとのコメント履歴、ステータス履歴、"
        "主要操作ログを確認する管理者向け画面です。"
    )

    st.markdown("### 操作ログ")

    operation_logs = get_operation_logs(limit=100)

    if operation_logs:
        st.dataframe(
            pd.DataFrame(operation_logs),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("操作ログはまだありません。")

    st.markdown("---")
    st.markdown("### 問い合わせ別履歴")

    if df.empty:
        st.warning("確認できる問い合わせデータがありません。")
        return

    display_df = df.copy()
    display_df["history_label"] = display_df.apply(
        lambda row: (
            f'{row.get("request_id", "")}|'
            f'{row.get("requester", "")}|'
            f'{row.get("category", "")}|'
            f'{row.get("status", "")}'
        ),
        axis=1,
    )

    label_to_id = dict(zip(display_df["history_label"], display_df["request_id"]))

    selected_label = st.selectbox(
        "履歴を確認する問い合わせ",
        display_df["history_label"].tolist(),
    )

    selected_request_id = label_to_id[selected_label]

    history_bundle = get_inquiry_history_bundle(selected_request_id)

    comments = history_bundle["comments"]
    status_histories = history_bundle["status_history"]
    related_operation_logs = history_bundle["operation_logs"]

    st.markdown("#### コメント履歴")

    if comments:
        for comment in comments:
            visibility_label = (
                "依頼者にも表示"
                if comment["visibility"] == "requester"
                else "内部メモ"
            )

            with st.container(border=True):
                st.caption(
                    f'{visibility_label} / '
                    f'作成者: {comment.get("created_by", "") or "不明"} / '
                    f'作成日時: {comment.get("created_at", "")}'
                )
                st.write(comment.get("comment_body", ""))
    else:
        st.info("コメント履歴はありません。")

    st.markdown("#### ステータス履歴")

    if status_histories:
        for history in status_histories:
            with st.container(border=True):
                st.caption(
                    f'変更者: {history.get("changed_by", "") or "不明"} / '
                    f'変更日時: {history.get("changed_at", "")}'
                )
                st.write(
                    f'{history.get("old_status", "") or "未設定"} '
                    f'→ {history.get("new_status", "")}'
                )
    else:
        st.info("ステータス履歴はありません。")

    st.markdown("#### この問い合わせに関連する操作ログ")

    if related_operation_logs:
        st.dataframe(
            pd.DataFrame(related_operation_logs),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("関連する操作ログはありません。")