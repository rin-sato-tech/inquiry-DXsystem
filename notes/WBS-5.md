# WBS-5: 登録・更新機能の開発

## `master_data.py`

`master_data.py` は、ひと言でいうと `config/` フォルダにあるCSVを読み込んで、Streamlitの選択肢として使うためのファイルです。

たとえば、部署・カテゴリ・担当者・ステータスなどを読み込みます。

```text
config/departments.csv
config/categories.csv
config/assignees.csv
config/status_master.csv
config/channels.csv
config/priorities.csv
```

これらを `app.py` から直接読むのではなく、`master_data.py` に読み込み処理をまとめています。

### 1. 全体の流れ

```text
config/*.csv
  ↓
master_data.py
  ↓
app.py
  ↓
Streamlitのselectbox / multiselect
```

たとえば、新規登録画面の部署選択で、`departments = get_departments()`として、`departments.csv` の中身を取得します。

### 2. 中心になる関数 `read_master_csv()`

一番大事なのはこれです。

```python
def read_master_csv(file_name: str, column_name: str, fallback: list[str]) -> list[str]:

    path = CONFIG_DIR / file_name

    if not path.exists():
        return fallback

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return fallback

    if column_name not in df.columns:
        return fallback

    values = (df[column_name].dropna().astype(str).str.strip())
    result = [v for v in values.tolist() if v]
    return result if result else fallback
```

これは、指定されたCSVファイルから、指定された列を読み込む共通関数です。

たとえば、

```python
read_master_csv(
    file_name="departments.csv",
    column_name="department",
    fallback=["営業部", "業務部", "管理部"],
)
```

なら、`config/departments.csv`を読み込み、その中の `department` 列をリストとして返します。

#### 2-1. `fallback` とは何か

`fallback` は、CSVが読めなかったときの予備の値です。
たとえば、`departments.csv` が存在しない、列名が間違っている、読み込みに失敗した、という場合でも、アプリが止まらないようにします。

つまり、

```text
CSVが読める → CSVの内容を使う
CSVが読めない → fallbackの固定リストを使う
```

という安全策です。

#### 2-2. この部分の意味

```python
path = CONFIG_DIR / file_name

if not path.exists():
    return fallback
```

これは、対象のCSVファイルが存在するか確認しています。存在しなければ、エラーにせず `fallback` を返します。

#### 2-3. 列名チェック

```python
if column_name not in df.columns:
    return fallback
```

CSVファイルはあっても、列名が間違っている可能性があります。

たとえば、本来は、

```text
department
営業部
```

なのに、

```text
departments
営業部
```

となっていると、`department` 列がありません。その場合も、エラーで止めずに `fallback` を返します。

#### 2-4. 値の整形

```python
values = (df[column_name].dropna().astype(str).str.strip())
```

これは、CSVの値をきれいにしています。

| 処理              | 意味             |
| ----------------- | ---------------- |
| `df[column_name]` | 指定列を取り出す |
| `.dropna()`       | 欠損値を除く     |
| `.astype(str)`    | 文字列に変換する |
| `.str.strip()`    | 前後の空白を削る |

#### 2-5. 空文字を除外する

```python
result = [v for v in values.tolist() if v]
```

これは、空文字を除外してリスト化しています。

最後に、`return result if result else fallback`で、読み込めた値があればそれを返し、空なら `fallback` を返します。

### 3. 各 `get_...()` 関数

下の関数たちは、`read_master_csv()` を使いやすくするためのラッパーです。

| 関数                                  | 意味                             |
| ------------------------------------- | -------------------------------- |
| `def get_departments() -> list[str]:` | これは部署一覧を返します。       |
| `def get_categories() -> list[str]:`  | これはカテゴリ一覧を返します。   |
| `def get_assignees() -> list[str]:`   | これは担当者一覧を返します。     |
| `def get_statuses() -> list[str]:`    | これはステータス一覧を返します。 |
| `def get_channels() -> list[str]:`    | これは受付経路一覧を返します。   |
| `def get_priorities() -> list[str]:`  | これは優先度一覧を返します。     |

### 4. なぜ個別関数に分けるのか

`app.py` 側で毎回こう書くのは面倒です。

```python
read_master_csv("departments.csv", "department", [...])
```

そこで、`get_departments()`と書けば済むようにしています。つまり、`app.py` 側では細かいファイル名や列名を意識しなくてよくなります。

### 5. 具体的な使われ方

`app.py` では、たとえばこう使います。

```python
departments = get_departments()
department = st.selectbox("部署 *", departments)
```

