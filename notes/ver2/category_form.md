# WBS5 学習ログ：カテゴリ別入力フォーム

## 1. 目的

カテゴリ別入力フォームの目的は、管理部と依頼者の確認往復を減らすことである。DX化前や初期版では、問い合わせ内容だけでは状況が分からず、管理部が後から追加確認することがあった。

例：

- 「PCが使えません」だけでは、どのPCか、どんなエラーか分からない
- 「勤怠を修正したい」だけでは、対象日や修正前後の時刻が分からない
- 「権限を追加してください」だけでは、対象システムや必要権限が分からない

そこで、カテゴリごとに必要情報を入力できるようにした。

## 2. 追加したカテゴリ別項目

今回のWBS5では、以下のカテゴリに対して追加入力項目を設定した。

| カテゴリ         | 追加項目                                                 |
| ---------------- | -------------------------------------------------------- |
| PC・システム     | PC管理番号、発生時刻、エラー内容、再起動有無             |
| アカウント・権限 | 対象システム、対象フォルダ・対象機能、必要な権限、承認者 |
| 勤怠・労務       | 対象日、修正前時刻、修正後時刻、理由                     |
| 経費・請求       | 金額、取引先、対象月、添付書類有無                       |
| 備品・設備       | 備品名・設備名、数量、利用目的、希望日                   |

これにより、カテゴリに応じて入力すべき情報が明確になった。

## 3. dataclass について

`src/category_fields.py` では、カテゴリ別項目を表すために `dataclass` を使った。

```python
@dataclass(frozen=True)
class CategoryField:
    """カテゴリ別追加項目の定義。"""

    key: str
    label: str
    field_type: str = "text"
    options: tuple[str, ...] = ()
```

`dataclass` は、データをまとめて持つためのクラスを簡単に作れる仕組みである。今回の `CategoryField` は、1つの入力項目について以下を持っている。

| 属性         | 内容                       |
| ------------ | -------------------------- |
| `key`        | プログラム内部で使う項目名 |
| `label`      | 画面に表示する項目名       |
| `field_type` | 入力欄の種類               |
| `options`    | selectbox用の選択肢        |

たとえば、以下のように書く。

```python
CategoryField("pc_asset_id", "PC管理番号")
CategoryField("error_detail", "エラー内容", field_type="text_area")
CategoryField("reboot_done", "再起動有無", field_type="select", options=("未確認", "実施済み", "未実施"))
```

これにより、入力項目をデータとして扱えるようになる。

### 3-1. `frozen=True` の意味

`dataclass(frozen=True)` とすると、そのインスタンスは作成後に変更できなくなる。
今回のカテゴリ別項目定義は、アプリ実行中に変更するものではない。そのため、誤って値を書き換えないように `frozen=True` にした。これは、設定値や定義情報を安全に扱うための書き方である。

## 4. `CATEGORY_FIELDS` の役割

`CATEGORY_FIELDS` は、カテゴリごとの追加項目をまとめた辞書である。

```python
CATEGORY_FIELDS: dict[str, list[CategoryField]] = {
    "PC・システム": [
        CategoryField("pc_asset_id", "PC管理番号"),
        CategoryField("occurred_at", "発生時刻"),
        CategoryField("error_detail", "エラー内容", field_type="text_area"),
        CategoryField("reboot_done", "再起動有無", field_type="select", options=("未確認", "実施済み", "未実施")),
    ],
}
```

構造としては以下である。

```text
カテゴリ名
  ↓
そのカテゴリで表示する入力項目リスト
```

このようにしておくことで、カテゴリを選択したときに対応する入力項目を取り出せる。

## 5. `additional_info` に保存する設計

WBS2で、`inquiries` テーブルに `additional_info` カラムを追加していた。WBS5では、この `additional_info` にカテゴリ別追加情報を保存する。
本格的なDB設計であれば、カテゴリごとに別テーブルを作ったり、JSON形式で保存したりする方法もある。しかし、Ver.2では以下の理由から、複数行テキストとして保存する設計にした。

- 実装がシンプル
- SQLiteで扱いやすい
- Streamlit上で表示しやすい
- カテゴリ別項目が少数である

つまり、Ver.2では複雑なデータ構造よりも、業務改善の流れが分かることを優先した。

## 6. `render_category_additional_fields()` の役割

`render_category_additional_fields()` は、カテゴリに応じた追加項目を画面に表示し、入力内容を保存用テキストとして返す関数である。
主な流れは以下である。

```text
カテゴリを受け取る
↓
get_category_fields() で追加項目定義を取得
↓
field_type に応じて Streamlit ウィジェットを表示
↓
入力値を values にまとめる
↓
format_additional_info() で複数行テキストに変換
↓
additional_info として返す
```

この関数を作ったことで、`show_create_form()` の中にカテゴリ別項目の表示処理を直接書きすぎずに済む。

## 7. `widget_key` の役割

カテゴリ別入力項目では、各ウィジェットに `key` を付けた。

```python
widget_key = f"create_additional_{category}_{field.key}"
```

Streamlitでは、同じ種類のウィジェットが複数ある場合、それぞれを識別するために `key` が必要になることがある。今回のように、カテゴリ別に複数の `text_input` や `text_area` を表示する場合、`key` を明示しておくと安全である。`key` を付けることで、Streamlitが各入力欄を区別できる。

## 8. DB保存確認

新規登録後、DBに `additional_info` が保存されているか確認した。

```bash
python - << 'EOF'
import sqlite3
from pathlib import Path

db_path = Path("data/inquiry.db")

with sqlite3.connect(db_path) as conn:
    rows = conn.execute("""
        SELECT
            request_id,
            category,
            additional_info
        FROM inquiries
        WHERE additional_info != ''
        ORDER BY created_at DESC
        LIMIT 5;
    """).fetchall()

for row in rows:
    print("request_id:", row[0])
    print("category:", row[1])
    print("additional_info:")
    print(row[2])
    print("-" * 40)
EOF
```

期待する表示例は以下である。

```text
request_id: REQ-20260702-001
category: PC・システム
additional_info:
PC管理番号: PC-014
発生時刻: 09:30
エラー内容: 販売管理システム起動時に認証エラー
再起動有無: 実施済み
```

このように表示されれば、カテゴリ別追加情報がDBに保存されている。

## 9. 今後の実装とのつながり

WBS5で追加した `additional_info` は、今後以下に展開できる。

| 今後の機能                 | つながり                                       |
| -------------------------- | ---------------------------------------------- |
| 依頼者向け確認画面         | 依頼者が自分の追加情報も確認できる             |
| Tableau出力                | カテゴリ別追加情報をCSVに含められる            |
| 入力品質分析               | 追加情報が入力されているかを分析できる         |
| FAQ候補管理                | 追加情報をもとにFAQ回答案を整理しやすくなる    |
| 添付ファイル対応           | 将来的にエラー画面や証憑資料の添付へ発展できる |
| カテゴリ別テンプレート改善 | 問い合わせ実績をもとに追加項目を見直せる       |

WBS5では、問い合わせを単に受け付けるだけでなく、カテゴリに応じて必要情報を集める仕組みを追加した。これにより、問い合わせ管理アプリは「記録するアプリ」から、「確認の往復を減らす業務改善アプリ」へ一段階発展した。
