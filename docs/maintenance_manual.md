# 保守手順書

## 1. 目的

本ドキュメントは、社内問い合わせ管理システムの保守、再実行、DB確認、設定変更、テスト実行、トラブル対応の手順をまとめるものです。
本システムは、Python、SQLite、Streamlit、pandas、Tableau用CSV出力で構成されています。

Ver.1では、問い合わせの登録、一覧表示、ステータス更新、集計、Tableau連携を対象としました。
Ver.2では、以下の機能を追加しています。

- 要対応アラート
- FAQ候補管理
- カテゴリ別入力フォーム
- 依頼者向け確認画面
- Ver.2追加集計
- Tableau出力列の拡張
- Ver.2用DB移行処理
- Ver.2スモークテスト

## 2. 基本的な起動手順

初回セットアップ、または環境を作り直す場合は、以下の順に実行します。

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python -m src.import_csv
python -m src.migrate_db
python -m src.check_db

streamlit run app.py
```

既にDBが存在する場合でも、Ver.2追加カラムを確認するために `python -m src.migrate_db` を実行します。

## 3. DBを初期化する

SQLite DBを作成するには、以下を実行します。

```bash
python -m src.db
```

DBファイルは以下に作成されます。

```text
data/inquiry.db
```

ただし、通常の利用では `src.import_csv` を実行することで、テーブル作成とCSV取込をまとめて行います。

```bash
python -m src.import_csv
```

## 4. CSVを取り込む

ダミーCSVをSQLiteに取り込むには、以下を実行します。

```bash
python -m src.import_csv
```

標準では以下のCSVを読み込みます。

```text
data/inquiry_dx_before_sample.csv
```

別のCSVを指定する場合は以下です。

```bash
python -m src.import_csv path/to/file.csv
```

CSV取込後は、DB確認を実行します。

```bash
python -m src.check_db
```

## 5. Ver.2 DB移行を実行する

既存DBをVer.2に対応させる場合は、以下を実行します。

```bash
python -m src.migrate_db
```

このスクリプトは、既存の `inquiries` テーブルにVer.2追加カラムが存在するか確認し、不足しているカラムだけを追加します。確認対象のカラムは以下です。

| カラム名                 | 内容                       |
| ------------------------ | -------------------------- |
| `faq_candidate`          | FAQ候補かどうか            |
| `faq_title`              | FAQタイトル                |
| `faq_answer`             | FAQ回答案                  |
| `additional_info`        | カテゴリ別追加情報         |
| `requester_visible`      | 依頼者向け画面に表示するか |
| `last_status_changed_at` | 最終ステータス変更日時     |

この処理は、既に存在するカラムを再追加しないようにしているため、複数回実行しても問題ありません。

## 6. DB移行結果を確認する

DB移行後、以下のコマンドでVer.2追加カラムが存在するか確認します。

```bash
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

期待する結果は以下です。

```text
問い合わせ件数: 150
OK: Ver.2追加カラムはすべて存在します。
```

問い合わせ件数は、取り込んだデータ件数によって変わります。

## 7. DBの中身を確認する

簡易確認は以下です。

```bash
python -m src.check_db
```

SQLiteで直接確認する場合は以下です。

```bash
sqlite3 data/inquiry.db
```

```sql
SELECT COUNT(*) FROM inquiries;
```

```sql
SELECT request_id, requester, category, status FROM inquiries LIMIT 5;
```

```sql
.exit
```

Ver.2追加カラムも含めて確認する場合は以下です。

```sql
SELECT request_id, faq_candidate, additional_info, requester_visible FROM inquiries LIMIT 5;
```

## 8. Tableau用CSVを出力する

ターミナルから出力する場合は以下です。

```bash
python -m src.export_tableau_csv
```

出力先は以下です。

```text
data/tableau_output.csv
```

Ver.2では、Tableau出力に以下のような列も含めています。

| 列名                      | 内容                                 |
| ------------------------- | ------------------------------------ |
| `has_alert`               | 要対応アラート対象か                 |
| `alert_type`              | アラート種別                         |
| `faq_candidate_int`       | FAQ候補かどうか                      |
| `has_additional_info_int` | カテゴリ別追加情報が入力されているか |
| `requester_visible_int`   | 依頼者向け画面に表示するか           |
| `requester_visible_label` | 依頼者向け表示区分                   |

CSV出力後、列を確認する場合は以下です。

