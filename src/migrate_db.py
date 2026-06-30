from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "inquiry.db"


VER2_COLUMNS = {
    "faq_candidate": "INTEGER DEFAULT 0",
    "faq_title": "TEXT DEFAULT ''",
    "faq_answer": "TEXT DEFAULT ''",
    "additional_info": "TEXT DEFAULT ''",
    "requester_visible": "INTEGER DEFAULT 1",
    "last_status_changed_at": "TEXT DEFAULT ''",
}


def get_existing_columns(conn: sqlite3.Connection) -> set[str]:
    """inquiriesテーブルに存在するカラム名を取得する。"""
    cursor = conn.execute("PRAGMA table_info(inquiries);")
    rows = cursor.fetchall()
    return {row[1] for row in rows}


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """指定したテーブルが存在するか確認する。"""
    cursor = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?;
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None


def migrate() -> None:
    """既存DBにVer.2用カラムを追加する。"""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DBファイルが見つかりません: {DB_PATH}\n"
            "先に python -m src.import_csv または init_db() を実行してください。"
        )

    with sqlite3.connect(DB_PATH) as conn:
        if not table_exists(conn, "inquiries"):
            raise RuntimeError("inquiriesテーブルが存在しません。DB初期化を確認してください。")

        existing_columns = get_existing_columns(conn)
        added_columns: list[str] = []

        for column_name, column_def in VER2_COLUMNS.items():
            if column_name not in existing_columns:
                sql = f"ALTER TABLE inquiries ADD COLUMN {column_name} {column_def};"
                conn.execute(sql)
                added_columns.append(column_name)

        conn.commit()

    if added_columns:
        print("Ver.2用カラムを追加しました。")
        for column in added_columns:
            print(f"- {column}")
    else:
        print("追加が必要なカラムはありません。既にVer.2対応済みです。")


if __name__ == "__main__":
    migrate()