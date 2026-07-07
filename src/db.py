from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "inquiry.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


COLUMNS = [
    "request_id",
    "request_date",
    "request_time",
    "requester",
    "department",
    "channel",
    "category",
    "subcategory",
    "detail",
    "missing_info",
    "priority",
    "due_date",
    "assignee",
    "status",
    "response_summary",
    "record_issue",
    "completed_date",

    # Ver.2用カラム
    "faq_candidate",
    "faq_title",
    "faq_answer",
    "additional_info",
    "requester_visible",
    "last_status_changed_at",

    "management_minutes",
    "actual_response_minutes",
    "created_at",
    "updated_at",
]


REQUIRED_COLUMNS = [
    "request_id",
    "request_date",
    "requester",
    "department",
    "channel",
    "category",
    "detail",
    "priority",
    "due_date",
    "status",
]


INTEGER_COLUMNS = {
    "management_minutes",
    "actual_response_minutes",

    # Ver.2用カラム
    "faq_candidate",
    "requester_visible",
}


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """SQLite接続を返す。取得結果をdict風に扱えるようrow_factoryを設定する。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """schema.sqlを使ってDBとテーブルを作成する。"""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"schema.sql が見つかりません: {SCHEMA_PATH}")

    with get_connection(db_path) as conn:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()


def _is_missing(value: Any) -> bool:
    """None, NaN, 空文字を欠損として扱う。"""
    if value is None:
        return True
    if isinstance(value, float) and value != value:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _to_int_or_zero(value: Any) -> int:
    """欠損値は0に変換し、数値に変換できない場合も0を返す。"""
    if _is_missing(value):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _to_int_or_default(value, default: int = 0) -> int:
    """整数に変換する。欠損や変換不能な値はdefaultを返す。"""
    if _is_missing(value):
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """DB登録前に、欠損値・数値・日時を整える。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    normalized: dict[str, Any] = {}

    for col in COLUMNS:
        if col == "requester_visible":
            # デフォルト値を1にする
            value = record.get(col, 1)
        else:
            value = record.get(col, "")

        if col in INTEGER_COLUMNS:
            normalized[col] = _to_int_or_zero(value)
        elif col in {"created_at", "updated_at"}:
            normalized[col] = value if not _is_missing(value) else now
        else:
            normalized[col] = "" if _is_missing(value) else str(value).strip()

    for col in REQUIRED_COLUMNS:
        if _is_missing(normalized.get(col)):
            raise ValueError(f"必須項目が空です: {col}, record={record}")

    return normalized


def upsert_inquiry(record: dict[str, Any], conn: sqlite3.Connection | None = None) -> None:
    """1件の問い合わせを登録または更新する。"""
    normalized = normalize_record(record)

    placeholders = ", ".join(["?"] * len(COLUMNS))
    columns_sql = ", ".join(COLUMNS)

    update_columns = [col for col in COLUMNS if col != "request_id"]
    update_sql = ", ".join([f"{col} = excluded.{col}" for col in update_columns])

    sql = f"""
        INSERT INTO inquiries ({columns_sql})
        VALUES ({placeholders})
        ON CONFLICT(request_id) DO UPDATE SET
        {update_sql}
    """

    values = [normalized[col] for col in COLUMNS]

    if conn is None:
        with get_connection() as local_conn:
            local_conn.execute(sql, values)
            local_conn.commit()
    else:
        conn.execute(sql, values)


def upsert_inquiries(records: Iterable[dict[str, Any]]) -> int:
    """複数の問い合わせをまとめて登録または更新する。"""
    count = 0
    with get_connection() as conn:
        for record in records:
            upsert_inquiry(record, conn=conn)
            count += 1
        conn.commit()
    return count


def fetch_all_inquiries() -> list[dict[str, Any]]:
    """問い合わせを全件取得する。"""
    sql = """
        SELECT *
        FROM inquiries
        ORDER BY request_date DESC, request_time DESC, request_id DESC
    """
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(row) for row in rows]


def fetch_inquiry_by_id(request_id: str) -> dict[str, Any] | None:
    """request_idを指定して1件取得する。"""
    sql = "SELECT * FROM inquiries WHERE request_id = ?"
    with get_connection() as conn:
        row = conn.execute(sql, (request_id,)).fetchone()
    return dict(row) if row else None


