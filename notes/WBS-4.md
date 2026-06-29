# WBS-4: Streamlitの画面開発

![alt text](<./streamlit_list_for_WBS4.png>)

## `aggregation.py`

`aggregation.py` は、ひと言でいうと DBから取ってきた問い合わせデータに、表示・集計用の列を追加するファイルです。
`db.py` が「DBから生データを取る係」だとすると、`aggregation.py` は その生データを画面表示・KPI計算しやすい形に加工する係です。

### 1. なぜ必要か

DBには、基本的には元データだけを保存しています。
たとえば、DBにあるのはこういう列です。

```text
request_date
due_date
completed_date
status
management_minutes
actual_response_minutes
```

しかし、画面では次のような情報も見たいです。

```text
期限超過しているか
完了済みか
未完了か
対応に何日かかったか
受付月はいつか
管理作業時間は何時間か
```

これらは、DBに直接保存しなくても、既存の列から計算できます。その計算を担当するのが `aggregation.py` です。

### 2. `add_derived_columns()` の意味

```python
def add_derived_columns(df: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    result = df.copy()

    for col in ["request_date", "due_date", "completed_date"]:
        if col in result.columns:
            result[col] = pd.to_datetime(result[col], errors="coerce")

    today_ts = pd.Timestamp(today or date.today()).normalize()

    """以下、各種追加列の計算"""
    result["is_completed"] = result["status"].eq("完了")
    result["is_open"] = ~result["is_completed"]

    """後略"""

    return result
```

中心はこの関数です。これは、問い合わせ一覧のDataFrameに、派生列を追加します。たとえば、元のデータがこうだとします。

```text
request_date: 2026-06-20
due_date: 2026-06-25
completed_date: 空欄
status: 対応中
management_minutes: 30
```

今日が `2026-06-28` なら、`aggregation.py` はこういう列を追加します。

```text
is_completed: False
is_open: True
overdue_flag: True
response_days: 空欄
request_month: 2026-06
management_hours: 0.5
```

つまり、画面や集計で使いやすい形に変換しています。

### 3. 追加される列

主に以下を作っています。

| 追加列                  | 意味                           |
| ----------------------- | ------------------------------ |
| `is_completed`          | ステータスが「完了」なら True  |
| `is_open`               | 完了していないなら True        |
| `overdue_flag`          | 未完了かつ期限切れなら True    |
| `response_days`         | 受付日から完了日までの日数     |
| `request_month`         | 受付月。例：`2026-06`          |
| `management_hours`      | 管理作業時間を分から時間に変換 |
| `actual_response_hours` | 実対応時間を分から時間に変換   |

たとえば、KPIカードの「期限超過件数」は、`df["overdue_flag"].sum()`で計算できます。「未完了件数」は、`df["is_open"].sum()`で計算できます。
このように、先に列を作っておくと、画面側の処理がかなり簡単になります。

#### 日付の処理について

```python
for col in ["request_date", "due_date", "completed_date"]:
        if col in result.columns:
            result[col] = pd.to_datetime(result[col], errors="coerce")

    today_ts = pd.Timestamp(today or date.today()).normalize()
```

##### `pd.to_datetime(result[col], errors="coerce")`

たとえば、`"2026-06-28"`という文字列を、日付計算できる型に変換します。
`errors="coerce"` は、変換できない値があった場合にエラーで止めず、`NaT` にする指定です。`NaT` は日付版の欠損値のようなものです。

##### `pd.Timestamp(today or date.today()).normalize()`

これは、比較用の「今日の日付」を作っています。`today or date.today()` は、

```text
today が指定されていれば today を使う
today が None なら date.today() を使う
```

という意味です。

`.normalize()` は、時刻部分を `00:00:00` にそろえる処理です。たとえば、`2026-06-28 15:30:00`を、`2026-06-28 00:00:00`にします。これにより、`due_date < today_ts` のような期限超過判定がしやすくなります。

### 4. なぜDBに保存しないのか