これにより、`departments.csv` の内容がそのまま選択肢になります。

担当者も同じです。

```python
assignee_options = ["未設定"] + get_assignees()
```

`get_assignees()` で担当者一覧を読み込み、先頭に `"未設定"` を追加しています。

### 結論

`master_data.py` は、部署・カテゴリ・担当者・ステータスなどのマスタ情報を `config` CSV から読み込むためのファイルです。

役割をまとめると、

```text
config CSVを読む
CSVがなければfallbackを使う
欠損や空白を整える
選択肢リストとしてapp.pyに渡す
```

です。
`app.py` が画面担当、`db.py` がDB担当だとすると、`master_data.py` は 選択肢・マスタ情報の読み込み担当です。

## `app.py`

WBS5時点の `app.py` は、WBS4の「閲覧画面」に加えて、新規登録とステータス更新ができるようになった版です。
全体像はこうです。

```text
WBS4 app.py
  → DBの問い合わせを表示する
  → フィルタする
  → KPIを見る
  → 簡易集計を見る

WBS5 app.py
  → 上記に加えて
  → 新規問い合わせを登録する
  → 既存問い合わせを更新する
  → 更新後に画面へ反映する
```

### 1. WBS4から引き継いでいる部分

WBS4で作った部分は、主にそのまま残っています。

| 関数                    | 役割                                 |
| ----------------------- | ------------------------------------ |
| `load_inquiries()`      | DBから問い合わせ一覧を読み込む       |
| `get_options()`         | フィルタ用の選択肢を作る             |
| `apply_filters()`       | 部署・カテゴリ・担当者などで絞り込む |
| `show_kpi_cards()`      | 件数・期限超過・管理時間などを表示   |
| `show_inquiry_table()`  | 問い合わせ一覧を表で表示             |
| `show_simple_summary()` | 簡易集計を表示                       |

つまり、WBS4までの `app.py` は 見る画面 でした。WBS5では、ここに 入力・更新する画面 が追加されました。

### 2. WBS5で増えた`import`

WBS5では、DB操作とマスタ読み込みの関数が増えています。

```python
from src.db import (
    fetch_all_inquiries,
    fetch_inquiry_by_id,
    generate_request_id,
    init_db,
    update_inquiry,
    upsert_inquiry,
)
```

意味はこうです。

| 関数                    | 役割                              |
| ----------------------- | --------------------------------- |
| `fetch_inquiry_by_id()` | 更新対象の問い合わせを1件取得する |
| `generate_request_id()` | 新規登録時のIDを自動発行する      |
| `update_inquiry()`      | 既存問い合わせを更新する          |
| `upsert_inquiry()`      | 新規問い合わせをDBに登録する      |

また、`master_data.py` から選択肢を読み込みます。

```python
from src.master_data import (
    get_assignees,
    get_categories,
    get_channels,
    get_departments,
    get_priorities,
    get_statuses,
)
```

これは、部署・カテゴリ・担当者・ステータスなどを `config/*.csv` から取得するためです。

### 3. `clear_cache()`

```python
def clear_cache() -> None:
    st.cache_data.clear()
```

これは、DB更新後にStreamlitのキャッシュを消す関数です。
`load_inquiries()` には、`@st.cache_data(ttl=10)`がついているので、DBを更新しても画面が古いデータを持っている可能性があります。
そのため、新規登録や更新をした後に、`clear_cache()`を呼び、次回読み込み時に最新のDB内容を取り直すようにしています。

### 4. `index_or_zero()`

```python
def index_or_zero(options: list[str], value: str | None) -> int:
    if value in options:
        return options.index(value)
    return 0
```

これは、selectbox の初期選択位置を安全に決める関数です。
たとえば、`statuses = ["未対応", "対応中", "情報待ち", "承認待ち", "完了"]`の中で、現在のステータスが "対応中" なら、その位置を返します。

```python
statuses.index("対応中") # 1
```

もし値が選択肢に存在しなければ、先頭の 0 を返します。

つまり、

```text
現在値が選択肢にある → その位置を初期値にする
現在値が選択肢にない → 先頭を初期値にする
```

という安全策です。

### 5. `parse_date_or_none()`

```python
def parse_date_or_none(value: Any) -> date | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None

    return parsed.date()
```

これは、DBから取った日付文字列を `date` 型に変換する関数です。たとえば、`"2026-06-28"`を、`date(2026, 6, 28)`に変換します。
なぜ必要かというと、Streamlitの `st.date_input()` は、文字列ではなく `date` 型を受け取るのが自然だからです。空欄や変な日付なら `None` を返します。

