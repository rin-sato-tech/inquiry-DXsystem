# db.pyファイルの役割

`db.py` は、ひと言でいうと SQLiteデータベースを操作するための窓口です。
`schema.sql` が「DBの設計図」だとすると、`db.py` はその設計図で作ったDBに対して、作成・登録・取得・更新を行う処理をまとめたファイルです。

## 1. `db.py`の位置づけ

今回の構成では、役割はこうです。

| ファイル名        | 役割                                     |
| ----------------- | ---------------------------------------- |
| `schema.sql`      | DBの構造を定義する                       |
| `data/inquiry.db` | 実際のSQLiteデータベースファイル         |
| `src/db.py`       | PythonからDBを操作する処理を書く         |
| `app.py`          | Streamlit画面から`db.py`の関数を呼び出す |

つまり、`app.py` が直接SQLiteを触るのではなく、`db.py` を通じて操作します。

```text
Streamlit画面
↓
app.py
↓
src/db.py
↓
data/inquiry.db
```

## 2. `db.py`が担っている主な役割

現在の `db.py` は、主に以下を担っています。

| 役割         | 内容                                       |
| ------------ | ------------------------------------------ |
| DB接続       | SQLiteファイルに接続する                   |
| DB初期化     | `schema.sql` を読み込んでテーブルを作る    |
| データ正規化 | 欠損値・数値・日時を整える                 |
| 新規登録     | 問い合わせをDBへ登録する                   |
| 複数登録     | CSVから読み込んだ複数件をまとめて登録する  |
| 一覧取得     | 問い合わせを全件取得する                   |
| 1件取得      | `request_id` で問い合わせを1件取得する     |
| 更新         | ステータス・担当者・対応内容などを更新する |
| ID発行       | `REQ-YYYYMMDD-001` 形式のIDを作る          |

## 3. 各関数の意味

### 3-1. `get_connection()`

```python
# DB_PATH = data/inquiry.db
def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
```

これは、SQLiteに接続する関数です。`data/inquiry.db` に接続し、PythonからSQLを実行できる状態にします。

---

### 3-2. `init_db()`

```python
# SCHEMA_PATH = schema.sql
def init_db(db_path: Path = DB_PATH) -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"schema.sql が見つかりません: {SCHEMA_PATH}")

    with get_connection(db_path) as conn:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()
```

これは、DBを初期化する関数です。具体的には、

```text
schema.sqlを読む
↓
CREATE TABLEを実行
↓
inquiriesテーブルを作る
```

という処理をします。初回起動時に `data/inquiry.db` がない場合でも、この関数を実行すればDB構造を作れます。

---

### 3-3. `normalize_record()`

def normalize_record(record: dict[str, Any]) -> dict[str, Any]:

これは、DB登録前にデータを整える関数です。

たとえば、

| 処理         | 内容                                         |
| ------------ | -------------------------------------------- |
| 欠損値処理   | `None` や `NaN` を空文字にする               |
| 数値変換     | `management_minutes` を整数にする            |
| 日時補完     | `created_at`, `updated_at` を補う            |
| 必須チェック | `requester` や `detail` が空ならエラーにする |

つまり、DBに入れる前の安全確認です。

<details open>
<summary>データの正規化 normalize_record()の詳細</summary>

### A. なぜこの処理が必要なのか

CSVや画面入力から来るデータは、そのままDBに入れるには少し危ないです。たとえば、こういう値が混ざります。

```text
None
NaN
""
" "
"15"
15.0
"15.0"
"abc"
```

人間から見ると「空欄」や「15分」でも、PythonやSQLiteから見ると型がバラバラです。そのままDBに入れると、

```text
本当は空欄なのに "nan" という文字列になる
数値のはずなのに文字列で入る
必須項目が空のまま入る
created_at がない
updated_at がない
```

ということが起きます。そこで、DB登録前に `normalize_record()` で整えます。

### B. `_is_missing()` の役割

まずこれです。