```bash
python - << 'EOF'
import pandas as pd
from pathlib import Path

path = Path("data/tableau_output.csv")
df = pd.read_csv(path)

required_columns = [
    "has_alert",
    "alert_type",
    "faq_candidate_int",
    "has_additional_info_int",
    "requester_visible_int",
    "requester_visible_label",
]

missing = [col for col in required_columns if col not in df.columns]

print("行数:", len(df))
print("列数:", len(df.columns))

if missing:
    print("不足列:", missing)
else:
    print("OK: Ver.2列はすべて存在します。")
EOF
```

## 9. スモークテストを実行する

主要処理が壊れていないか確認するには以下を実行します。

```bash
python -m src.smoke_test
```

確認対象は以下です。

- DBからデータを取得できるか
- 必須列が存在するか
- `request_id` が重複していないか
- 派生列を作成できるか
- 集計処理が動くか
- Tableau用DataFrameを作成できるか

Ver.2追加機能のスモークテストは以下です。

```bash
python -m src.smoke_test_ver2
```

Ver.2スモークテストでは、以下を確認します。

| 確認対象       | 内容                                        |
| -------------- | ------------------------------------------- |
| DB取得結果     | Ver.2追加カラムが存在するか                 |
| アラート       | アラート列を作成できるか                    |
| FAQ候補        | FAQ候補列・抽出処理が動くか                 |
| カテゴリ別項目 | 追加項目定義と整形処理が動くか              |
| 依頼者向け表示 | 表示制御・検索処理が動くか                  |
| Ver.2集計      | Ver.2集計関数が動くか                       |
| Tableau出力    | Ver.2列がTableau出力用DataFrameに含まれるか |

## 10. Ver.2の動作確認手順

Ver.2全体を確認する場合は、以下を順に実行します。

```bash
python -m py_compile app.py src/*.py
python -m src.migrate_db
python -m src.check_db
python -m src.smoke_test
python -m src.smoke_test_ver2
python -m src.export_tableau_csv
streamlit run app.py
```

Streamlit画面では、以下を確認します。

| 画面                   | 確認内容                                 |
| ---------------------- | ---------------------------------------- |
| 問い合わせ一覧         | 一覧表示・絞り込みができる               |
| 新規登録               | 問い合わせを登録できる                   |
| ステータス更新         | 担当者、ステータス、対応内容を更新できる |
| 要対応アラート         | アラート件数・一覧・絞り込みが表示される |
| FAQ候補管理            | FAQ候補の登録・更新・解除ができる        |
| カテゴリ別入力フォーム | カテゴリごとの追加項目を入力できる       |
| 依頼者向け確認         | 問い合わせID・依頼者名で検索できる       |
| 集計・CSV出力          | Ver.1集計とVer.2追加集計が表示される     |
| Tableau出力            | er.2列を含むCSVを出力できる              |

## 11. マスタデータを変更する

以下のCSVを変更すると、画面上の選択肢を変更できます。

| ファイル                   | 内容               |
| -------------------------- | ------------------ |
| `config/departments.csv`   | 部署               |
| `config/categories.csv`    | 問い合わせカテゴリ |
| `config/assignees.csv`     | 管理部担当者       |
| `config/status_master.csv` | ステータス         |
| `config/channels.csv`      | 受付経路           |
| `config/priorities.csv`    | 優先度             |

例として、担当者を追加する場合は以下を編集します。

```text
config/assignees.csv
```

形式は以下です。

```text
assignee
藤原 直子
松尾 佳奈
原田 健太
石井 美咲
```

マスタ変更後は、Streamlitアプリを再起動して画面表示を確認します。

```bash
streamlit run app.py
```

## 12. カテゴリ別入力項目を変更する

Ver.2のカテゴリ別入力フォームは、以下のファイルで定義しています。

```text
src/category_fields.py
```

カテゴリごとの追加項目を変更する場合は、`CATEGORY_FIELDS` を修正します。変更後は以下を実行します。

```bash
python -m py_compile src/category_fields.py
python -m src.smoke_test_ver2
streamlit run app.py
```

画面上では、「新規登録」タブでカテゴリを選び、追加項目が意図通り表示されるか確認します。

## 13. DBスキーマを変更する場合

DBのカラムを変更する場合は、以下の修正が必要です。

