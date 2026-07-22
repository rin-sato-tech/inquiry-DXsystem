from __future__ import annotations

from datetime import date, timedelta

from pathlib import Path
import tempfile

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
from src.services.history_service import (
    add_inquiry_comment,
    get_comments_for_requester,
    get_comments_for_staff,
    get_operation_logs,
    get_status_history,
    record_inquiry_created,
    record_status_history_if_changed,
)
from src.services.notification_service import (
    extract_before_due_targets,
    extract_notification_targets,
    extract_overdue_targets,
    extract_unassigned_targets,
    extract_waiting_too_long_targets,
    generate_notification_message,
    save_notification_target,
)
from src.services.report_service import (
    get_ver3_export_dataframes,
    summarize_comments_by_visibility,
    summarize_faq_by_category,
    summarize_notification_logs_by_status,
    summarize_notification_logs_by_type,
    summarize_operation_logs_by_action,
    summarize_status_history_by_new_status,
    summarize_ver3_metrics,
)
from src.tableau_export import export_ver3_tableau_csvs


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


def check_history_functions() -> None:
    """WBS6の履歴系サービス関数を確認する。"""
    inquiries = fetch_all_inquiries()

    if not inquiries:
        print("問い合わせデータがないため、履歴系テストをスキップします。")
        return

    request_id = inquiries[0]["request_id"]

    internal_comment_id = add_inquiry_comment(
        request_id=request_id,
        comment_body="WBS6スモークテスト用内部コメント",
        visibility="internal",
        user_id="U002",
    )

    requester_comment_id = add_inquiry_comment(
        request_id=request_id,
        comment_body="WBS6スモークテスト用依頼者向けコメント",
        visibility="requester",
        user_id="U002",
    )

    staff_comments = get_comments_for_staff(request_id)
    requester_comments = get_comments_for_requester(request_id)

    assert any(
        comment["comment_id"] == internal_comment_id
        for comment in staff_comments
    )
    assert any(
        comment["comment_id"] == requester_comment_id
        for comment in staff_comments
    )
    assert not any(
        comment["comment_id"] == internal_comment_id
        for comment in requester_comments
    )
    assert any(
        comment["comment_id"] == requester_comment_id
        for comment in requester_comments
    )

    history_id = record_status_history_if_changed(
        request_id=request_id,
        old_status="未対応",
        new_status="対応中",
        user_id="U002",
    )

    assert history_id is not None

    status_histories = get_status_history(request_id)
    assert any(
        history["history_id"] == history_id
        for history in status_histories
    )

    record_inquiry_created(
        request_id=request_id,
        user_id="U001",
    )

    operation_logs = get_operation_logs(limit=100)
    assert any(
        log["action"] == "create_inquiry"
        and log["target_id"] == request_id
        for log in operation_logs
    )

    print("WBS6履歴系サービス関数の確認が完了しました。")


