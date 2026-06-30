# WBS-2: DB・データ構造の拡張

## 1. 今回やったこと

既存の `inquiries` テーブルに以下のカラムを追加した。

| カラム名                 | 型      | 初期値 | 内容                       |
| ------------------------ | ------- | ------ | -------------------------- |
| `faq_candidate`          | INTEGER | 0      | FAQ候補かどうか            |
| `faq_title`              | TEXT    | 空文字 | FAQ化する場合のタイトル    |
| `faq_answer`             | TEXT    | 空文字 | FAQ回答案                  |
| `additional_info`        | TEXT    | 空文字 | カテゴリ別追加情報         |
| `requester_visible`      | INTEGER | 1      | 依頼者向け画面に表示するか |
| `last_status_changed_at` | TEXT    | 空文字 | 最終ステータス変更日時     |

## 2. `schema.sql` と `migrate_db.py` の違い

今回重要だったのは、`schema.sql` と `migrate_db.py` の役割の違いである。

### schema.sql

`schema.sql` は、新しくDBを作るときの設計図である。新規に `inquiry.db` を作成する場合は、`schema.sql` に書かれたテーブル構造が使われる。
そのため、Ver.2で新しくDBを作った場合にも追加カラムが入るように、`schema.sql` の `CREATE TABLE inquiries` にVer.2用カラムを追加した。

### migrate_db.py

一方で、すでに存在している `data/inquiry.db` は、`schema.sql` を更新しただけでは変わらない。既存DBに新しいカラムを追加するには、`ALTER TABLE` を使ってDB構造を変更する必要がある。そのため、既存DBにVer.2用カラムを追加するために `src/migrate_db.py` を作成した。

## 3. `ALTER TABLE` について

SQLiteでは、既存テーブルにカラムを追加する場合、以下のように書く。

```sql
ALTER TABLE inquiries ADD COLUMN faq_candidate INTEGER DEFAULT 0;
```

今回の `migrate_db.py` では、すでに存在するカラムを重複して追加しないように、先に現在のカラム一覧を確認している。

```python
PRAGMA table_info(inquiries);
```

これにより、すでに追加済みのカラムはスキップし、不足しているカラムだけを追加できる。このようにしておくと、`python -m src.migrate_db` を何度実行しても壊れない。

## 4. `COLUMNS` の役割

`src/db.py` には、DB登録対象のカラム一覧として `COLUMNS` が定義されている。
`upsert_inquiry()` や `normalize_record()` は、この `COLUMNS` をもとに、どの項目をDBに保存するかを決めている。そのため、DBにカラムを追加しただけでは不十分で、Python側の `COLUMNS` にもVer.2追加カラムを入れる必要がある。これを追加しないと、DB側にカラムが存在していても、Pythonから値を保存できない。

## 5. `normalize_record()` の役割

`normalize_record()` は、DBに登録する前にデータを整える関数である。

主な役割は以下である。

- 欠損値を空文字や0にそろえる
- 数値カラムを整数に変換する
- `created_at` や `updated_at` が空なら現在日時を入れる
- 必須項目が空ならエラーにする

今回の既存コードでは、`normalize_record()` が `COLUMNS` を1つずつ回して処理する形になっていた。そのため、`COLUMNS` と `INTEGER_COLUMNS` に追加すれば基本的に対応できる。
ただし、`requester_visible` は初期値を1にしたいので、値がない場合に0にならないよう注意が必要だった。

## 6. `requester_visible` の初期値に注意

`faq_candidate` は、初期値0で問題ない。一方、`requester_visible` は、初期値1にしたい。
理由は、基本的には依頼者向け画面に問い合わせ状況を表示する想定だからである。
もしCSVに `requester_visible` 列がなく、空文字として補完された場合、整数変換で0になってしまう可能性がある。そのため、`import_csv.py` の不足カラム補完処理で、`requester_visible` だけは明示的に1を入れるようにした。

```python
elif col == "requester_visible":
    df[col] = 1
```

## 7. import_csv.py の役割

`src/import_csv.py` は、CSVからデータを読み込み、DBに登録する処理を担当している。
既存のCSVにはVer.2追加カラムが存在しない。そのため、CSV取込時に不足カラムを補完しないと、DB登録時にエラーになったり、想定外の値が入ったりする。
今回の修正では、不足カラムに以下の初期値を入れるようにした。

| カラム                   | 初期値 |
| ------------------------ | ------ |
| `faq_candidate`          | 0      |
| `faq_title`              | 空文字 |
| `faq_answer`             | 空文字 |
| `additional_info`        | 空文字 |
| `requester_visible`      | 1      |
| `last_status_changed_at` | 空文字 |

これにより、既存CSVをそのまま使ってもVer.2対応DBに取り込める。

## 8. DB拡張時の確認手順

DB構造を変更したときは、以下の順で確認する。

### 8-1. migration実行

```bash
python -m src.migrate_db
```

初回はカラム追加の表示が出る。2回目以降は、追加が必要なカラムがないという表示になればよい。

### 8-2. カラム一覧確認

```bash
python - << 'EOF'
import sqlite3
from pathlib import Path

db_path = Path("data/inquiry.db")

with sqlite3.connect(db_path) as conn:
    rows = conn.execute("PRAGMA table_info(inquiries);").fetchall()

for row in rows:
    print(row[1])
EOF
```

追加した6カラムが表示されればよい。

### 8-3. CSV取込確認

```bash
python -m src.import_csv
```

エラーが出なければよい。

### 8-4. 初期値確認

```bash
python - << 'EOF'
import sqlite3
from pathlib import Path

db_path = Path("data/inquiry.db")

with sqlite3.connect(db_path) as conn:
    rows = conn.execute("""
        SELECT
            request_id,
            faq_candidate,
            faq_title,
            faq_answer,
            additional_info,
            requester_visible,
            last_status_changed_at
        FROM inquiries
        LIMIT 5;
    """).fetchall()

for row in rows:
    print(row)
EOF
```

期待する状態は以下である。

```text
faq_candidate = 0
faq_title = ''
faq_answer = ''
additional_info = ''
requester_visible = 1
last_status_changed_at = ''
```

### 8-5. 既存機能確認

```bash
python -m src.check_db
python -m src.smoke_test
python -m src.export_tableau_csv
streamlit run app.py
```

DB構造を拡張しても、既存機能が壊れていないことを確認する。

## 9. 今後の実装とのつながり

今回追加したカラムは、今後のWBSで以下のように使う。

| カラム                   | 今後の用途                     |
| ------------------------ | ------------------------------ |
| `faq_candidate`          | FAQ候補管理機能で使用          |
| `faq_title`              | FAQ候補のタイトルとして使用    |
| `faq_answer`             | FAQ回答案として使用            |
| `additional_info`        | カテゴリ別入力フォームで使用   |
| `requester_visible`      | 依頼者向け確認画面で使用       |
| `last_status_changed_at` | 情報待ち長期化などの判定で使用 |

WBS2は、画面上の変化は少ないが、Ver.2機能を実装するための土台になる作業である。