```python
def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and value != value:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False
```

これは、値が「実質的に空かどうか」を判定する関数です。

#### 何を空とみなすか

| 値             |       判定 | 理由                         |
| -------------- | ---------: | ---------------------------- |
| `None`         |         空 | Pythonの空値                 |
| `float("nan")` |         空 | pandasで欠損値として出てくる |
| `""`           |         空 | 空文字                       |
| `"   "`        |         空 | 空白だけの文字列             |
| `"原田 健太"`  | 空ではない | 中身がある                   |
| `0`            | 空ではない | 数値として意味がある         |
| `"0"`          | 空ではない | 文字列だが中身がある         |

#### 更なる詳細 `value != value`

```python
# valueがfloat型かつNaNであれば真となり、Trueが返る
if isinstance(value, float) and value != value:
    return True
```

この部分は 「value が NaN かどうか」を判定しています。

普通の数値は、自分自身と等しいです。

```python
value = 10.0
value == value #True
```

しかし、NaN だけは例外です。

```python
value = float("nan")
value == value #False
value != value #True
```

つまり、NaN は「数値ではない値」を表す特殊な値で、自分自身と比較しても等しくならないという性質があります。

だからこの条件は、
`isinstance(value, float)`で「float型か確認」し、
`value != value`で「NaN特有の性質があるか確認」しています。

具体的にはこうです。

```python
_is_missing(10.0) #False

_is_missing(float("nan")) #True

_is_missing("") #True

_is_missing("原田 健太") #False
```

要するに、

```python
if isinstance(value, float) and value != value:
    return True
```

は、かなり特殊な書き方ですが、意味としては単純に、`value が NaN なら欠損として扱う`という処理です。

### C. `_to_int_or_zero()` の役割

次にこれです。

```python
def _to_int_or_zero(value: Any) -> int:
    if _is_missing(value):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0
```

これは、値を整数に変換する関数です。変換できなければ 0 にします。今回だと、主に以下の列に使います。

```text
management_minutes (管理作業時間)
actual_response_minutes (実対応時間)
```

#### 変換例

| 入力値   | 出力 | 理由                |
| -------- | ---: | ------------------- |
| `15`     | `15` | そのまま整数        |
| `15.0`   | `15` | floatをintへ        |
| `"15"`   | `15` | 文字列を数値へ      |
| `"15.0"` | `15` | 文字列floatを数値へ |
| `""`     |  `0` | 空欄だから0         |
| `None`   |  `0` | 空だから0           |
| `NaN`    |  `0` | 欠損だから0         |
| `"abc"`  |  `0` | 数値にできないから0 |

この部分です。

```python
return int(float(value))
```

なぜいきなり `int(value)` にしないかというと、CSVから読むと `"15.0"` のような文字列になることがあるからです。

```python
int("15") # OK
int("15.0") # エラー
```

一方で、

```python
int(float("15.0")) # OK
```

なので、一度 `float` にしてから `int` にしています。

### D. normalize_record() の役割

本体がこれです。

```python
def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
normalized: dict[str, Any] = {}

    for col in COLUMNS:
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
```

これは、問い合わせ1件分のデータをDB登録用に整える関数です。イメージとしては、こうです。

```text
入力された問い合わせデータ
↓
必要な列を順番に確認
↓
空欄を処理する
↓
数値を整数にする
↓
作成日時・更新日時を補う
↓
必須項目が空ならエラーにする
↓
DBに入れられるきれいなdictを返す
```

#### D-1. `record` とは何か

record は、問い合わせ1件分の辞書です。

たとえばこういうものです。

```python
record = {
"request_id": "REQ-20260628-001",
"request_date": "2026-06-28",
"request_time": "10:15",
"requester": "田口 航",
"department": "施工管理部",
"channel": "フォーム",
"category": "PC・システム",
"subcategory": "PC本体",
"detail": "PCの動作が遅い",
"missing_info": "",
"priority": "高",
"due_date": "2026-06-30",
"assignee": "原田 健太",
"status": "未対応",
"response_summary": "",
"record_issue": "",
"completed_date": "",
"management_minutes": "10",
"actual_response_minutes": "",
}
```