### 6. `show_create_form()`

![alt text](<スクリーンショット 2026-06-28 午後9.06.41.png>)

```python
def show_create_form() -> None:
    st.header("新規登録")
    st.caption("DX化後の問い合わせ受付フォームを想定した登録画面です。")

    departments = get_departments()
    categories = get_categories()
    channels = get_channels()
    priorities = get_priorities()
    statuses = get_statuses()
    assignee_options = ["未設定"] + get_assignees()

    default_due_date = date.today() + timedelta(days=3)

    with st.form("create_inquiry_form", clear_on_submit=False):
        col1, col2, col3 = st.columns(3)

        """後略(画面表示するコード)"""

    if submitted:
        errors = []

        """中略(エラー処理)"""

        if errors:
            for error in errors:
                st.error(error)
            return

        now = datetime.now()
        request_date = now.strftime("%Y-%m-%d")
        request_time = now.strftime("%H:%M")
        request_id = generate_request_id(request_date)

        assignee = "" if assignee_label == "未設定" else assignee_label

        record = {
            "request_id": request_id,
            "request_date": request_date,
            "request_time": request_time,
            """後略"""
        }

        try:
            upsert_inquiry(record)
            clear_cache()
            st.success(f"問い合わせを登録しました: {request_id}")
            st.info("一覧画面に戻ると、登録した問い合わせを確認できます。")
        except Exception as exc:
            st.error("登録に失敗しました。")
            st.exception(exc)
```

ここがWBS5の中心その1です。新規登録フォームを表示する関数です。
この関数では、以下を行います。

```text
configから選択肢を読む
↓
Streamlitフォームを表示する
↓
入力内容を受け取る
↓
必須項目をチェックする
↓
request_idを自動発行する
↓
record辞書を作る
↓
upsert_inquiry()でDBに登録する
↓
キャッシュを消す
↓
成功メッセージを表示する
```

### 6-1. エラー処理

```python
if errors:
    for error in errors:
        st.error(error)
    return
```

`st.error(error)`はStreamlit画面上にエラーメッセージを赤色で表示する処理です。また、`return`を書くことで処理が終了します。

特に重要なのはこのあたりです。

```python
request_id = generate_request_id(request_date)
```

ここで、`REQ-20260628-001`のような問い合わせIDを自動で作っています。
そして、

```python
record = {
    "request_id": request_id,
    "request_date": request_date,
    ...
}
```

で、DBに登録する1件分の辞書を作ります。

最後に、`upsert_inquiry(record)`でSQLiteに保存します。

### 7. `make_update_label()`

![alt text](<スクリーンショット 2026-06-28 午後9.30.38.png>)

```python
def make_update_label(row: pd.Series) -> str:
    detail = str(row.get("detail", ""))
    short_detail = detail[:35] + "..." if len(detail) > 35 else detail

    return (
        f'{row.get("request_id", "")} | '
        f'{row.get("status", "")} | '
        f'{row.get("requester", "")} | '
        f'{row.get("category", "")} | '
        f"{short_detail}"
    )
```

これは、更新画面の selectbox に表示するラベルを作る関数です。
たとえば、問い合わせを選ぶときに単に、`REQ-20260628-001`だけだと分かりにくいです。そこで、

```text
REQ-20260628-001 | 未対応 | 田口 航 | PC・システム | PCの動作が遅い...
```

のように、ID・ステータス・依頼者・カテゴリ・内容の一部をまとめて表示します。これにより、更新対象を選びやすくしています。

### 8. `show_update_form()`

```python
def show_update_form(df: pd.DataFrame) -> None:
    st.header("ステータス更新")
    st.caption("管理部が担当者、ステータス、対応内容、完了日を更新する画面です。")

    if df.empty:
        st.warning("更新できる問い合わせデータがありません。")
        return

    display_df = df.copy()
    display_df["update_label"] = display_df.apply(make_update_label, axis=1)

    labels = display_df["update_label"].tolist()
    label_to_id = dict(zip(display_df["update_label"], display_df["request_id"]))

    selected_label = st.selectbox("更新対象の問い合わせ", labels)
    selected_request_id = label_to_id[selected_label]

    current = fetch_inquiry_by_id(selected_request_id)
    if current is None:
        st.error("選択した問い合わせが見つかりません。")
        return

    with st.expander("現在の問い合わせ内容", expanded=True):
        st.write(f"**問い合わせID**: {current.get('request_id', '')}")
        st.write(f"**依頼者**: {current.get('requester', '')}（{current.get('department', '')}）")
        st.write(f"**カテゴリ**: {current.get('category', '')} / {current.get('subcategory', '')}")
        st.write(f"**希望期限**: {current.get('due_date', '')}")
        st.write(f"**問い合わせ内容**: {current.get('detail', '')}")
        if current.get("missing_info"):
            st.write(f"**不足情報・確認事項**: {current.get('missing_info', '')}")

    assignee_options = ["未設定"] + get_assignees()
    statuses = get_statuses()

    current_assignee = current.get("assignee") or "未設定"
    current_status = current.get("status") or "未対応"

    current_completed_date = parse_date_or_none(current.get("completed_date"))
    completed_date_enabled_default = current_completed_date is not None

    with st.form("update_inquiry_form"):
        col1, col2, col3 = st.columns(3)

        """中略(更新フォームのコード)"""

        submitted = st.form_submit_button("更新する")

    if submitted:
        """後略（更新ボタン押下後の処理コード）"""
```

