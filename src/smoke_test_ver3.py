from __future__ import annotations

import pandas as pd

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
    fetch_faq_items,
    increment_faq_helpful_count,
    increment_faq_view_count,
)
from src.services.auth_service import get_available_page_keys
from src.services.requester_service import (
    filter_inquiries_for_requester,
    get_requester_summary,
)

def check_role_pages() -> None:
    assert "requester_home" in get_available_page_keys("requester")
    assert "alert" not in get_available_page_keys("requester")

    assert "alert" in get_available_page_keys("staff")
    assert "report" not in get_available_page_keys("staff")

    assert "report" in get_available_page_keys("admin")
    assert "report" in get_available_page_keys("viewer")
    assert "inquiry_update" not in get_available_page_keys("viewer")

    print("ロール別ページ設定の確認が完了しました。")


def check_faq_public_functions() -> None:
    """FAQ公開関連の基本DB関数を確認する。"""
    faq_items = fetch_faq_items(is_public=None)

    if not faq_items:
        print("FAQ項目がないため、FAQ公開機能の詳細確認はスキップします。")
        return

    faq = faq_items[0]
    faq_id = faq["faq_id"]

    before_view_count = int(faq["view_count"])
    before_helpful_count = int(faq["helpful_count"])

    increment_faq_view_count(faq_id)
    increment_faq_helpful_count(faq_id)

    updated = fetch_faq_items(is_public=None)
    updated_faq = next(item for item in updated if item["faq_id"] == faq_id)

    assert int(updated_faq["view_count"]) == before_view_count + 1
    assert int(updated_faq["helpful_count"]) == before_helpful_count + 1

    print("FAQ公開関連DB関数の確認が完了しました。")


def check_requester_filter_functions() -> None:
    """依頼者本人の問い合わせ抽出ロジックを確認する。"""
    test_user = {
        "user_id": "U001",
        "user_name": "山田 太郎",
        "department": "営業部",
        "role": "requester",
    }

    df = pd.DataFrame(
        [
            {
                "request_id": "REQ-TEST-001",
                "requester": "山田 太郎",
                "department": "営業部",
                "status": "対応中",
                "requester_visible": 1,
                "is_overdue": False,
            },
            {
                "request_id": "REQ-TEST-002",
                "requester": "山田 太郎",
                "department": "営業部",
                "status": "完了",
                "requester_visible": 1,
                "is_overdue": False,
            },
            {
                "request_id": "REQ-TEST-003",
                "requester": "山田 太郎",
                "department": "営業部",
                "status": "未対応",
                "requester_visible": 0,
                "is_overdue": True,
            },
            {
                "request_id": "REQ-TEST-004",
                "requester": "佐藤 花子",
                "department": "管理部",
                "status": "対応中",
                "requester_visible": 1,
                "is_overdue": False,
            },
        ]
    )

    result = filter_inquiries_for_requester(
        df=df,
        user=test_user,
        include_hidden=False,
    )

    assert len(result) == 2
    assert set(result["request_id"].tolist()) == {
        "REQ-TEST-001",
        "REQ-TEST-002",
    }

    summary = get_requester_summary(result)

    assert summary["total"] == 2
    assert summary["open"] == 1
    assert summary["completed"] == 1
    assert summary["overdue"] == 0

    print("依頼者向け本人表示ロジックの確認が完了しました。")


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

    check_role_pages()
    check_faq_public_functions()
    check_requester_filter_functions()

    print("Ver.3 DBスモークテストが正常に完了しました。")


if __name__ == "__main__":
    main()