これをDBに入れる前に、`normalize_record()` が整えます。

#### D-2. COLUMNS に従って処理する意味

```python
for col in COLUMNS:
    value = record.get(col, "")
```

COLUMNS は、DBに保存する列の一覧です。
つまり、`normalize_record()` は、入力された `record` に何が入っているかではなく、DBに必要な列を基準に処理するようになっています。
これにはメリットがあります。たとえば、入力データに `created_at` がなくても、

```python
value = record.get("created_at", "")
```

で空として扱い、あとで現在時刻を補えます。

辞書である `record` に対して、存在しないキーを指定するとエラーになります。そこで使うのが`.get()`です。

```python
record.get("assignee", "")
```

これは、

```text
assignee というキーがあれば、その値を返す
なければ "" を返す
```

という意味です。

#### D-3. 整数列の処理

```python
if col in INTEGER_COLUMNS:
    normalized[col] = _to_int_or_zero(value)
```

`INTEGER_COLUMNS` はこうでした。

```python
INTEGER_COLUMNS = {
    "management_minutes",
    "actual_response_minutes",
}
```

つまり、管理作業時間と実対応時間だけは、文字列ではなく整数に変換します。たとえば、`"15.0"` が来たら、`15` にします。空なら、`0` にします。

#### D-4. 作成日時・更新日時の処理

```python
elif col in {"created_at", "updated_at"}:
    normalized[col] = value if not _is_missing(value) else now
```

`created_at` と `updated_at` は、レコードの作成日時・更新日時です。入力データに値があればそれを使います。なければ、現在時刻を入れます。

```python
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

たとえば、入力に `created_at` がなければ、`2026-06-28 12:30:45`のような値を自動で入れます。

**A if 条件 else B**
これは普通の`if-else`を一行で書く構文です。意味は、`条件がTrueならA、FalseならB`です。

```python
value if not _is_missing(value) else now
```

`_is_missing()`は欠損なら`True`を返す関数でした。すなわち、この`if`文の意味は、

```text
value が欠損でなければ value を使う
value が欠損なら now を使う
```

となります。

#### D-5. 文字列列の処理

```python
else:
    normalized[col] = "" if _is_missing(value) else str(value).strip()
```

整数列でも日時列でもないものは、基本的に文字列として扱います。

たとえば、`" 原田 健太 "`が来たら、前後の空白を削って、`"原田 健太"`にします。空欄や `None` なら、`""`にします。つまり、この行はかなり大事で、

```python
空欄なら空文字にする
空欄でなければ文字列にして前後の空白を削る
```

という処理です。
なお、`strip()`は文字列の前後の空白を削るメソッドなので、文字列中の空白は削られません。

### E. 必須項目チェック

```python
for col in REQUIRED_COLUMNS:
    if _is_missing(normalized.get(col)):
        raise ValueError(f"必須項目が空です: {col}, record={record}")
