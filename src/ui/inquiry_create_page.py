from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import streamlit as st

from src.db import generate_request_id, upsert_inquiry
from src.master_data import (
    get_assignees,
    get_categories,
    get_channels,
    get_departments,
    get_priorities,
    get_statuses,
)
from src.ui.components import index_or_zero, render_category_additional_fields
from src.ui.cache_utils import clear_cache
from src.services.auth_service import get_current_role, get_current_user


def show_inquiry_create_page() -> None:
    """新規問い合わせ登録フォームを表示する。"""
    st.header("新規登録")
    st.caption("DX化後の問い合わせ受付フォームを想定した登録画面です。")

    current_user = get_current_user()
    current_role = get_current_role()

    default_requester = ""
    default_department = ""

    if current_user is not None:
        default_requester = str(current_user.get("user_name", "")).strip()
        default_department = str(current_user.get("department", "")).strip()

    is_requester = current_role == "requester"

    departments = get_departments()
    categories = get_categories()
    channels = get_channels()
    priorities = get_priorities()
    statuses = get_statuses()
    assignee_options = ["未設定"] + get_assignees()

    st.markdown("### カテゴリ選択")
    category = st.selectbox(
        "カテゴリ *",
        categories,
        key="create_category",
    )

    st.caption(
        "カテゴリを選択すると、下のフォームにカテゴリ別の追加入力項目が表示されます。"
    )

    default_due_date = date.today() + timedelta(days=3)

    with st.form("create_inquiry_form", clear_on_submit=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            requester = st.text_input(
                "依頼者名 *",
                value=default_requester,
                disabled=is_requester,
                help="依頼者ロールでは、ログイン中ユーザー名が自動入力されます。",
            )
            department = st.selectbox(
                "部署 *",
                departments,
                index=index_or_zero(departments, default_department),
                disabled=is_requester,
                help="依頼者ロールでは、ログイン中ユーザーの部署が自動入力されます。",
            )
            channel = st.selectbox(
                "受付経路 *",
                channels,
                index=index_or_zero(channels, "フォーム"),
            )

        with col2:
            st.text_input(
                "カテゴリ *",
                value=category,
                disabled=True,
            )
            subcategory = st.text_input("小分類")
            priority = st.selectbox(
                "優先度 *",
                priorities,
                index=index_or_zero(priorities, "中"),
            )

        with col3:
            due_date = st.date_input("希望期限 *", value=default_due_date)

            if is_requester:
                assignee_label = "未設定"
                status = "未対応"

                st.text_input(
                    "担当者",
                    value="未設定",
                    disabled=True,
                    help="担当者は管理部側で設定します。",
                )

                st.text_input(
                    "ステータス *",
                    value="未対応",
                    disabled=True,
                    help="新規登録時は未対応として登録されます。",
                )
            else:
                assignee_label = st.selectbox("担当者", assignee_options)

                status = st.selectbox(
                    "ステータス *",
                    statuses,
                    index=index_or_zero(statuses, "未対応"),
                )

        detail = st.text_area("問い合わせ内容 *", height=120)
        missing_info = st.text_area("不足情報・確認事項", height=80)

        additional_info = render_category_additional_fields(category)

        submitted = st.form_submit_button("登録する")

    if submitted:
        errors = []

        if not requester.strip():
            errors.append("依頼者名を入力してください。")
        if not department.strip():
            errors.append("部署を選択してください。")
        if not detail.strip():
            errors.append("問い合わせ内容を入力してください。")
        if due_date is None:
            errors.append("希望期限を入力してください。")

        if errors:
            for error in errors:
                st.error(error)
            return

        now = datetime.now()
        request_date = now.strftime("%Y-%m-%d")
        request_time = now.strftime("%H:%M")
        request_id = generate_request_id(request_date)

        assignee = "" if assignee_label == "未設定" else assignee_label

        record = {
            "request_id": request_id,
            "request_date": request_date,
            "request_time": request_time,
            "requester": requester.strip(),
            "department": department,
            "channel": channel,
            "category": category,
            "subcategory": subcategory.strip(),
            "detail": detail.strip(),
            "missing_info": missing_info.strip(),
            "additional_info": additional_info,
            "priority": priority,
            "due_date": due_date.strftime("%Y-%m-%d"),
            "assignee": assignee,
            "status": status,
            "response_summary": "",
            "record_issue": "",
            "completed_date": "",
            "management_minutes": 0,
            "actual_response_minutes": 0,
        }

        try:
            upsert_inquiry(record)
            clear_cache()
            st.success(f"問い合わせを登録しました: {request_id}")
            st.info("一覧画面に戻ると、登録した問い合わせを確認できます。")
        except Exception as exc:
            st.error("登録に失敗しました。")
            st.exception(exc)