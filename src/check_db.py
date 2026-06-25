from __future__ import annotations

from collections import Counter

from src.db import fetch_all_inquiries


def main() -> None:
    rows = fetch_all_inquiries()

    print(f"問い合わせ件数: {len(rows)}件")

    if not rows:
        print("データがありません。")
        return

    print("\n先頭5件:")
    for row in rows[:5]:
        print(
            row["request_id"],
            row["request_date"],
            row["requester"],
            row["department"],
            row["category"],
            row["status"],
        )

    print("\nカテゴリ別件数:")
    category_counts = Counter(row["category"] for row in rows)
    for category, count in category_counts.items():
        print(f"{category}: {count}件")

    print("\nステータス別件数:")
    status_counts = Counter(row["status"] for row in rows)
    for status, count in status_counts.items():
        print(f"{status}: {count}件")


if __name__ == "__main__":
    main()