`overdue_flag` や `response_days` は、DBに保存してもよさそうに見えます。でも、これは保存しない方が自然です。理由は、時間が経つと変わる値だからです。たとえば、今日が 2026-06-24 なら期限超過ではない案件でも、

```text
due_date = 2026-06-25
status = 対応中
```

今日が `2026-06-28` になると、期限超過になります。つまり、`overdue_flag` は毎日変わる可能性があります。だからDBに固定値として保存するより、画面を開いた時点で計算した方が安全です。

### 5. `format_date_columns_for_display()` の意味

もう一つの関数がこれです。

```python
def format_date_columns_for_display(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    for col in ["request_date", "due_date", "completed_date"]:
        if col in result.columns:
            result[col] = pd.to_datetime(result[col], errors="coerce").dt.strftime("%Y-%m-%d")
            result[col] = result[col].fillna("")

    return result
```

これは、日付列を画面表示用に整える関数です。pandasで日付を扱うと、表示がこうなることがあります。

```text
2026-06-28 00:00:00
```

でも、画面では普通にこう表示したいです。

```text
2026-06-28
```

そのために、表示前に日付列を `YYYY-MM-DD` 形式に整えています。

### 6. なぜ `app.py` に直接書かないのか

`app.py` に直接書いても動きます。ただし、そうすると `app.py` がどんどん重くなります。

```text
画面表示
フィルタ
KPI表示
日付変換
期限超過判定
対応日数計算
時間変換
```

これらが全部 `app.py` に入ると読みにくくなります。

そこで、

```text
app.py
  → 画面を作る

aggregation.py
  → 表示・集計用の加工をする
```

と分けています。

この分離によって、`app.py` は画面に集中できます。

### 7. WBS上の位置づけ

`aggregation.py` は、WBS4で作りましたが、実質的には WBS6 集計・判定処理の前倒しでもあります。

| WBS                    | 関係                                       |
| ---------------------- | ------------------------------------------ |
| WBS4 Streamlit基本画面 | KPIカードや期限超過表示に必要              |
| WBS6 集計・判定処理    | 期限超過判定、対応日数計算、時間集計の土台 |

つまり、WBS4では一覧画面を作るために最低限必要だったので、先に `aggregation.py` を作った、という位置づけです。

### 結論

`aggregation.py` は、DBから取った問い合わせデータを、画面表示・KPI・集計に使いやすい形へ加工するファイルです。役割を一文で言うと、`DBの生データに、期限超過・完了フラグ・対応日数・受付月・時間換算などの派生列を追加する。`です。
`db.py` は「保存・取得」、`aggregation.py` は「取得後の加工」、`app.py` は「画面表示」と考えると分かりやすいです。

## `app.py`

WBS4時点の `app.py` は、ひと言でいうと SQLiteに入っている問い合わせデータをStreamlitで表示するための画面ファイルです。
この時点では、まだ新規登録・更新は作っていません。主な役割は以下です。

```text
DBから問い合わせデータを読む
  ↓
pandas DataFrameにする
  ↓
期限超過などの派生列を追加する
  ↓
Streamlitで一覧・KPI・簡易集計を表示する
  ↓
部署・カテゴリ・担当者・ステータスなどで絞り込む
```

### 1. 全体構成

WBS4時点の `app.py` は、だいたい次の構造です。

```python
import ...

st.set_page_config(...)

@st.cache_data(ttl=10)
def load_inquiries():

def get_options(...):

def apply_filters(...):

def show_kpi_cards(...):

def show_inquiry_table(...):

def show_simple_summary(...):

def main():

if __name__ == "__main__":
    main()
```

関数ごとに役割を分けています。

### 2. `import`部分

| import                            | 役割                               |
| --------------------------------- | ---------------------------------- |
| `pandas`                          | DBから取ったデータを表形式で扱う   |
| `streamlit`                       | Web画面を作る                      |
| `add_derived_columns`             | 期限超過・完了フラグなどを追加する |
| `format_date_columns_for_display` | 日付を表示用に整える               |
| `fetch_all_inquiries`             | SQLiteから問い合わせ一覧を取得する |
| `init_db`                         | DBとテーブルを初期化する           |