def update_inquiry(request_id: str, updates: dict[str, Any]) -> None:
    """指定した問い合わせの一部項目を更新する。"""
    if not updates:
        return

    allowed_columns = set(COLUMNS) - {"request_id", "created_at"}

    invalid_columns = set(updates) - allowed_columns
    if invalid_columns:
        raise ValueError(f"更新できないカラムが含まれています: {invalid_columns}")

    updates = dict(updates)
    updates["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    set_clause = ", ".join([f"{col} = ?" for col in updates.keys()])
    values = list(updates.values()) + [request_id]

    sql = f"""
        UPDATE inquiries
        SET {set_clause}
        WHERE request_id = ?
    """

    with get_connection() as conn:
        conn.execute(sql, values)
        conn.commit()


def generate_request_id(target_date: str) -> str:
    """
    REQ-YYYYMMDD-001形式のIDを発行する。
    target_dateはYYYY-MM-DD形式。
    """
    date_part = target_date.replace("-", "")
    prefix = f"REQ-{date_part}-"

    sql = """
        SELECT request_id
        FROM inquiries
        WHERE request_id LIKE ?
        ORDER BY request_id DESC
        LIMIT 1
    """

    with get_connection() as conn:
        row = conn.execute(sql, (f"{prefix}%",)).fetchone()

    if row is None:
        next_number = 1
    else:
        last_id = row["request_id"]
        last_number = int(last_id.split("-")[-1])
        next_number = last_number + 1

    return f"{prefix}{next_number:03d}"


ALLOWED_ID_TARGETS = {
    ("faq_items", "faq_id"),
    ("inquiry_comments", "comment_id"),
    ("status_history", "history_id"),
    ("operation_logs", "log_id"),
    ("notification_logs", "notification_id"),
}


def generate_sequential_id(
    table_name: str,
    id_column: str,
    prefix: str,
    digits: int = 4,
) -> str:
    """指定テーブルのIDを、PREFIX-0001形式で発行する。"""
    if (table_name, id_column) not in ALLOWED_ID_TARGETS:
        raise ValueError(f"ID生成対象外です: {table_name}.{id_column}")

    sql = f"""
    SELECT {id_column}
    FROM {table_name}
    WHERE {id_column} LIKE ?
    ORDER BY {id_column} DESC
    LIMIT 1
    """

    with get_connection() as conn:
        row = conn.execute(sql, (f"{prefix}-%",)).fetchone()

    if row is None:
        next_number = 1
    else:
        last_id = row[id_column]
        last_number = int(str(last_id).split("-")[-1])
        next_number = last_number + 1

    return f"{prefix}-{next_number:0{digits}d}"


INITIAL_USERS = [
    {
        "user_id": "U001",
        "user_name": "山田 太郎",
        "department": "営業部",
        "email": "yamada@example.com",
        "role": "requester",
    },
    {
        "user_id": "U002",
        "user_name": "佐藤 花子",
        "department": "管理部",
        "email": "sato@example.com",
        "role": "staff",
    },
    {
        "user_id": "U003",
        "user_name": "鈴木 一郎",
        "department": "管理部",
        "email": "suzuki@example.com",
        "role": "admin",
    },
    {
        "user_id": "U004",
        "user_name": "高橋 美咲",
        "department": "経営企画部",
        "email": "takahashi@example.com",
        "role": "viewer",
    },
]


def seed_initial_users() -> int:
    """Ver.3用の初期ユーザーを登録する。既存ユーザーは上書きしない。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sql = """
    INSERT OR IGNORE INTO users (
        user_id,
        user_name,
        department,
        email,
        role,
        is_active,
        created_at,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
    """

    with get_connection() as conn:
        count = 0
        for user in INITIAL_USERS:
            cursor = conn.execute(
                sql,
                (
                    user["user_id"],
                    user["user_name"],
                    user["department"],
                    user["email"],
                    user["role"],
                    now,
                    now,
                ),
            )
            count += cursor.rowcount
        conn.commit()

    return count


def fetch_active_users() -> list[dict[str, Any]]:
    """有効なユーザーを取得する。"""
    sql = """
    SELECT *
    FROM users
    WHERE is_active = 1
    ORDER BY user_id
    """

    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()

    return [dict(row) for row in rows]


def fetch_user_by_id(user_id: str) -> dict[str, Any] | None:
    """user_idを指定してユーザーを1件取得する。"""
    sql = """
    SELECT *
    FROM users
    WHERE user_id = ?
    """

    with get_connection() as conn:
        row = conn.execute(sql, (user_id,)).fetchone()

    return dict(row) if row else None


def migrate_faq_candidates_to_faq_items(created_by: str = "U003") -> int:
    """
    inquiries のFAQ候補から faq_items を作成する。

    既に同じ source_request_id のFAQがある場合は作成しない。
    初期状態では非公開にする。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    select_sql = """
    SELECT
        request_id,
        category,
        faq_title,
        faq_answer
    FROM inquiries
    WHERE faq_candidate = 1
      AND TRIM(COALESCE(faq_title, '')) != ''
      AND TRIM(COALESCE(faq_answer, '')) != ''
    """

    exists_sql = """
    SELECT faq_id
    FROM faq_items
    WHERE source_request_id = ?
    """

    last_id_sql = """
    SELECT faq_id
    FROM faq_items
    WHERE faq_id LIKE 'FAQ-%'
    ORDER BY faq_id DESC
    LIMIT 1
    """

    insert_sql = """
    INSERT INTO faq_items (
        faq_id,
        source_request_id,
        category,
        title,
        answer,
        is_public,
        view_count,
        helpful_count,
        created_by,
        updated_by,
        created_at,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?, ?)
    """

    with get_connection() as conn:
        rows = conn.execute(select_sql).fetchall()

        last_id_row = conn.execute(last_id_sql).fetchone()
        if last_id_row is None:
            next_number = 1
        else:
            last_id = str(last_id_row["faq_id"])
            next_number = int(last_id.split("-")[-1]) + 1

        count = 0

        for row in rows:
            exists = conn.execute(exists_sql, (row["request_id"],)).fetchone()
            if exists:
                continue

            faq_id = f"FAQ-{next_number:04d}"
            next_number += 1

            conn.execute(
                insert_sql,
                (
                    faq_id,
                    row["request_id"],
                    row["category"],
                    row["faq_title"],
                    row["faq_answer"],
                    created_by,
                    created_by,
                    now,
                    now,
                ),
            )
            count += 1

        conn.commit()

    return count


def fetch_table_count(table_name: str) -> int:
    """指定テーブルの件数を取得する。"""
    allowed_tables = {
        "inquiries",
        "users",
        "faq_items",
        "inquiry_comments",
        "status_history",
        "operation_logs",
        "notification_logs",
    }

    if table_name not in allowed_tables:
        raise ValueError(f"確認対象外のテーブルです: {table_name}")

    sql = f"SELECT COUNT(*) AS count FROM {table_name}"

    with get_connection() as conn:
        row = conn.execute(sql).fetchone()

    return int(row["count"])


def generate_comment_id() -> str:
    """コメントIDを発行する。"""
    return generate_sequential_id(
        table_name="inquiry_comments",
        id_column="comment_id",
        prefix="COM",
    )


def generate_status_history_id() -> str:
    """ステータス履歴IDを発行する。"""
    return generate_sequential_id(
        table_name="status_history",
        id_column="history_id",
        prefix="STH",
    )


def generate_operation_log_id() -> str:
    """操作ログIDを発行する。"""
    return generate_sequential_id(
        table_name="operation_logs",
        id_column="log_id",
        prefix="LOG",
    )


def generate_notification_id() -> str:
    """通知ログIDを発行する。"""
    return generate_sequential_id(
        table_name="notification_logs",
        id_column="notification_id",
        prefix="NTF",
    )


def insert_inquiry_comment(
    request_id: str,
    comment_body: str,
    visibility: str = "internal",
    created_by: str = "",
) -> str:
    """問い合わせコメントを追加する。"""
    if visibility not in {"internal", "requester"}:
        raise ValueError(f"不正なvisibilityです: {visibility}")

    comment_id = generate_comment_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sql = """
    INSERT INTO inquiry_comments (
        comment_id,
        request_id,
        comment_body,
        visibility,
        created_by,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """

    with get_connection() as conn:
        conn.execute(
            sql,
            (
                comment_id,
                request_id,
                comment_body,
                visibility,
                created_by,
                now,
            ),
        )
        conn.commit()

    return comment_id


def fetch_comments_by_request_id(request_id: str) -> list[dict[str, Any]]:
    """問い合わせIDに紐づくコメントを取得する。"""
    sql = """
    SELECT *
    FROM inquiry_comments
    WHERE request_id = ?
    ORDER BY created_at ASC, comment_id ASC
    """

    with get_connection() as conn:
        rows = conn.execute(sql, (request_id,)).fetchall()

    return [dict(row) for row in rows]


def insert_status_history(
    request_id: str,
    old_status: str,
    new_status: str,
    changed_by: str = "",
) -> str:
    """ステータス変更履歴を追加する。"""
    history_id = generate_status_history_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sql = """
    INSERT INTO status_history (
        history_id,
        request_id,
        old_status,
        new_status,
        changed_by,
        changed_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """

    with get_connection() as conn:
        conn.execute(
            sql,
            (
                history_id,
                request_id,
                old_status,
                new_status,
                changed_by,
                now,
            ),
        )
        conn.commit()

    return history_id


def fetch_status_history_by_request_id(request_id: str) -> list[dict[str, Any]]:
    """問い合わせIDに紐づくステータス履歴を取得する。"""
    sql = """
    SELECT *
    FROM status_history
    WHERE request_id = ?
    ORDER BY changed_at ASC, history_id ASC
    """

    with get_connection() as conn:
        rows = conn.execute(sql, (request_id,)).fetchall()

    return [dict(row) for row in rows]


def insert_operation_log(
    action: str,
    target_table: str,
    target_id: str,
    user_id: str = "",
    detail: str = "",
) -> str:
    """操作ログを追加する。"""
    log_id = generate_operation_log_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sql = """
    INSERT INTO operation_logs (
        log_id,
        user_id,
        action,
        target_table,
        target_id,
        detail,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    with get_connection() as conn:
        conn.execute(
            sql,
            (
                log_id,
                user_id,
                action,
                target_table,
                target_id,
                detail,
                now,
            ),
        )
        conn.commit()

    return log_id


def fetch_operation_logs(limit: int = 100) -> list[dict[str, Any]]:
    """操作ログを新しい順に取得する。"""
    sql = """
    SELECT *
    FROM operation_logs
    ORDER BY created_at DESC, log_id DESC
    LIMIT ?
    """

    with get_connection() as conn:
        rows = conn.execute(sql, (limit,)).fetchall()

    return [dict(row) for row in rows]


def insert_notification_log(
    request_id: str,
    notification_type: str,
    message: str,
    recipient_user_id: str = "",
    status: str = "created",
) -> str:
    """通知ログを追加する。"""
    allowed_types = {
        "before_due",
        "overdue",
        "unassigned",
        "waiting_too_long",
        "status_changed",
        "completed",
    }
    allowed_statuses = {"created", "reviewed", "skipped", "sent"}

    if notification_type not in allowed_types:
        raise ValueError(f"不正なnotification_typeです: {notification_type}")

    if status not in allowed_statuses:
        raise ValueError(f"不正なstatusです: {status}")

    notification_id = generate_notification_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sql = """
    INSERT INTO notification_logs (
        notification_id,
        request_id,
        notification_type,
        recipient_user_id,
        message,
        status,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    with get_connection() as conn:
        conn.execute(
            sql,
            (
                notification_id,
                request_id,
                notification_type,
                recipient_user_id,
                message,
                status,
                now,
            ),
        )
        conn.commit()

    return notification_id


def fetch_notification_logs(limit: int = 100) -> list[dict[str, Any]]:
    """通知ログを新しい順に取得する。"""
    sql = """
    SELECT *
    FROM notification_logs
    ORDER BY created_at DESC, notification_id DESC
    LIMIT ?
    """

    with get_connection() as conn:
        rows = conn.execute(sql, (limit,)).fetchall()

    return [dict(row) for row in rows]


def update_notification_status(
    notification_id: str,
    status: str,
) -> None:
    """通知ログの状態を更新する。"""
    allowed_statuses = {"created", "reviewed", "skipped", "sent"}

    if status not in allowed_statuses:
        raise ValueError(f"不正なstatusです: {status}")

    sql = """
    UPDATE notification_logs
    SET status = ?
    WHERE notification_id = ?
    """

    with get_connection() as conn:
        conn.execute(sql, (status, notification_id))
        conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"DBを初期化しました: {DB_PATH}")