```

`REQUIRED_COLUMNS` は、DBに登録するうえで空だと困る項目です。たとえば、`detail` が空だと、何の問い合わせか分かりません。その場合は、DBに登録せずにエラーにします。

```python
raise ValueError(...)
```

これは「明示的に失敗させる」処理です。変なデータを黙ってDBに入れるより、ここで止めた方が安全です。

### F. 具体例

たとえば、入力がこうだとします。

```python
record = {
"request_id": "REQ-20260628-001",
"request_date": "2026-06-28",
"request_time": " 10:15 ", ←空白がある
"requester": " 田口 航 ", ←空白がある
"department": "施工管理部",
"channel": "フォーム",
"category": "PC・システム",
"detail": " PCの動作が遅い ", ←空白がある
"priority": "高",
"due_date": "2026-06-30",
"status": "未対応",
"management_minutes": "15.0", ←整数に変更される
"actual_response_minutes": "", ←0にされる
}
```

`normalize_record()` を通すと、概念的にはこうなります。

```python
{
"request_id": "REQ-20260628-001",
"request_date": "2026-06-28",
"request_time": "10:15",
"requester": "田口 航",
"department": "施工管理部",
"channel": "フォーム",
"category": "PC・システム",
"subcategory": "", ←なかったので追加
"detail": "PCの動作が遅い",
"missing_info": "", ←なかったので追加
"priority": "高",
"due_date": "2026-06-30",
"assignee": "", ←なかったので追加
"status": "未対応",
"response_summary": "", ←なかったので追加
"record_issue": "", ←なかったので追加
"completed_date": "", ←なかったので追加
"management_minutes": 15,
"actual_response_minutes": 0,
"created_at": "2026-06-28 12:30:45", ←追加
"updated_at": "2026-06-28 12:30:45", ←追加
}
```

主な変化は、

```text
前後の空白が消える
足りない列が空文字で補われる
作業時間が整数になる
空の作業時間が0になる
created_at / updated_at が追加される
```

です。

### G. なぜ関数を分けているのか

`normalize_record()` の中に全部書くこともできます。しかし、こう分けた方が読みやすいです。

```text
_is_missing()
→ 空欄判定だけを担当

_to_int_or_zero()
→ 整数変換だけを担当

normalize_record()
→ 1件分のデータ全体を整える
```

これは「小さな部品に分ける」という考え方です。

たとえば、`_is_missing()` は `normalize_record()` 以外でも使えます。また、欠損判定のルールを変えたいときも、`_is_missing()` だけ見ればよくなります。

### H. 先頭の `_` の意味

`_is_missing` や `_to_int_or_zero` のように、関数名の先頭に `_` がついています。これはPythonの慣習で、

```text
このファイル内部で使う補助関数です
外から直接使う想定ではありません
```

という意味です。厳密にアクセス禁止になるわけではありません。ただ、「内部用ですよ」という目印です。一方で、`normalize_record()` は外から使われる可能性がある主要関数なので、 `_` がついていません。

## I. 3つの関数の関係を一文で言うと

この3つの関係はこうです。

```text
_is_missing() で空かどうかを判定し、
_to_int_or_zero() で数値項目を安全に整数化し、
normalize_record() で問い合わせ1件分をDB登録できる形に整える。
```

## J. この処理がないとどうなるか

この処理を省くと、次のような問題が起きやすいです。

| 問題                     | 例                                              |
| ------------------------ | ----------------------------------------------- |
| 欠損値が変な文字列になる | `"nan"` がDBに入る                              |
| 数値列が文字列になる     | `"15.0"` のまま入る                             |
| 空白が残る               | `" 原田 健太 "` と `"原田 健太"` が別扱いになる |
| 必須項目が空のまま入る   | 依頼者なしの問い合わせが登録される              |
| 作成日時が入らない       | いつ登録されたか分からない                      |
| 更新日時が入らない       | いつ変更されたか分からない                      |

だから、少し面倒でも `normalize_record()` が必要になります。

## 結論

`normalize_record()` と補助関数の役割は、DB登録前のデータ整形・安全確認です。

```text
_is_missing()
  → None、NaN、空文字、空白だけの文字列を「欠損」と判定する

_to_int_or_zero()
  → 作業時間などを整数に変換し、失敗したら0にする

normalize_record()
  → 問い合わせ1件分のデータを、DBに入れられる安全な形へ整える
