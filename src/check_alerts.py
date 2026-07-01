from src.alerts import add_alert_columns, filter_alerts, summarize_alerts
from src.db import fetch_all_inquiries


def main() -> None:
    df = fetch_all_inquiries()
    alert_df = add_alert_columns(df)

    print("=== アラート集計 ===")
    print(summarize_alerts(alert_df))

    print()
    print("=== 要対応問い合わせ ===")
    display_columns = [
        "request_id",
        "request_date",
        "requester",
        "category",
        "due_date",
        "assignee",
        "status",
        "alert_type",
    ]

    display_columns = [col for col in display_columns if col in alert_df.columns]
    print(filter_alerts(alert_df)[display_columns].head(20))


if __name__ == "__main__":
    main()