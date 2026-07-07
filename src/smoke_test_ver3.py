from __future__ import annotations

from src.db import (
    fetch_all_inquiries,
    fetch_comments_by_request_id,
    fetch_notification_logs,
    fetch_operation_logs,
    fetch_status_history_by_request_id,
    fetch_table_count,
    init_db,
    insert_inquiry_comment,
    insert_notification_log,
    insert_operation_log,
    insert_status_history,
    migrate_faq_candidates_to_faq_items,
    seed_initial_users,
)


def main() -> None:
    init_db()

    print("Ver.3 DBスモークテストを開始します。")

    inserted_users = seed_initial_users()
    migrated_faqs = migrate_faq_candidates_to_faq_items()

    print(f"初期ユーザー追加件数: {inserted_users}")
    print(f"FAQ候補移行件数: {migrated_faqs}")

    users_count = fetch_table_count("users")
    assert users_count >= 4, "users に初期ユーザーが登録されていません。"

    inquiries = fetch_all_inquiries()
    assert inquiries, "テスト対象の問い合わせデータがありません。"

    request_id = inquiries[0]["request_id"]

    comment_id = insert_inquiry_comment(
        request_id=request_id,
        comment_body="Ver.3スモークテスト用コメント",
        visibility="internal",
        created_by="U002",
    )
    comments = fetch_comments_by_request_id(request_id)
    assert any(c["comment_id"] == comment_id for c in comments), "コメントが取得できません。"

    history_id = insert_status_history(
        request_id=request_id,
        old_status="未対応",
        new_status="対応中",
        changed_by="U002",
    )
    histories = fetch_status_history_by_request_id(request_id)
    assert any(h["history_id"] == history_id for h in histories), "ステータス履歴が取得できません。"

    log_id = insert_operation_log(
        action="ver3_smoke_test",
        target_table="inquiries",
        target_id=request_id,
        user_id="U002",
        detail="Ver.3 DBスモークテスト",
    )
    logs = fetch_operation_logs()
    assert any(log["log_id"] == log_id for log in logs), "操作ログが取得できません。"

    notification_id = insert_notification_log(
        request_id=request_id,
        notification_type="overdue",
        recipient_user_id="U002",
        message="Ver.3スモークテスト用通知文です。",
    )
    notifications = fetch_notification_logs()
    assert any(
        n["notification_id"] == notification_id for n in notifications
    ), "通知ログが取得できません。"

    for table_name in [
        "users",
        "faq_items",
        "inquiry_comments",
        "status_history",
        "operation_logs",
        "notification_logs",
    ]:
        count = fetch_table_count(table_name)
        print(f"{table_name}: {count}件")

    print("Ver.3 DBスモークテストが正常に完了しました。")


if __name__ == "__main__":
    main()