```

要するに、これらは「業務データの掃除係」です。画面やCSVから来た不揃いなデータを、そのままDBに入れず、欠損・型・日時・必須項目を整えてから保存するための関数です。

</details>

---

### 3-4. `upsert_inquiry()`

```python
def upsert_inquiry(record: dict[str, Any], conn: sqlite3.Connection | None = None) -> None:
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
```

これは、問い合わせを1件登録または更新する関数です。

`upsert` は、以下の意味です。

```text
存在しなければINSERTする
存在すればUPDATEする
```

今回の場合、`request_id` が同じデータがすでにあれば更新、なければ新規登録します。CSV取込でも、新規登録画面でも使えます。

中心はこのSQLです。

```sql
INSERT INTO inquiries (...)
VALUES (...)
ON CONFLICT(request_id) DO UPDATE SET ...
```

`ON CONFLICT(request_id)` は、
同じ `request_id` があったらエラーにせず、更新に切り替えるという意味です。

**{col} = excluded.{col}**
これは SQLite の `ON CONFLICT ... DO UPDATE` で使う書き方です。

```sql
ON CONFLICT(request_id) DO UPDATE SET
status = excluded.status
```

意味は、

```text
同じ request_id がすでにある場合、
新しく入れようとした status の値で、
既存レコードの status を更新する
```

です。ここでの `excluded.status` は、INSERTしようとした新しいデータ側の `status` という意味です。

---

### 3-5. `upsert_inquiries()`

```python
def upsert_inquiries(records: Iterable[dict[str, Any]]) -> int:
    count = 0
    with get_connection() as conn:
        for record in records:
            upsert_inquiry(record, conn=conn)
            count += 1
        conn.commit()
    return count
```

これは、複数の問い合わせをまとめて登録する関数です。主に `src/import_csv.py` から使います。

```text
CSVを読み込む
↓
recordsに変換
↓
upsert_inquiries()
↓
SQLiteへまとめて登録
```

たとえば、CSVから21件読み込んだ場合、

```python
records = [
    {...1件目...},
    {...2件目...},
    {...3件目...},
]
```

これを、`upsert_inquiries(records)`でまとめてDBに入れます。

---

### 3-6. `fetch_all_inquiries()`

```python
def fetch_all_inquiries() -> list[dict[str, Any]]:
    sql = """
        SELECT *
        FROM inquiries
        ORDER BY request_date DESC, request_time DESC, request_id DESC
    """
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(row) for row in rows]
```

これは、問い合わせを全件取得する関数です。Streamlitの一覧画面では、この関数を使っています。

```text
app.py
↓
fetch_all_inquiries()
↓
SQLiteから全件取得
↓
DataFrame化
↓
一覧表示
```

#### `[dict(row) for row in rows]`

たとえば、DBから次の2行が取れたとします。

```text
rows = [
    <sqlite3.Row 1件目>,
    <sqlite3.Row 2件目>
]
```

sqlite3.Row は、見た目は少し特殊ですが、列名で値を取り出せます。ただ、このままだと普通の辞書ではありません。そこで `dict(row)` に変換します。

たとえば1行目がこういう内容なら、

```python
row = {
    "request_id": "REQ-20260628-001",
    "requester": "田口 航",
    "status": "未対応"
}
```

実際には `sqlite3.Row` ですが、`dict(row)`によって普通の辞書になります。

```python
{
    "request_id": "REQ-20260628-001",
    "requester": "田口 航",
    "status": "未対応"
}
```

これを複数行に対して繰り返しているのが、`[dict(row) for row in rows]`です。
具体例として、rows に2件あるとすると、

```python
rows = [
    {"request_id": "REQ-001", "requester": "田口 航", "status": "未対応"},
    {"request_id": "REQ-002", "requester": "山下 颯太", "status": "完了"},
]
```

変換後はこうなります。

```python
[
    {
        "request_id": "REQ-001",
        "requester": "田口 航",
        "status": "未対応",
    },
    {
        "request_id": "REQ-002",
        "requester": "山下 颯太",
        "status": "完了",
    },
]
```

つまり、`[dict(row) for row in rows]`は、普通の `for` 文で書くとこうです。

```python
result = []

for row in rows:
    result.append(dict(row))

