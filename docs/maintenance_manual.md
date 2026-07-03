# 保守手順書

## 1. 目的

この文書は、社内問い合わせ管理システムの保守・再実行・設定変更方法をまとめたものです。

## 2. DBを初期化する

SQLite DBを作成するには以下を実行します。

```bash
python -m src.db
```

DBファイルは以下に作成されます。

```text
data/inquiry.db
```

## 3. CSVを取り込む

ダミーCSVをSQLiteに取り込むには以下を実行します。

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

## 4. DBの中身を確認する

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
SELECT request_id, requester, category, status FROM inquiries LIMIT 5;
.exit
```

## 5. Tableau用CSVを出力する

ターミナルから出力する場合は以下です。

```bash
python -m src.export_tableau_csv
```

出力先は以下です。

```text
data/tableau_output.csv
```

## 6. スモークテストを実行する

主要処理が壊れていないか確認するには以下を実行します。

```bash
python -m src.smoke_test
```

確認対象は以下です。

- DBからデータを取得できるか
- 必須列が存在するか
- request_id が重複していないか
- 派生列を作成できるか
- 集計処理が動くか
- Tableau用DataFrameを作成できるか

## 7. マスタデータを変更する

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

## 8. DBスキーマを変更する場合

DBのカラムを変更する場合は、以下の修正が必要です。

| ファイル                  | 修正内容                   |
| ------------------------- | -------------------------- |
| `schema.sql`              | テーブル定義を変更         |
| `src/db.py`               | COLUMNSを変更              |
| `src/import_csv.py`       | CSV取込時の補完処理を確認  |
| `src/aggregation.py`      | 派生列作成処理を確認       |
| `src/tableau_export.py`   | Tableau出力列を確認        |
| `app.py`                  | 表示・入力・更新画面を確認 |
| `docs/data_definition.md` | データ定義書を更新         |

## 9. DBをバックアップする

テストや修正前には、DBをバックアップします。

```bash
mkdir -p backups
cp data/inquiry.db backups/inquiry_backup.db
```

復元する場合は以下です。

```bash
cp backups/inquiry_backup.db data/inquiry.db
```

## 10. Git管理上の注意

以下はGit管理しません。

- data/inquiry.db
- data/tableau_output.csv
- pycache
- .venv

これらは再生成可能なためです。

Gitに保存する主な対象は以下です。

- Pythonコード
- schema.sql
- requirements.txt
- config CSV
- docs
- README
- screenshots
- Tableauワークブック

## 11. よくあるトラブル

### データが表示されない

CSVがDBに取り込まれていない可能性があります。

```bash
python -m src.import_csv
python -m src.check_db
```

### Streamlitが起動しない

仮想環境が有効でない可能性があります。

```bash
source .venv/bin/activate
streamlit run app.py
```

### Tableau用CSVがない

以下を実行します。

```bash
python -m src.export_tableau_csv
```

### 画面に更新結果が反映されない

Streamlitのキャッシュが残っている可能性があります。

- ブラウザを再読み込みする
- アプリを再起動する
- `st.cache_data.clear()` が呼ばれているか確認する

## Ver.2 DB移行手順

既存DBをVer.2に対応させる場合は、以下を実行する。

```bash
python -m src.migrate_db
```

このスクリプトは、既存の `inquiries` テーブルにVer.2追加カラムが存在するか確認し、不足しているカラムだけを追加する。

確認対象のカラムは以下である。

- `faq_candidate`
- `faq_title`
- `faq_answer`
- `additional_info`
- `requester_visible`
- `last_status_changed_at`

複数回実行しても、既に存在するカラムは再追加しない。

## Ver.2動作確認手順

以下を順に実行する。

```bash
python -m py_compile app.py src/*.py
python -m src.migrate_db
python -m src.check_db
python -m src.smoke_test
python -m src.smoke_test_ver2
python -m src.export_tableau_csv
streamlit run app.py
```

## Streamlit非推奨警告への対応

Streamlitのバージョンによっては、`use_container_width` に関する非推奨警告が表示される場合がある。

その場合は、以下のように置き換える。

| 旧                          | 新                |
| --------------------------- | ----------------- |
| `use_container_width=True`  | `width="stretch"` |
| `use_container_width=False` | `width="content"` |
