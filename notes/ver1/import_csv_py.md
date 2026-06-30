# import_csv.pyファイルの役割

`import_csv.py` は、ひと言でいうと CSVファイルを読み込んで、SQLiteのDBに取り込むためのファイルです。

今回の流れでは、ここを担当しています。

```text
data/inquiry_dx_before_sample.csv
  ↓
src/import_csv.py
  ↓
src/db.py の upsert_inquiries()
  ↓
data/inquiry.db
```

つまり、CSV → DB の橋渡し役です。

## 1. 全体の役割

`import_csv.py` がやっていることは主に3つです。

| 処理             | 内容                                      |
| ---------------- | ----------------------------------------- |
| CSVを読む        | `pandas.read_csv()` でCSVを読み込む       |
| DB用に整える     | 足りない列を補い、余分な列を落とす        |
| SQLiteへ登録する | `upsert_inquiries()` を使ってDBに保存する |

## 2. 冒頭の`import`

```python
import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db import BASE_DIR, COLUMNS, init_db, upsert_inquiries
```

ここでは必要な道具を読み込んでいます。

| import | 役割 |
| ------------------ | ------------------------------------ |
| `argparse` | ターミナルからCSVパスを指定できるようにする |
| `datetime` | `created_at`, `updated_at` 用の現在時刻を作る |
| `Path` | ファイルパスを扱いやすくする |
| `pandas` | CSVを読み込む |
| `BASE_DIR` | プロジェクトの基準フォルダ |
| `COLUMNS` | DBに必要なカラム一覧 |
| `init_db` | DB初期化 |
| `upsert_inquiries` | 複数件をDB登録・更新 |

## 3. `DEFAULT_CSV_PATH`

```python
DEFAULT_CSV_PATH = BASE_DIR / "data" / "inquiry_dx_before_sample.csv"
```

これは、標準で読み込むCSVの場所です。つまり、何も指定せずに、

```bash
python -m src.import_csv
```

を実行すると、`data/inquiry_dx_before_sample.csv`を読み込みます。

## 4. `load_csv()` の役割

```python
def load_csv(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for col in COLUMNS:
        if col not in df.columns:
            if col in {"created_at", "updated_at"}:
                df[col] = now
            elif col in {"management_minutes", "actual_response_minutes"}:
                df[col] = 0
            else:
                df[col] = ""

    df = df[COLUMNS]
    df = df.fillna("")
    return df.to_dict(orient="records")
```

これは、CSVを読み込んで、DB登録用のデータに変換する関数です。中身の流れはこうです。

```text
CSVファイルが存在するか確認
  ↓
pandasでCSVを読む
  ↓
DBに必要な列がなければ追加する
  ↓
DBに不要な列は落とす
  ↓
欠損値を空文字にする
  ↓
辞書のリストに変換する
```

### 4-1. 足りない列を補う

```python
for col in COLUMNS:
    if col not in df.columns:
        if col in {"created_at", "updated_at"}:
            df[col] = now
        elif col in {"management_minutes", "actual_response_minutes"}:
            df[col] = 0
        else:
            df[col] = ""
```

ここが重要です。CSVにDBで必要な列が全部あるとは限りません。たとえば、CSVに `created_at` がない場合があります。

そのときに、

| 足りない列                                      | 補う値      |
| ----------------------------------------------- | ----------- |
| `created_at`, `updated_at`                      | 現在時刻    |
| `management_minutes`, `actual_response_minutes` | `0`         |
| その他                                          | 空文字 `""` |

を入れます。つまり、CSVの列が多少足りなくてもDBに入れられる形に整える処理です。

### 4-2. 辞書のリストに変換する

```python
return df.to_dict(orient="records")
```

これは、DataFrameを「1行 = 1辞書」のリストに変換します。たとえば、こういう表があるとします。

| request_id | requester | status |
| ---------- | --------- | ------ |
| REQ-001    | 田口 航   | 未対応 |
| REQ-002    | 山下 颯太 | 完了   |

これをこう変換します。

```python
[
    {"request_id": "REQ-001", "requester": "田口 航", "status": "未対応"},
    {"request_id": "REQ-002", "requester": "山下 颯太", "status": "完了"},
]
```

この形にすると、`upsert_inquiries()` に渡しやすくなります。

## 5. `main()` の役割

```python
def main() -> None:
    parser = argparse.ArgumentParser(description="問い合わせCSVをSQLiteに取り込む")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=str(DEFAULT_CSV_PATH),
        help="取り込むCSVファイルのパス",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)

    init_db()
    records = load_csv(csv_path)
    count = upsert_inquiries(records)

    print(f"CSVを取り込みました: {csv_path}")
    print(f"登録・更新件数: {count}件")
```

`main()` は、実際にコマンドとして実行したときの処理本体です。流れはこうです。

```text
コマンドライン引数を読む
  ↓
CSVパスを決める
  ↓
DBを初期化する
  ↓
CSVを読み込む
  ↓
DBに登録する
  ↓
結果を表示する
```

### 5-1. `argparse` の意味

```python
parser = argparse.ArgumentParser(description="問い合わせCSVをSQLiteに取り込む")
parser.add_argument(
    "csv_path",
    nargs="?",
    default=str(DEFAULT_CSV_PATH),
    help="取り込むCSVファイルのパス",
)
```

これは、ターミナルから読み込むCSVを指定できるようにする処理です。何も指定しなければ、標準のCSVを読みます。

```bash
python -m src.import_csv
```

別のCSVを指定することもできます。

```nash
python -m src.import_csv data/other_sample.csv
```

`nargs="?"` は、引数があってもなくてもよいという意味です。

**parser.add_argument()**
これは、受け取る引数のルールを登録する処理です。ここでは、`csv_path という名前の引数を受け取れるようにする`という意味です。

**parser.parse_args()**
これは、実際にターミナルから渡された引数を読み取る処理です。たとえば、

```bash
python -m src.import_csv data/other_sample.csv
```

と実行すると、`parse_args()` が `data/other_sample.csv` を読み取ります。そして、結果を `args` に入れます。

## 6. 最後の部分

```python
if __name__ == "__main__":
    main()
```

これは、`このファイルを直接実行したときだけ main() を動かす`、という意味です。つまり、

```bash
python -m src.import_csv
```

と実行したときは `main()` が動きます。
一方、別ファイルから関数だけ読み込む場合は、勝手にCSV取込は走りません。

## まとめ

`import_csv.py` は、CSV取込専用の実行ファイルです。

役割はこうです。

```text
CSVを読む
  ↓
DBに必要な列をそろえる
  ↓
欠損を整える
  ↓
辞書リストに変換する
  ↓
db.py の upsert_inquiries() でSQLiteに保存する
```

`db.py` が「DB操作の部品」だとすると、`import_csv.py` はその部品を使って、CSVから初期データを投入するための入口です。
