# WBS3 学習ログ：要対応アラート機能

## 1. 今回やったこと

WBS3では、問い合わせ管理アプリに「要対応アラート」機能を追加した。判定対象は以下である。

| アラート種別   | 内容                             |
| -------------- | -------------------------------- |
| 期限超過       | 未完了で希望期限を過ぎている     |
| 本日期限       | 未完了で希望期限が今日           |
| 期限間近       | 未完了で希望期限が明日まで       |
| 担当者未設定   | 担当者が空欄                     |
| 情報待ち長期化 | 情報待ち状態が一定日数続いている |

## 2. `fetch_all_inquiries()` の返り値

今回のエラーで重要だったのは、`fetch_all_inquiries()` の返り値である。この関数は、pandasのDataFrameではなく、`list[dict]` を返す。
つまり、取得結果は以下のような形である。

```python
[
    {"request_id": "REQ-20260701-001", "status": "対応中", ...},
    {"request_id": "REQ-20260701-002", "status": "完了", ...},
]
```

一方で、アラート判定では `df.empty` や `df.columns` のようなDataFrame用の処理を使う。そのため、`list[dict]` をそのまま渡すとエラーになる。
そこで、`add_alert_columns()` の冒頭で以下のようにDataFrameへ変換した。

```python
result = pd.DataFrame(df).copy()
```

これにより、`df` が `list[dict]` でも `pd.DataFrame` でも、アラート判定処理ではDataFrameとして扱えるようになった。

## 3. 日付比較のための変換

```python
pd.to_datetime(df[column], errors="coerce").dt.normalize()
```

この処理の意味は以下である。

| 処理               | 意味                                 |
| ------------------ | ------------------------------------ |
| `pd.to_datetime()` | 文字列を日付型に変換する             |
| `errors="coerce"`  | 変換できない値は `NaT` にする        |
| `.dt.normalize()`  | 時刻情報を落として日付だけにそろえる |

`NaT` は、pandasにおける日付版の欠損値である。変換できない日付があってもエラーで止めず、判定対象から外せるようにしている。

## 4. `has_alert` の意味

`has_alert` は、何らかのアラートに該当するかどうかを表す列である。以下のように、アラート列のうち1つでもTrueなら `has_alert` をTrueにする。

```python
result["has_alert"] = result[alert_columns].any(axis=1)
```

`any(axis=1)` は、行方向に見て1つでもTrueがあるかを判定する。

## 5. `filter_alerts()` の役割

`filter_alerts()` は、アラート種別で問い合わせを絞り込む関数である。たとえば、画面で「期限超過」を選択したら、期限超過の問い合わせだけを表示する。

```python
display_df = filter_alerts(alert_df, selected_alert)
```

`selected_alert` が `"すべて"` の場合は、何らかのアラートを持つ問い合わせをすべて表示する。それ以外の場合は、対応するアラート列がTrueの行だけを表示する。

## 6. `get_alert_display_columns()` の役割

`get_alert_display_columns()` は、アラート一覧画面で表示する列を決める関数である。データに存在する列だけを返すようにしている。

```python
return [col for col in columns if col in df.columns]
```

これにより、存在しない列を表示しようとしてエラーになることを防いでいる。

## 7. 今回発生したエラー

今回、以下のエラーが発生した。

```text
AttributeError: 'list' object has no attribute 'empty'
```

原因は、`add_alert_columns()` に渡していたデータがDataFrameではなく、`list[dict]` だったこと。`fetch_all_inquiries()` は `list[dict]` を返すため、そのままでは `df.empty` が使えない。修正として、`add_alert_columns()` の冒頭を以下のようにした。

```python
result = pd.DataFrame(df).copy()
```

これにより、DataFrameでもlistでも処理できるようになった。また、型注釈も以下のように変更した。

```python
df: pd.DataFrame | list[dict]
```

これにより、この関数がDataFrameだけでなく辞書リストも受け取れることが分かりやすくなった。

## 8. 動作確認の方法

アラート機能の確認では、以下を実行した。

### 構文確認

```bash
python -m py_compile src/alerts.py app.py
```

### アラート集計の確認

```bash
python - << 'EOF'
from src.db import fetch_all_inquiries
from src.alerts import add_alert_columns, summarize_alerts

records = fetch_all_inquiries()
print(type(records))

alert_df = add_alert_columns(records)
print(type(alert_df))

print(summarize_alerts(alert_df))
EOF
```

期待する型は以下である。

```text
<class 'list'>
<class 'pandas.core.frame.DataFrame'>
```

これは、DB取得時点ではlistだが、アラート判定後はDataFrameになっていることを示している。

## 9. 今後の実装とのつながり

WBS3で作成したアラート機能は、今後以下に展開できる。

| 今後の機能             | つながり                                            |
| ---------------------- | --------------------------------------------------- |
| 集計画面更新           | アラート件数を集計に追加できる                      |
| Tableau出力更新        | `has_alert` や `alert_type` をCSVに出力できる       |
| 管理部向け優先順位付け | 要対応案件を先に表示できる                          |
| 通知機能               | 将来的に期限超過・期限間近をメールやSlack通知できる |
| 操作改善               | 期限超過や未担当案件の見落としを減らせる            |

WBS3では、Ver.2の中でも「画面上で改善が見えやすい機能」を実装した。
DB構造の追加だけだったWBS2と比べて、WBS3では実際にユーザーが確認できる機能として、問い合わせ管理の実用性が高まった。