つまり、`app.py` 自体はDBを直接操作せず、`db.py` や `aggregation.py` の関数を呼んでいます。

### 3. `st.set_page_config()`

```python
st.set_page_config(
    page_title="社内問い合わせ管理システム",
    layout="wide",
)
```

これはStreamlit画面の基本設定です。

| 項目            | 意味                   |
| --------------- | ---------------------- |
| `page_title`    | ブラウザタブのタイトル |
| `layout="wide"` | 横幅を広く使う         |

問い合わせ一覧は横に長い表なので、wide にしています。

### 4. `load_inquiries()`

```python
@st.cache_data(ttl=10)
def load_inquiries() -> pd.DataFrame:
    init_db()
    rows = fetch_all_inquiries()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = add_derived_columns(df)
    return df
```

これは、DBから問い合わせデータを読み込む関数です。
流れはこうです。

| 関数                      | 役割                               |
| ------------------------- | ---------------------------------- |
| `init_db()`               | DBがなければ作る                   |
| `fetch_all_inquiries()`   | SQLiteから全件取得する             |
| `pd.DataFrame(rows)`      | 辞書リストをDataFrameにする        |
| `add_derived_columns(df)` | 期限超過・完了フラグなどを追加する |

`@st.cache_data(ttl=10)` は、10秒間は同じ読み込み結果を使い回すという意味です。毎回DBを読みに行くと無駄なので、軽くキャッシュしています。

### 5. `get_options()`

```python
def get_options(df: pd.DataFrame, column: str) -> list[str]:
    if df.empty or column not in df.columns:
        return []

    values = (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return sorted([v for v in values.unique().tolist() if v])
```

これは、フィルタの選択肢を作る関数です。たとえば、`get_options(df, "department")`なら、DataFrame内の `department` 列から、

```text
営業部
業務部
施工管理部
管理部
```

のような選択肢を作ります。Streamlitの multiselect で使います。

#### 5-1. `values = (df[column].fillna("").astype(str).str.strip())`

元データ: `["営業部", None, " 管理部 ", "業務部"]`
処理後: `["営業部", "", "管理部", "業務部"]`

#### 5-2. `sorted([v for v in values.unique().tolist() if v])`

これは、重複なし・空欄なし・並び替え済みの選択肢リストを返しています。

`values.unique()`: 重複を消します。

```text
["営業部", "営業部", "管理部", "業務部"] → ["営業部", "管理部", "業務部"]
```

`.tolist()`: pandasの配列をPythonの普通のリストにします。

`[v for v in values.unique().tolist() if v]`: 空文字 `""` を除外します。`if v` は、ざっくり言うと「中身があるものだけ残す」という意味です。

最後に、`sorted(...)`で並び替えます。結果として、たとえばこうなります。

```text
["営業部", "業務部", "管理部"]
```

### 6. `apply_filters()`

これは、画面で選んだ条件に合わせてDataFrameを絞り込む関数です。

たとえば、

```text
部署 = 営業部
カテゴリ = PC・システム
ステータス = 未対応
期限超過のみ = True
```

のように選んだら、その条件に合う問い合わせだけを残します。

内部では、こういう処理をしています。

```python
filtered = filtered[filtered["department"].isin(departments)]
```

これは、`department列が、選択された部署に含まれる行だけ残す`という意味です。

たとえば、`departments = ["営業部", "管理部"]`だとします。
このとき、`filtered["department"].isin(departments)`は各行について、`department が 営業部 または 管理部` なら `True`、それ以外なら `False`を返します。そして、`filtered[ ... ]`で、`True` の行だけ残します。

### 7. `show_kpi_cards()`

これは、画面上部にKPIカードを表示する関数です。表示するのは以下です。

| KPI            | 内容                          |
| -------------- | ----------------------------- |
| 問い合わせ件数 | 表示中の問い合わせ総数        |
| 未完了件数     | `is_open` が True の件数      |
| 完了件数       | `is_completed` が True の件数 |
| 期限超過件数   | `overdue_flag` が True の件数 |
| 管理作業時間   | `management_hours` の合計     |