| ファイル                           | 修正内容                                       |
| ---------------------------------- | ---------------------------------------------- |
| `schema.sql`                       | テーブル定義を変更                             |
| `src/migrate_db.py`                | 既存DB向けの移行処理を追加                     |
| `src/db.py`                        | `COLUMNS`、`INTEGER_COLUMNS`、正規化処理を確認 |
| `src/import_csv.py`                | CSV取込時の不足カラム補完処理を確認            |
| `src/aggregation.py`               | 派生列作成処理を確認                           |
| `src/summary.py`                   | 集計処理を確認                                 |
| `src/tableau_export.py`            | Tableau出力列を確認                            |
| `app.py`                           | 表示・入力・更新画面を確認                     |
| `docs/data_definition.md`          | データ定義書を更新                             |
| `docs/maintenance_manual.md`       | 保守手順書を更新                               |
| `docs/ver2/ver2_test_checklist.md` | テストチェックリストを更新                     |

DBスキーマを変更した後は、以下を実行します。

```bash
python -m src.migrate_db
python -m src.check_db
python -m src.smoke_test
python -m src.smoke_test_ver2
python -m src.export_tableau_csv
```

## 14. DBをバックアップする

テストや修正前には、DBをバックアップします。

```bash
mkdir -p backups
cp data/inquiry.db backups/inquiry_backup.db
```

復元する場合は以下です。

```bash
cp backups/inquiry_backup.db data/inquiry.db
```

WBSや大きな修正の前には、バックアップファイル名に日付や作業名を含めると分かりやすくなります。

```bash
cp data/inquiry.db backups/inquiry_backup_before_wbs8.db
```

## 15. Git管理上の注意

以下はGit管理しません。

- `data/inquiry.db`
- `data/tableau_output.csv`
- `__pycache__`
- `.venv`

これらは再生成可能なためです。

Gitに保存する主な対象は以下です。

- Pythonコード
- `schema.sql`
- `requirements.txt`
- `config/` 配下のCSV
- `docs/`
- `notes/`
- `README.md`
- `screenshots/`
- Tableauワークブック

作業後は、以下で差分を確認します。

```bash
git status
git diff
```

コミット例は以下です。

```bash
git add .
git commit -m "Update maintenance manual"
git push
```

## 16. よくあるトラブル

### データが表示されない

CSVがDBに取り込まれていない可能性があります。DBファイルが存在するかも確認します。

```bash
python -m src.import_csv
python -m src.check_db
```

### Ver.2追加カラムがない

既存DBにVer.2追加カラムが入っていない可能性があります。

```bash
python -m src.migrate_db
python -m src.check_db
```

直接確認する場合は以下です。

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

### Streamlitが起動しない

仮想環境が有効でない可能性があります。

```bash
source .venv/bin/activate
streamlit run app.py
```

依存ライブラリが不足している場合は、以下を実行します。

```bash
pip install -r requirements.txt
```

### Tableau用CSVがない

以下を実行します。

```bash
python -m src.export_tableau_csv
```

出力先を確認します。

```bash
ls data
```

### 画面に更新結果が反映されない

Streamlitのキャッシュが残っている可能性があります。

- ブラウザを再読み込みする
- アプリを再起動する
- 更新処理後に `clear_cache()` が呼ばれているか確認する

### Ver.2スモークテストが失敗する

まず、不足列やエラーメッセージを確認します。

```bash
python -m src.smoke_test_ver2
```

よくある原因は以下です。

| 原因                             | 対応                                                    |
| -------------------------------- | ------------------------------------------------------- |
| Ver.2追加カラムがない            | `python -m src.migrate_db` を実行する                   |
| Tableau出力列が不足している      | `src/tableau_export.py` の `TABLEAU_COLUMNS` を確認する |
| 依頼者向け表示関数が見つからない | `src/requester_view.py` の有無とimportを確認する        |
| カテゴリ別項目の定義がない       | `src/category_fields.py` を確認する                     |

## 18. 保守時の基本方針

保守時は、以下の順で確認します。

1. 変更前にDBをバックアップする
2. 変更対象のファイルを確認する
3. 必要に応じてデータ定義書を更新する
4. 構文確認を実行する
5. DB確認を実行する
6. スモークテストを実行する
7. Streamlit画面で手動確認する
8. Tableau用CSVを出力する
9. ドキュメントを更新する
10. Gitにコミットする

## Streamlit非推奨警告への対応

Streamlitのバージョンによっては、`use_container_width` に関する非推奨警告が表示される場合がある。その場合は、以下のように置き換える。

| 旧                          | 新                |
| --------------------------- | ----------------- |
| `use_container_width=True`  | `width="stretch"` |
| `use_container_width=False` | `width="content"` |
