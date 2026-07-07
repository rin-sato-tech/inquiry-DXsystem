from __future__ import annotations

from collections import Counter

from src.db import (
    fetch_all_inquiries,
    fetch_table_count,
    init_db,
    migrate_faq_candidates_to_faq_items,
    seed_initial_users,
)


VER3_TABLES = [
    "users",
    "faq_items",
    "inquiry_comments",
    "status_history",
    "operation_logs",
    "notification_logs",
]

def main() -> None:
    init_db()

    inserted_users = seed_initial_users()
    migrated_faqs = migrate_faq_candidates_to_faq_items()

    print("DB確認を開始します。")
    print(f"初期ユーザー追加件数: {inserted_users}")
    print(f"FAQ候補移行件数: {migrated_faqs}")

    print("\nVer.3追加テーブル件数:")
    for table in VER3_TABLES:
        count = fetch_table_count(table)
        print(f"{table}: {count}件")

    rows = fetch_all_inquiries()

    print(f"\n問い合わせ件数: {len(rows)}件")

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