たとえば、`open_count = int(df["is_open"].sum())`は、未完了件数を数えています。`True` は集計上 `1` として扱われるので、`sum()` で件数になります。

### 8. `show_inquiry_table()`

これは、問い合わせ一覧の表を表示する関数です。まず、表示する列を選びます。

```python
display_columns = [
    "request_id",
    "request_date",
    ...
]
```

その後、存在する列だけを取り出します。

```python
existing_columns = [col for col in display_columns if col in df.columns]
display_df = df[existing_columns].copy()
```

これは、列が存在しない場合のエラー防止です。

最後に、`st.dataframe(...)`でStreamlit上に表として表示します。また、`column_config` を使って、英語のカラム名を日本語表示に変えています。

### 9. `show_simple_summary()`

これは、確認用の簡易集計を表示する関数です。
WBS4時点では、本格的なCSV出力やTableau連携はまだ作っていません。その代わり、Streamlit上で簡単な集計を見られるようにしています。表示する集計は以下です。

| 集計             | 内容                  |
| ---------------- | --------------------- |
| カテゴリ別件数   | `category` ごとの件数 |
| 担当者別件数     | `assignee` ごとの件数 |
| ステータス別件数 | `status` ごとの件数   |
| 受付経路別件数   | `channel` ごとの件数  |

たとえば、`df["category"].value_counts()`は、カテゴリごとの件数を数えています。

### 10. `main()`

`main()` は、画面全体を組み立てる本体です。最初にタイトルを表示します。

```python
st.title("社内問い合わせ管理システム")
```

次に、DBからデータを読み込みます。

```python
df = load_inquiries()
```

その後、4つのタブを作ります。

```python
tab_list, tab_create, tab_update, tab_summary = st.tabs(
    [
        "問い合わせ一覧",
        "新規登録",
        "ステータス更新",
        "集計・CSV出力",
    ]
)
```

WBS4時点では、実際に動くのは主に以下です。

| タブ           | WBS4時点の状態             |
| -------------- | -------------------------- |
| 問い合わせ一覧 | 実装済み                   |
| 新規登録       | 「次フェーズで実装」と表示 |
| ステータス更新 | 「次フェーズで実装」と表示 |
| 集計・CSV出力  | 簡易集計のみ表示           |

つまり、WBS4時点では 閲覧・確認用の画面です。

### 11. 問い合わせ一覧タブの流れ

問い合わせ一覧タブでは、以下の順で処理します。

```text
DBから読み込んだdfを使う
↓
データが空なら警告を出す
↓
フィルタUIを表示する
↓
選択された条件でdfを絞り込む
↓
KPIを表示する
↓
問い合わせ一覧表を表示する
```

コード上では、だいたいこういう流れです。

```python
filtered_df = apply_filters(...)

show_kpi_cards(filtered_df)

show_inquiry_table(filtered_df)
```

ポイントは、KPIも一覧も 絞り込み後の `filtered_df` を使っていることです。だから、たとえば「原田 健太」で絞ると、KPIも原田担当分だけになります。

### 12. 最後の部分

```python
if __name__ == "__main__":
    main()
```

これは、このファイルを直接実行したときに `main()` を動かすという意味です。Streamlitでは、

```bash
streamlit run app.py
```

で実行するので、この `main()` が呼ばれて画面が作られます。

### まとめ

WBS4時点の `app.py` は、問い合わせ管理システムの閲覧画面です。主な役割は以下です。

```text
SQLiteから問い合わせデータを取得する
DataFrameに変換する
期限超過などの派生列を追加する
部署・カテゴリ・担当者・ステータスで絞り込む
KPIカードを表示する
問い合わせ一覧を表示する
簡易集計を表示する
```

ただし、この時点ではまだ、

```text
新規登録
ステータス更新
CSV出力
Tableau連携
```

は本実装されていません。
つまり、WBS4の `app.py` は、DBに入った問い合わせデータを見える化するための最初の画面です。
