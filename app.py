from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from src.aggregation import add_derived_columns, format_date_columns_for_display
from src.db import (
    fetch_all_inquiries,
    fetch_inquiry_by_id,
    generate_request_id,
    init_db,
    update_inquiry,
    upsert_inquiry,
)
from src.master_data import (
    get_assignees,
    get_categories,
    get_channels,
    get_departments,
    get_priorities,
    get_statuses,
)
from src.summary import (
    count_by,
    effort_by,
    overdue_table,
    response_days_by_category,
    summarize_basic_metrics,
)
from src.tableau_export import export_tableau_csv, make_tableau_dataframe, to_csv_bytes

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
        "response_summary": "対応内容",
    }

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )


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
            category = st.selectbox("カテゴリ *", categories)
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
        st.dataframe(columns_df, use_container_width=True, hide_index=True)

    with st.expander("出力データのプレビュー"):
        st.dataframe(
            tableau_df.head(20),
            use_container_width=True,
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
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    st.markdown("### 件数集計")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### カテゴリ別件数")
        st.dataframe(
            count_by(df, "category", "カテゴリ"),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### 担当者別件数")
        st.dataframe(
            count_by(df, "assignee", "担当者"),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### 部署別件数")
        st.dataframe(
            count_by(df, "department", "部署"),
            use_container_width=True,
            hide_index=True,
        )

    with col_b:
        st.markdown("#### ステータス別件数")
        st.dataframe(
            count_by(df, "status", "ステータス"),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### 受付経路別件数")
        st.dataframe(
            count_by(df, "channel", "受付経路"),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### 優先度別件数")
        st.dataframe(
            count_by(df, "priority", "優先度"),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    st.markdown("### 作業時間集計")

    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("#### 担当者別 作業時間")
        st.dataframe(
            effort_by(df, "assignee", "担当者"),
            use_container_width=True,
            hide_index=True,
        )

    with col_d:
        st.markdown("#### カテゴリ別 作業時間")
        st.dataframe(
            effort_by(df, "category", "カテゴリ"),
            use_container_width=True,
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
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    show_tableau_export_section(df)


def main() -> None:
    st.title("社内問い合わせ管理システム")
    st.caption("管理部に寄せられる社内問い合わせ・依頼対応を一元管理するためのデモアプリです。")

    df = load_inquiries()

    tab_list, tab_create, tab_update, tab_summary = st.tabs(
        [
            "問い合わせ一覧",
            "新規登録",
            "ステータス更新",
            "集計・CSV出力",
        ]
    )

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

    with tab_summary:
        st.header("集計・CSV出力")
        show_simple_summary(df)


if __name__ == "__main__":
    main()