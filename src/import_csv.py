from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db import BASE_DIR, COLUMNS, init_db, upsert_inquiries


DEFAULT_CSV_PATH = BASE_DIR / "data" / "inquiry_dx_before_sample.csv"


def load_csv(csv_path: Path) -> list[dict]:
    """CSVを読み込み、DB登録用のrecordsに変換する。"""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # CSVに存在しないDBカラムを補う
    for col in COLUMNS:
        if col not in df.columns:
            if col in {"created_at", "updated_at"}:
                df[col] = now
            elif col in {"management_minutes", "actual_response_minutes"}:
                df[col] = 0
            else:
                df[col] = ""

    # DB定義にない余分な列は落とす
    df = df[COLUMNS]

    # 欠損を空文字にする
    df = df.fillna("")

    return df.to_dict(orient="records")


def main() -> None:
    parser = argparse.ArgumentParser(description="問い合わせCSVをSQLiteに取り込む")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=str(DEFAULT_CSV_PATH),
        help="取り込むCSVファイルのパス",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)

    init_db()
    records = load_csv(csv_path)
    count = upsert_inquiries(records)

    print(f"CSVを取り込みました: {csv_path}")
    print(f"登録・更新件数: {count}件")


if __name__ == "__main__":
    main()