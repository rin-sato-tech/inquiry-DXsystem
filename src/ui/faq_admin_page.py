from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.db import update_inquiry
from src.faq import (
    add_faq_columns,
    get_completed_inquiries,
    get_faq_candidates,
    get_faq_display_columns,
    summarize_faq_candidates,
    to_faq_csv_bytes,
)
from src.ui.components import show_additional_info_block
from src.ui.cache_utils import clear_cache

clear_cache()


def show_faq_admin_page(df: pd.DataFrame) -> None:
    """FAQ候補管理画面を表示する。"""

    st.subheader("FAQ候補管理")

    # st.rerun() 後もメッセージを表示するため、session_stateから取り出して表示する
    if "faq_message" in st.session_state:
        st.success(st.session_state.pop("faq_message"))

    if df.empty:
        st.info("問い合わせデータがありません。")
        return

    faq_df = add_faq_columns(df)
    completed_df = get_completed_inquiries(faq_df)
    candidates_df = get_faq_candidates(faq_df)
    category_summary = summarize_faq_candidates(faq_df)

    st.write(
        "完了済み問い合わせの中から、よくある問い合わせとしてFAQ化できそうなものを候補登録します。"
    )

    st.info(
        "FAQ候補として保存・更新すると、選択した問い合わせがFAQ候補一覧に表示されます。"
        "すでにFAQ候補になっている問い合わせを保存した場合は、FAQタイトル・回答案を上書き更新します。"
        "FAQ候補から外すと一覧には表示されなくなりますが、入力済みのタイトル・回答案は下書きとして保持されます。"
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("完了済み問い合わせ", len(completed_df))
    col2.metric("FAQ候補", len(candidates_df))
    col3.metric(
        "FAQ候補カテゴリ数",
        category_summary["category"].nunique() if not category_summary.empty else 0,
    )

    st.markdown("### FAQ候補の登録・編集")

    if completed_df.empty:
        st.info("FAQ候補にできる完了済み問い合わせがありません。")
    else:
        completed_df = completed_df.copy()

        def format_inquiry_label(request_id: str) -> str:
            """selectbox表示用のラベルを作る。"""
            row = completed_df[completed_df["request_id"] == request_id].iloc[0]

            category = str(row.get("category", "") or "")
            detail = str(row.get("detail", "") or "")

            return f"{request_id}|{category}|{detail[:40]}"

        request_ids = completed_df["request_id"].astype(str).tolist()

        selected_request_id = st.selectbox(
            "FAQ候補として編集する問い合わせ",
            request_ids,
            format_func=format_inquiry_label,
        )

        selected_row = completed_df[
            completed_df["request_id"].astype(str) == selected_request_id
        ].iloc[0]

        current_candidate = int(selected_row.get("faq_candidate", 0) or 0) == 1
        current_title = str(selected_row.get("faq_title", "") or "")
        current_answer = str(selected_row.get("faq_answer", "") or "")

        with st.expander("元の問い合わせ内容", expanded=True):
            st.write(f"**問い合わせID**：{selected_row.get('request_id', '')}")
            st.write(f"**カテゴリ**：{selected_row.get('category', '')}")
            st.write(f"**サブカテゴリ**：{selected_row.get('subcategory', '')}")
            st.write(f"**問い合わせ内容**：{selected_row.get('detail', '')}")

            show_additional_info_block(selected_row.get("additional_info", ""))

            st.write(f"**対応内容**：{selected_row.get('response_summary', '')}")
            st.write(f"**完了日**：{selected_row.get('completed_date', '')}")

            if current_candidate:
                st.success("この問い合わせは現在FAQ候補です。")
            else:
                st.info("この問い合わせはまだFAQ候補ではありません。")



        with st.form(f"faq_form_{selected_request_id}"):
            faq_title = st.text_input(
                "FAQタイトル",
                value=current_title,
                placeholder="例：販売管理システムにログインできない場合の対応",
            )

            faq_answer = st.text_area(
                "FAQ回答案",
                value=current_answer,
                height=160,
                placeholder="依頼者向けに、原因・確認手順・対応方法を簡潔に整理します。",
            )

            save_label = (
                "FAQ候補として保存・更新"
                if current_candidate
                else "FAQ候補として保存"
            )

            submitted = st.form_submit_button(save_label)

            if submitted:
                if not faq_title.strip():
                    st.error("FAQタイトルを入力してください。")
                    return

                if not faq_answer.strip():
                    st.error("FAQ回答案を入力してください。")
                    return

                updates = {
                    "faq_candidate": 1,
                    "faq_title": faq_title.strip(),
                    "faq_answer": faq_answer.strip(),
                }

                update_inquiry(selected_request_id, updates)
                clear_cache()

                if current_candidate:
                    st.session_state["faq_message"] = "FAQ候補情報を更新しました。"
                else:
                    st.session_state["faq_message"] = "FAQ候補として保存しました。"

                st.rerun()

        if current_candidate:
            st.markdown("#### FAQ候補の解除")

            st.warning(
                "この操作を行うと、FAQ候補一覧には表示されなくなります。"
                "ただし、入力済みのFAQタイトル・FAQ回答案は下書きとして保持されます。"
            )

            if st.button(
                "FAQ候補から外す",
                key=f"remove_faq_candidate_{selected_request_id}",
            ):
                updates = {
                    "faq_candidate": 0,
                }

                update_inquiry(selected_request_id, updates)
                clear_cache()

                st.session_state["faq_message"] = "FAQ候補から外しました。"
                st.rerun()

    st.markdown("### FAQ候補一覧")

    if candidates_df.empty:
        st.info("現在、FAQ候補は登録されていません。")
    else:
        display_columns = get_faq_display_columns(candidates_df)

        st.dataframe(
            candidates_df[display_columns],
            width="stretch",
            hide_index=True,
        )

        st.markdown("### カテゴリ別FAQ候補件数")

        if category_summary.empty:
            st.info("カテゴリ別集計はありません。")
        else:
            st.dataframe(
                category_summary,
                width="stretch",
                hide_index=True,
            )

        csv_bytes = to_faq_csv_bytes(candidates_df)

        st.download_button(
            label="FAQ候補CSVをダウンロード",
            data=csv_bytes,
            file_name="faq_candidates.csv",
            mime="text/csv",
        )

    with st.expander("FAQ候補管理の考え方"):
        st.markdown(
            """
            - FAQ候補にできる対象は、原則として完了済み問い合わせです。
            - `FAQ候補として保存・更新` を押すと、選択した問い合わせがFAQ候補になります。
            - すでにFAQ候補になっている問い合わせを保存した場合、FAQタイトル・回答案は上書き更新されます。
            - `FAQ候補から外す` を押すと、FAQ候補一覧には表示されなくなります。
            - FAQ候補から外しても、FAQタイトル・FAQ回答案は下書きとして保持します。
            - Ver.2ではFAQ公開ページまでは作らず、FAQ候補を蓄積する段階までを対象とします。
            """
        )