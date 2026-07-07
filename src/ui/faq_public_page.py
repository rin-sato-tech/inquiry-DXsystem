from __future__ import annotations

import streamlit as st

from src.services.faq_service import (
    get_faq_detail,
    get_faq_detail_with_view_count,
    get_public_faq_categories,
    mark_faq_helpful,
    search_public_faqs,
)


FAQ_VIEWED_IDS_KEY = "faq_viewed_ids"
FAQ_HELPFUL_IDS_KEY = "faq_helpful_ids"
FAQ_PUBLIC_MESSAGE_KEY = "faq_public_message"


def get_session_id_set(key: str) -> set[str]:
    """session_stateからFAQ ID管理用のsetを取得する。"""
    if key not in st.session_state:
        st.session_state[key] = set()

    return st.session_state[key]


def set_faq_public_message(message_type: str, text: str) -> None:
    """FAQ検索画面用の一時メッセージを保存する。"""
    st.session_state[FAQ_PUBLIC_MESSAGE_KEY] = {
        "type": message_type,
        "text": text,
    }


def show_faq_public_message() -> None:
    """FAQ検索画面用の一時メッセージを表示する。"""
    message = st.session_state.pop(FAQ_PUBLIC_MESSAGE_KEY, None)

    if message is None:
        return

    if message["type"] == "success":
        st.success(message["text"])
    elif message["type"] == "info":
        st.info(message["text"])
    elif message["type"] == "error":
        st.error(message["text"])
    else:
        st.write(message["text"])


def show_faq_public_page() -> None:
    """公開FAQ検索画面を表示する。"""
    st.subheader("FAQ検索")

    st.write(
        "問い合わせ前に、よくある質問を検索できます。"
        "FAQで解決しない場合は、新規問い合わせを登録してください。"
    )

    categories = ["すべて"] + get_public_faq_categories()

    col1, col2 = st.columns([2, 1])

    with col1:
        keyword = st.text_input(
            "キーワード",
            placeholder="例：パスワード、経費精算、PC不具合",
        )

    with col2:
        selected_category = st.selectbox("カテゴリ", categories)

    category_filter = "" if selected_category == "すべて" else selected_category

    faqs = search_public_faqs(
        keyword=keyword,
        category=category_filter,
    )

    st.markdown("### 検索結果")
    st.caption(f"{len(faqs)}件のFAQが見つかりました。")

    if not faqs:
        st.info("該当する公開FAQはありません。")
        st.markdown("FAQで解決しない場合は、メニューから「新規登録」を選択してください。")
        return

    faq_options = {
        f'{faq["title"]}（{faq["category"]} / 閲覧 {faq["view_count"]}）': faq["faq_id"]
        for faq in faqs
    }

    selected_label = st.selectbox(
        "FAQを選択",
        list(faq_options.keys()),
    )

    selected_faq_id = faq_options[selected_label]

    viewed_faq_ids = get_session_id_set(FAQ_VIEWED_IDS_KEY)

    if st.button("FAQ詳細を表示", type="primary"):
        should_count_view = selected_faq_id not in viewed_faq_ids

        faq = get_faq_detail_with_view_count(
            selected_faq_id,
            count_view=should_count_view,
        )

        if should_count_view:
            viewed_faq_ids.add(selected_faq_id)
            st.session_state[FAQ_VIEWED_IDS_KEY] = viewed_faq_ids

        st.session_state["selected_public_faq"] = faq

    faq = st.session_state.get("selected_public_faq")

    if faq is None:
        return

    if faq["faq_id"] != selected_faq_id:
        return

    st.markdown("---")
    st.markdown("### FAQ詳細")
    st.markdown(f'#### {faq["title"]}')
    st.write(f'カテゴリ: {faq["category"]}')
    st.write(f'最終更新: {faq["updated_at"]}')
    st.write(f'閲覧数: {faq["view_count"]} / 役立ち件数: {faq["helpful_count"]}')

    st.markdown("#### 回答")
    st.write(faq["answer"])

    col_helpful, col_inquiry = st.columns(2)

    with col_helpful:
        helpful_faq_ids = get_session_id_set(FAQ_HELPFUL_IDS_KEY)
        already_marked_helpful = faq["faq_id"] in helpful_faq_ids

        if already_marked_helpful:
            st.info("このFAQへのフィードバックは記録済みです。")

        if st.button(
            "このFAQは役に立った",
            disabled=already_marked_helpful,
        ):
            mark_faq_helpful(faq["faq_id"])

            helpful_faq_ids.add(faq["faq_id"])
            st.session_state[FAQ_HELPFUL_IDS_KEY] = helpful_faq_ids

            updated_faq = get_faq_detail(faq["faq_id"])
            st.session_state["selected_public_faq"] = updated_faq

            set_faq_public_message(
                "success",
                "フィードバックを記録しました。",
            )

            st.rerun()

        show_faq_public_message()

    with col_inquiry:
        st.info("解決しない場合は、メニューから「新規登録」を選択してください。")