from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from src.alerts import (
    add_alert_columns,
    filter_alerts,
    get_alert_display_columns,
    summarize_alerts,
)
from src.aggregation import add_derived_columns, format_date_columns_for_display
from src.db import (
    fetch_all_inquiries,
    fetch_inquiry_by_id,
    generate_request_id,
    init_db,
    update_inquiry,
    upsert_inquiry,
)
from src.category_fields import (
    format_additional_info,
    get_category_fields,
)
from src.master_data import (
    get_assignees,
    get_categories,
    get_channels,
    get_departments,
    get_priorities,
    get_statuses,
)
from src.requester_view import (
    filter_requester_inquiries,
    get_requester_display_columns,
    get_requester_status_counts,
)
from src.summary import (
    count_by,
    effort_by,
    overdue_table,
    response_days_by_category,
    summarize_basic_metrics,
    category_additional_info_summary,
    faq_candidate_by_category,
    requester_visible_summary,
    summarize_ver2_metrics,
)
from src.tableau_export import export_tableau_csv, make_tableau_dataframe, to_csv_bytes
from src.faq import (
    add_faq_columns,
    get_completed_inquiries,
    get_faq_candidates,
    get_faq_display_columns,
    summarize_faq_candidates,
    to_faq_csv_bytes,
)

st.set_page_config(
    page_title="社内問い合わせ管理システム",
    layout="wide",
)


@st.cache_data(ttl=10)
def load_inquiries() -> pd.DataFrame:
    """SQLiteから問い合わせデータを読み込み、派生列を追加する。"""
    init_db()
    rows = fetch_all_inquiries()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = add_derived_columns(df)
    return df


def clear_cache() -> None:
    """DB更新後にStreamlitのキャッシュをクリアする。"""
    st.cache_data.clear()


def get_options(df: pd.DataFrame, column: str) -> list[str]:
    """フィルタ用の選択肢を作る。"""
    if df.empty or column not in df.columns:
        return []

    values = (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return sorted([v for v in values.unique().tolist() if v])


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


def apply_filters(
    df: pd.DataFrame,
    departments: list[str],
    categories: list[str],
    assignees: list[str],
    statuses: list[str],
    priorities: list[str],
    show_overdue_only: bool,
) -> pd.DataFrame:
    """画面で選択された条件に従ってDataFrameを絞り込む。"""
    filtered = df.copy()

    if departments:
        filtered = filtered[filtered["department"].isin(departments)]

    if categories:
        filtered = filtered[filtered["category"].isin(categories)]

    if assignees:
        filtered = filtered[filtered["assignee"].isin(assignees)]

    if statuses:
        filtered = filtered[filtered["status"].isin(statuses)]

    if priorities:
        filtered = filtered[filtered["priority"].isin(priorities)]

    if show_overdue_only:
        filtered = filtered[filtered["overdue_flag"]]

    return filtered


def show_kpi_cards(df: pd.DataFrame) -> None:
    """主要KPIを表示する。"""
    total_count = len(df)

    if df.empty:
        open_count = 0
        overdue_count = 0
        completed_count = 0
        management_hours = 0.0
    else:
        open_count = int(df["is_open"].sum())
        overdue_count = int(df["overdue_flag"].sum())
        completed_count = int(df["is_completed"].sum())
        management_hours = float(df["management_hours"].sum())

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("問い合わせ件数", f"{total_count}件")
    col2.metric("未完了件数", f"{open_count}件")
    col3.metric("完了件数", f"{completed_count}件")
    col4.metric("期限超過件数", f"{overdue_count}件")
    col5.metric("管理作業時間", f"{management_hours:.1f}時間")


def show_inquiry_table(df: pd.DataFrame) -> None:
    """問い合わせ一覧を表示する。"""
    if df.empty:
        st.warning("表示できる問い合わせデータがありません。")
        return

    display_columns = [
        "request_id",
        "request_date",
        "request_time",
        "requester",
        "department",
        "channel",
        "category",
        "subcategory",
        "priority",
        "due_date",
        "assignee",
        "status",
        "overdue_flag",
        "detail",
        "additional_info",
        "response_summary",
    ]

    existing_columns = [col for col in display_columns if col in df.columns]
    display_df = df[existing_columns].copy()
    display_df = format_date_columns_for_display(display_df)

    if "overdue_flag" in display_df.columns:
        display_df["overdue_flag"] = display_df["overdue_flag"].map(
            {True: "期限超過", False: ""}
        )

    column_config = {
        "request_id": "問い合わせID",
        "request_date": "受付日",
        "request_time": "受付時刻",
        "requester": "依頼者",
        "department": "部署",
        "channel": "受付経路",
        "category": "カテゴリ",
        "subcategory": "小分類",
        "priority": "優先度",
        "due_date": "希望期限",
        "assignee": "担当者",
        "status": "ステータス",
        "overdue_flag": "期限超過",
        "detail": "問い合わせ内容",
        "additional_info": "カテゴリ別追加情報",
        "response_summary": "対応内容",
    }

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config=column_config,
    )


