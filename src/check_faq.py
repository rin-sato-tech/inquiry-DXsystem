from src.db import fetch_all_inquiries
from src.faq import (
    add_faq_columns,
    get_completed_inquiries,
    get_faq_candidates,
    summarize_faq_candidates,
)


def main() -> None:
    df = add_faq_columns(fetch_all_inquiries())

    print("=== FAQ候補管理 確認 ===")
    print(f"全件: {len(df)}")
    print(f"完了済み: {len(get_completed_inquiries(df))}")
    print(f"FAQ候補: {len(get_faq_candidates(df))}")

    print()
    print("=== カテゴリ別FAQ候補件数 ===")
    print(summarize_faq_candidates(df))

    print()
    print("=== FAQ候補一覧 ===")
    candidates = get_faq_candidates(df)
    display_columns = [
        "request_id",
        "category",
        "detail",
        "response_summary",
        "faq_title",
        "faq_answer",
    ]
    display_columns = [col for col in display_columns if col in candidates.columns]
    print(candidates[display_columns].head(20))


if __name__ == "__main__":
    main()