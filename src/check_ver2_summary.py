import pandas as pd

from src.db import fetch_all_inquiries
from src.summary import (
    category_additional_info_summary,
    faq_candidate_by_category,
    requester_visible_summary,
    summarize_ver2_metrics,
)
from src.alerts import add_alert_columns, summarize_alerts


def main() -> None:
    records = fetch_all_inquiries()
    df = pd.DataFrame(records)

    print("=== Ver.2 KPI ===")
    print(summarize_ver2_metrics(df))

    print()
    print("=== アラート種別別件数 ===")
    alert_df = add_alert_columns(df)
    print(summarize_alerts(alert_df))

    print()
    print("=== カテゴリ別FAQ候補件数 ===")
    print(faq_candidate_by_category(df))

    print()
    print("=== カテゴリ別追加情報入力率 ===")
    print(category_additional_info_summary(df))

    print()
    print("=== 依頼者向け表示制御 ===")
    print(requester_visible_summary(df))


if __name__ == "__main__":
    main()