def check_notification_functions() -> None:
    """WBS7の通知対象抽出・通知文生成を確認する。"""
    today = date.today()

    df = pd.DataFrame(
        [
            {
                "request_id": "REQ-NOTIFY-001",
                "requester": "山田 太郎",
                "department": "営業部",
                "category": "PC・システム",
                "status": "対応中",
                "assignee": "藤原 直子",
                "due_date": (today + timedelta(days=2)).isoformat(),
                "priority": "中",
                "last_status_changed_at": today.isoformat(),
                "updated_at": today.isoformat(),
                "request_date": today.isoformat(),
            },
            {
                "request_id": "REQ-NOTIFY-002",
                "requester": "佐藤 花子",
                "department": "管理部",
                "category": "経費・請求",
                "status": "未対応",
                "assignee": "",
                "due_date": (today - timedelta(days=1)).isoformat(),
                "priority": "高",
                "last_status_changed_at": today.isoformat(),
                "updated_at": today.isoformat(),
                "request_date": today.isoformat(),
            },
            {
                "request_id": "REQ-NOTIFY-003",
                "requester": "田中 次郎",
                "department": "業務部",
                "category": "アカウント・権限",
                "status": "情報待ち",
                "assignee": "松尾 佳奈",
                "due_date": (today + timedelta(days=10)).isoformat(),
                "priority": "低",
                "last_status_changed_at": (today - timedelta(days=7)).isoformat(),
                "updated_at": (today - timedelta(days=7)).isoformat(),
                "request_date": (today - timedelta(days=8)).isoformat(),
            },
            {
                "request_id": "REQ-NOTIFY-004",
                "requester": "完了 太郎",
                "department": "営業部",
                "category": "その他",
                "status": "完了",
                "assignee": "藤原 直子",
                "due_date": (today - timedelta(days=3)).isoformat(),
                "priority": "低",
                "last_status_changed_at": today.isoformat(),
                "updated_at": today.isoformat(),
                "request_date": today.isoformat(),
            },
        ]
    )

    before_due_targets = extract_before_due_targets(df, days_before=3)
    overdue_targets = extract_overdue_targets(df)
    unassigned_targets = extract_unassigned_targets(df)
    waiting_targets = extract_waiting_too_long_targets(df, waiting_days=5)

    assert any(target["request_id"] == "REQ-NOTIFY-001" for target in before_due_targets)
    assert any(target["request_id"] == "REQ-NOTIFY-002" for target in overdue_targets)
    assert any(target["request_id"] == "REQ-NOTIFY-002" for target in unassigned_targets)
    assert any(target["request_id"] == "REQ-NOTIFY-003" for target in waiting_targets)
    assert not any(target["request_id"] == "REQ-NOTIFY-004" for target in overdue_targets)

    all_targets = extract_notification_targets(df)
    assert len(all_targets) >= 4

    message = generate_notification_message(
        notification_type="overdue",
        inquiry=df.iloc[1].to_dict(),
        reason="希望期限を過ぎています。",
    )

    assert "期限超過" in message
    assert "REQ-NOTIFY-002" in message

    notification_id = save_notification_target(
        all_targets[0],
        user_id="U003",
    )

    assert notification_id.startswith("NTF-")

    print("WBS7通知対象抽出・通知文生成の確認が完了しました。")


def check_ver3_report_functions() -> None:
    """WBS8のVer.3集計・CSV出力関数を確認する。"""
    metrics = summarize_ver3_metrics()

    required_keys = {
        "total_faq",
        "public_faq",
        "private_faq",
        "total_view_count",
        "total_helpful_count",
        "helpful_rate",
        "comment_count",
        "requester_comment_count",
        "internal_comment_count",
        "status_history_count",
        "operation_log_count",
        "notification_log_count",
    }

    assert required_keys.issubset(metrics.keys())

    assert summarize_faq_by_category() is not None
    assert summarize_comments_by_visibility() is not None
    assert summarize_status_history_by_new_status() is not None
    assert summarize_operation_logs_by_action() is not None
    assert summarize_notification_logs_by_type() is not None
    assert summarize_notification_logs_by_status() is not None

    export_dataframes = get_ver3_export_dataframes()

    expected_exports = {
        "tableau_faq_items",
        "tableau_inquiry_comments",
        "tableau_status_history",
        "tableau_operation_logs",
        "tableau_notification_logs",
    }

    assert expected_exports.issubset(export_dataframes.keys())

    with tempfile.TemporaryDirectory() as temp_dir:
        output_paths = export_ver3_tableau_csvs(
            export_dataframes,
            output_dir=Path(temp_dir),
        )

        assert len(output_paths) == len(export_dataframes)

        for output_path in output_paths:
            assert output_path.exists()

    print("WBS8 Ver.3集計・Tableau CSV出力関数の確認が完了しました。")


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
    check_history_functions()
    check_notification_functions()
    check_ver3_report_functions()

    print("Ver.3 DBスモークテストが正常に完了しました。")


if __name__ == "__main__":
    main()