return result
```

要するに、DBから取ってきた各行を、扱いやすい辞書に変換して、リストとして返しているという処理です。

---

### 3-7. `fetch_inquiry_by_id()`

```python
def fetch_inquiry_by_id(request_id: str) -> dict[str, Any] | None:
    sql = "SELECT * FROM inquiries WHERE request_id = ?"
    with get_connection() as conn:
        row = conn.execute(sql, (request_id,)).fetchone()
    return dict(row) if row else None
```

これは、問い合わせIDを指定して1件だけ取得する関数です。ステータス更新画面で使います。
たとえば、`REQ-20260626-001`を選ぶと、その問い合わせの現在の内容を取得して、更新フォームに表示します。

### 3-8. `update_inquiry()`

def update_inquiry(request_id: str, updates: dict[str, Any]) -> None:

これは、既存問い合わせの一部項目を更新する関数です。

たとえば、以下のような更新に使います。

| 更新項目     | 例                     |
| ------------ | ---------------------- |
| 担当者       | 原田 健太              |
| ステータス   | 対応中、完了           |
| 対応内容     | パスワードを再設定した |
| 完了日       | 2026-06-26             |
| 管理作業時間 | 10分                   |
| 実対応時間   | 20分                   |

app.py のステータス更新画面から呼び出されます。

### 3-9. `generate_request_id()`

def generate_request_id(target_date: str) -> str:

これは、新規問い合わせIDを発行する関数です。

たとえば、2026年6月26日に登録する場合、

REQ-20260626-001
REQ-20260626-002
REQ-20260626-003

のように、同じ日の中で連番を作ります。

新規登録画面で使います。

## 4. なぜapp.pyに直接DB処理を書かないのか

`app.py` に直接SQLを書いても動きます。しかし、それをすると `app.py` が肥大化します。

```text
画面表示、フォーム処理、DB接続、SQL実行、データ整形、エラー処理
```

これらが全部 `app.py` に混ざると、後で読みにくくなります。そこで、DB操作は `db.py` に分けます。

| ファイル         | 役割               |
| ---------------- | ------------------ |
| `app.py`         | 画面を作る         |
| `db.py`          | DBを操作する       |
| `aggregation.py` | 集計・派生列を作る |
| `master_data.py` | configを読む       |
| `import_csv.py`  | CSVを取り込む      |

このように分けることで、責任範囲が明確になります。

## 5. `db.py`は「データアクセス層」

少し専門的に言うと、`db.py` は データアクセス層 に近い役割です。データアクセス層とは、アプリケーションからデータベースを操作するための層です。今回なら、

```text
app.py は「画面」
db.py は「DB操作」
schema.sql は「DB構造」
```

という分担です。この分け方にすると、たとえば将来SQLiteからPostgreSQLに変える場合でも、主に `db.py` を修正すればよくなります。

## 6. 今回のシステムでの処理の流れ

### CSV取込時

```text
data/inquiry_dx_before_sample.csv
↓
src/import_csv.py
↓
src/db.py の upsert_inquiries()
↓
data/inquiry.db
```

### 一覧表示時

```text
data/inquiry.db
↓
src/db.py の fetch_all_inquiries()
↓
app.py
↓
Streamlit一覧画面
```

### 新規登録時

```text
Streamlit新規登録フォーム
↓
app.py
↓
src/db.py の generate_request_id()
↓
src/db.py の upsert_inquiry()
↓
data/inquiry.db
```

### ステータス更新時

```text
Streamlitステータス更新フォーム
↓
app.py
↓
src/db.py の update_inquiry()
↓
data/inquiry.db
```

## 結論

`db.py` は、PythonからSQLiteを操作するための中核ファイルです。具体的には、

```text
DBに接続する
schema.sqlからテーブルを作る
問い合わせを登録する
問い合わせを取得する
問い合わせを更新する
request_idを発行する
登録前にデータを整える
```

という役割を担っています。
`schema.sql` が「DBの設計図」、`config` が「選択肢の管理」、`app.py` が「画面」だとすると、`db.py` は 画面とデータベースをつなぐ操作窓口です。
