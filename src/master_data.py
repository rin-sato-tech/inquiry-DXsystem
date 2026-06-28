from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"


def read_master_csv(file_name: str, column_name: str, fallback: list[str]) -> list[str]:
    """
    config配下のマスタCSVを読み込む。
    ファイルが存在しない場合や読み込みに失敗した場合はfallbackを返す。
    """
    path = CONFIG_DIR / file_name

    if not path.exists():
        return fallback

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return fallback

    if column_name not in df.columns:
        return fallback

    values = (
        df[column_name]
        .dropna()
        .astype(str)
        .str.strip()
    )

    result = [v for v in values.tolist() if v]

    return result if result else fallback


def get_departments() -> list[str]:
    return read_master_csv(
        file_name="departments.csv",
        column_name="department",
        fallback=["営業部", "業務部", "施工管理部", "倉庫・物流部", "管理部", "経営層"],
    )


def get_categories() -> list[str]:
    return read_master_csv(
        file_name="categories.csv",
        column_name="category",
        fallback=[
            "PC・システム",
            "アカウント・権限",
            "経費・請求",
            "勤怠・労務",
            "備品・設備",
            "契約・書類",
            "車両・配送",
            "その他",
        ],
    )


def get_assignees() -> list[str]:
    return read_master_csv(
        file_name="assignees.csv",
        column_name="assignee",
        fallback=["藤原 直子", "松尾 佳奈", "原田 健太", "石井 美咲"],
    )


def get_statuses() -> list[str]:
    return read_master_csv(
        file_name="status_master.csv",
        column_name="status",
        fallback=["未対応", "対応中", "情報待ち", "承認待ち", "完了"],
    )


def get_channels() -> list[str]:
    return read_master_csv(
        file_name="channels.csv",
        column_name="channel",
        fallback=["フォーム", "メール", "電話", "口頭", "チャット", "Excel"],
    )


def get_priorities() -> list[str]:
    return read_master_csv(
        file_name="priorities.csv",
        column_name="priority",
        fallback=["高", "中", "低"],
    )