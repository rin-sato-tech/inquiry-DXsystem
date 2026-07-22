from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.auth_service import get_current_role, get_current_user
from src.services.history_service import get_user_id
from src.services.notification_service import (
    change_notification_status,
    extract_notification_targets,
    get_notification_logs,
    save_notification_target,
)


def show_notification_page(df: pd.DataFrame) -> None:
    """通知対象確認画面を表示する。"""
    st.header("通知対象確認")

    current_role = get_current_role()
    current_user = get_current_user()
    user_id = get_user_id(current_user)

    if current_role not in {"staff", "admin"}:
        st.error("この画面を利用する権限がありません。")
        return

    st.caption(
        "外部送信は行わず、対応漏れ・遅延リスクのある問い合わせを抽出し、"
        "通知文を生成・保存する画面です。"
    )

    if df.empty:
        st.warning("確認できる問い合わせデータがありません。")
        return

    st.markdown("### 抽出条件")

    col_before, col_waiting = st.columns(2)

    with col_before:
        days_before = st.number_input(
            "期限前通知の日数",
            min_value=1,
            max_value=14,
            value=3,
            step=1,
        )

    with col_waiting:
        waiting_days = st.number_input(
            "情報待ち長期化の日数",
            min_value=1,
            max_value=30,
            value=5,
            step=1,
        )

    targets = extract_notification_targets(
        df=df,
        days_before=int(days_before),
        waiting_days=int(waiting_days),
    )

    st.markdown("### 通知対象一覧")
    st.caption(f"{len(targets)}件の通知対象があります。")

    if not targets:
        st.info("現在、通知対象はありません。")
    else:
        display_columns = [
            "notification_label",
            "request_id",
            "reason",
            "requester",
            "department",
            "category",
            "status",
            "assignee",
            "due_date",
            "priority",
        ]

        st.dataframe(
            pd.DataFrame(targets)[display_columns],
            width="stretch",
            hide_index=True,
        )

        st.markdown("### 通知文生成・保存")

        target_options = {
            (
                f'{target["notification_label"]}|'
                f'{target["request_id"]}|'
                f'{target["requester"]}|'
                f'{target["reason"]}'
            ): index
            for index, target in enumerate(targets)
        }

        selected_label = st.selectbox(
            "通知文を確認する対象",
            list(target_options.keys()),
        )

        selected_target = targets[target_options[selected_label]]

        st.markdown("#### 通知文プレビュー")
        st.text_area(
            "通知文",
            value=selected_target["message"],
            height=220,
            disabled=True,
        )

        if st.button("通知ログに保存", type="primary"):
            notification_id = save_notification_target(
                selected_target,
                user_id=user_id,
            )
            st.success(f"通知ログに保存しました: {notification_id}")
            st.rerun()

    st.markdown("---")
    st.markdown("### 通知ログ")

    logs = get_notification_logs(limit=100)

    if not logs:
        st.info("通知ログはまだありません。")
        return

    logs_df = pd.DataFrame(logs)

    st.dataframe(
        logs_df,
        width="stretch",
        hide_index=True,
    )

    st.markdown("### 通知ログの状態更新")

    log_options = {
        (
            f'{log["notification_id"]}|'
            f'{log["notification_type"]}|'
            f'{log["status"]}|'
            f'{log["request_id"]}'
        ): log["notification_id"]
        for log in logs
    }

    selected_log_label = st.selectbox(
        "状態を更新する通知ログ",
        list(log_options.keys()),
    )

    selected_notification_id = log_options[selected_log_label]

    new_status_label = st.radio(
        "新しい状態",
        ["確認済み", "除外", "作成済みに戻す"],
        horizontal=True,
    )

    status_map = {
        "確認済み": "reviewed",
        "除外": "skipped",
        "作成済みに戻す": "created",
    }

    if st.button("通知状態を更新"):
        change_notification_status(
            notification_id=selected_notification_id,
            status=status_map[new_status_label],
            user_id=user_id,
        )
        st.success("通知状態を更新しました。")
        st.rerun()