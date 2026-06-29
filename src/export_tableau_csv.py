from __future__ import annotations

import pandas as pd

from src.aggregation import add_derived_columns
from src.db import fetch_all_inquiries, init_db
from src.tableau_export import export_tableau_csv


def main() -> None:
    init_db()

    rows = fetch_all_inquiries()

    if not rows:
        print("問い合わせデータがありません。")
        return

    df = pd.DataFrame(rows)
    df = add_derived_columns(df)

    output_path = export_tableau_csv(df)

    print(f"Tableau用CSVを出力しました: {output_path}")
    print(f"出力件数: {len(df)}件")


if __name__ == "__main__":
    main()