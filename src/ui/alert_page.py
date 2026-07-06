from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.alerts import (
    add_alert_columns,
    filter_alerts,
    get_alert_display_columns,
    summarize_alerts,
)

def show_alert_page(df: pd.DataFrame) -> None:
    """要対応アラート画面を表示する。"""

    st.subheader("要対応アラート")

    if df.empty:
        st.info("問い合わせデータがありません。")
        return

    alert_df = add_alert_columns(df)
    summary_df = summarize_alerts(alert_df)

    counts = {
        row["alert_type"]: int(row["count"])
        for _, row in summary_df.iterrows()
    }

    total_alerts = int(alert_df["has_alert"].sum())

    st.write(
        "期限超過、期限間近、担当者未設定など、優先的に確認すべき問い合わせを表示します。"
    )

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("アラート対象", total_alerts)
    col2.metric("期限超過", counts.get("期限超過", 0))
    col3.metric("本日期限", counts.get("本日期限", 0))
    col4.metric("期限間近", counts.get("期限間近", 0))
    col5.metric("担当者未設定", counts.get("担当者未設定", 0))
    col6.metric("情報待ち長期化", counts.get("情報待ち長期化", 0))

    if total_alerts == 0:
        st.success("現在、要対応アラートはありません。")
    else:
        st.warning(f"要対応の問い合わせが {total_alerts} 件あります。")

    st.markdown("### アラート種別で絞り込み")

    selected_alert = st.selectbox(
        "表示するアラート種別",
        [
            "すべて",
            "期限超過",
            "本日期限",
            "期限間近",
            "担当者未設定",
            "情報待ち長期化",
        ],
    )

    display_df = filter_alerts(alert_df, selected_alert)

    if display_df.empty:
        st.info("該当する問い合わせはありません。")
        return

    display_columns = get_alert_display_columns(display_df)
    display_df = display_df[display_columns].copy()

    st.markdown("### 要対応問い合わせ一覧")
    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
    )

    with st.expander("アラート判定条件"):
        st.markdown(
            """
            - **期限超過**：未完了かつ希望期限が今日より前
            - **本日期限**：未完了かつ希望期限が今日
            - **期限間近**：未完了かつ希望期限が明日まで
            - **担当者未設定**：担当者が空欄
            - **情報待ち長期化**：ステータスが情報待ちで、受付日から3日以上経過
            """
        )