from __future__ import annotations

from datetime import date

import pandas as pd


ALERT_LABELS = {
    "alert_overdue": "期限超過",
    "alert_due_today": "本日期限",
    "alert_due_soon": "期限間近",
    "alert_unassigned": "担当者未設定",
    "alert_info_waiting_long": "情報待ち長期化",
}


def _today_timestamp(today: date | str | None = None) -> pd.Timestamp:
    """比較用の今日の日付をTimestampで返す。"""
    if today is None:
        return pd.Timestamp(date.today()).normalize()

    return pd.Timestamp(today).normalize()


def _text_series(df: pd.DataFrame, column: str) -> pd.Series:
    """指定列を文字列Seriesとして取得する。存在しない場合は空文字Seriesを返す。"""
    if column not in df.columns:
        return pd.Series([""] * len(df), index=df.index)

    return df[column].fillna("").astype(str).str.strip()


def _date_series(df: pd.DataFrame, column: str) -> pd.Series:
    """指定列を日付Seriesとして取得する。変換できない値はNaTにする。"""
    if column not in df.columns:
        return pd.Series([pd.NaT] * len(df), index=df.index)

    return pd.to_datetime(df[column], errors="coerce").dt.normalize()


def _build_alert_type(row: pd.Series) -> str:
    """1行分のアラート種別を文字列にまとめる。"""
    labels: list[str] = []

    for column, label in ALERT_LABELS.items():
        if bool(row.get(column, False)):
            labels.append(label)

    return "、".join(labels)


def add_alert_columns(
    df: pd.DataFrame | list[dict],
    today: date | str | None = None,
    info_waiting_days: int = 3,
) -> pd.DataFrame:
    """
    問い合わせデータにアラート判定列を追加する。

    追加する主な列:
    - alert_overdue
    - alert_due_today
    - alert_due_soon
    - alert_unassigned
    - alert_info_waiting_long
    - has_alert
    - alert_type
    - days_until_due
    - days_overdue
    """

    result = pd.DataFrame(df).copy()

    alert_columns = list(ALERT_LABELS.keys())

    if result.empty:
        for col in alert_columns:
            result[col] = False

        result["has_alert"] = False
        result["alert_type"] = ""
        result["days_until_due"] = pd.NA
        result["days_overdue"] = pd.NA
        return result

    today_ts = _today_timestamp(today)

    status = _text_series(result, "status")
    assignee = _text_series(result, "assignee")

    request_date = _date_series(result, "request_date")
    due_date = _date_series(result, "due_date")

    is_open = status != "完了"
    has_due_date = due_date.notna()
    has_request_date = request_date.notna()

    result["days_until_due"] = (due_date - today_ts).dt.days
    result["days_overdue"] = (today_ts - due_date).dt.days

    result["alert_overdue"] = is_open & has_due_date & (due_date < today_ts)
    result["alert_due_today"] = is_open & has_due_date & (due_date == today_ts)
    result["alert_due_soon"] = (
        is_open
        & has_due_date
        & (due_date > today_ts)
        & (due_date <= today_ts + pd.Timedelta(days=1))
    )
    result["alert_unassigned"] = assignee.eq("")
    result["alert_info_waiting_long"] = (
        status.eq("情報待ち")
        & has_request_date
        & ((today_ts - request_date).dt.days >= info_waiting_days)
    )

    result["has_alert"] = result[alert_columns].any(axis=1)
    result["alert_type"] = result.apply(_build_alert_type, axis=1)

    result.loc[~result["alert_overdue"], "days_overdue"] = 0

    return result


def summarize_alerts(df: pd.DataFrame) -> pd.DataFrame:
    """アラート種別ごとの件数を集計する。"""
    rows = []

    for column, label in ALERT_LABELS.items():
        count = int(df[column].sum()) if column in df.columns else 0
        rows.append(
            {
                "alert_type": label,
                "count": count,
            }
        )

    return pd.DataFrame(rows)


def filter_alerts(df: pd.DataFrame, alert_type: str = "すべて") -> pd.DataFrame:
    """指定したアラート種別の問い合わせだけを抽出する。"""
    if "has_alert" not in df.columns:
        df = add_alert_columns(df)

    if alert_type == "すべて":
        return df[df["has_alert"]].copy()

    reverse_map = {label: column for column, label in ALERT_LABELS.items()}

    column = reverse_map.get(alert_type)

    if column is None or column not in df.columns:
        return df.iloc[0:0].copy()

    return df[df[column]].copy()


def get_alert_display_columns(df: pd.DataFrame) -> list[str]:
    """アラート一覧で表示する列を返す。存在する列だけ返す。"""
    columns = [
        "request_id",
        "request_date",
        "requester",
        "department",
        "category",
        "priority",
        "due_date",
        "days_until_due",
        "days_overdue",
        "assignee",
        "status",
        "alert_type",
    ]

    return [col for col in columns if col in df.columns]