ここがWBS5の中心その2です。既存問い合わせの更新画面です。

流れはこうです。

```text
問い合わせ一覧dfを受け取る
↓
更新対象の選択肢ラベルを作る
↓
ユーザーが更新対象を選ぶ
↓
request_idを取り出す
↓
fetch_inquiry_by_id()でDBから最新の1件を取得
↓
現在の問い合わせ内容を表示
↓
担当者・ステータス・対応内容・完了日などを入力
↓
update_inquiry()でDBを更新
↓
キャッシュを消す
↓
成功メッセージを表示
```

特に重要なのはここです。

```python
current = fetch_inquiry_by_id(selected_request_id)
```

一覧DataFrameからではなく、DBから1件を取り直しています。これは、更新対象の最新状態を確実に取得するためです。
更新時には、

```python
updates = {
    "assignee": assignee,
    "status": status,
    "response_summary": response_summary.strip(),
    "record_issue": record_issue.strip(),
    "completed_date": completed_date_text,
    "management_minutes": int(management_minutes),
    "actual_response_minutes": int(actual_response_minutes),
}
```

という更新用辞書を作り、`update_inquiry(selected_request_id, updates)`でDBを更新します。

### 9. 完了時のチェック

この処理も重要です。

```python
if status == "完了" and not set_completed_date:
    st.error("ステータスを完了にする場合は、完了日を設定してください。")
    return
```

これは、`ステータスを完了にするなら、完了日も入れてください`という業務ルールです。
完了日がないと、後で `response_days`、つまり対応日数を計算できません。そのため、完了時には完了日を必須にしています。

### 10. `main()` の変化

WBS4の `main()` では、新規登録タブとステータス更新タブは仮表示でした。WBS5では、ここが実装済みに変わっています。
つまり、タブ構成は同じですが、中身が本物のフォームになりました。

| タブ           | WBS4     | WBS5           |
| -------------- | -------- | -------------- |
| 問い合わせ一覧 | 実装済み | 継続           |
| 新規登録       | 仮表示   | 実装済み       |
| ステータス更新 | 仮表示   | 実装済み       |
| 集計・CSV出力  | 簡易集計 | 簡易集計のまま |

### 11. WBS5時点の`app.py`全体の役割

WBS5時点の `app.py` は、以下の3つを担います。

```text
1. 問い合わせを見る
2. 問い合わせを登録する
3. 問い合わせを更新する
```

データの流れで見るとこうです。

#### 一覧表示

```text
SQLite
↓
fetch_all_inquiries()
↓
load_inquiries()
↓
Streamlit一覧画面
```

#### 新規登録

```text
Streamlit新規登録フォーム
↓
record辞書を作成
↓
generate_request_id()
↓
upsert_inquiry()
↓
SQLite
```

#### ステータス更新

```text
Streamlit更新フォーム
↓
fetch_inquiry_by_id()
↓
現在値を表示
↓
update_inquiry()
↓
SQLite
```

### 結論

WBS5での `app.py` は、WBS4の閲覧画面に加えて、新規登録フォームとステータス更新フォームを追加したものです。特に追加された重要部分は以下です。

```text
clear_cache()
→ DB更新後に画面の古いデータを消す

index_or_zero()
→ selectboxの初期値を安全に設定する

parse_date_or_none()
→ DBの日付文字列をdate_input用に変換する

show_create_form()
→ 新規問い合わせを登録する

make_update_label()
→ 更新対象を選びやすくする表示名を作る

show_update_form()
→ 既存問い合わせを更新する
```

これで、単なる「見える化アプリ」から、問い合わせ台帳として登録・更新できる業務アプリに近づいた、という位置づけです。
