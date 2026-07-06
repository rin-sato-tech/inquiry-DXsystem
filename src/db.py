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


if __name__ == "__main__":
    init_db()
    print(f"DBを初期化しました: {DB_PATH}")