from __future__ import annotations

from typing import Any

import streamlit as st

from src.db import fetch_active_users, fetch_user_by_id


PageConfig = dict[str, str]


PAGE_CONFIGS: dict[str, PageConfig] = {
    "requester_home": {
        "label": "依頼者トップ",
        "role_group": "requester",
    },
    "faq_public": {
        "label": "FAQ検索",
        "role_group": "shared",
    },
    "inquiry_create": {
        "label": "新規登録",
        "role_group": "shared",
    },
    "requester_inquiries": {
        "label": "自分の問い合わせ",
        "role_group": "requester",
    },
    "alert": {
        "label": "要対応アラート",
        "role_group": "staff",
    },
    "inquiry_list": {
        "label": "問い合わせ一覧",
        "role_group": "staff",
    },
    "inquiry_update": {
        "label": "ステータス更新",
        "role_group": "staff",
    },
    "faq_admin": {
        "label": "FAQ候補管理",
        "role_group": "staff",
    },
    "report": {
        "label": "集計・CSV出力",
        "role_group": "viewer",
    },
        "history": {
        "label": "履歴確認",
        "role_group": "admin",
    },
        "notification": {
        "label": "通知対象確認",
        "role_group": "staff",
    },
}


ROLE_PAGES: dict[str, list[str]] = {
    "requester": [
        "requester_home",
        "faq_public",
        "inquiry_create",
        "requester_inquiries",
    ],
    "staff": [
        "alert",
        "notification",
        "inquiry_list",
        "inquiry_update",
        "faq_admin",
        "faq_public",
        "inquiry_create",
    ],
    "admin": [
        "alert",
        "notification",
        "inquiry_list",
        "inquiry_update",
        "faq_admin",
        "faq_public",
        "inquiry_create",
        "requester_inquiries",
        "history",
        "report",
    ],
    "viewer": [
        "report",
    ],
}


def initialize_auth_state() -> None:
    """ログイン状態の初期値を設定する。"""
    st.session_state.setdefault("is_logged_in", False)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("current_role", None)


def get_active_users() -> list[dict[str, Any]]:
    """有効ユーザー一覧を取得する。"""
    return fetch_active_users()


def login_user(user_id: str) -> None:
    """指定ユーザーでログインする。"""
    user = fetch_user_by_id(user_id)

    if user is None:
        raise ValueError(f"ユーザーが見つかりません: {user_id}")

    if int(user.get("is_active", 0)) != 1:
        raise ValueError(f"無効なユーザーです: {user_id}")

    st.session_state["is_logged_in"] = True
    st.session_state["current_user"] = user
    st.session_state["current_role"] = user["role"]


def logout_user() -> None:
    """ログアウトする。"""
    st.session_state["is_logged_in"] = False
    st.session_state["current_user"] = None
    st.session_state["current_role"] = None


def get_current_user() -> dict[str, Any] | None:
    """ログイン中ユーザーを取得する。"""
    return st.session_state.get("current_user")


def get_current_role() -> str | None:
    """ログイン中ユーザーのロールを取得する。"""
    return st.session_state.get("current_role")


def is_logged_in() -> bool:
    """ログイン済みかどうかを返す。"""
    return bool(st.session_state.get("is_logged_in"))


def get_available_page_keys(role: str) -> list[str]:
    """ロールに応じて利用可能なページキー一覧を返す。"""
    return ROLE_PAGES.get(role, [])


def get_available_page_labels(role: str) -> list[str]:
    """ロールに応じて利用可能なページ表示名一覧を返す。"""
    return [PAGE_CONFIGS[key]["label"] for key in get_available_page_keys(role)]


def get_page_key_by_label(role: str, label: str) -> str:
    """ページ表示名からページキーを取得する。"""
    for key in get_available_page_keys(role):
        if PAGE_CONFIGS[key]["label"] == label:
            return key

    raise ValueError(f"利用できないページです: {label}")


def has_permission(page_key: str, role: str | None = None) -> bool:
    """指定ページを利用できるか判定する。"""
    target_role = role or get_current_role()

    if target_role is None:
        return False

    return page_key in get_available_page_keys(target_role)