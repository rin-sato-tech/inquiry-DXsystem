# WBS8 学習ログ：テスト・修正

## 1. `PRAGMA table_info` について

`PRAGMA table_info(テーブル名);` は、SQLiteでテーブルのカラム情報を確認するために使う。たとえば、以下のように実行する。

```python id="qolm3d"
rows = conn.execute("PRAGMA table_info(inquiries);").fetchall()
```

取得できる情報には、以下が含まれる。

| 項目            | 内容           |
| --------------- | -------------- |
| `cid`           | カラム番号     |
| `name`          | カラム名       |
| `type`          | データ型       |
| `notnull`       | NOT NULL制約   |
| `default_value` | 初期値         |
| `pk`            | 主キーかどうか |

WBS8では、この情報を使って、Ver.2追加カラムが存在するかを確認した。

## 2. `assert` を使った確認

`smoke_test_ver2.py` では、条件を満たさない場合に `AssertionError` を出す形にした。たとえば、必要な列が存在するかを確認する関数を作った。

```python id="6wcvq6"
def assert_columns_exist(df: pd.DataFrame, columns: list[str], label: str) -> None:
    missing_columns = [col for col in columns if col not in df.columns]

    if missing_columns:
        raise AssertionError(f"{label} に不足列があります: {missing_columns}")
```

この関数により、指定した列がDataFrameに存在しない場合、明確なエラーを出せる。単に処理が途中で落ちるよりも、どの列が不足しているか分かりやすい。

## 3. WBS8で使った主な確認コマンド

WBS8では、以下のようなコマンドを使って確認した。

### 構文確認

```bash id="trg54x"
python -m py_compile app.py src/*.py
```

### DB移行確認

```bash id="ajtw1i"
python -m src.migrate_db
python -m src.migrate_db
```

### DB状態確認

```bash id="psk4r6"
python - << 'EOF'
import sqlite3
from pathlib import Path

db_path = Path("data/inquiry.db")

required_columns = {
    "faq_candidate",
    "faq_title",
    "faq_answer",
    "additional_info",
    "requester_visible",
    "last_status_changed_at",
}

with sqlite3.connect(db_path) as conn:
    rows = conn.execute("PRAGMA table_info(inquiries);").fetchall()
    count = conn.execute("SELECT COUNT(*) FROM inquiries;").fetchone()[0]

existing_columns = {row[1] for row in rows}
missing_columns = required_columns - existing_columns

print("問い合わせ件数:", count)

if missing_columns:
    print("不足カラム:", sorted(missing_columns))
else:
    print("OK: Ver.2追加カラムはすべて存在します。")
EOF
```

### 既存テスト

```bash id="f48hiq"
python -m src.check_db
python -m src.smoke_test
```

### Ver.2スモークテスト

```bash id="ynguk1"
python -m src.smoke_test_ver2
```

### Tableau CSV出力

```bash id="iypt9d"
python -m src.export_tableau_csv
```

### Streamlit確認

```bash id="la9voz"
streamlit run app.py
```

## 4. 今後の実装とのつながり

WBS8でテスト・修正を行ったことで、Ver.2の機能が一通り確認済みの状態になった。今後の作業は、実装追加よりもドキュメント整備とポートフォリオ反映が中心になる。

| 次の作業    | 内容                                             |
| ----------- | ------------------------------------------------ |
| WBS9        | README、操作手順書、データ定義書、発展課題の更新 |
| WBS10       | スクリーンショット更新、GitHub整理、リリース作成 |
| Tableau更新 | Ver.2列を使ったダッシュボード改善                |
| 面接説明文  | Ver.2で改善した点を説明できるようにする          |

WBS8では、Ver.2機能を「作った状態」から「確認済みの状態」に進めた。これにより、次のWBS9では、安心してドキュメント更新に進める。