def show_alerts(df: pd.DataFrame) -> None:
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


def show_create_form() -> None:
    """新規問い合わせ登録フォームを表示する。"""
    st.header("新規登録")
    st.caption("DX化後の問い合わせ受付フォームを想定した登録画面です。")

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
            requester = st.text_input("依頼者名 *")
            department = st.selectbox("部署 *", departments)
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


def show_update_form(df: pd.DataFrame) -> None:
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


def show_faq_management(df: pd.DataFrame) -> None:
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


def show_tableau_export_section(df: pd.DataFrame) -> None:
    """Tableau連携用CSVの出力UIを表示する。"""
    st.markdown("### Tableau用CSV出力")
    st.caption(
        "Tableauで可視化しやすいように、期限超過フラグ、完了フラグ、対応日数、作業時間などの派生列を追加して出力します。"
    )

    tableau_df = make_tableau_dataframe(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("出力行数", f"{len(tableau_df)}行")
    col2.metric("出力列数", f"{len(tableau_df.columns)}列")
    col3.metric("出力ファイル", "tableau_output.csv")

    with st.expander("出力列を確認する"):
        columns_df = pd.DataFrame(
            {
                "列名": tableau_df.columns.tolist(),
            }
        )
        st.dataframe(columns_df, width="stretch", hide_index=True)

    with st.expander("出力データのプレビュー"):
        st.dataframe(
            tableau_df.head(20),
            width="stretch",
            hide_index=True,
        )

    col_download, col_save = st.columns(2)

    with col_download:
        st.download_button(
            label="Tableau用CSVをダウンロード",
            data=to_csv_bytes(df),
            file_name="tableau_output.csv",
            mime="text/csv",
        )

    with col_save:
        if st.button("data/tableau_output.csv に保存"):
            try:
                output_path = export_tableau_csv(df)
                st.success(f"CSVを保存しました: {output_path}")
            except Exception as exc:
                st.error("CSVの保存に失敗しました。")
                st.exception(exc)


def show_requester_view(df: pd.DataFrame) -> None:
    """依頼者向け確認画面を表示する。"""

    st.header("依頼者向け確認")

    st.caption(
        "依頼者が、自分の問い合わせ状況を確認するための画面です。"
    )

    st.info(
        "この画面はデモ用です。本格運用ではログイン認証・権限管理を行い、"
        "本人の問い合わせのみ表示する必要があります。"
    )

    if df.empty:
        st.warning("確認できる問い合わせデータがありません。")
        return

    status_summary = get_requester_status_counts(df)

    if not status_summary.empty:
        with st.expander("依頼者向け表示対象のステータス別件数"):
            st.dataframe(
                status_summary,
                width="stretch",
                hide_index=True,
            )
    st.markdown("### 問い合わせを検索")

    with st.form("requester_search_form"):
        search_mode = st.radio(
            "検索方法",
            ["問い合わせIDで検索", "依頼者名で検索"],
            horizontal=True,
        )

        request_id_query = ""
        requester_query = ""

        if search_mode == "問い合わせIDで検索":
            request_id_query = st.text_input(
                "問い合わせID",
                placeholder="例：REQ-20260701-001",
            )
        else:
            requester_query = st.text_input(
                "依頼者名",
                placeholder="例：吉田 拓也",
            )

        search_submitted = st.form_submit_button("問い合わせ状況を確認")

    if not search_submitted:
        st.info("問い合わせIDまたは依頼者名を入力して検索してください。")
        return

    if not request_id_query.strip() and not requester_query.strip():
        st.error("検索条件を入力してください。")
        return
        if not request_id_query.strip() and not requester_query.strip():
            st.error("検索条件を入力してください。")
            return

    result_df = filter_requester_inquiries(
        df,
        request_id=request_id_query,
        requester=requester_query,
        include_hidden=False,
    )

    if result_df.empty:
        st.warning("該当する問い合わせは見つかりませんでした。")
        return

    display_columns = get_requester_display_columns(result_df)
    display_df = result_df[display_columns].copy()

    display_df = format_date_columns_for_display(display_df)

    column_config = {
        "request_id": "問い合わせID",
        "request_date": "受付日",
        "requester": "依頼者",
        "department": "部署",
        "category": "カテゴリ",
        "subcategory": "小分類",
        "detail": "問い合わせ内容",
        "additional_info": "追加情報",
        "status": "ステータス",
        "assignee": "担当者",
        "due_date": "希望期限",
        "completed_date": "完了日",
        "response_summary": "管理部からの回答・対応内容",
    }

    st.markdown("### 問い合わせ状況")

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config=column_config,
    )

    st.markdown("### 詳細確認")

    for _, row in display_df.iterrows():
        request_id = row.get("request_id", "")

        with st.expander(f"問い合わせID：{request_id}", expanded=len(display_df) == 1):
            st.write(f"**受付日**：{row.get('request_date', '')}")
            st.write(f"**依頼者**：{row.get('requester', '')}（{row.get('department', '')}）")
            st.write(f"**カテゴリ**：{row.get('category', '')} / {row.get('subcategory', '')}")
            st.write(f"**ステータス**：{row.get('status', '')}")
            st.write(f"**担当者**：{row.get('assignee', '') or '未設定'}")
            st.write(f"**希望期限**：{row.get('due_date', '')}")
            st.write(f"**完了日**：{row.get('completed_date', '') or '未完了'}")
            st.write("**問い合わせ内容**：")
            st.write(row.get("detail", ""))

            if row.get("additional_info"):
                st.write("**追加情報**：")
                st.text(row.get("additional_info", ""))

            if row.get("response_summary"):
                st.write("**管理部からの回答・対応内容**：")
                st.write(row.get("response_summary", ""))
            else:
                st.info("管理部からの回答・対応内容はまだ登録されていません。")

    with st.expander("この画面で表示しない情報"):
        st.markdown(
            """
            依頼者向け画面では、以下のような管理部内部向け情報は表示しません。

            - 管理作業時間
            - 実対応時間
            - 記録・管理上の問題
            - FAQ候補フラグ
            - FAQ回答案の下書き
            """
        )


