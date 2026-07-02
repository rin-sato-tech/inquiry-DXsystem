# WBS4 学習ログ：FAQ候補管理機能

## 1. 今回やったこと

WBS4では、問い合わせ管理アプリに「FAQ候補管理機能」を追加した。

初期版では、問い合わせを登録・更新・集計することはできたが、完了済み問い合わせを次の業務改善に活用する仕組みは弱かった。

Ver.2では、完了済み問い合わせの中から「よくある問い合わせ」としてFAQ化できそうなものを選び、FAQ候補として蓄積できるようにした。

実装した主な機能は以下である。

| 機能           | 内容                                |
| -------------- | ----------------------------------- |
| FAQ候補選択    | 完了済み問い合わせからFAQ候補を選ぶ |
| FAQ候補保存    | FAQタイトル・FAQ回答案を保存する    |
| FAQ候補更新    | 既存のFAQ候補情報を上書き更新する   |
| FAQ候補解除    | FAQ候補一覧から外す                 |
| FAQ候補一覧    | FAQ候補だけを一覧表示する           |
| カテゴリ別集計 | FAQ候補をカテゴリ別に集計する       |
| CSV出力        | FAQ候補をCSVでダウンロードする      |

## 2. FAQ候補管理の位置づけ

今回の機能は、FAQ公開ページを作るものではない。あくまで、問い合わせ対応履歴からFAQ化できそうなものを管理部が選び、候補として蓄積する段階である。
流れとしては以下である。

```text
問い合わせが完了する
↓
管理部がFAQ化できそうな問い合わせを選ぶ
↓
FAQタイトル・回答案を整理する
↓
FAQ候補一覧に蓄積する
↓
将来的にFAQページやナレッジベースへ展開する
```

つまり、WBS4は「問い合わせ管理」から「問い合わせ削減・自己解決支援」へ発展するための土台である。

また、本格運用であれば、FAQ専用テーブルを作る方が自然である。この構成にすると、FAQを問い合わせ履歴から独立して管理できる。
しかし、Ver.2の目的はFAQ公開システムを作ることではなく、問い合わせ履歴からFAQ候補を蓄積することである。そのため、今回はシンプルに `inquiries` テーブル上でFAQ候補情報を管理する設計にした。Ver.3以降でFAQ公開ページを作る場合は、`faqs` テーブルを新設する方針とする。

## 3. `to_faq_csv_bytes()` の役割

`to_faq_csv_bytes()` は、FAQ候補をCSVダウンロードできる形に変換する関数である。
Streamlitの `st.download_button()` では、CSVデータを文字列やbytesとして渡す必要がある。そのため、`StringIO` を使ってCSV文字列を作り、最後にbytesへ変換している。

```python
buffer = io.StringIO()
output_df.to_csv(buffer, index=False, encoding="utf-8-sig")
return buffer.getvalue().encode("utf-8-sig")
```

`utf-8-sig` を使う理由は、Excelで開いたときの文字化けを防ぎやすくするためである。

## 4. `st.session_state` を使ったメッセージ表示

当初は、保存後に以下のようにメッセージを表示していた。

```python
st.success("FAQ候補として保存しました。")
st.rerun()
```

しかし、この書き方だと、メッセージを表示した直後に `st.rerun()` で画面が再描画される。そのため、成功メッセージが一瞬しか表示されなかった。
これを改善するために、`st.session_state` を使った。保存時には、メッセージを `st.session_state` に入れる。

```python
st.session_state["faq_message"] = "FAQ候補として保存しました。"
st.rerun()
```

画面の先頭では、そのメッセージを取り出して表示する。

```python
if "faq_message" in st.session_state:
    st.success(st.session_state.pop("faq_message"))
```

これにより、再描画後も成功メッセージを表示できる。

## 5. selectbox の format_func

FAQ候補として編集する問い合わせを選ぶとき、`st.selectbox()` を使った。ただし、選択肢として問い合わせIDだけを表示しても分かりにくい。そこで、`format_func` を使い、画面上では以下のようなラベルで表示する設計にした。

```text
REQ-20260701-001｜PC・システム｜販売管理システムにログインできない
```

内部的には `request_id` を保持し、表示だけを分かりやすくしている。

```python
selected_request_id = st.selectbox(
    "FAQ候補として編集する問い合わせ",
    request_ids,
    format_func=format_inquiry_label,
)
```

このようにすると、DB更新時には正確なIDを使いながら、ユーザーには内容が分かりやすい選択肢を見せられる。

## 6. 今回の動作確認

WBS4では、以下を確認した。

### 構文確認

```bash
python -m py_compile src/faq.py app.py
```

### FAQ関数の確認

```bash
python - << 'EOF'
from src.db import fetch_all_inquiries
from src.faq import add_faq_columns, get_completed_inquiries, get_faq_candidates, summarize_faq_candidates

records = fetch_all_inquiries()
faq_df = add_faq_columns(records)

print("全件:", len(faq_df))
print("完了済み:", len(get_completed_inquiries(faq_df)))
print("FAQ候補:", len(get_faq_candidates(faq_df)))
print(summarize_faq_candidates(faq_df))
EOF
```

## 7. 今後の実装とのつながり

WBS4で作成したFAQ候補管理機能は、今後以下に展開できる。

| 今後の機能         | つながり                                 |
| ------------------ | ---------------------------------------- |
| FAQ公開ページ      | FAQ候補を依頼者向けに公開する            |
| FAQ検索            | タイトルや回答案から検索できるようにする |
| FAQ専用テーブル    | 問い合わせ履歴から独立してFAQを管理する  |
| FAQ編集履歴        | FAQ回答案の変更履歴を残す                |
| Tableau出力        | FAQ候補件数やカテゴリ別件数を可視化する  |
| 問い合わせ削減分析 | FAQ候補が多いカテゴリを改善対象にする    |

WBS4では、問い合わせ対応履歴を単なる記録で終わらせず、次の業務改善に活かす仕組みを追加した。
