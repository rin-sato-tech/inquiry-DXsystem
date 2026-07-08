from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.db import fetch_inquiry_by_id, update_inquiry
from src.master_data import get_assignees, get_statuses
from src.ui.components import (
    index_or_zero,
    parse_date_or_none,
    show_additional_info_block,
    make_update_label
)
from src.ui.cache_utils import clear_cache
from src.services.auth_service import get_current_user
from src.services.history_service import (
    add_inquiry_comment,
    get_comments_for_staff,
    get_status_history,
    get_user_id,
    record_inquiry_update_history,
)


def show_inquiry_update_page(df: pd.DataFrame) -> None:
    """既存問い合わせの更新フォームを表示する。"""
    st.header("ステータス更新")
    st.caption("管理部が担当者、ステータス、対応内容、完了日を更新する画面です。")

    if df.empty:
        st.warning("更新できる問い合わせデータがありません。")
        return

    display_df = df.copy()
    display_df["update_label"] = display_df.apply(make_update_label, axis=1)

    labels = display_df["update_label"].tolist()
    label_to_id = dict(zip(display_df["update_label"], display_df["request_id"]))

    selected_label = st.selectbox("更新対象の問い合わせ", labels)
    selected_request_id = label_to_id[selected_label]

    current = fetch_inquiry_by_id(selected_request_id)
    if current is None:
        st.error("選択した問い合わせが見つかりません。")
        return

    with st.expander("現在の問い合わせ内容", expanded=True):
        st.write(f"**問い合わせID**: {current.get('request_id', '')}")
        st.write(f"**依頼者**: {current.get('requester', '')}（{current.get('department', '')}）")
        st.write(f"**カテゴリ**: {current.get('category', '')} / {current.get('subcategory', '')}")
        st.write(f"**希望期限**: {current.get('due_date', '')}")
        st.write(f"**現在のステータス**: {current.get('status', '')}")
        st.write(f"**現在の完了日**: {current.get('completed_date', '') or '未設定'}")
        st.write(f"**問い合わせ内容**: {current.get('detail', '')}")
        if current.get("missing_info"):
            st.write(f"**不足情報・確認事項**: {current.get('missing_info', '')}")

        show_additional_info_block(current.get("additional_info", ""))

    assignee_options = ["未設定"] + get_assignees()
    statuses = get_statuses()

    current_assignee = current.get("assignee") or "未設定"
    current_status = current.get("status") or "未対応"
    current_completed_date = parse_date_or_none(current.get("completed_date"))

    st.markdown("### 更新内容")

    # ステータスはフォーム外に置く。
    # st.form内に入れると、ステータス変更に応じた完了日欄の表示切替が分かりにくくなるため。
    status = st.selectbox(
        "ステータス",
        statuses,
        index=index_or_zero(statuses, current_status),
        key=f"update_status_{selected_request_id}",
    )

    if status == "完了":
        st.info("ステータスが完了の場合は、完了日の入力が必須です。")
    else:
        st.info("ステータスが完了以外の場合、完了日は保存されません。既存の完了日がある場合は更新時にクリアされます。")

        if current_completed_date is not None:
            st.warning(
                "この問い合わせには現在完了日が入っています。"
                "ステータスを完了以外で更新すると、完了日はクリアされます。"
            )

    with st.form("update_inquiry_form"):
        col1, col2 = st.columns(2)

        with col1:
            assignee_label = st.selectbox(
                "担当者",
                assignee_options,
                index=index_or_zero(assignee_options, current_assignee),
            )

        with col2:
            if status == "完了":
                completed_date_value = st.date_input(
                    "完了日",
                    value=current_completed_date or date.today(),
                )
            else:
                completed_date_value = None
                st.text_input(
                    "完了日",
                    value="ステータスが完了以外のため設定不可",
                    disabled=True,
                )

        response_summary = st.text_area(
            "対応内容",
            value=current.get("response_summary", "") or "",
            height=120,
        )

        record_issue = st.text_area(
            "記録・管理上の問題",
            value=current.get("record_issue", "") or "",
            height=80,
        )

        col3, col4 = st.columns(2)

        with col3:
            management_minutes = st.number_input(
                "管理作業時間（分）",
                min_value=0,
                step=1,
                value=int(current.get("management_minutes") or 0),
            )

        with col4:
            actual_response_minutes = st.number_input(
                "実対応時間（分）",
                min_value=0,
                step=1,
                value=int(current.get("actual_response_minutes") or 0),
            )

        submitted = st.form_submit_button("更新する")

    if submitted:
        assignee = "" if assignee_label == "未設定" else assignee_label

        if status == "完了":
            if completed_date_value is None:
                st.error("ステータスを完了にする場合は、完了日を入力してください。")
                return

            completed_date_text = completed_date_value.strftime("%Y-%m-%d")
        else:
            completed_date_text = ""

        updates = {
            "assignee": assignee,
            "status": status,
            "response_summary": response_summary.strip(),
            "record_issue": record_issue.strip(),
            "completed_date": completed_date_text,
            "management_minutes": int(management_minutes),
            "actual_response_minutes": int(actual_response_minutes),
        }

        try:
            current_user = get_current_user()
            user_id = get_user_id(current_user)

            changed_fields = record_inquiry_update_history(
                request_id=selected_request_id,
                before=current,
                updates=updates,
                user_id=user_id,
            )

            if not changed_fields:
                st.info("同じ内容で登録されています。変更はありません。")
                return

            update_inquiry(selected_request_id, updates)
            clear_cache()
            st.success(f"問い合わせを更新しました: {selected_request_id}")

            if status == "完了":
                st.info("完了日を保存しました。")
            else:
                st.info("ステータスが完了以外のため、完了日は保存していません。")

        except Exception as exc:
            st.error("更新に失敗しました。")
            st.exception(exc)

    st.markdown("---")
    st.markdown("### コメント履歴")

    comments = get_comments_for_staff(selected_request_id)

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
        st.info("コメントはまだありません。")

    st.markdown("#### コメントを追加")

    with st.form(f"add_comment_form_{selected_request_id}", clear_on_submit=True):
        comment_body = st.text_area(
            "コメント本文",
            height=100,
            placeholder="対応経緯、依頼者への補足、内部メモなどを記録します。",
        )

        visibility_label = st.radio(
            "表示区分",
            ["内部メモ", "依頼者にも表示"],
            horizontal=True,
        )

        submitted_comment = st.form_submit_button("コメントを追加")

        if submitted_comment:
            visibility = "requester" if visibility_label == "依頼者にも表示" else "internal"

            try:
                current_user = get_current_user()
                user_id = get_user_id(current_user)

                add_inquiry_comment(
                    request_id=selected_request_id,
                    comment_body=comment_body,
                    visibility=visibility,
                    user_id=user_id,
                )

                clear_cache()
                st.success("コメントを追加しました。")
                st.rerun()

            except ValueError as error:
                st.error(str(error))

    st.markdown("---")
    st.markdown("### ステータス履歴")

    status_histories = get_status_history(selected_request_id)

    if not status_histories:
        st.info("ステータス変更履歴はまだありません。")
    else:
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