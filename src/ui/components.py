from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.category_fields import (
    format_additional_info,
    get_category_fields,
)


def index_or_zero(options: list[str], value: str | None) -> int:
    """selectboxの初期位置を安全に返す。"""
    if value in options:
        return options.index(value)
    return 0


def parse_date_or_none(value: Any) -> date | None:
    """DB上の日付文字列をdate型に変換する。失敗したらNoneを返す。"""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None

    return parsed.date()


def show_additional_info_block(value: object) -> None:
    """カテゴリ別追加情報を表示する。未登録の場合も明示する。"""

    additional_info = str(value or "").strip()

    st.write("**カテゴリ別追加情報**:")

    if additional_info:
        st.text(additional_info)
    else:
        st.info("カテゴリ別追加情報は登録されていません。")


def render_category_additional_fields(category: str) -> str:
    """カテゴリに応じた追加入力項目を表示し、保存用テキストを返す。"""

    fields = get_category_fields(category)

    st.markdown("### カテゴリ別追加情報")
    st.caption(
        "カテゴリに応じて、初回問い合わせ時に確認しておきたい情報を入力します。"
        "未入力でも登録できますが、入力すると管理部との確認往復を減らしやすくなります。"
    )

    values: dict[str, Any] = {}

    if not fields:
        free_text = st.text_area(
            "追加情報",
            height=90,
            placeholder="このカテゴリで補足しておきたい情報を入力してください。",
        )
        return free_text.strip()

    for field in fields:
        widget_key = f"create_additional_{category}_{field.key}"

        if field.field_type == "text_area":
            values[field.key] = st.text_area(
                field.label,
                height=80,
                key=widget_key,
            )
        elif field.field_type == "select":
            values[field.key] = st.selectbox(
                field.label,
                field.options,
                key=widget_key,
            )
        elif field.field_type == "date":
            selected_date = st.date_input(
                field.label,
                value=None,
                key=widget_key,
            )
            values[field.key] = selected_date.strftime("%Y-%m-%d") if selected_date else ""
        else:
            values[field.key] = st.text_input(
                field.label,
                key=widget_key,
            )

    return format_additional_info(category, values)


def make_update_label(row: pd.Series) -> str:
    """更新対象選択用の表示ラベルを作る。"""
    detail = str(row.get("detail", ""))
    short_detail = detail[:35] + "..." if len(detail) > 35 else detail

    return (
        f'{row.get("request_id", "")} | '
        f'{row.get("status", "")} | '
        f'{row.get("requester", "")} | '
        f'{row.get("category", "")} | '
        f"{short_detail}"
    )