def show_simple_summary(df: pd.DataFrame) -> None:
    """問い合わせ状況の集計・判定結果を表示する。"""
    if df.empty:
        st.warning("集計できるデータがありません。")
        return

    st.subheader("集計・判定結果")
    st.caption("問い合わせ管理の状況を、件数・期限超過・担当者負荷・作業時間の観点から確認します。")

    metrics = summarize_basic_metrics(df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("問い合わせ件数", f"{metrics['total_count']}件")
    col2.metric("未完了件数", f"{metrics['open_count']}件")
    col3.metric("期限超過件数", f"{metrics['overdue_count']}件")
    col4.metric("平均対応日数", f"{metrics['avg_response_days']:.1f}日")

    col5, col6, col7 = st.columns(3)
    col5.metric("管理作業時間", f"{metrics['total_management_hours']:.1f}時間")
    col6.metric("実対応時間", f"{metrics['total_actual_response_hours']:.1f}時間")
    col7.metric(
        "問い合わせ関連時間",
        f"{metrics['total_management_hours'] + metrics['total_actual_response_hours']:.1f}時間",
    )

    st.divider()

    st.markdown("### 期限超過案件")
    overdue_df = overdue_table(df)

    if overdue_df.empty:
        st.success("期限超過案件はありません。")
    else:
        display_overdue_df = format_date_columns_for_display(overdue_df)
        st.dataframe(
            display_overdue_df,
            width="stretch",
            hide_index=True,
        )

    st.divider()

    st.markdown("### 件数集計")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### カテゴリ別件数")
        st.dataframe(
            count_by(df, "category", "カテゴリ"),
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### 担当者別件数")
        st.dataframe(
            count_by(df, "assignee", "担当者"),
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### 部署別件数")
        st.dataframe(
            count_by(df, "department", "部署"),
            width="stretch",
            hide_index=True,
        )

    with col_b:
        st.markdown("#### ステータス別件数")
        st.dataframe(
            count_by(df, "status", "ステータス"),
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### 受付経路別件数")
        st.dataframe(
            count_by(df, "channel", "受付経路"),
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### 優先度別件数")
        st.dataframe(
            count_by(df, "priority", "優先度"),
            width="stretch",
            hide_index=True,
        )

    st.divider()

    st.markdown("### 作業時間集計")

    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("#### 担当者別 作業時間")
        st.dataframe(
            effort_by(df, "assignee", "担当者"),
            width="stretch",
            hide_index=True,
        )

    with col_d:
        st.markdown("#### カテゴリ別 作業時間")
        st.dataframe(
            effort_by(df, "category", "カテゴリ"),
            width="stretch",
            hide_index=True,
        )

    st.divider()

    st.markdown("### 対応日数")

    response_summary = response_days_by_category(df)

    if response_summary.empty:
        st.info("完了日が登録された案件がないため、対応日数はまだ集計できません。")
    else:
        st.dataframe(
            response_summary,
            width="stretch",
            hide_index=True,
        )

    st.divider()

    st.markdown("### Ver.2追加機能の集計")

    ver2_metrics = summarize_ver2_metrics(df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("要対応アラート", ver2_metrics["alert_count"])
    col2.metric("FAQ候補", ver2_metrics["faq_candidate_count"])
    col3.metric("追加情報あり", ver2_metrics["additional_info_count"])
    col4.metric("追加情報入力率", f'{ver2_metrics["additional_info_rate"]}%')

    col5, col6 = st.columns(2)
    col5.metric("依頼者向け表示", ver2_metrics["requester_visible_count"])
    col6.metric("依頼者向け非表示", ver2_metrics["requester_hidden_count"])

    st.markdown("#### アラート種別別件数")
    alert_summary_df = summarize_alerts(add_alert_columns(df))
    st.dataframe(
        alert_summary_df,
        width="stretch",
        hide_index=True,
    )

    st.markdown("#### カテゴリ別FAQ候補件数")
    faq_category_df = faq_candidate_by_category(df)

    if faq_category_df.empty:
        st.info("FAQ候補はまだ登録されていません。")
    else:
        st.dataframe(
            faq_category_df,
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### カテゴリ別追加情報入力率")
    additional_info_summary_df = category_additional_info_summary(df)

    if additional_info_summary_df.empty:
        st.info("追加情報の集計対象がありません。")
    else:
        st.dataframe(
            additional_info_summary_df,
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### 依頼者向け表示制御")
    st.dataframe(
        requester_visible_summary(df),
        width="stretch",
        hide_index=True,
    )

    st.divider()

    show_tableau_export_section(df)


def main() -> None:
    st.title("社内問い合わせ管理システム")
    st.caption("管理部に寄せられる社内問い合わせ・依頼対応を一元管理するためのデモアプリです。")

    df = load_inquiries()

    tab_alert, tab_list, tab_create, tab_update, tab_faq, tab_requester, tab_summary = st.tabs(
        [
            "要対応アラート",
            "問い合わせ一覧",
            "新規登録",
            "ステータス更新",
            "FAQ候補管理",
            "依頼者向け確認",
            "集計・CSV出力",
        ]
    )

    with tab_alert:
        show_alerts(df)

    with tab_list:
        st.header("問い合わせ一覧")

        if df.empty:
            st.warning("問い合わせデータがありません。先にCSVをSQLiteへ取り込んでください。")
            st.code("python -m src.import_csv", language="bash")
        else:
            st.markdown("### 絞り込み条件")

            filter_col1, filter_col2, filter_col3 = st.columns(3)

            with filter_col1:
                selected_departments = st.multiselect(
                    "部署",
                    options=get_options(df, "department"),
                )

                selected_categories = st.multiselect(
                    "カテゴリ",
                    options=get_options(df, "category"),
                )

            with filter_col2:
                selected_assignees = st.multiselect(
                    "担当者",
                    options=get_options(df, "assignee"),
                )

                selected_statuses = st.multiselect(
                    "ステータス",
                    options=get_options(df, "status"),
                )

            with filter_col3:
                selected_priorities = st.multiselect(
                    "優先度",
                    options=get_options(df, "priority"),
                )

                show_overdue_only = st.checkbox("期限超過のみ表示")

            filtered_df = apply_filters(
                df=df,
                departments=selected_departments,
                categories=selected_categories,
                assignees=selected_assignees,
                statuses=selected_statuses,
                priorities=selected_priorities,
                show_overdue_only=show_overdue_only,
            )

            st.markdown("### KPI")
            st.caption("現在の絞り込み条件に基づく件数です。")
            show_kpi_cards(filtered_df)

            st.markdown("### 問い合わせ一覧")
            show_inquiry_table(filtered_df)

    with tab_create:
        show_create_form()

    with tab_update:
        show_update_form(df)

    with tab_faq:
        show_faq_management(df)

    with tab_requester:
        show_requester_view(df)

    with tab_summary:
        st.header("集計・CSV出力")
        show_simple_summary(df)


if __name__ == "__main__":
    main()